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


/**
 * Multi-agent (Supervisor pattern) event types.
 * Backend schemas/stream.py와 1:1 대응.
 */

export interface PlanCreatedEvent {
  type: 'plan_created';
  plan: string;
}

export interface Task {
  id: string;
  description: string;
  agent: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  result?: string;
  error_message?: string;
}

export interface TaskListCreatedEvent {
  type: 'task_list_created';
  tasks: Task[];
}

export interface TaskStartedEvent {
  type: 'task_started';
  task_id: string;
  agent_name: string;
}

export interface TaskCompletedEvent {
  type: 'task_completed';
  task_id: string;
  status: 'completed' | 'failed';
  result_preview?: string;
  error_message?: string;
}

export interface SubAgentTokenEvent {
  type: 'sub_agent_token';
  task_id: string;
  content: string;
}

export interface ErrorEvent {
  type: 'error';
  code: string;
  message: string;
  recoverable: boolean;
}

// 기존 StreamEvent type을 multi-agent 이벤트까지 확장
export type StreamEvent =
  | TokenEvent
  | ToolCallStartEvent
  | ToolCallEndEvent
  | DoneEvent
  | PlanCreatedEvent
  | TaskListCreatedEvent
  | TaskStartedEvent
  | TaskCompletedEvent
  | SubAgentTokenEvent
  | ErrorEvent;

/**
 * UI에서 사용할 multi-agent 메시지 type.
 */
export interface UISupervisorMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  plan?: string;
  tasks: Task[];
  taskTokens: Record<string, string>;
}
