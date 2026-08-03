"use client";
import type { ReactNode } from "react";
import { useState } from "react";

type Step = { label: string; detail?: ReactNode };

type Props = {
  steps: Step[];
  title?: string;
};

export function AciklamaZinciri({ steps, title = "Neden?" }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="kl-border-soft rounded">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="kl-font-body kl-ink hover:kl-accent flex w-full items-center gap-2 px-3 py-2 text-sm font-medium transition-colors"
      >
        <svg
          className={`h-3 w-3 shrink-0 transition-transform ${open ? "rotate-90" : ""}`}
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={2}
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        {title}
      </button>
      {open && (
        <div className="kl-border-soft border-t px-3 py-2">
          {steps.map((step, i) => (
            <div
              key={i}
              className="flex items-start gap-3 py-1.5"
            >
              <span className="kl-font-mono kl-muted mt-0.5 text-xs">
                {(i + 1).toString().padStart(2, "0")}
              </span>
              <div>
                <span className="kl-font-body kl-ink text-sm font-medium">
                  {step.label}
                </span>
                {step.detail && (
                  <div className="kl-font-body kl-muted mt-0.5 text-xs">
                    {step.detail}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
