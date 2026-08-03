import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
};

export function KlavyeOdagi({ children }: Props) {
  return (
    <kbd className="kl-font-mono kl-border-soft kl-paper-alt kl-ink inline-flex h-6 min-w-6 items-center justify-center rounded px-1.5 text-xs font-semibold">
      {children}
    </kbd>
  );
}
