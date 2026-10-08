import type { Buyer, CustomerDetail } from '../api'
import { NumberInput, Row } from '../components/ui'
import { accountName, loanName, money } from '../format'

export default function FinanceScreen({ customerId, customer, buyer, draft, onDraft, saving, onSave }: {
  customerId: number; customer: CustomerDetail | null; buyer: Buyer; draft: Buyer
  onDraft: <K extends keyof Buyer>(key: K, value: Buyer[K]) => void; saving: boolean; onSave: () => void
}) {
  const budget = customer?.customer.consumption_source === 'budget'
  const months = customer?.customer.cf_months
  return <>
    <p className="intro">고객 {customerId}의 제공 CSV 재무정보입니다. 현금흐름 관측기간: {months == null ? '정보 없음' : `${months}개월`}입니다.</p>
    {budget && <p className="hint">월 지출은 관측 거래액이 아닌 제공된 소비 예산입니다. 주소는 시·도까지만 제공되어 검색 시 시·군·구를 선택해 주세요.</p>}
    <section className="mobile-card">
      <h2>월 소득·지출</h2>
      <Row label="월 소득 · 가구 연소득÷12" value={money(buyer.income / 12)} />
      <Row label={budget ? '월 소비 예산' : '월 총지출'} value={money(buyer.consumption)} />
      <Row label="기존 대출 월 상환" value={money(buyer.existing_payment)} />
    </section>
    <section className="mobile-card">
      <h2>자산</h2>
      <Row label={budget ? '계산에 사용한 계좌 잔액 합계' : '금융 자산'} value={money(buyer.assets)} />
      {budget && customer && <Row label="금융 자산" value={money(customer.customer.financial_assets_estimated)} />}
      <p className="hint">계좌 잔액 합계와 금융 자산은 서로 다른 값입니다.</p>
    </section>
    <section className="mobile-card">
      <h2>연결된 계좌</h2>
      {customer?.accounts.map((account, i) => <Row key={i} label={accountName(account.account_type)} value={money(account.balance)} />)}
    </section>
    <section className="mobile-card">
      <h2>대출 잔액</h2>
      {customer?.loans.length
        ? customer.loans.map((loan, i) => <Row key={i} label={loanName(loan.loan_type)} value={money(loan.outstanding_balance)} />)
        : <p>대출 기록 없음</p>}
    </section>
    {customer?.property && <section className="mobile-card">
      <h2>보유 주택 참조</h2>
      <Row label="단지" value={customer.property.apt_name} />
      <Row label="전용면적 · 층" value={`${customer.property.exclusive_area_m2}㎡ · ${customer.property.floor == null ? '정보 없음' : customer.property.floor + '층'}`} />
      <Row label="거래 참조가격" value={money(customer.property.purchase_reference_price)} />
      <p className="hint">참조 거래일 {customer.property.reference_deal_date}</p>
    </section>}
    <section className="mobile-card">
      <h2>직접 입력</h2>
      <NumberInput label="기타 동원 자금" value={draft.other_funds / 1e4} onChange={v => onDraft('other_funds', v * 1e4)} unit="만원" step={10} />
      <p className="hint">금융자산 원천값과 별도로 계산에 사용합니다.</p>
    </section>
    <button className="primary" disabled={saving} onClick={onSave}>저장하고 다시 계산</button>
  </>
}
