/**
 * Supervisor의 Plan을 표시하는 카드.
 */

interface Props {
  plan: string;
}

export function PlanView({ plan }: Props) {
  return (
    <div className="my-3 p-4 bg-indigo-50 border border-indigo-200 rounded-lg">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">📋</span>
        <span className="font-semibold text-indigo-900">Plan</span>
      </div>
      <p className="text-sm text-gray-700 whitespace-pre-wrap">{plan}</p>
    </div>
  );
}
