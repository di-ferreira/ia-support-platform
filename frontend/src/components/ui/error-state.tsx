import { AlertTriangle } from "lucide-react";

type Props = {
  title?: string;
  description?: string;
  onRetry?: () => void;
};

export function ErrorState({
  title = "Algo deu errado",
  description = "Não foi possível carregar os dados. Tente novamente.",
  onRetry,
}: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-status-danger-soft bg-status-danger-soft px-6 py-12 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-status-danger-soft text-status-danger">
        <AlertTriangle className="h-6 w-6" aria-hidden="true" />
      </div>
      <h3 className="text-sm font-semibold text-status-danger">{title}</h3>
      <p className="max-w-sm text-sm text-status-danger">{description}</p>
      {onRetry ? (
        <button
          onClick={onRetry}
          className="mt-2 rounded-lg border border-status-danger-soft bg-white px-4 py-2 text-sm font-medium text-status-danger hover:bg-status-danger-soft"
        >
          Tentar novamente
        </button>
      ) : null}
    </div>
  );
}