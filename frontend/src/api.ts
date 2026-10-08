// Shapes returned by the FastAPI server (housing_app/api.py) and a small fetch wrapper.

export interface Buyer {
  age: number; income: number; assets: number; other_funds: number; consumption: number;
  price: number; area: number; sido: string; sigungu: string; existing_payment: number;
  reserve: number; cost_rate: number; ltv_cap: number; dsr_cap: number;
  mortgage_rate: number; term: number; allow_credit: boolean; credit_rate: number;
  credit_cap_ratio: number; area_tolerance: number; min_year: number; max_results: number;
  target_surplus: number;
}
export interface Plan {
  price: number; costs: number; available: number; need: number; mortgage: number; credit: number;
  loan: number; loan_basis: 'trained_model' | 'assumption' | 'limit_scenario'; shortfall: number;
  payment: number; dsr: number; surplus: number; eligible: boolean; reasons: string[];
}
export interface LoanSummary { customers: number; original: number; balance: number }
export interface Trade {
  complex_id: string; apt_name: string; address: string; exclusive_area_m2: number;
  purchase_reference_price: number; reference_deal_date: string; build_year: number | null;
  plan?: Plan; stress_plan?: Plan; loan_summary: LoanSummary;
  latitude?: number; longitude?: number; is_owned?: boolean;
}
export interface Meta {
  regions: Record<string, string[]>; defaults: Buyer; model: string; openai_ready: boolean;
  naver_client_id: string; synthetic: boolean;
}
export interface Message {
  role: 'user' | 'assistant'; content: string; choices?: { complex_id: string; reason: string }[];
  recommendations?: { trade: Trade; reason: string }[]; caveat?: string;
}
export type Bands = { safe: number; possible: number; maximum: number }
export interface PlanResult {
  plan: Plan; safe_plan: Plan | null; max_affordable: number; bands: Bands; binding_reasons: string[];
  band_assumptions: {
    safe_dsr_cap: number; possible_dsr_cap: number; limit_monthly_surplus: number;
    limit_uses_model_loan_cap: boolean;
  };
}
export interface ExploreResult { total: number; rows: Trade[] }
export interface LoanPrediction {
  basis_price: number; mortgage_ratio: number; credit_ratio: number; mortgage: number;
  credit: number; total: number;
}
export interface PatternResult {
  description: Record<string, string>; share: Record<string, number>;
  probability: Record<string, number>; loan_prediction: LoanPrediction | null;
}
export interface DemoCustomer { customer_id: number; age: number; household_size: number; display_name?: string | null }
export interface CustomerDetail {
  customer: {
    customer_id: number; name: string; age: number; household_annual_income: number;
    financial_assets_estimated: number; account_balance_total: number;
    avg_monthly_consumption: number; monthly_debt_service: number; is_home_owner: number;
    cf_months: number | null; sido: string; sigungu: string | null;
    exclusive_area_m2: number | null; purchase_reference_price: number | null;
    consumption_source: 'budget' | 'observed'; residence_region: string;
  };
  loans: { loan_type: string; outstanding_balance: number; monthly_payment_estimated: number | null }[];
  accounts: { account_type: string; balance: number; status: string }[];
  property: {
    real_asset_id: number; apt_name: string; exclusive_area_m2: number; floor: number | null;
    build_year: number | null; reference_deal_date: string; purchase_reference_price: number;
    reference_trade_id: string;
  } | null;
}
export interface ChatReply {
  answer: string; choices: Message['choices']; recommendations: Message['recommendations'];
  caveat: string; applied_region: { sido: string; sigungu: string } | null;
}
export interface MapResult { markers: Trade[]; missing: number }

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch('/api' + path, { ...options, headers: { 'Content-Type': 'application/json', ...options?.headers } })
  } catch {
    throw new Error('서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.')
  }
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(typeof error?.detail === 'string' ? error.detail : `요청 실패 (${response.status})`)
  }
  return response.json() as Promise<T>
}
export const post = <T,>(path: string, body: unknown) => api<T>(path, { method: 'POST', body: JSON.stringify(body) })
export const deleteChat = (threadId: string) => api(`/chat/${threadId}`, { method: 'DELETE' }).catch(() => undefined)
