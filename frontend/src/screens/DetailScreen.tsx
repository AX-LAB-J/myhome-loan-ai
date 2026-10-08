import type { Buyer, PlanResult, Trade } from '../api'
import { BandBar, PlanWarnings, Row } from '../components/ui'
import { band, bandLabels, money, rateLabel } from '../format'

export default function DetailScreen({ trade, buyer, calcBuyer, plan }: {
  trade: Trade; buyer: Buyer; calcBuyer: Buyer; plan: PlanResult | null
}) {
  const current = trade.plan
  const stressed = trade.stress_plan
  const name = band(trade.purchase_reference_price, plan?.bands)
  return <>
    <section className="mobile-card hero">
      <span>{buyer.sigungu} · 전용 {trade.exclusive_area_m2}㎡</span>
      <h1>{trade.apt_name}</h1>
      <span className={'status ' + name}>{bandLabels[name]}</span>
      <p>최근 실거래</p>
      <strong>{money(trade.purchase_reference_price)}</strong>
      {plan && <BandBar bands={plan.bands} price={trade.purchase_reference_price} />}
      <PlanWarnings trade={trade} />
    </section>
    <section className="mobile-card">
      <h2>자금 계획</h2>
      <Row label="필요 자기자금" value={money(current ? current.price + current.costs - current.loan : null)} />
      <Row label="내 가용 자금 · 예비비 제외" value={money(current?.available)} />
      <Row label="예상 대출" value={money(current?.loan)} />
      {!!current?.shortfall && <p className="warning">{money(current.shortfall)}이 부족해요.</p>}
    </section>
    <section className="mobile-card">
      <h2>매달 남는 돈</h2>
      <Row label="월 소득" value={money(buyer.income / 12)} />
      <Row label="월 총지출" value={<>− {money(buyer.consumption)}</>} />
      <Row label="예상 월 상환" value={<>− {money(current?.payment)}</>} />
      <Row label="남는 돈" value={money(current?.surplus)} total />
    </section>
    <section className="mobile-card">
      <h2>금리가 1%p 오르면</h2>
      <div className="comparison">
        <span>지금 {calcBuyer.mortgage_rate}%</span><span>{rateLabel(calcBuyer.mortgage_rate + 1)}%</span>
        <b>{money(current?.payment)}</b><b>{money(stressed?.payment)}</b>
        <b>{money(current?.surplus)}</b><b>{money(stressed?.surplus)}</b>
      </div>
      <p className="hint">대출 원금과 만기는 그대로 두고 금리만 바꿔 계산해요.</p>
    </section>
    <section className="mobile-card">
      <h2>데이터 기준</h2>
      <p>제공 CSV 거래 참조값 · {trade.reference_deal_date}</p>
      <p className="hint">실제 매물이나 금융기관의 대출 심사 결과와 다를 수 있어요.</p>
    </section>
  </>
}
