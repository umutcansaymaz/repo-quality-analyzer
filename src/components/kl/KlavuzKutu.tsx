import type { ReactNode } from "react";

type Variant = "info" | "warn" | "tip" | "empty";

type Props = {
  title: string;
  description?: string;
  action?: ReactNode;
  variant?: Variant;
};

const variantBorder: Record<Variant, string> = {
  info: "kl-border-soft",
  warn: "kl-accent kl-border-soft",
  tip: "kl-success kl-border-soft",
  empty: "kl-border-soft",
};

export function KlavuzKutu({
  title,
  description,
  action,
  variant = "info",
}: Props) {
  return (
    <div
      className={`kl-card flex flex-col items-center gap-3 p-8 text-center ${variantBorder[variant]}`}
    >
      <h3 className="kl-font-display kl-ink text-lg font-semibold">
        {title}
      </h3>
      {description && (
        <p className="kl-font-body kl-muted max-w-md text-sm">{description}</p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
