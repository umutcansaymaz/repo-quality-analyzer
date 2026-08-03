"use client";

type Step = {
  id: string;
  label: string;
  status: "pending" | "running" | "completed" | "error";
};

type Props = {
  steps: Step[];
  currentRepo?: string;
};

const statusIcon: Record<Step["status"], string> = {
  pending: "h-2 w-2 rounded-full inline-block kl-border-soft opacity-50",
  running: "kl-accent h-2 w-2 animate-spin rounded-full inline-block",
  completed: "kl-success h-2 w-2 rounded-full inline-block",
  error: "kl-danger h-2 w-2 rounded-full inline-block",
};

export function IlerlemeCubugu({ steps, currentRepo }: Props) {
  const completed = steps.filter((s) => s.status === "completed").length;

  return (
    <div className="flex flex-col gap-4">
      {currentRepo && (
        <p className="kl-font-mono kl-muted text-xs truncate">
          {currentRepo}
        </p>
      )}
      <div className="kl-paper-alt kl-border-soft h-2 w-full rounded-full overflow-hidden">
        <div
          className="kl-accent h-full rounded-full transition-all duration-500"
          style={{
            width: `${Math.max(0, Math.min(100, (completed / steps.length) * 100))}%`,
          }}
        />
      </div>
      <div className="flex flex-col gap-1">
        {steps.map((step, i) => (
          <div
            key={step.id}
            className="kl-font-body flex items-center gap-3 text-sm transition-opacity"
            style={{
              opacity: step.status === "pending" ? 0.4 : 1,
              animationDelay: `${i * 0.05}s`,
            }}
          >
            <span className={statusIcon[step.status]} />
            <span
              className={
                step.status === "running"
                  ? "kl-accent font-medium"
                  : step.status === "error"
                    ? "kl-danger"
                    : "kl-ink"
              }
            >
              {step.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
