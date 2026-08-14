import { TestInfo } from '@playwright/test';

const restoreMap = new WeakMap<TestInfo, () => Promise<void>>();

export function startConsoleCapture(info: TestInfo, attachmentName = 'console-logs') {
  const originalLog = console.log.bind(console);
  const logs: string[] = [];

  console.log = (...args: any[]) => {
    try {
      const msg = args
        .map((a) => (typeof a === 'string' ? a : JSON.stringify(a)))
        .join(' ');
      logs.push(msg);
    } catch (e) {
      logs.push(String(args));
    }
    originalLog(...args);
  };

  restoreMap.set(info, async () => {
    console.log = originalLog;
    try {
      await info.attach(attachmentName, {
        body: Buffer.from(logs.join('\n'), 'utf-8'),
        contentType: 'text/plain',
      });
    } catch (e) {
      originalLog('Failed to attach console logs:', e);
    }
  });
}

export async function restoreConsoleCapture(info: TestInfo) {
  const fn = restoreMap.get(info);
  if (fn) {
    await fn();
    restoreMap.delete(info);
  }
}

