/**
 * Stream 중 발생한 error를 사용자에게 표시.
 */
interface Props {
  message: string;
  recoverable: boolean;
}

export function ErrorBanner({ message, recoverable }: Props) {
  return (
    <div className={`my-2 p-3 rounded border ${
      recoverable
        ? 'bg-yellow-50 border-yellow-300 text-yellow-900'
        : 'bg-red-50 border-red-300 text-red-900'
    }`}>
      <div className="flex items-center gap-2">
        <span>{recoverable ? '⚠️' : '❌'}</span>
        <span className="text-sm">{message}</span>
      </div>
    </div>
  );
}
