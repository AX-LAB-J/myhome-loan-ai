import type { Buyer } from '../api'
import { NumberInput, Row } from '../components/ui'

export default function AssumptionsScreen({ draft, onDraft, saving, onSave }: {
  draft: Buyer; onDraft: <K extends keyof Buyer>(key: K, value: Buyer[K]) => void
  saving: boolean; onSave: () => void
}) {
  return <>
    <p className="intro">대출 규제 기준이 아니라 계산에 쓰는 가정이에요. 저장하면 구간을 다시 계산해요.</p>
    <section className="mobile-card">
      <h2>내 기준</h2>
      <NumberInput label="목표 여유자금" value={draft.target_surplus / 1e4} onChange={v => onDraft('target_surplus', v * 1e4)} unit="만원/월" step={10} />
      <NumberInput label="예비비" value={draft.reserve / 1e4} onChange={v => onDraft('reserve', v * 1e4)} unit="만원" step={100} />
    </section>
    <section className="mobile-card">
      <h2>대출 조건</h2>
      <NumberInput label="주담대 금리" value={draft.mortgage_rate} onChange={v => onDraft('mortgage_rate', v)} unit="%" step={0.1} max={25} />
      <NumberInput label="만기" value={draft.term} onChange={v => onDraft('term', v)} unit="년" max={50} />
      <Row label="상환 방식" value="원리금균등" />
      <label className="switch-row">한도대출도 포함 <input type="checkbox" checked={draft.allow_credit} onChange={e => onDraft('allow_credit', e.target.checked)} /></label>
      {draft.allow_credit && <NumberInput label="한도대출 금리" value={draft.credit_rate} onChange={v => onDraft('credit_rate', v)} unit="%" step={0.1} max={25} />}
    </section>
    <section className="mobile-card">
      <h2>계산 기준</h2>
      <NumberInput label="주담대 비율 상한" value={draft.ltv_cap * 100} onChange={v => onDraft('ltv_cap', v / 100)} unit="%" max={100} />
      <NumberInput label="상환 부담 비율 상한" value={draft.dsr_cap * 100} onChange={v => onDraft('dsr_cap', v / 100)} unit="%" max={100} />
      <NumberInput label="부대비용 적립률" value={draft.cost_rate * 100} onChange={v => onDraft('cost_rate', v / 100)} unit="%" step={0.5} max={30} />
    </section>
    <button className="primary" disabled={saving} onClick={onSave}>저장하고 다시 계산</button>
    <p className="hint">저장하면 AI 대화가 새로 시작돼요.</p>
  </>
}
