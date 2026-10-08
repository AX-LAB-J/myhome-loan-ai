import type { CustomerDetail } from '../api'
import { Row } from '../components/ui'

const SOURCES = ['주택 구매 이력', '고객 재무·현금흐름', '부동산 상세·거래 참조', '대출 이력', '고객 프로필·부채 요약·계좌']

export default function ConnectionsScreen({ customerId, customer, onFinance }: {
  customerId: number | null; customer: CustomerDetail | null; onFinance: () => void
}) {
  return <>
    <p className="intro">고객 프로필·부채 요약·계좌 CSV를 기존 주택·대출 DB에 보강해 고객별 조회와 계산에 사용하고 있습니다.</p>
    <section className="mobile-card">
      <h2>연결된 데이터</h2>
      {SOURCES.map(name => <Row key={name} label={name} value="연결됨" />)}
      <p className="hint">고객 ID와 부동산 ID로 고객 프로필·계좌·구매·부동산 상세·대출 기록을 연결합니다. 현재 화면의 고객 정보와 단지 검색은 이 데이터에서 가져옵니다.</p>
    </section>
    <section className="mobile-card">
      <h2>선택한 고객</h2>
      {customerId == null ? <p>메뉴에서 고객을 선택하면 연결된 기록을 확인할 수 있습니다.</p> : <>
        <Row label="고객 ID" value={customerId} />
        <Row label="대출 기록" value={`${customer?.loans.length ?? 0}건`} />
        <button className="secondary" onClick={onFinance}>내 재무 정보 보기</button>
      </>}
    </section>
    <p className="hint">현재 연결은 제공 CSV를 로컬 DB로 가져온 방식입니다. 금융기관의 실시간 마이데이터 연동이나 동의 내역은 포함되지 않습니다.</p>
  </>
}
