export interface Buyer {
  age: number; income: number; assets: number; other_funds: number; consumption: number;
  price: number; area: number; sido: string; sigungu: string; existing_payment: number;
  reserve: number; cost_rate: number; ltv_cap: number; dsr_cap: number;
  mortgage_rate: number; term: number; allow_credit: boolean; credit_rate: number;
  credit_cap_ratio: number; area_tolerance: number; min_year: number; max_results: number;
  target_surplus: number;
}
export interface Plan { price: number; costs: number; available: number; need: number; mortgage: number; credit: number; loan: number; loan_basis: 'trained_model' | 'assumption' | 'limit_scenario'; shortfall: number; payment: number; dsr: number; surplus: number; eligible: boolean; reasons: string[] }
export interface LoanSummary { customers: number; original: number; balance: number }
export interface Trade { complex_id: string; apt_name: string; address: string; exclusive_area_m2: number; purchase_reference_price: number; reference_deal_date: string; build_year: number | null; plan?: Plan; stress_plan?: Plan; loan_summary: LoanSummary; latitude?: number; longitude?: number; is_owned?: boolean }
export interface Recommendation { status: 'MATCHES' | 'NO_MATCH' | 'NO_DATA' | 'NO_REFERENCE_IN_SCOPE'; candidates: Trade[]; examined: number; matched_count?: number }
export interface Meta { regions: Record<string, string[]>; defaults: Buyer; model: string; openai_ready: boolean; naver_client_id: string; synthetic: boolean }
export interface Message { role: 'user' | 'assistant'; content: string; choices?: {complex_id: string; reason: string}[]; recommendations?: { trade: Trade; reason: string }[]; caveat?: string }

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response
  try { response = await fetch('/api' + path, { ...options, headers: { 'Content-Type': 'application/json', ...options?.headers } }) }
  catch { throw new Error('서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.') }
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(typeof error?.detail === 'string' ? error.detail : `요청 실패 (${response.status})`)
  }
  return response.json() as Promise<T>
}
export const post = <T,>(path: string, body: unknown) => api<T>(path, { method: 'POST', body: JSON.stringify(body) })
export const won = (value: number | null | undefined) => value == null ? '—' : Math.abs(value) >= 1e8 ? `${(value / 1e8).toLocaleString('ko-KR', { maximumFractionDigits: 2 })}억 원` : `${Math.round(value / 1e4).toLocaleString('ko-KR')}만 원`
export const pct = (value: number | null | undefined) => value == null ? '—' : `${(value * 100).toFixed(1)}%`
