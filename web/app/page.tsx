"use client";

import { useState } from "react";
import AccountBox, { getStoredApiKey } from "@/components/AccountBox";
import EvalView from "@/components/EvalView";
import ReportView from "@/components/ReportView";
import type { ReportResponse } from "@/lib/types";

export default function Home() {
  const [ticker, setTicker] = useState("");
  const [thesis, setThesis] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ReportResponse | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!ticker.trim() || loading) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const apiKey = getStoredApiKey();
      const res = await fetch("/api/backend/v1/reports", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          ...(apiKey ? { "X-API-Key": apiKey } : {}),
        },
        body: JSON.stringify({
          ticker: ticker.trim().toUpperCase(),
          thesis: thesis.trim() || null,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail ?? `HTTP ${res.status}`);
      }
      setData((await res.json()) as ReportResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-black tracking-tight">Thesis Snapshot</h1>
        <p className="mt-1 text-sm text-zinc-600">
          미국 티커의 강세/약세 논거 리포트 — 내 투자 논거가 최신 데이터로 버티는지 검증합니다.
        </p>
      </header>

      <AccountBox />

      <form onSubmit={submit} className="mb-8 space-y-3 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
        <div className="flex gap-3">
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="티커 (예: NVDA)"
            maxLength={10}
            pattern="[A-Za-z.\-]{1,10}"
            required
            className="w-40 rounded-lg border border-zinc-300 px-3 py-2 font-mono uppercase focus:border-blue-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-blue-600 px-5 py-2 font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "생성 중…" : "리포트 생성"}
          </button>
        </div>
        <textarea
          value={thesis}
          onChange={(e) => setThesis(e.target.value)}
          placeholder="검증받고 싶은 투자 논거 (선택) — 예: 데이터센터 수요 덕분에 앞으로도 실적 성장이 이어질 것이다"
          maxLength={2000}
          rows={2}
          className="w-full resize-y rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        />
        {loading && (
          <p className="text-sm text-zinc-500">
            <span className="mr-2 inline-block animate-spin">⏳</span>
            캐시가 없는 티커는 웹 리서치에 1~2분 걸립니다. 창을 닫지 마세요.
          </p>
        )}
      </form>

      {error && (
        <div className="mb-6 rounded-lg border border-rose-300 bg-rose-50 p-4 text-sm text-rose-800">
          오류: {error}
        </div>
      )}

      {data && (
        <div className="space-y-8">
          <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
            <span className={`rounded-full px-2 py-0.5 font-medium ${
              data.meta.cache_hit ? "bg-emerald-100 text-emerald-700" : "bg-blue-100 text-blue-700"
            }`}>
              {data.meta.cache_hit ? "캐시 히트 (24h 내 생성됨)" : "신규 생성"}
            </span>
            {(data.meta.input_tokens > 0 || data.meta.output_tokens > 0) && (
              <span>토큰 in {data.meta.input_tokens.toLocaleString()} / out {data.meta.output_tokens.toLocaleString()}</span>
            )}
            {data.meta.web_searches > 0 && <span>웹 검색 {data.meta.web_searches}회</span>}
          </div>

          {data.thesis_eval && <EvalView ev={data.thesis_eval} />}

          <ReportView
            report={data.report}
            supporting={data.thesis_eval?.supporting}
            contradicting={data.thesis_eval?.contradicting}
          />

          <footer className="border-t border-zinc-200 pt-4 text-xs leading-relaxed text-zinc-500">
            {data.disclaimer}
          </footer>
        </div>
      )}
    </main>
  );
}
