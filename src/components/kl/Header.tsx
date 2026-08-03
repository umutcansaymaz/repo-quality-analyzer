import { Damga } from "./Damga";

type MetaItem = { label: string; value: string };

type Props = {
  title: string;
  subtitle?: string;
  meta?: MetaItem[];
  reportNo?: number;
  repoName?: string;
  date?: Date;
};

export function Header({
  title,
  subtitle,
  meta,
  reportNo = 1,
  repoName = "",
  date,
}: Props) {
  return (
    <header className="kl-paper kl-border-soft relative flex flex-wrap items-start gap-4 p-4 sm:p-6">
      <div className="kl-asym-left min-w-[180px]">
        <h1 className="kl-font-display kl-ink text-2xl font-bold tracking-tight sm:text-3xl">
          {title}
        </h1>
        {subtitle && (
          <p className="kl-font-body kl-muted mt-1 text-sm">{subtitle}</p>
        )}
      </div>
      <div className="kl-asym-right flex flex-wrap items-start gap-3">
        {meta?.map((m, i) => (
          <div key={i} className="kl-font-body text-xs">
            <span className="kl-muted uppercase tracking-wider">{m.label}</span>
            <span className="kl-ink ml-2 font-medium">{m.value}</span>
          </div>
        ))}
      </div>
      <Damga
        reportNo={reportNo}
        repoName={repoName}
        date={date}
      />
    </header>
  );
}
