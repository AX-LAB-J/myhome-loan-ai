// Display formatting and affordability-band helpers shared by every screen.
import type { Bands } from './api'

export type Range = 'all' | 'safe' | 'possible' | 'limit'
export type BandName = Exclude<Range, 'all'> | 'outside'

export const bandLabels: Record<BandName, string> = { safe: '안정권', possible: '가능권', limit: '한계권', outside: '범위 밖' }

export const won = (value: number | null | undefined) => value == null ? '—'
  : Math.abs(value) >= 1e8 ? `${(value / 1e8).toLocaleString('ko-KR', { maximumFractionDigits: 2 })}억 원`
  : `${Math.round(value / 1e4).toLocaleString('ko-KR')}만 원`
export const pct = (value: number | null | undefined) => value == null ? '—' : `${(value * 100).toFixed(1)}%`
export const money = (n: number | null | undefined) => n == null ? '정보 없음' : won(n)
export const eok = (n: number | null | undefined) => n == null ? '—' : `${(n / 1e8).toFixed(2)}억`
export const rateLabel = (rate: number) => Math.round(rate * 100) / 100

export const hasPriceRange = (lower: number, upper: number) => upper - lower >= 10_000
export const boundaryMoney = (value: number, fine = false) => fine
  ? `${Math.round(value / 10_000).toLocaleString('ko-KR')}만원`
  : eok(value)
export const tierCap = (lower: number, upper: number) => hasPriceRange(lower, upper)
  ? `${boundaryMoney(upper, upper - lower < 1_000_000)} 이하`
  : '해당 가격 없음'

const accountNames: Record<string, string> = { CHECKING: '입출금', SAVINGS: '저축' }
const loanNames: Record<string, string> = { MORTGAGE: '주택담보대출', CREDIT_LINE: '마이너스통장' }
export const accountName = (type: string) => accountNames[type] ?? type
export const loanName = (type: string) => loanNames[type] ?? type

export function band(price: number, bands?: Bands): BandName {
  if (!bands) return 'outside'
  if (price <= bands.safe) return 'safe'
  if (price <= bands.possible) return 'possible'
  if (price <= bands.maximum) return 'limit'
  return 'outside'
}

/** Upper price of a range tab ('limit' tab means up to the limit-band ceiling). */
export const rangeCap = (range: Exclude<Range, 'all'>, bands: Bands) =>
  bands[range === 'limit' ? 'maximum' : range]

export function withinRange(price: number, range: Range, bands?: Bands): boolean {
  if (range === 'all') return true
  if (!bands) return false
  return price <= rangeCap(range, bands)
}
