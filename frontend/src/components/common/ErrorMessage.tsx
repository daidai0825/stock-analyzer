interface ErrorMessageProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message = '發生錯誤。', onRetry }: ErrorMessageProps) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
      <p className="text-sm text-red-700">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 rounded-md bg-red-100 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-200 transition-colors"
        >
          重試
        </button>
      )}
    </div>
  );
}
