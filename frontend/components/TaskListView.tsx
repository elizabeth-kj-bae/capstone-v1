/**
 * Task 목록 및 각 task의 진행 상황을 표시.
 */

import type { Task } from '@/lib/types';

interface Props {
  tasks: Task[];
  taskTokens: Record<string, string>;
  activeTaskId?: string;
}

export function TaskListView({ tasks, taskTokens, activeTaskId }: Props) {
  if (tasks.length === 0) return null;
  
  return (
    <div className="my-3 space-y-2">
      {tasks.map((task) => (
        <TaskCard
          key={task.id}
          task={task}
          currentToken={taskTokens[task.id]}
          isActive={task.id === activeTaskId}
        />
      ))}
    </div>
  );
}

interface TaskCardProps {
  task: Task;
  currentToken?: string;
  isActive: boolean;
}

function TaskCard({ task, currentToken, isActive }: TaskCardProps) {
  const statusIcon = {
    pending: '⏸',
    in_progress: '🔄',
    completed: '✅',
    failed: '❌',
  }[task.status];
  
  const statusColor = {
    pending: 'bg-gray-50 border-gray-200',
    in_progress: 'bg-yellow-50 border-yellow-300',
    completed: 'bg-green-50 border-green-200',
    failed: 'bg-red-50 border-red-200',
  }[task.status];
  
  // Agent별 표시 차별화
  const agentLabel = {
    research: '🔍 Research',
    analysis: '📊 Analysis',
    writing: '✍️ Writing',
  }[task.agent] || task.agent;
  
  const agentColor = {
    research: 'text-blue-700',
    analysis: 'text-purple-700',
    writing: 'text-green-700',
  }[task.agent] || 'text-gray-700';
  
  return (
    <div className={`p-3 border rounded ${statusColor}`}>
      <div className="flex items-start gap-2">
        <span>{statusIcon}</span>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <span className="font-medium text-sm">{task.description}</span>
            <span className={`text-xs font-mono ${agentColor}`}>
              {agentLabel}
            </span>
          </div>
          
          {/* 기존: in_progress 시 token streaming, completed 시 result */}
          {isActive && currentToken && (
            <div className="mt-2 text-xs text-gray-600 italic">
              {currentToken.slice(-150)}{currentToken.length > 150 ? '...' : ''}
            </div>
          )}
          
          {task.status === 'completed' && task.result && (
            <details className="mt-2 text-xs">
              <summary className="cursor-pointer text-gray-600">결과 보기</summary>
              <div className="mt-1 p-2 bg-white border rounded whitespace-pre-wrap">
                {task.result}
              </div>
            </details>
          )}
          
          {task.status === 'failed' && task.error_message && (
            <div className="mt-2 text-xs text-red-700">
              {task.error_message}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
