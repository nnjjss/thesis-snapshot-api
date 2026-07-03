"use client";

import { useEffect, useState } from "react";

const KEY_STORAGE = "thesis_api_key";
const EMAIL_STORAGE = "thesis_email";

export function getStoredApiKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(KEY_STORAGE) ?? "";
}

export default function AccountBox() {
  const [email, setEmail] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setApiKey(getStoredApiKey());
    setEmail(localStorage.getItem(EMAIL_STORAGE) ?? "");
  }, []);

  function saveKey(k: string) {
    setApiKey(k);
    localStorage.setItem(KEY_STORAGE, k);
  }

  async function signup() {
    if (!email.trim() || busy) return;
    setBusy(true);
    setMsg(null);
    try {
      const res = await fetch("/api/backend/v1/signup", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body?.detail ?? `HTTP ${res.status}`);
      saveKey(body.api_key);
      localStorage.setItem(EMAIL_STORAGE, email.trim());
      setMsg("✅ API 키가 발급·저장되었습니다. 이 키는 재표시되지 않으니 별도 보관하세요.");
    } catch (e) {
      setMsg(`오류: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
    }
  }

  async function upgrade() {
    if (!email.trim() || busy) return;
    setBusy(true);
    setMsg(null);
    try {
      const res = await fetch("/api/backend/v1/billing/checkout", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body?.detail ?? `HTTP ${res.status}`);
      window.location.href = body.url; // Stripe Checkout으로 이동
    } catch (e) {
      setMsg(`오류: ${e instanceof Error ? e.message : String(e)}`);
      setBusy(false);
    }
  }

  return (
    <details className="mb-6 rounded-xl border border-zinc-200 bg-white px-5 py-3 text-sm shadow-sm">
      <summary className="cursor-pointer select-none font-semibold text-zinc-800">
        계정 · API 키 {apiKey ? <span className="ml-2 rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">키 저장됨</span> : <span className="ml-2 rounded bg-zinc-100 px-2 py-0.5 text-xs text-zinc-500">미설정</span>}
      </summary>
      <div className="mt-3 space-y-3">
        <div className="flex flex-wrap gap-2">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="이메일"
            className="w-64 rounded-lg border border-zinc-300 px-3 py-1.5 focus:border-blue-500 focus:outline-none"
          />
          <button onClick={signup} disabled={busy}
                  className="rounded-lg border border-zinc-300 px-3 py-1.5 font-medium hover:bg-zinc-50 disabled:opacity-50">
            무료 키 발급
          </button>
          <button onClick={upgrade} disabled={busy}
                  className="rounded-lg bg-zinc-900 px-3 py-1.5 font-medium text-white hover:bg-zinc-700 disabled:opacity-50">
            Pro 업그레이드
          </button>
        </div>
        <div>
          <label className="mb-1 block text-xs text-zinc-500">API 키 (요청 헤더에 자동 첨부)</label>
          <input
            value={apiKey}
            onChange={(e) => saveKey(e.target.value)}
            placeholder="ts_..."
            className="w-full rounded-lg border border-zinc-300 px-3 py-1.5 font-mono text-xs focus:border-blue-500 focus:outline-none"
          />
        </div>
        {msg && <p className="text-xs text-zinc-600">{msg}</p>}
        <p className="text-xs text-zinc-400">
          무료 플랜: 24시간당 신규 생성 10건. 캐시된 리포트 조회는 무제한 무료입니다.
        </p>
      </div>
    </details>
  );
}
