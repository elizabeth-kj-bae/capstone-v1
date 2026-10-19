/**
 * Validator의 검증 결과를 표시.
 * 
 * - System이 자체 검증 중임을 사용자에게 노출.
 */

import type { ValidationInfo } from '@/lib/types';

interface Props {
  validation: ValidationInfo;
  retried: boolean;
  retryFeedback?: string;
}

export function ValidationView({ validation, retried, retryFeedback }: Props) {
  const passColor = validation.is_acceptable
    ? 'bg-green-50 border-green-200 text-green-900'
    : validation.will_retry
    ? 'bg-yellow-50 border-yellow-300 text-yellow-900'
    : 'bg-orange-50 border-orange-300 text-orange-900';
  
  const passIcon = validation.is_acceptable
    ? '✅'
    : validation.will_retry
    ? '🔄'
    : '⚠️';
  
  const passLabel = validation.is_acceptable
    ? '품질 검증 통과'
    : validation.will_retry
    ? '품질 검증: 재작성 진행'
    : '품질 검증: 한계 도달';
  
  return (
    <div className={`my-3 p-3 border rounded ${passColor}`}>
      <div className="flex items-center gap-2 text-sm font-medium">
        <span>{passIcon}</span>
        <span>{passLabel}</span>
        <span className="text-xs text-gray-600 ml-auto">
          Score: {validation.score.toFixed(2)}
        </span>
      </div>
      
      <details className="mt-2 text-xs text-gray-700">
        <summary className="cursor-pointer">검증 근거 보기</summary>
        <div className="mt-1 pl-2 italic">{validation.reasoning}</div>
      </details>
      
      {retried && retryFeedback && (
        <details className="mt-2 text-xs text-gray-700">
          <summary className="cursor-pointer">재작성 피드백 보기</summary>
          <div className="mt-1 pl-2 italic">{retryFeedback}</div>
        </details>
      )}
    </div>
  );
}
