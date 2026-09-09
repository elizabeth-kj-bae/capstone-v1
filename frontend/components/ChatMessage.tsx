/**
 * 단일 chat 메시지 렌더링.
 * 
 * Token stream과 tool call을 함께 표시.
 */

import type { UIMessage } from '@/lib/types';
import { ToolCallView } from './ToolCallView';

interface Props {
  message: UIMessage;
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user';
  
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
        {/* Tool call들이 먼저 (token이 그 뒤에 누적) */}
        {message.toolCalls.map((tc, i) => (
          <ToolCallView key={i} toolCall={tc} />
        ))}
        
        {/* Token 누적 텍스트 */}
        {message.content && (
          <div className="whitespace-pre-wrap">{message.content}</div>
        )}
      </div>
    </div>
  );
}
