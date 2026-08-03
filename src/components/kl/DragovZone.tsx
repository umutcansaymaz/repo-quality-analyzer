"use client";
import type { ReactNode } from "react";

type Props = {
  isDragging: boolean;
  isScanning: boolean;
  fileCount?: number;
  scannedCount?: number;
  error?: string;
  stats?: { topExts: string[]; total: number } | null;
  selectedName?: string;
  onClear?: () => void;
  children?: ReactNode;
};

export function DragovZone({
  isDragging,
  isScanning,
  fileCount,
  scannedCount,
  error,
  stats,
  selectedName,
  onClear,
  children,
}: Props) {
  return (
    <div
      className={`kl-card flex flex-col items-center gap-3 p-10 text-center transition-all duration-200
        ${isDragging ? "kl-accent kl-border-soft scale-[1.02]" : "kl-border-soft"}`}
    >
      {isScanning ? (
        <div className="flex flex-col items-center gap-3">
          <svg
            className="kl-accent h-10 w-10 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="3"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          <p className="kl-font-body kl-ink text-sm font-medium">
            klasör taranıyor...
          </p>
          {scannedCount != null && (
            <p className="kl-font-body kl-muted text-xs">
              {scannedCount.toLocaleString()}
              {fileCount != null
                ? ` / ${fileCount.toLocaleString()}`
                : ""}{" "}
              dosya
            </p>
          )}
        </div>
      ) : stats ? (
        <div className="flex flex-col items-center gap-3">
          <svg
            className="kl-success h-10 w-10"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="kl-font-body kl-ink text-sm font-medium">
            {stats.total.toLocaleString()} dosya seçildi
          </p>
          {stats.topExts.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {stats.topExts.map((ext) => (
                <span
                  key={ext}
                  className="kl-font-mono kl-muted kl-border-soft rounded px-1.5 py-0.5 text-xs"
                >
                  {ext}
                </span>
              ))}
            </div>
          )}
          {selectedName && (
            <div className="kl-border-soft kl-paper-alt flex items-center gap-2 rounded px-3 py-1 text-sm">
              <span className="kl-font-mono kl-ink text-xs">
                {selectedName}
              </span>
              {onClear && (
                <button
                  onClick={onClear}
                  className="kl-muted hover:kl-accent rounded p-0.5 transition-colors"
                  title="seçimi temizle"
                >
                  <svg
                    className="h-3 w-3"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={2}
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          <svg
            className="kl-muted h-10 w-10"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z"
            />
          </svg>
          <p className="kl-font-body kl-ink text-sm font-medium">
            {isDragging
              ? "buraya bırak"
              : "bir klasörü buraya bırak, ya da göz atmak için tıkla"}
          </p>
        </div>
      )}
      {error && (
        <div className="kl-card-danger kl-font-body flex items-center gap-2 rounded p-3 text-sm">
          <svg
            className="kl-danger h-4 w-4 shrink-0"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
            />
          </svg>
          <span>{error}</span>
        </div>
      )}
      {children}
    </div>
  );
}
