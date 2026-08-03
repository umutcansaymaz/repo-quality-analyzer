import type { ReactNode } from "react";

type Accent = "good" | "warn" | "bad" | "neutral";

type Props = {
  leftLabel: string;
  rightValue: ReactNode;
  accent?: Accent;
  hint?: string;
};

const accentBorder: Record<Accent, string> = {
  good: "kl-card-success",
  warn: "kl-card-accent",
  bad: "kl-card-danger",
  neutral: "kl-card-muted",
};

export function AnalizKarti({
  leftLabel,
  rightValue,
  accent = "neutral",
  hint,
}: Props) {
  return (
    <div
      className={`kl-card ${accentBorder[accent]} flex items-stretch`}
      title={hint}
    >
      <div className="kl-asym-left flex items-center">
        <span className="kl-font-body kl-muted text-xs uppercase tracking-widest">
          {leftLabel}
        </span>
      </div>
      <div className="kl-asym-right flex items-center">
        <span className="kl-font-display kl-ink text-2xl font-bold">
          {rightValue}
        </span>
      </div>
    </div>
  );
}
