/**
 * Tool call 가시화 컴포넌트.
 * 
 * Streaming > Content에서 강조한 "Agent의 사고 과정 가시화"의 UI 구현.
 */

import type { UIToolCall } from '@/lib/types';

interface Props {
  toolCall: UIToolCall;
}

export function ToolCallView({ toolCall }: Props) {
  return (
    <div className="my-2 p-3 bg-blue-50 border border-blue-200 rounded">
      <div className="flex items-center gap-2 text-sm">
        {toolCall.status === 'pending' ? (
          <span className="text-blue-600">🔄 도구 사용 중</span>
        ) : (
          <span className="text-green-600">✓ 도구 완료</span>
        )}
        <span className="font-mono text-gray-700">{toolCall.toolName}</span>
      </div>
      
      <details className="mt-2 text-xs text-gray-600">
        <summary className="cursor-pointer">상세 보기</summary>
        <div className="mt-1 pl-2">
          <div>
            <strong>인자:</strong>
            <pre className="text-xs">{JSON.stringify(toolCall.args, null, 2)}</pre>
          </div>
          {toolCall.result && (
            <div className="mt-1">
              <strong>결과:</strong>
              <pre className="text-xs whitespace-pre-wrap">{toolCall.result}</pre>
            </div>
          )}
        </div>
      </details>
    </div>
  );
}
