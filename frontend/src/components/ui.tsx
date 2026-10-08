// Small presentational pieces reused across screens.
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import type { Bands, Trade } from '../api'
import { boundaryMoney, hasPriceRange, money } from '../format'

export function Row({ label, value, total = false }: { label: ReactNode; value: ReactNode; total?: boolean }) {
  return <div className={total ? 'amount-row total' : 'amount-row'}><span>{label}</span><b>{value}</b></div>
}

const LABEL_GAP = 6   // px between neighbouring labels on one line
const LABEL_LINE = 15 // px per label line

type Tick = { value: number; label: string; name: string }
type Placement = { left: number; row: number }

/** Put each label under its tick; a label that would touch the previous one on a line
 * drops to the next line, and labels are kept inside the bar's width. */
function placeLabels(box: HTMLElement, ticks: Tick[], total: number): Placement[] {
  const width = box.clientWidth
  const lineEnds: number[] = []
  return Array.from(box.children as HTMLCollectionOf<HTMLElement>).map((span, i) => {
    const w = span.offsetWidth
    const center = ticks[i].value / total * width
    const left = i === 0 ? 0 : Math.min(Math.max(center - w / 2, 0), Math.max(0, width - w))
    let row = lineEnds.findIndex(end => left >= end + LABEL_GAP)
    if (row === -1) { row = lineEnds.length; lineEnds.push(0) }
    lineEnds[row] = left + w
    return { left, row }
  })
}

export function BandBar({ price, bands }: { price?: number; bands: Bands }) {
  const total = Math.max(bands.maximum * 1.12, price ?? 0, 1)
  const at = (value: number) => `${value / total * 100}%`
  const ticks: Tick[] = [
    { value: 0, label: '0', name: '시작' },
    ...(hasPriceRange(0, bands.safe) ? [{ value: bands.safe, label: boundaryMoney(bands.safe), name: '안정권 상한' }] : []),
    ...(hasPriceRange(bands.safe, bands.possible) ? [{ value: bands.possible, label: boundaryMoney(bands.possible, bands.possible - bands.safe < 1_000_000), name: '가능권 상한' }] : []),
    ...(hasPriceRange(bands.possible, bands.maximum) ? [{ value: bands.maximum, label: boundaryMoney(bands.maximum, bands.maximum - bands.possible < 1_000_000), name: '한계권 상한' }] : []),
  ]
  const tickKey = ticks.map(t => `${t.value}:${t.label}`).join('|')
  const endsRef = useRef<HTMLDivElement>(null)
  const [placement, setPlacement] = useState<Placement[] | null>(null)
  useLayoutEffect(() => {
    const box = endsRef.current
    if (!box) return
    const update = () => setPlacement(current => {
      const next = placeLabels(box, ticks, total)
      return JSON.stringify(next) === JSON.stringify(current) ? current : next
    })
    update()
    const observer = new ResizeObserver(update)
    observer.observe(box)
    return () => observer.disconnect()
    // ticks/total are fully described by tickKey
  }, [tickKey, total])
  const lines = placement ? Math.max(...placement.map(p => p.row)) + 1 : 1
  return <div className="band-wrap">
    <div className="band-bar">
      <i className="safe" style={{ width: at(bands.safe) }} />
      <i className="possible" style={{ width: at(Math.max(0, bands.possible - bands.safe)) }} />
      <i className="limit" style={{ width: at(Math.max(0, bands.maximum - bands.possible)) }} />
      <i className="outside" style={{ flex: 1 }} />
      {ticks.slice(1).map(tick => <b key={tick.name} className="band-tick" style={{ left: at(tick.value) }} />)}
      {price != null && <span className="band-pointer" style={{ left: `${Math.min(100, price / total * 100)}%` }}>▼</span>}
    </div>
    <div className="band-ends" ref={endsRef} style={{ height: lines * LABEL_LINE }}>
      {ticks.map((tick, i) => {
        const spot = placement?.[i]
        const style = spot
          ? { left: spot.left, top: spot.row * LABEL_LINE, transform: 'none' }
          : { left: at(tick.value), visibility: 'hidden' as const }
        return <span key={tick.name} title={tick.name} className={spot && spot.row > 0 ? 'lower' : undefined} style={style}>{tick.label}</span>
      })}
    </div>
  </div>
}

export function NumberInput({ label, value, onChange, unit, step = 1, max }: {
  label: string; value: number; onChange: (n: number) => void; unit: string; step?: number; max?: number
}) {
  // Keep the typed text separately so clearing the field does not snap back to the old value.
  const [text, setText] = useState(String(value))
  useEffect(() => setText(String(value)), [value])
  return <label className="mobile-field"><span>{label}</span><span className="mobile-number">
    <input type="number" min="0" max={max} step={step} value={text} onChange={e => {
      const next = e.target.value
      setText(next)
      if (next !== '' && Number.isFinite(Number(next))) onChange(Number(next))
    }} onBlur={() => setText(String(value))} />
    <em>{unit}</em>
  </span></label>
}

export function PlanWarnings({ trade }: { trade: Trade }) {
  return <>
    {trade.plan?.loan_basis === 'limit_scenario' && <p className="warning">한계권 가정: 모델 예측 대출 비율·설정 DSR을 넘길 수 있어요. 실제 승인 가능액이 아닙니다.</p>}
    {trade.plan && trade.plan.surplus < 0 && <p className="warning">월 적자 예상 · 추천 대상이 아닙니다.</p>}
  </>
}

export function ChatRecommendation({ trade, reason, onOpen }: { trade: Trade; reason: string; onOpen: () => void }) {
  return <button className="chat-recommendation" onClick={onOpen}>
    <strong>{trade.apt_name}</strong><span>{trade.address} · 전용 {trade.exclusive_area_m2}㎡</span>
    <span>거래 참조가격 {money(trade.purchase_reference_price)} · {trade.reference_deal_date}</span>
    <span>예상 대출 {money(trade.plan?.loan)} (주담대 {money(trade.plan?.mortgage)}{trade.plan?.credit ? `, 한도대출 ${money(trade.plan.credit)}` : ''})</span>
    <span>예상 월 상환 {money(trade.plan?.payment)} · 월 잔여금 {money(trade.plan?.surplus)}</span>
    <small>{reason}</small>
  </button>
}
