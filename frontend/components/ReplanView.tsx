/**
 * Supervisor의 재계획 결정 표시.
 * 
 * Dynamic Planning의 결정 과정을 사용자에게 노출.
 */

import type { ReplanInfo } from '@/lib/types';

interface Props {
  replans: ReplanInfo[];
}

export function ReplanView({ replans }: Props) {
  if (replans.length === 0) return null;
  
  return (
    <div className="my-3 space-y-2">
      {replans.map((replan, i) => (
        <SingleReplanCard key={i} replan={replan} index={i + 1} />
      ))}
    </div>
  );
}

function SingleReplanCard({ replan, index }: { replan: ReplanInfo; index: number }) {
  const isReplanning = !replan.is_sufficient;
  
  const cardColor = isReplanning
    ? 'bg-amber-50 border-amber-300 text-amber-900'
    : 'bg-gray-50 border-gray-200 text-gray-700';
  
  const icon = isReplanning ? '🔍' : '✓';
  const taskCountSuffix = replan.added_task_count > 0
    ? ` (${replan.added_task_count}개 task 추가)`
    : '';

  const label = isReplanning 
    ? `재검토 ${index}: 추가 정보 수집 필요${taskCountSuffix}`
    : `재검토 ${index}: 수집된 정보 충분`;
  
  return (
    <div className={`p-3 border rounded ${cardColor}`}>
      <div className="flex items-center gap-2 text-sm font-medium">
        <span>{icon}</span>
        <span>{label}</span>
      </div>
      <details className="mt-2 text-xs text-gray-700">
        <summary className="cursor-pointer">판단 근거 보기</summary>
        <div className="mt-1 pl-2 italic">{replan.reasoning}</div>
      </details>
    </div>
  );
}
