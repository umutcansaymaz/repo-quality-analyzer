import type { ReactNode } from "react";

export type Status = "good" | "warn" | "bad" | "info" | "pending" | "running";

type Props = {
  status: Status;
  children: ReactNode;
};

const statusStyle: Record<Status, string> = {
  good: "kl-success kl-border-soft",
  warn: "kl-accent kl-border-soft",
  bad: "kl-danger kl-border-soft",
  info: "kl-muted kl-border-soft",
  pending: "kl-muted kl-border-soft opacity-50",
  running: "kl-accent kl-border-soft animate-pulse",
};

export function SinyalCubugu({ status, children }: Props) {
  return (
    <span
      className={`kl-font-body inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${statusStyle[status]}`}
    >
      {status === "running" && (
        <span className="kl-font-mono text-xs">…</span>
      )}
      {children}
    </span>
  );
}
