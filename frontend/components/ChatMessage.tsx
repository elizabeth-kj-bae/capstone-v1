import type { UISupervisorMessage } from '@/lib/types';
import { PlanView } from './PlanView';
import { TaskListView } from './TaskListView';

interface Props {
  message: UISupervisorMessage;
  activeTaskId?: string;
}

export function ChatMessage({ message, activeTaskId }: Props) {
  const isUser = message.role === 'user';
  const isSimple = message.route === 'simple';
  
  return (
    <div className={`my-4 ${isUser ? 'text-right' : 'text-left'}`}>
      <div className="text-xs text-gray-500 mb-1">
        {isUser ? '사용자' : 'AI Agent'}
      </div>
      
      <div className={`inline-block max-w-3xl p-3 rounded ${
        isUser 
          ? 'bg-gray-200 text-black' 
          : 'bg-white border border-gray-300'
      }`}>
        {/* Simple 응답: Plan/Task 표시 안 함, 바로 응답 */}
        {isSimple ? (
          <div className="whitespace-pre-wrap">{message.content}</div>
        ) : (
          /* Complex 응답: 기존 Multi-agent UI */
          <>
            {message.plan && <PlanView plan={message.plan} />}
            
            {message.tasks.length > 0 && (
              <TaskListView
                tasks={message.tasks}
                taskTokens={message.taskTokens}
                activeTaskId={activeTaskId}
              />
            )}

            {/* 최종 응답 token */}
            {message.content && (
              <div className="mt-3 whitespace-pre-wrap border-t pt-3">
                {message.content}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
