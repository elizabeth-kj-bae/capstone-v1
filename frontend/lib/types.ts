/**
 * Backend SSE event types.
 * 
 * Backend의 schemas/stream.py와 1:1 대응되어야 함.
 * 한쪽이 변경되면 다른 쪽도 함께 업데이트 필요.
 */

export interface TokenEvent {
  type: 'token';
  content: string;
}

export interface ToolCallStartEvent {
  type: 'tool_call_start';
  tool_name: string;
  args: Record<string, unknown>;
}

export interface ToolCallEndEvent {
  type: 'tool_call_end';
  tool_name: string;
  result?: string;
}

export interface DoneEvent {
  type: 'done';
  thread_id: string;
}

export type StreamEvent =
  | TokenEvent
  | ToolCallStartEvent
  | ToolCallEndEvent
  | DoneEvent;

/**
 * UI에서 사용할 메시지 type.
 * Backend의 thread state와는 별개로, frontend가 자체 관리하는 message 표현.
 */
export interface UIMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;          // 누적된 token text
  toolCalls: UIToolCall[];  // 이 메시지 처리 중 발생한 tool call들
}

export interface UIToolCall {
  toolName: string;
  args: Record<string, unknown>;
  result?: string;
  status: 'pending' | 'completed';
}
