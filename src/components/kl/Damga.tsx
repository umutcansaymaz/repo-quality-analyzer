"use client";

type Props = {
  date?: Date;
  repoName?: string;
  reportNo: number;
};

export function Damga({
  date = new Date(),
  repoName = "",
  reportNo = 1,
}: Props) {
  const dd = String(date.getDate()).padStart(2, "0");
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const yyyy = date.getFullYear();

  const handleClick = () => {
    if (typeof window !== "undefined") window.print();
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      title={`${repoName ? `${repoName} — ` : ""}Rapor nº${reportNo} (${dd}.${mm}.${yyyy}) — PDF / Yazdır`}
      className="kl-damga kl-print-hide flex flex-col items-center justify-center p-1 font-sans select-none"
      aria-label={`Yazdır: ${repoName} rapor ${reportNo}`}
    >
      <span className="kl-font-display text-[7px] font-bold uppercase tracking-wider kl-accent leading-none">
        KALİTE
      </span>
      <span className="kl-font-display text-[10px] font-bold kl-ink leading-tight my-0.5">
        Nº{reportNo}
      </span>
      <span className="kl-font-mono text-[6px] uppercase tracking-widest kl-muted leading-none opacity-80">
        RAPOR
      </span>
    </button>
  );
}
