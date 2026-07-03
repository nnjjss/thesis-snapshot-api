import type { ThesisEval, Verdict } from "@/lib/types";

const VERDICT_LABEL: Record<Verdict, string> = {
  valid: "논거 유효",
  partially_valid: "부분 유효",
  weakened: "논거 약화됨",
  insufficient_data: "판정 근거 부족",
};
const VERDICT_STYLE: Record<Verdict, string> = {
  valid: "bg-emerald-600",
  partially_valid: "bg-amber-500",
  weakened: "bg-rose-600",
  insufficient_data: "bg-zinc-500",
};

export default function EvalView({ ev }: { ev: ThesisEval }) {
  return (
    <section className="rounded-xl border border-blue-200 bg-blue-50/40 p-5">
      <div className="mb-3 flex items-center gap-3">
        <h2 className="text-lg font-bold text-zinc-900">내 논거 검증</h2>
        <span className={`rounded-full px-3 py-1 text-sm font-semibold text-white ${VERDICT_STYLE[ev.verdict]}`}>
          {VERDICT_LABEL[ev.verdict]}
        </span>
      </div>

      <p className="mb-3 text-sm text-zinc-600">
        <span className="font-medium text-zinc-800">논거 재진술:</span> {ev.thesis_restated}
      </p>

      <p className="whitespace-pre-line text-sm leading-relaxed text-zinc-800">{ev.reasoning_ko}</p>

      {ev.watch_items_ko.length > 0 && (
        <div className="mt-4">
          <h3 className="mb-1 text-sm font-semibold text-zinc-800">관찰 포인트 (논거의 생사를 가를 것들)</h3>
          <ul className="list-inside list-disc space-y-1 text-sm text-zinc-700">
            {ev.watch_items_ko.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}

      <p className="mt-3 text-xs text-zinc-500">
        아래 리포트에서 <span className="font-medium text-blue-600">파란 테두리</span> 카드가 이 논거와 직접 관련된 근거입니다.
      </p>
    </section>
  );
}
