import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  children: ReactNode;
};

const variantStyle: Record<Variant, string> = {
  primary:
    "kl-paper-alt kl-ink kl-border-soft hover:kl-accent hover:kl-border-soft kl-font-body",
  secondary:
    "kl-ink kl-border-soft hover:kl-paper-alt kl-font-body",
  ghost:
    "kl-ink hover:kl-paper-alt kl-font-body",
};

export function OlayButonu({
  variant = "primary",
  children,
  className = "",
  ...rest
}: Props) {
  return (
    <button
      className={`kl-focus-ring inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${variantStyle[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
