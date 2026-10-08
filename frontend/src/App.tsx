import { useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, ArrowRight, BarChart3, Building2, ChevronDown, CircleHelp, Home, Landmark, MapPinned, Menu, MessageCircle, Plus, Send, SlidersHorizontal, X } from 'lucide-react'
import NaverMap from './NaverMap'
import { api, post, pct, won } from './api'
import type { Buyer, Message, Meta, Plan, Recommendation, Trade } from './api'

type Page = 'chat' | 'map' | 'homes' | 'loans' | 'plan' | 'validation'
type Customer = { customer_id: number; apt_name: string; exclusive_area_m2: number; purchase_reference_price: number; all_original: number; all_balance: number; all_loan_count: number }
type Loan = { loan_id: number; loan_type: string; loan_purpose: string; original_principal: number; outstanding_balance: number; interest_rate: number; opened_at: string }
type Region = { sido: string; sigungu: string; trades: number; avg_price: number; customers: number; original: number; balance: number }
type Patterns = { description: Record<string, string>; share: Record<string, number>; probability: Record<string, number>; stats: Record<string, string>[]; alternatives?: { region_basis: string; regions: Record<string, string>[]; price_bands: Record<string, string>[]; area_bands: Record<string, string>[] } }
type Validation = { model: { rows: number; selected: Record<string, string>; results: Record<string, string | number>[] }; audit: { source_kind: string; checks: Record<string, boolean>; limitations: string[] } }

const nav: { page: Page; title: string; icon: typeof Home }[] = [
  { page: 'chat', title: 'AI 채팅', icon: MessageCircle },
  { page: 'map', title: '네이버 지도', icon: MapPinned },
  { page: 'homes', title: '추천 단지', icon: Building2 },
  { page: 'loans', title: '지역·고객 대출', icon: Landmark },
  { page: 'plan', title: '내 대출 계획', icon: BarChart3 },
  { page: 'validation', title: '검증 결과', icon: CircleHelp },
]
const initial: Buyer = { age: 31, income: 70_000_000, assets: 100_000_000, other_funds: 0, consumption: 2_500_000, price: 500_000_000, area: 59, sido: '서울특별시', sigungu: '노원구', existing_payment: 0, reserve: 0, cost_rate: .04, ltv_cap: .7, dsr_cap: .4, mortgage_rate: 4.5, term: 30, allow_credit: false, credit_rate: 7, credit_cap_ratio: .12, area_tolerance: .2, min_year: 2022, max_results: 3, target_surplus: 1_000_000 }
const statusText: Record<string, string> = { NO_DATA: '이 지역의 자료가 없습니다.', NO_REFERENCE_IN_SCOPE: '선택한 연도·면적의 거래 참조자료가 없습니다.', NO_MATCH: '가격·자금·상환 조건을 모두 만족하는 단지가 없습니다.' }

function Table({ rows, columns }: { rows: Record<string, unknown>[]; columns: [string, string][] }) {
  if (!rows.length) return <p className="muted">표시할 자료가 없습니다.</p>
  return <div className="table-scroll"><table><thead><tr>{columns.map(([key, label]) => <th key={key}>{label}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{columns.map(([key]) => <td key={key}>{String(row[key] ?? '—')}</td>)}</tr>)}</tbody></table></div>
}

function Metric({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return <div className={'metric ' + (accent ? 'accent' : '')}><span>{label}</span><strong>{value}</strong></div>
}

function CandidateCard({ trade, number }: { trade: Trade; number?: number }) {
  const plan = trade.plan!
  return <article className="candidate-card"><div className="card-top"><div className="candidate-number">{number ?? <Home size={19} />}</div><div><h3>{trade.apt_name}</h3><p>{trade.address} · 전용 {trade.exclusive_area_m2}㎡ · {trade.reference_deal_date} 거래</p></div></div>
    <div className="metrics four"><Metric label="거래 참조가격" value={won(plan.price)} accent /><Metric label="필요 대출" value={won(plan.loan)} /><Metric label="예상 월 상환" value={won(plan.payment)} /><Metric label="상환 부담" value={pct(plan.dsr)} /></div>
    <p className="card-note">주담대 {won(plan.mortgage)} · 한도대출 {won(plan.credit)} · 부대비용 {won(plan.costs)} · 월 잉여 {won(plan.surplus)}</p>
    <p className="card-note">해당 단지의 합성 고객 {trade.loan_summary.customers}명 · 최초 원금 합계 {won(trade.loan_summary.original)} · 잔액 합계 {won(trade.loan_summary.balance)}</p>
  </article>
}

function NumberField({ label, value, onChange, step = 1, min = 0, max, suffix = '' }: { label: string; value: number; onChange: (value: number) => void; step?: number; min?: number; max?: number; suffix?: string }) {
  return <label className="field"><span>{label}</span><span className="field-input"><input type="number" value={value} step={step} min={min} max={max} onChange={event => onChange(Number(event.target.value))} />{suffix && <em>{suffix}</em>}</span></label>
}

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null)
  const [buyer, setBuyer] = useState<Buyer>(initial)
  const [page, setPage] = useState<Page>('chat')
  const [sidebar, setSidebar] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [messageText, setMessageText] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null)
  const [markers, setMarkers] = useState<Trade[]>([])
  const [missing, setMissing] = useState(0)
  const [mapBusy, setMapBusy] = useState(false)
  const [mapNonce, setMapNonce] = useState(0)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [trades, setTrades] = useState<Trade[]>([])
  const [tradeTotal, setTradeTotal] = useState(0)
  const [tradePage, setTradePage] = useState(0)
  const [customerTotal, setCustomerTotal] = useState(0)
  const [customerPage, setCustomerPage] = useState(0)
  const [selectedCustomer, setSelectedCustomer] = useState<number | null>(null)
  const [loans, setLoans] = useState<Loan[]>([])
  const [regions, setRegions] = useState<Region[]>([])
  const [plan, setPlan] = useState<{plan: Plan; max_affordable: number} | null>(null)
  const [patterns, setPatterns] = useState<Patterns | null>(null)
  const [validation, setValidation] = useState<Validation | null>(null)
  const lastSignature = useRef(JSON.stringify(initial))
  const chatBottom = useRef<HTMLDivElement>(null)
  const mapResolved = useRef(new Set<string>())
  const region = `${buyer.sido} ${buyer.sigungu}`
  const buyerSignature = useMemo(() => JSON.stringify(buyer), [buyer])
  const update = <K extends keyof Buyer>(key: K, value: Buyer[K]) => setBuyer(current => ({ ...current, [key]: value }))

  useEffect(() => { api<Meta>('/meta').then(value => { setMeta(value); setBuyer(value.defaults); lastSignature.current = JSON.stringify(value.defaults) }).catch(e => setError(e.message)) }, [])
  useEffect(() => { if (!meta) return; if (lastSignature.current !== buyerSignature) { setMessages([]); lastSignature.current = buyerSignature } }, [buyerSignature, meta])
  useEffect(() => { if (!meta) return; let active = true; post<Recommendation>('/recommendations', buyer).then(value => { if (active) setRecommendation(value) }).catch(e => { if (active) setError(e.message) }); return () => { active = false } }, [buyerSignature, meta])
  useEffect(() => { chatBottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, busy])

  useEffect(() => {
    if (page !== 'map' || !meta) return
    const key = `${buyer.sido}|${buyer.sigungu}`
    let active = true
    setMarkers([]); setMissing(0); setMapBusy(true)
    const query = `?sido=${encodeURIComponent(buyer.sido)}&sigungu=${encodeURIComponent(buyer.sigungu)}`
    api<{markers: Trade[]; missing: number}>('/map' + query).then(cached => {
      if (!active) return
      setMarkers(cached.markers); setMissing(cached.missing)
      if (!cached.missing || mapResolved.current.has(key)) { setMapBusy(false); return }
      mapResolved.current.add(key)
      return post<{markers: Trade[]; missing: number}>('/map/resolve' + query, {}).then(resolved => { if (active) { setMarkers(resolved.markers); setMissing(resolved.missing) } }).catch(e => { mapResolved.current.delete(key); throw e })
    }).catch(e => { if (active) setError(e.message) }).finally(() => { if (active) setMapBusy(false) })
    return () => { active = false }
  }, [page, buyer.sido, buyer.sigungu, meta, mapNonce])

  useEffect(() => { if (page !== 'loans' || !meta) return; api<Region[]>('/regions/summary').then(setRegions).catch(e => setError(e.message)) }, [page, meta])
  useEffect(() => {
    if (page !== 'loans' || !meta) return
    const query = `?sido=${encodeURIComponent(buyer.sido)}&sigungu=${encodeURIComponent(buyer.sigungu)}&offset=${tradePage * 100}&limit=100`
    api<{rows: Trade[]; total: number}>('/trades' + query).then(data => { setTrades(data.rows); setTradeTotal(data.total) }).catch(e => setError(e.message))
  }, [page, buyer.sido, buyer.sigungu, tradePage, meta])
  useEffect(() => {
    if (page !== 'loans' || !meta) return
    const query = `?sido=${encodeURIComponent(buyer.sido)}&sigungu=${encodeURIComponent(buyer.sigungu)}&offset=${customerPage * 100}&limit=100`
    api<{rows: Customer[]; total: number}>('/customers' + query).then(data => { setCustomers(data.rows); setCustomerTotal(data.total) }).catch(e => setError(e.message))
  }, [page, buyer.sido, buyer.sigungu, customerPage, meta])
  useEffect(() => { setSelectedCustomer(null); setLoans([]) }, [buyer.sido, buyer.sigungu])
  useEffect(() => { if (selectedCustomer !== null) api<Loan[]>(`/customers/${selectedCustomer}/loans`).then(setLoans).catch(e => setError(e.message)) }, [selectedCustomer])
  useEffect(() => { if (page !== 'plan' || !meta) return; post<{plan: Plan; max_affordable: number}>('/plan', buyer).then(setPlan).catch(e => setError(e.message)); post<Patterns>('/patterns', buyer).then(setPatterns).catch(e => setError(e.message)) }, [page, buyerSignature, meta])
  useEffect(() => { if (page === 'validation') api<Validation>('/validation').then(setValidation).catch(e => setError(e.message)) }, [page])

  async function sendMessage(event: React.FormEvent) {
    event.preventDefault()
    const text = messageText.trim()
    if (!text || busy || !meta?.openai_ready) return
    const userMessage: Message = { role: 'user', content: text }
    const conversation = [...messages, userMessage]
    setMessageText(''); setMessages(conversation); setBusy(true); setError('')
    try {
      const answer = await post<{answer: string; choices: Message['choices']; caveat: string}>('/chat', { buyer, messages: conversation.slice(-20).map(({role, content}) => ({role, content})) })
      setMessages([...conversation, { role: 'assistant', content: answer.answer, choices: answer.choices, caveat: answer.caveat }])
    } catch (e) { setMessages(messages); setError(e instanceof Error ? e.message : '답변을 받지 못했습니다.') }
    finally { setBusy(false) }
  }

  const go = (next: Page) => { setPage(next); setSidebar(false); setError(''); window.scrollTo(0, 0) }
  const selectedRegion = regions.find(row => row.sido === buyer.sido && row.sigungu === buyer.sigungu)

  return <div className="app-shell">
    {sidebar && <button className="backdrop" aria-label="메뉴 닫기" onClick={() => setSidebar(false)} />}
    <aside className={'sidebar ' + (sidebar ? 'open' : '')}>
      <div className="brand"><span className="brand-icon"><Home size={21} strokeWidth={2.4} /></span><div><strong>내 집 마련</strong><small>지역과 대출을 한눈에</small></div><button className="icon-button mobile-only" onClick={() => setSidebar(false)} aria-label="메뉴 닫기"><X size={20} /></button></div>
      <p className="nav-caption">WORKSPACE</p>
      <nav className="nav-list">{nav.map(({page: name, title, icon: Icon}) => <button key={name} className={'nav-item ' + (page === name ? 'active' : '')} onClick={() => go(name)}><Icon size={19} strokeWidth={1.8} /><span>{title}</span>{page === name && <span className="nav-dot" />}</button>)}</nav>
      <div className="sidebar-divider" />
      <button className="sidebar-action" onClick={() => { setMessages([]); go('chat') }}><Plus size={18} /> 새 대화 시작</button>
      <button className={'sidebar-action ' + (settingsOpen ? 'selected' : '')} onClick={() => setSettingsOpen(!settingsOpen)}><SlidersHorizontal size={18} /> 내 조건 설정 <ChevronDown className={settingsOpen ? 'flip' : ''} size={16} /></button>
      {settingsOpen && <div className="settings-panel">
        <p className="setting-title">주택 조건</p>
        <label className="field"><span>시·도</span><select value={buyer.sido} onChange={event => { const sido = event.target.value; setBuyer(current => ({...current, sido, sigungu: meta?.regions[sido]?.[0] ?? ''})); setCustomerPage(0); setTradePage(0) }}>{Object.keys(meta?.regions ?? {[buyer.sido]: []}).map(value => <option key={value}>{value}</option>)}</select></label>
        <label className="field"><span>시·군·구</span><select value={buyer.sigungu} onChange={event => { update('sigungu', event.target.value); setCustomerPage(0); setTradePage(0) }}>{(meta?.regions[buyer.sido] ?? [buyer.sigungu]).map(value => <option key={value}>{value}</option>)}</select></label>
        <NumberField label="주택가격 상한" value={buyer.price / 1e4} onChange={v => update('price', v * 1e4)} step={1000} suffix="만원" />
        <NumberField label="희망 전용면적" value={buyer.area} onChange={v => update('area', v)} suffix="㎡" />
        <NumberField label="면적 허용 범위" value={buyer.area_tolerance * 100} onChange={v => update('area_tolerance', v / 100)} max={100} suffix="%" />
        <NumberField label="거래 참조 시작연도" value={buyer.min_year} onChange={v => update('min_year', v)} min={2018} max={2026} />
        <NumberField label="추천 단지 수" value={buyer.max_results} onChange={v => update('max_results', v)} min={1} max={10} />
        <p className="setting-title">내 자금</p>
        <NumberField label="나이" value={buyer.age} onChange={v => update('age', v)} min={20} max={79} suffix="세" />
        <NumberField label="가구 연소득 · 세전" value={buyer.income / 1e4} onChange={v => update('income', v * 1e4)} step={100} suffix="만원" />
        <NumberField label="금융자산" value={buyer.assets / 1e4} onChange={v => update('assets', v * 1e4)} step={500} suffix="만원" />
        <NumberField label="기타 동원 자금" value={buyer.other_funds / 1e4} onChange={v => update('other_funds', v * 1e4)} step={100} suffix="만원" />
        <NumberField label="월 소비 · 대출상환 제외" value={buyer.consumption / 1e4} onChange={v => update('consumption', v * 1e4)} step={10} suffix="만원" />
        <NumberField label="기존 대출 월 상환" value={buyer.existing_payment / 1e4} onChange={v => update('existing_payment', v * 1e4)} step={10} suffix="만원" />
        <NumberField label="남겨둘 예비비" value={buyer.reserve / 1e4} onChange={v => update('reserve', v * 1e4)} step={100} suffix="만원" />
        <p className="setting-title">시뮬레이션 가정</p>
        <NumberField label="주담대 비율 상한" value={buyer.ltv_cap * 100} onChange={v => update('ltv_cap', v / 100)} min={1} max={100} suffix="%" />
        <NumberField label="상환 부담 비율 상한" value={buyer.dsr_cap * 100} onChange={v => update('dsr_cap', v / 100)} min={1} max={100} suffix="%" />
        <NumberField label="주담대 연금리" value={buyer.mortgage_rate} onChange={v => update('mortgage_rate', v)} step={.1} max={25} suffix="%" />
        <NumberField label="주담대 만기" value={buyer.term} onChange={v => update('term', v)} min={1} max={50} suffix="년" />
        <NumberField label="부대비용 적립률" value={buyer.cost_rate * 100} onChange={v => update('cost_rate', v / 100)} step={.5} max={30} suffix="%" />
        <label className="check-field"><input type="checkbox" checked={buyer.allow_credit} onChange={e => update('allow_credit', e.target.checked)} /> 한도대출도 포함</label>
        <NumberField label="한도대출 연금리" value={buyer.credit_rate} onChange={v => update('credit_rate', v)} step={.1} max={25} suffix="%" />
        <p className="tiny-note">입력값을 바꾸면 채팅 이력이 초기화됩니다. 비율은 현행 대출 규제가 아닌 계산 가정입니다.</p>
      </div>}
      <div className="sidebar-bottom"><span className="status-led" /> 합성 데이터 기반 서비스 <small>현재 매물·대출 승인 보장 없음</small></div>
    </aside>

    <main className={'main ' + (page === 'chat' ? 'chat-page' : '')}>
      <header className="topbar"><button className="icon-button" aria-label="메뉴 열기" onClick={() => setSidebar(true)}><Menu size={22} /></button><span className="topbar-title">{page === 'chat' ? '내 집 마련' : nav.find(item => item.page === page)?.title}</span><span className="topbar-region">{region}</span></header>
      {error && <div className="toast" role="alert"><span>{error}</span><button onClick={() => setError('')} aria-label="오류 닫기"><X size={16}/></button></div>}

      {page === 'chat' && <><div className="chat-scroll"><div className="chat-messages">{messages.map((message, index) => <div className={'message ' + message.role} key={index}><div className="bubble">{message.content}</div>{message.choices?.map(choice => { const match = recommendation?.candidates.find(x => x.complex_id === choice.complex_id); return <div className="chat-choice" key={choice.complex_id}>{match && <CandidateCard trade={match} />}<p>{choice.reason}</p></div> })}{message.caveat && <p className="tiny-note">{message.caveat}</p>}</div>)}{busy && <div className="message assistant"><div className="bubble typing">DB 후보와 조건을 확인하는 중<span className="dots">···</span></div></div>}<div ref={chatBottom} /></div></div><form className="composer-wrap" onSubmit={sendMessage}><div className="composer"><textarea aria-label="채팅 입력" placeholder={meta?.openai_ready ? '내 조건에 맞는 아파트를 물어보세요' : 'OpenAI 키 설정이 필요합니다'} value={messageText} onChange={e => setMessageText(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit() } }} disabled={!meta?.openai_ready || busy} rows={1} maxLength={4000} /><button type="submit" aria-label="메시지 보내기" disabled={!messageText.trim() || busy || !meta?.openai_ready}><Send size={18} /></button></div><p>합성 DB의 과거 거래 참조값입니다. 실제 매물·승인 결과가 아닙니다.</p></form></>}

      {page === 'map' && <section className="content map-content"><div className="section-heading"><div><span className="eyebrow">EXPLORE</span><h1>네이버 지도</h1><p>{region}의 아파트 거래와 합성 대출 기록을 지도로 확인하세요.</p></div><span className="pill"><MapPinned size={14}/> 최근 단지 최대 30곳</span></div><p className="map-help">배경에 네이버 인증 실패가 보이면 현재 접속 주소의 지도 사용 권한을 확인해주세요.</p><NaverMap clientId={meta?.naver_client_id ?? ''} markers={markers} /><div className="map-footer"><span>{mapBusy ? '단지 좌표를 확인하고 있습니다…' : `지도 마커 ${markers.length}개 · 좌표 미확인 ${missing}개`}</span><button className="text-button" onClick={() => { mapResolved.current.delete(`${buyer.sido}|${buyer.sigungu}`); setMapNonce(v => v + 1) }}>좌표 다시 확인 <ArrowRight size={14}/></button></div><p className="footnote">마커를 누르면 거래 참조가격과 해당 단지의 합성 고객 대출 원금·잔액 합계를 볼 수 있습니다. 지역 변경은 왼쪽 메뉴의 ‘내 조건 설정’에서 합니다. 배경에 네이버 인증 실패가 표시되면 현재 접속 주소의 지도 사용 권한을 네이버 Cloud에서 확인해주세요.</p></section>}

      {page === 'homes' && <section className="content"><div className="section-heading"><div><span className="eyebrow">DISCOVER</span><h1>내 조건에 맞는 단지</h1><p>{region} · 전용 {buyer.area}㎡ ±{Math.round(buyer.area_tolerance*100)}% · {buyer.min_year}년 이후</p></div><span className="pill"><Building2 size={14}/> {recommendation?.matched_count ?? 0}개 충족</span></div>{!recommendation ? <div className="loading">단지를 확인하고 있습니다…</div> : recommendation.status !== 'MATCHES' ? <div className="empty-state"><Building2 size={28}/><h2>조건에 맞는 단지가 없습니다</h2><p>{statusText[recommendation.status]}</p></div> : <><div className="insight">{recommendation.examined}개 단지를 살펴보고, 조건을 만족하는 {recommendation.matched_count}개 중 면적·거래일·상환 부담을 기준으로 {recommendation.candidates.length}개를 보여드립니다.</div><div className="candidate-list">{recommendation.candidates.map((trade,index) => <CandidateCard key={trade.complex_id} trade={trade} number={index+1} />)}</div></>}<p className="footnote">가격은 해당 면적에서 확인된 단지별 최근 거래의 참조가격입니다. 현재 매물 가격이나 대출 승인 한도가 아닙니다.</p></section>}

      {page === 'loans' && <section className="content"><div className="section-heading"><div><span className="eyebrow">REGIONAL DATA</span><h1>지역·고객 대출</h1><p>{region} · 보유 아파트 소재지 기준</p></div></div><div className="metrics three"><Metric label="합성 고객" value={`${customerTotal.toLocaleString('ko-KR')}명`} /><Metric label="최초 대출원금 합계" value={won(selectedRegion?.original)} /><Metric label="현재 대출잔액 합계" value={won(selectedRegion?.balance)} /></div><p className="tiny-note">원금·잔액은 현재 페이지가 아닌 선택 지역 전체 고객의 합계입니다.</p><details className="panel"><summary>전국·시군구별 비교 <ChevronDown size={16}/></summary><div className="panel-content"><Table rows={regions as unknown as Record<string,unknown>[]} columns={[["sido","시·도"],["sigungu","시·군·구"],["trades","거래 참조"],["avg_price","평균 가격(원)"],["customers","고객 수"],["original","최초 원금(원)"],["balance","잔액(원)"]]} /></div></details><div className="panel"><div className="panel-head"><h2>합성 고객별 현황</h2><span>{customerTotal.toLocaleString('ko-KR')}명 중 {customerPage*100+1}–{Math.min((customerPage+1)*100,customerTotal)}명</span></div><div className="customer-list">{customers.map(row => <button className={'customer-row ' + (selectedCustomer===row.customer_id?'selected':'')} key={row.customer_id} onClick={() => setSelectedCustomer(row.customer_id)}><div><strong>{row.apt_name}</strong><span>ID {row.customer_id} · {row.exclusive_area_m2}㎡ · 대출 {row.all_loan_count}건</span></div><div><b>{won(row.all_balance)}</b><small>잔액 / 원금 {won(row.all_original)}</small></div></button>)}</div><div className="pagination"><button disabled={customerPage===0} onClick={()=>setCustomerPage(v=>v-1)}><ArrowLeft size={15}/> 이전</button><button disabled={(customerPage+1)*100>=customerTotal} onClick={()=>setCustomerPage(v=>v+1)}>다음 <ArrowRight size={15}/></button></div></div>{selectedCustomer!==null && <div className="panel"><div className="panel-head"><h2>고객 {selectedCustomer} · 대출 상세</h2><button className="icon-button" onClick={()=>setSelectedCustomer(null)}><X size={17}/></button></div><Table rows={loans as unknown as Record<string,unknown>[]} columns={[["loan_id","대출 ID"],["loan_type","종류"],["loan_purpose","용도"],["original_principal","최초 원금(원)"],["outstanding_balance","잔액(원)"],["interest_rate","금리(%)"],["opened_at","개설일"]]} /></div>}<details className="panel"><summary>단지별 거래 참조 목록 · {tradeTotal.toLocaleString('ko-KR')}건 <ChevronDown size={16}/></summary><div className="panel-content"><Table rows={trades as unknown as Record<string,unknown>[]} columns={[["apt_name","단지"],["address","주소"],["exclusive_area_m2","전용면적(㎡)"],["purchase_reference_price","거래 참조가격(원)"],["reference_deal_date","거래 참조일"]]}/><div className="pagination"><button disabled={tradePage===0} onClick={()=>setTradePage(v=>v-1)}><ArrowLeft size={15}/> 이전</button><button disabled={(tradePage+1)*100>=tradeTotal} onClick={()=>setTradePage(v=>v+1)}>다음 <ArrowRight size={15}/></button></div></div></details><p className="footnote">원금은 최초 실행액, 잔액은 현재 미상환액입니다. 이 데이터는 합성 고객의 교육용 기록입니다.</p></section>}

      {page === 'plan' && <section className="content"><div className="section-heading"><div><span className="eyebrow">YOUR PLAN</span><h1>내 대출 계획</h1><p>입력한 가격 상한 {won(buyer.price)}을 기준으로 계산합니다.</p></div></div>{plan && <><div className="metrics four"><Metric label="필요 대출" value={won(plan.plan.loan)} accent/><Metric label="월 신규 상환" value={won(plan.plan.payment)}/><Metric label="상환 부담 비율" value={pct(plan.plan.dsr)}/><Metric label="자금 부족" value={won(plan.plan.shortfall)}/></div><div className={'insight ' + (plan.plan.eligible ? 'positive' : 'negative')}>{plan.plan.eligible ? '입력한 계산 가정에서 자금·상환 조건을 충족합니다.' : plan.plan.reasons.join(' · ')}</div><div className="panel highlight-panel"><span>입력한 가정에서 계산한 최대 가격</span><strong>{won(plan.max_affordable)}</strong></div></>}<div className="section-heading secondary"><div><span className="eyebrow">SIMILAR BUYERS</span><h2>나와 비슷한 합성 구매자</h2></div></div>{patterns ? <><div className="panel"><div className="tag-line">{Object.entries(patterns.description).map(([key,value])=><span key={key}><b>{key}</b> {value}</span>)}</div><div className="table-scroll"><table><thead><tr><th>구매 패턴</th><th>유사 집단 비중</th><th>부스팅 확률</th></tr></thead><tbody>{Object.keys(patterns.share).map(key=><tr key={key}><td>{key}</td><td>{pct(patterns.share[key])}</td><td>{pct(patterns.probability[key])}</td></tr>)}</tbody></table></div><Table rows={patterns.stats} columns={Object.keys(patterns.stats[0]??{}).map(key=>[key,key])}/></div>{patterns.alternatives && <details className="panel"><summary>기존 유사 구매자 대안 통계 <ChevronDown size={16}/></summary><div className="panel-content"><p>{patterns.alternatives.region_basis}</p>{(['regions','price_bands','area_bands'] as const).map(key=><div key={key}><h3>{key==='regions'?'지역':key==='price_bands'?'가격대':'면적대'}</h3><Table rows={patterns.alternatives![key]} columns={Object.keys(patterns.alternatives![key][0]??{}).map(k=>[k,k])}/></div>)}</div></details>}</> : <div className="loading">유사 구매자 데이터를 불러오는 중…</div>}<p className="footnote">유사 집단 확률은 대출 승인 확률이 아닙니다. 월 상환과 자금 부족은 입력한 가정으로 별도 계산합니다.</p></section>}

      {page === 'validation' && <section className="content"><div className="section-heading"><div><span className="eyebrow">EVIDENCE</span><h1>데이터·모델 검증</h1><p>추천에 사용한 합성 DB와 구매 패턴 모델의 평가 결과입니다.</p></div></div>{validation ? <><div className="metrics three"><Metric label="학습 대상" value={`${validation.model.rows.toLocaleString('ko-KR')}명`}/><Metric label="대출 조합" value={validation.model.selected.combo}/><Metric label="주담대 LTV" value={validation.model.selected.mort_ltv}/></div><div className="panel"><h2>모델 평가 결과</h2><Table rows={validation.model.results} columns={[["split","검증"],["target","대상"],["model","모델"],["test_n","평가 수"],["log_loss","Log loss"],["mae","MAE"],["accuracy","정확도"],["r2","R²"]]}/></div><div className="panel"><h2>CSV 정합성 검사</h2><div className="checks">{Object.entries(validation.audit.checks).map(([key,passed])=><div key={key}><span>{key.replaceAll('_',' ')}</span><strong>{passed?'통과':'확인 필요'}</strong></div>)}</div></div><div className="insight negative">현재 소득·자산으로 과거 구매를 설명하는 후향 편향과 주택 보유자만의 표본 편향이 있습니다. 실제 추천 정확도 또는 대출 승인 확률이 아닙니다.</div></> : <div className="loading">검증 결과를 불러오는 중…</div>}</section>}
    </main>
  </div>
}
