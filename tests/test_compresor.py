"""Tests para el script unificado src/compresor.py (sugerencia 6.4 de sugerencias.md).

Los tests nunca invocan WinRAR real: subprocess.run se simula con un
side_effect que crea un archivo zip falso.
"""

from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

import compresor
from compresor import (
    PERFILES,
    Agrupacion,
    Config,
    agrupar_por_tamano,
    destino_listado,
    descubrir_archivos,
    empacar_grupos,
    escribir_output,
    ruta_segura,
    validar_tamanos,
    zip_files_with_winrar,
)


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    """Configuracion de prueba con rutas aisladas en tmp_path."""
    return Config(
        limite_grupo=3_990_000,
        limite_reempacado=3_900_000,
        limite_arch_origen=4_200_000,
        winrar_ruta=tmp_path / "WinRAR.exe",
        log_dir=tmp_path / "logs",
        wrkdir=tmp_path,
    )


@pytest.fixture
def log() -> logging.Logger:
    return logging.Logger("tests", level=logging.INFO)


def crear_archivos(ruta_carpeta: Path, tamanos: dict[str, int]) -> None:
    """Crea archivos de prueba con tamanos exactos."""
    for nombre, tamano in tamanos.items():
        ruta = ruta_carpeta / nombre
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(b"x" * tamano)


class TestDescubrirArchivos:
    def test_excluye_zip_bloqueos_y_vacios(self, tmp_path: Path, log) -> None:
        crear_archivos(
            tmp_path,
            {
                "a.txt": 100,
                "sin_extension": 50,
                "b.zip": 1_000,
                "~$c.xlsx": 10,
                "vacio.txt": 0,
                "sub/d.pdf": 200,
            },
        )
        archivos = descubrir_archivos(tmp_path)
        nombres = {a.name for a in archivos}
        assert nombres == {"a.txt", "sin_extension", "d.pdf"}

    def test_incluye_archivos_sin_extension(self, tmp_path: Path, log) -> None:
        crear_archivos(tmp_path, {"sin_extension": 50})
        archivos = descubrir_archivos(tmp_path)
        assert len(archivos) == 1

    def test_recursivo(self, tmp_path: Path, log) -> None:
        crear_archivos(tmp_path, {"sub/subsub/profundo.txt": 10})
        archivos = descubrir_archivos(tmp_path)
        assert len(archivos) == 1


class TestValidarTamanos:
    def test_ok_sin_excedidos(self, cfg: Config) -> None:
        validar_tamanos({Path("a.txt"): 100}, cfg)

    def test_aborta_con_archivo_excedido(self, cfg: Config) -> None:
        with pytest.raises(SystemExit):
            validar_tamanos({Path("grande.pdf"): cfg.limite_arch_origen + 1}, cfg)


class TestRutaSegura:
    def test_ruta_corta_sin_prefijo(self) -> None:
        assert ruta_segura("C:\\datos\\a.txt") == "C:\\datos\\a.txt"

    def test_ruta_larga_con_prefijo(self) -> None:
        larga = "relativa/" + "/".join("carpeta" for _ in range(40))
        resultado = ruta_segura(larga)
        assert resultado.startswith("\\\\?\\")


class TestAgruparPorTamano:
    @pytest.fixture
    def winrar_falso(self, monkeypatch):
        """Sustituye subprocess.run: crea un zip falso y no invoca WinRAR."""
        llamadas: list[list[str]] = []

        def fake_run(comando, **kwargs):
            llamadas.append(list(map(str, comando)))
            ruta_salida = next(p for p in comando if str(p).endswith(".zip"))
            Path(ruta_salida).write_bytes(b"zip-falso")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(compresor.subprocess, "run", fake_run)
        return llamadas

    def test_todos_los_archivos_quedan_en_algun_grupo(self, tmp_path, cfg, log, winrar_falso):
        crear_archivos(tmp_path, {"a.txt": 3_000_000, "b.txt": 2_500_000, "c.txt": 1_000_000})
        archivos = descubrir_archivos(tmp_path)
        agrupacion = agrupar_por_tamano(archivos, tmp_path, cfg, log)
        colocados = [a for grupo in agrupacion.grupos for a in grupo]
        assert sorted(colocados) == sorted(archivos)

    def test_ningun_grupo_supera_el_limite(self, tmp_path, cfg, log, winrar_falso):
        tamanos = {f"f{i}.txt": t for i, t in enumerate((3_000_000, 2_500_000, 1_000_000, 900_000))}
        crear_archivos(tmp_path, tamanos)
        archivos = descubrir_archivos(tmp_path)
        agrupacion = agrupar_por_tamano(archivos, tmp_path, cfg, log)
        assert all(tamano <= cfg.limite_grupo for tamano in agrupacion.tamanos)

    def test_dos_recorridos_separan_pequenos(self, tmp_path, cfg, log, winrar_falso):
        crear_archivos(tmp_path, {"grande.txt": 3_000_000, "pequeno.txt": 10_000})
        archivos = descubrir_archivos(tmp_path)
        agrupacion = agrupar_por_tamano(archivos, tmp_path, cfg, log)
        # El pequeno cabe en el grupo del grande en el segundo recorrido
        assert len(agrupacion.grupos) == 1

    def test_dry_run_no_invoca_subprocess(self, tmp_path, cfg, log, monkeypatch):
        crear_archivos(tmp_path, {"a.txt": 100_000})

        def fallar(*args, **kwargs):
            raise AssertionError("subprocess.run no debe invocarse en dry-run")

        monkeypatch.setattr(compresor.subprocess, "run", fallar)
        archivos = descubrir_archivos(tmp_path)
        agrupar_por_tamano(archivos, tmp_path, cfg, log, dry_run=True)


class TestEmpacarGrupos:
    @pytest.fixture
    def winrar_falso(self, monkeypatch, tmp_path):
        llamadas: list[list[str]] = []

        def fake_run(comando, **kwargs):
            llamadas.append(list(map(str, comando)))
            ruta_salida = next(p for p in comando if str(p).endswith(".zip"))
            Path(ruta_salida).write_bytes(b"zip-falso")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(compresor.subprocess, "run", fake_run)
        return llamadas

    def test_lotes_de_max_files_per_iteration(self, tmp_path, cfg, log, winrar_falso):
        crear_archivos(tmp_path, {f"f{i:03}.txt": 10 for i in range(250)})
        archivos = descubrir_archivos(tmp_path)
        grupos = [[a for a in archivos if a.name.startswith("f")]]
        tamanos = [sum(archivos.values())]
        empaquetados: set[int] = set()

        empacar_grupos(grupos, tamanos, empaquetados, tmp_path / "carpeta", cfg, log)

        assert len(winrar_falso) == 2  # 250 archivos / 200 por lote = 2 llamadas
        assert tamanos[0] > 0
        assert 0 in empaquetados

    def test_omite_grupos_ya_empaquetados(self, tmp_path, cfg, log, winrar_falso):
        grupos = [[tmp_path / "a.txt"]]
        empacar_grupos(grupos, [10], {0}, tmp_path / "carpeta", cfg, log)
        assert winrar_falso == []

    def test_final_reempaca_todos(self, tmp_path, cfg, log, winrar_falso):
        ruta_zip = tmp_path / "carpeta-0000.zip"
        ruta_zip.write_bytes(b"zip-viejo")
        grupos = [[tmp_path / "a.txt"]]
        empaquetados = {0}

        empacar_grupos(grupos, [10], empaquetados, tmp_path / "carpeta", cfg, log, final=True)

        assert len(winrar_falso) == 1
        assert ruta_zip.exists()  # recreado por el WinRAR falso
        assert ruta_zip.read_bytes() == b"zip-falso"

    def test_dry_run_no_invoca_winrar(self, tmp_path, cfg, log):
        crear_archivos(tmp_path, {"a.txt": 10})
        grupos = [[tmp_path / "a.txt"]]
        empaquetados: set[int] = set()

        empacar_grupos(grupos, [10], empaquetados, tmp_path / "carpeta", cfg, log, dry_run=True)

        assert not (tmp_path / "carpeta-0000.zip").exists()
        assert 0 in empaquetados

    def test_fallo_de_winrar_lanza_systemexit(self, tmp_path, cfg, log, monkeypatch):
        def fake_run(comando, **kwargs):
            return SimpleNamespace(returncode=1, stdout="", stderr="fallo simulado")

        monkeypatch.setattr(compresor.subprocess, "run", fake_run)
        with pytest.raises(SystemExit):
            empacar_grupos([[tmp_path / "a.txt"]], [10], set(), tmp_path / "carpeta", cfg, log)


class TestEscribirOutput:
    def test_formato_ruta_grupo_tamano(self, tmp_path, cfg, log):
        crear_archivos(tmp_path, {"a.txt": 100})
        archivos = descubrir_archivos(tmp_path)
        agrupacion = Agrupacion(grupos=[list(archivos)], tamanos=[100], empaquetados={0})

        escribir_output([(tmp_path, agrupacion, archivos)], cfg, log)

        lineas = (tmp_path / "output.txt").read_text(encoding="utf-8").strip().splitlines()
        assert lineas == [f"{list(archivos)[0]}|0|100"]

    def test_agrega_todas_las_carpetas(self, tmp_path, cfg, log):
        c1, c2 = tmp_path / "c1", tmp_path / "c2"
        crear_archivos(tmp_path, {"c1/a.txt": 100, "c2/b.txt": 200, "c2/c.txt": 300})
        archivos_c1 = descubrir_archivos(c1)
        archivos_c2 = descubrir_archivos(c2)
        agr1 = Agrupacion(grupos=[list(archivos_c1)], tamanos=[100], empaquetados={0})
        agr2 = Agrupacion(grupos=[list(archivos_c2)], tamanos=[500], empaquetados={0})

        escribir_output([(c1, agr1, archivos_c1), (c2, agr2, archivos_c2)], cfg, log)

        lineas = (tmp_path / "output.txt").read_text(encoding="utf-8").strip().splitlines()
        assert len(lineas) == 3  # ambas carpetas quedan en el mismo archivo
        assert f"{c1 / 'a.txt'}|0|100" in lineas
        assert f"{c2 / 'b.txt'}|0|200" in lineas
        assert f"{c2 / 'c.txt'}|0|300" in lineas

    def test_indices_de_grupo_por_carpeta(self, tmp_path, cfg, log):
        crear_archivos(tmp_path, {"c1/a.txt": 100, "c2/b.txt": 200})
        archivos_c1 = descubrir_archivos(tmp_path / "c1")
        archivos_c2 = descubrir_archivos(tmp_path / "c2")
        a1, b1 = list(archivos_c1)[0], list(archivos_c2)[0]
        # Cada carpeta con dos grupos: los índices reinician por carpeta
        agr1 = Agrupacion(grupos=[[a1], []], tamanos=[100, 0], empaquetados={0})
        agr2 = Agrupacion(grupos=[[b1], []], tamanos=[200, 0], empaquetados={0})

        escribir_output(
            [(tmp_path / "c1", agr1, archivos_c1), (tmp_path / "c2", agr2, archivos_c2)],
            cfg, log,
        )

        lineas = (tmp_path / "output.txt").read_text(encoding="utf-8").strip().splitlines()
        assert f"{a1}|0|100" in lineas
        assert f"{b1}|0|200" in lineas  # no "|1|": índices por carpeta, como los ZIP


class TestManejoAcceso:
    def test_winrar_no_ejecutable_lanza_systemexit(self, tmp_path, cfg, log, monkeypatch):
        def lanzar_error(comando, **kwargs):
            raise PermissionError(5, "Acceso denegado")

        monkeypatch.setattr(compresor.subprocess, "run", lanzar_error)
        with pytest.raises(SystemExit, match="No se pudo ejecutar WinRAR"):
            zip_files_with_winrar([tmp_path / "a.txt"], tmp_path / "x.zip", cfg, log)

    def test_zip_ausente_tras_empacar_lanza_systemexit(self, tmp_path, cfg, log, monkeypatch):
        def no_hace_nada(comando, **kwargs):
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(compresor.subprocess, "run", no_hace_nada)
        with pytest.raises(SystemExit, match="no fue creado o no es accesible"):
            empacar_grupos([[tmp_path / "a.txt"]], [10], set(), tmp_path / "carpeta", cfg, log)

    def test_destino_listado_preferida_ok(self, tmp_path, cfg, log):
        destino = destino_listado(tmp_path / "listado.txt", cfg, log, "prueba")
        assert destino == tmp_path / "listado.txt"

    def test_destino_listado_fallback_a_log_dir(self, tmp_path, cfg, log):
        (tmp_path / "listado.txt").mkdir()  # un directorio hace fallar open 'w'
        destino = destino_listado(tmp_path / "listado.txt", cfg, log, "prueba")
        assert destino == cfg.log_dir / "listado.txt"
        assert (cfg.log_dir / "listado.txt").exists()

    def test_destino_listado_ambos_fallan_devuelve_none(self, tmp_path, cfg, log):
        (tmp_path / "listado.txt").mkdir()
        (cfg.log_dir / "listado.txt").mkdir(parents=True)  # directorio: open 'w' falla
        destino = destino_listado(tmp_path / "listado.txt", cfg, log, "prueba")
        assert destino is None

    def test_output_con_carpeta_protegida_cae_a_log_dir(self, tmp_path, cfg, log):
        crear_archivos(tmp_path, {"a.txt": 100})
        archivos = descubrir_archivos(tmp_path)
        agrupacion = Agrupacion(grupos=[list(archivos)], tamanos=[100], empaquetados={0})
        (tmp_path / "output.txt").mkdir()  # bloquea la escritura en la carpeta de datos

        escribir_output([(tmp_path, agrupacion, archivos)], cfg, log)

        redirigido = cfg.log_dir / "output.txt"
        assert redirigido.exists()
        lineas = redirigido.read_text(encoding="utf-8").strip().splitlines()
        assert lineas == [f"{list(archivos)[0]}|0|100"]


class TestConfig:
    def test_perfil_4mb(self):
        cfg = PERFILES["4mb"]
        assert cfg.limite_grupo == 3_990_000
        assert cfg.limite_reempacado == 3_900_000
        assert cfg.limite_arch_origen == 4_200_000

    def test_perfil_19mb(self):
        cfg = PERFILES["19mb"]
        assert cfg.limite_grupo == 19_922_944
        assert cfg.limite_reempacado == 19_451_084
        assert cfg.limite_arch_origen == 19_922_944

    def test_config_es_inmutable(self):
        with pytest.raises(AttributeError):
            PERFILES["4mb"].limite_grupo = 0
