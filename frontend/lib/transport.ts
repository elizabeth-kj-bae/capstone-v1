/**
 * Backend SSE stream 파싱 및 처리.
 * 
 * 본 capstone의 자체 SSE format을 파싱하여 callback 호출.
 */

import type { StreamEvent } from './types';

/**
 * Backend `/chat/stream` endpoint로 메시지를 보내고, 
 * SSE event를 파싱하여 onEvent callback 호출.
 * 
 * @param backendUrl Backend URL (e.g., http://localhost:8000)
 * @param message 사용자 메시지
 * @param threadId Thread ID (Day 1 결정: Frontend가 생성·전송)
 * @param onEvent 각 event마다 호출되는 callback
 * @param signal AbortSignal (요청 취소용)
 */
export async function sendChatMessage(
  backendUrl: string,
  endpoint: string,
  message: string,
  threadId: string,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${backendUrl}${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      thread_id: threadId,
    }),
    signal,
  });
  
  if (!response.ok) {
    throw new Error(`Backend error: ${response.status} ${response.statusText}`);
  }
  
  if (!response.body) {
    throw new Error('No response body');
  }
  
  // SSE 응답 stream 파싱
  const reader = response.body
    .pipeThrough(new TextDecoderStream())
    .getReader();
  
  let buffer = '';
  
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += value;
      
      // SSE event는 빈 줄(\n\n)로 구분됨
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';  // 마지막은 다음 chunk와 합쳐질 수 있음
      
      for (const eventBlock of events) {
        const parsed = parseSSEEvent(eventBlock);
        if (parsed) {
          onEvent(parsed);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * 단일 SSE event block을 파싱.
 * 
 * Format:
 *   event: token
 *   data: {"type":"token","content":"..."}
 */
function parseSSEEvent(block: string): StreamEvent | null {
  const lines = block.split('\n');
  let dataLine: string | null = null;
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      dataLine = line.slice(6);  // "data: " 제거
    }
    // event: 라인은 data의 type 필드에 같은 정보가 있으므로 사용하지 않음
  }
  
  if (!dataLine) return null;
  
  try {
    return JSON.parse(dataLine) as StreamEvent;
  } catch (e) {
    console.error('Failed to parse SSE event:', dataLine, e);
    return null;
  }
}
