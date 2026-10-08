import type { Buyer, CustomerDetail, PatternResult, PlanResult } from '../api'
import { BandBar, Row } from '../components/ui'
import { accountName, boundaryMoney, eok, hasPriceRange, loanName, money, pct, tierCap } from '../format'

export default function HomeScreen({ buyer, calcBuyer, plan, pattern, customer, customerId, stress, onStress, onExplore }: {
  buyer: Buyer; calcBuyer: Buyer; plan: PlanResult | null; pattern: PatternResult | null
  customer: CustomerDetail | null; customerId: number; stress: boolean
  onStress: (on: boolean) => void; onExplore: () => void
}) {
  const bands = plan?.bands
  const prediction = pattern?.loan_prediction
  const loanTotal = customer?.loans.reduce((sum, loan) => sum + loan.outstanding_balance, 0) ?? 0
  return <>
    <section className="mobile-card hero">
      <span>지금 소비를 유지하며 감당할 수 있는 집값 · 안정권 상한</span>
      {stress && <p className="warning">금리 +1%p 적용 중 · 주담대 {calcBuyer.mortgage_rate}%</p>}
      <strong>{bands && !hasPriceRange(0, bands.safe) ? '해당 가격 없음' : <>{eok(bands?.safe)} <small>이하</small></>}</strong>
      {bands && <p className="hint">가능권 {tierCap(bands.safe, bands.possible)} · 한계권 {tierCap(bands.possible, bands.maximum)}</p>}
      {bands && <BandBar bands={bands} />}
    </section>
    {customer?.customer.consumption_source === 'budget' && <p className="hint">이 고객의 구매력 계산에는 계좌 잔액 합계와 제공된 월 소비 예산을 사용합니다. 시·군·구와 희망 주택 가격·면적은 기본 검색값이므로 지역·단지 찾기에서 조정해 주세요.</p>}
    {plan && bands && <section className="mobile-card"><h2>내 구매력 구간</h2><div className="band-grid">
      <div><b className="dot safe" /> 안정권 <strong>{tierCap(0, bands.safe)}</strong><small>목표 여유자금 유지 · DSR {Math.round(plan.band_assumptions.safe_dsr_cap * 100)}% 이하</small></div>
      <div><b className="dot possible" /> 가능권 <strong>{tierCap(bands.safe, bands.possible)}</strong><small>월 적자 없음 · DSR {Math.round(plan.band_assumptions.possible_dsr_cap * 100)}% 이하</small></div>
      <div><b className="dot limit" /> 한계권 <strong>{tierCap(bands.possible, bands.maximum)}</strong><small>월 잔여금 {money(plan.band_assumptions.limit_monthly_surplus)} 경계 · DSR 상한 초과 가능</small></div>
      <div><b className="dot outside" /> 범위 밖 <strong>{boundaryMoney(bands.maximum)} 초과</strong><small>한계권 시나리오의 자금·월 잔여금 기준 초과</small></div>
    </div></section>}
    <section className="mobile-card">
      <h2>매달 남는 돈 <small>안정권 상단 기준</small></h2>
      <Row label="월 소득 · 연소득÷12" value={money(buyer.income / 12)} />
      <Row label="월 총지출" value={<>− {money(buyer.consumption)}</>} />
      <Row label="기존 대출 상환" value={<>− {money(buyer.existing_payment)}</>} />
      <Row label="예상 월 상환" value={<>− {money(plan?.safe_plan?.payment)}</>} />
      <Row label="남는 돈" value={money(plan?.safe_plan?.surplus)} total />
      <p className="hint">목표 여유자금 월 {money(buyer.target_surplus)}과 비교해서 구간을 나눠요.</p>
    </section>
    {prediction && <section className="mobile-card">
      <h2>AI의 예상 대출 <small>안정권 상한 {money(prediction.basis_price)} 기준</small></h2>
      <Row label={`주택담보대출 · 집값의 ${pct(prediction.mortgage_ratio)}`} value={money(prediction.mortgage)} />
      <Row label={`마이너스통장 · 집값의 ${pct(prediction.credit_ratio)}`} value={money(prediction.credit)} />
      <Row label="예상 대출 합계" value={money(prediction.total)} total />
      <p className="hint">고객 {customerId}의 재무정보로 안정권 상한 가격의 집을 살 때 AI가 예측한 대출 비율입니다. 승인 한도가 아닙니다.</p>
    </section>}
    {customer && <section className="mobile-card">
      <h2>내 자산</h2>
      {customer.accounts.map((account, i) => <Row key={i} label={accountName(account.account_type)} value={money(account.balance)} />)}
      <Row label="계좌 잔액 합계" value={money(customer.customer.account_balance_total)} total />
      {customer.customer.consumption_source !== 'budget' && <Row label="금융 자산" value={money(buyer.assets)} />}
      {customer.loans.map((loan, i) => <Row key={i} label={`${loanName(loan.loan_type)} 잔액`} value={<>− {money(loan.outstanding_balance)}</>} />)}
      {customer.loans.length > 0 && <Row label="대출 잔액 합계" value={<>− {money(loanTotal)}</>} total />}
    </section>}
    <label className="switch-row">금리 +1%p로 다시 계산 <input type="checkbox" checked={stress} onChange={e => onStress(e.target.checked)} /></label>
    {stress && <p className="hint">설정 금리 {buyer.mortgage_rate}% 대신 {calcBuyer.mortgage_rate}%로 모든 구간·대출·단지 계산을 다시 했어요. 끄면 원래 금리로 돌아가요.</p>}
    <button className="primary" onClick={onExplore}>이 범위에서 지역 찾기</button>
  </>
}
