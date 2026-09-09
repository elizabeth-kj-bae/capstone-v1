'use client';

import { useEffect, useState } from 'react';
import { getOrCreateThreadId, startNewThread, clearThread } from '@/lib/thread';

export default function ThreadDevPage() {
  const [threadId, setThreadId] = useState<string>('');

  useEffect(() => {
    setThreadId(getOrCreateThreadId());
  }, []);

  return (
    <div style={{ padding: 24, fontFamily: 'monospace' }}>
      <h1>Thread ID 검증</h1>
      <p>현재 thread_id: <strong>{threadId}</strong></p>
      <div style={{ display: 'flex', gap: 8, margin: '12px 0' }}>
        <button
          onClick={() => setThreadId(startNewThread())}
          style={{ padding: '8px 16px', border: '1px solid #888', borderRadius: 4, cursor: 'pointer' }}
        >
          새 thread 생성
        </button>
        <button
          onClick={() => { clearThread(); setThreadId(''); }}
          style={{ padding: '8px 16px', border: '1px solid #888', borderRadius: 4, cursor: 'pointer' }}
        >
          thread 삭제
        </button>
      </div>
      <hr />
      <p>localStorage 직접 확인: DevTools → Application → Local Storage → <code>capstone:active_thread_id</code></p>
    </div>
  );
}
