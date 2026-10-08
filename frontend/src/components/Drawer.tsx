import { House, X } from 'lucide-react'
import type { CustomerDetail, DemoCustomer } from '../api'
import type { Screen } from '../screens'

export default function Drawer({ customerLabel, customer, query, onQuery, options, onPick, onGo, onClose }: {
  customerLabel: string; customer: CustomerDetail | null; query: string; onQuery: (q: string) => void
  options: DemoCustomer[]; onPick: (id: number) => void; onGo: (screen: Screen) => void; onClose: () => void
}) {
  return <div className="overlay" onClick={onClose}>
    <nav className="drawer" aria-label="메인 메뉴" onClick={e => e.stopPropagation()}>
      <div className="title-row">
        <button className="header-home" type="button" aria-label="내 구매력 홈으로" onClick={() => onGo('home')}><House size={20} /></button>
        <h2>내 집 마련</h2>
        <button className="plain-icon" aria-label="메뉴 닫기" onClick={onClose}><X /></button>
      </div>
      <p>감당할 수 있는 집부터 찾기</p>
      <div className="menu-card">
        <strong>{customerLabel}</strong>
        <span>{customer ? (customer.customer.is_home_owner ? '주택 보유' : '무주택') : '제공 CSV 고객'}</span>
        <label>사용자 바꾸기<input type="search" enterKeyHint="search" autoComplete="off" placeholder="고객 ID 또는 이름 검색" value={query} onChange={e => onQuery(e.target.value)} /></label>
        <div className="customer-options">{options.map(c => <button key={c.customer_id} onClick={() => onPick(c.customer_id)}>
          고객 {c.display_name ? `${c.display_name} · ` : ''}{c.customer_id} · {c.age}세 · {c.household_size}인 가구
        </button>)}</div>
      </div>
      <small>찾기</small>
      <button onClick={() => onGo('home')}>내 구매력</button>
      <button onClick={() => onGo('explore')}>지역·단지 찾기</button>
      <small>내 정보</small>
      <button onClick={() => onGo('finance')}>내 재무 정보</button>
      <button onClick={() => onGo('assumptions')}>계산 가정</button>
      <small>근거와 설정</small>
      <button onClick={() => onGo('connections')}>데이터 연결 현황</button>
      <p className="drawer-note">● 제공 CSV 기반 서비스<br />실제 매물이나 대출 승인을 보장하지 않아요.</p>
    </nav>
  </div>
}
