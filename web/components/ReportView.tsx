import type { BaseReport, CaseItem, Confidence } from "@/lib/types";

const CONF_LABEL: Record<Confidence, string> = {
  high: "근거 확실", medium: "교차 확인", low: "단일 출처",
};
const CONF_STYLE: Record<Confidence, string> = {
  high: "bg-emerald-100 text-emerald-800",
  medium: "bg-amber-100 text-amber-800",
  low: "bg-zinc-200 text-zinc-600",
};

function CaseCard({ item, index, tone, highlighted }: {
  item: CaseItem; index: number; tone: "bull" | "bear"; highlighted: boolean;
}) {
  return (
    <li
      className={`rounded-lg border p-4 text-sm leading-relaxed ${
        tone === "bull" ? "border-emerald-200 bg-emerald-50/50" : "border-rose-200 bg-rose-50/50"
      } ${highlighted ? "ring-2 ring-blue-400" : ""}`}
    >
      <div className="mb-1 flex items-start justify-between gap-2">
        <p className="font-semibold text-zinc-900">
          {tone === "bull" ? "🟢" : "🔴"} {index + 1}. {item.claim}
        </p>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${CONF_STYLE[item.confidence]}`}>
          {CONF_LABEL[item.confidence]}
        </span>
      </div>
      <p className="text-zinc-700">{item.evidence}</p>
      <a href={item.source_url} target="_blank" rel="noreferrer"
         className="mt-2 inline-block max-w-full truncate text-xs text-blue-600 hover:underline">
        출처: {item.source_url}
      </a>
      {highlighted && (
        <p className="mt-1 text-xs font-medium text-blue-600">↑ 내 논거와 직접 관련</p>
      )}
    </li>
  );
}

export default function ReportView({ report, supporting = [], contradicting = [] }: {
  report: BaseReport; supporting?: number[]; contradicting?: number[];
}) {
  return (
    <section className="space-y-6">
      <div>
        <h2 className="mb-1 text-xl font-bold text-zinc-900">
          {report.ticker} <span className="text-sm font-normal text-zinc-500">기준일 {report.as_of}</span>
        </h2>
        <p className="text-sm leading-relaxed text-zinc-700">{report.company_summary_ko}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <h3 className="mb-2 font-semibold text-emerald-700">강세 논거</h3>
          <ul className="space-y-3">
            {report.bull_case.map((c, i) => (
              <CaseCard key={i} item={c} index={i} tone="bull" highlighted={supporting.includes(i)} />
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 font-semibold text-rose-700">약세 논거</h3>
          <ul className="space-y-3">
            {report.bear_case.map((c, i) => (
              <CaseCard key={i} item={c} index={i} tone="bear" highlighted={contradicting.includes(i)} />
            ))}
          </ul>
        </div>
      </div>

      <details className="text-sm text-zinc-500">
        <summary className="cursor-pointer select-none">전체 출처 {report.sources.length}건</summary>
        <ul className="mt-2 list-inside list-disc space-y-1">
          {report.sources.map((s, i) => (
            <li key={i}>
              <a href={s.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
                {s.title}
              </a>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}
