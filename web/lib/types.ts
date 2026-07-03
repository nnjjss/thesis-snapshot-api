// 백엔드 app/models.py의 Pydantic 모델과 1:1 대응 (단일 소스는 백엔드 — 여기는 미러)
export type Confidence = "high" | "medium" | "low";
export type Verdict = "valid" | "partially_valid" | "weakened" | "insufficient_data";

export interface CaseItem {
  claim: string;
  evidence: string;
  confidence: Confidence;
  source_url: string;
}

export interface SourceItem {
  title: string;
  url: string;
}

export interface BaseReport {
  ticker: string;
  as_of: string;
  company_summary_ko: string;
  bull_case: CaseItem[];
  bear_case: CaseItem[];
  sources: SourceItem[];
}

export interface ThesisEval {
  thesis_restated: string;
  supporting: number[];
  contradicting: number[];
  verdict: Verdict;
  reasoning_ko: string;
  watch_items_ko: string[];
}

export interface CostMeta {
  cache_hit: boolean;
  input_tokens: number;
  output_tokens: number;
  web_searches: number;
}

export interface ReportResponse {
  report: BaseReport;
  thesis_eval: ThesisEval | null;
  disclaimer: string;
  meta: CostMeta;
}
