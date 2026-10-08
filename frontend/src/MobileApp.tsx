import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, ChevronRight, House, Menu, Send, X } from 'lucide-react'
import NaverMap from './NaverMap'
import { api, pct, post, won } from './api'
import type { Buyer, Message, Meta, Plan, Trade } from './api'
import './mobile.css'

type Screen = 'home' | 'explore' | 'detail' | 'finance' | 'assumptions' | 'connections'
type Bands = { safe: number; possible: number; maximum: number }
type PlanResult = { plan: Plan; safe_plan: Plan | null; max_affordable: number; bands: Bands; binding_reasons: string[]; band_assumptions: { safe_dsr_cap: number; possible_dsr_cap: number; limit_monthly_surplus: number; limit_uses_model_loan_cap: boolean } }
type ExploreResult = { total: number; rows: Trade[] }
type DemoCustomer = { customer_id: number; age: number; household_size: number; display_name?: string | null }
type DemoCustomerDetail = { customer: { customer_id: number; name: string; age: number; household_annual_income: number; financial_assets_estimated: number; account_balance_total: number; avg_monthly_consumption: number; monthly_debt_service: number; is_home_owner: number; cf_months: number | null; sido: string; sigungu: string | null; exclusive_area_m2: number | null; purchase_reference_price: number | null; consumption_source: 'budget' | 'observed'; residence_region: string }; loans: { loan_type: string; outstanding_balance: number; monthly_payment_estimated: number | null }[]; accounts: { account_type: string; balance: number; status: string }[]; property: { real_asset_id: number; apt_name: string; exclusive_area_m2: number; floor: number | null; build_year: number | null; reference_deal_date: string; purchase_reference_price: number; reference_trade_id: string } | null }
type PatternResult = { description: Record<string, string>; share: Record<string, number>; probability: Record<string, number>; loan_prediction: { basis_price: number; mortgage_ratio: number; credit_ratio: number; mortgage: number; credit: number; total: number } | null }
const accountName = (type: string) => ({ CHECKING: '입출금', SAVINGS: '저축' } as Record<string, string>)[type] ?? type
const loanName = (type: string) => ({ MORTGAGE: '주택담보대출', CREDIT_LINE: '마이너스통장' } as Record<string, string>)[type] ?? type
type ChatSession = { customerId: number; threadId: string; sido: string; sigungu: string; messages: Message[] }
function savedChatSession(): ChatSession | null {
  try {
    const value = JSON.parse(sessionStorage.getItem('housing-chat-session') ?? 'null') as ChatSession | null
    return value && Number.isInteger(value.customerId) && /^[0-9a-f-]{36}$/i.test(value.threadId) && Array.isArray(value.messages) ? value : null
  } catch { return null }
}
type Range = 'all' | 'safe' | 'possible' | 'limit'
const names: Record<Screen, string> = { home: '내 집 마련', explore: '지역·단지 찾기', detail: '단지 상세', finance: '내 재무 정보', assumptions: '계산 가정', connections: '데이터 연결 현황' }
const labels: Record<Exclude<Range, 'all'> | 'outside', string> = { safe: '안정권', possible: '가능권', limit: '한계권', outside: '범위 밖' }
const money = (n: number | null | undefined) => n == null ? '정보 없음' : won(n)
const eok = (n: number | null | undefined) => n == null ? '—' : `${(n / 1e8).toFixed(2)}억`
const hasPriceRange = (lower: number, upper: number) => upper - lower >= 10_000
const boundaryMoney = (value: number, fine = false) => fine
  ? `${Math.round(value / 10_000).toLocaleString('ko-KR')}만원`
  : eok(value)
const tierCap = (lower: number, upper: number) => hasPriceRange(lower, upper)
  ? `${boundaryMoney(upper, upper - lower < 1_000_000)} 이하`
  : '해당 가격 없음'
const rateLabel = (rate: number) => Math.round(rate * 100) / 100
const initialBuyer: Buyer = { age: 31, income: 70_000_000, assets: 100_000_000, other_funds: 0, consumption: 2_500_000, price: 500_000_000, area: 59, sido: '서울특별시', sigungu: '노원구', existing_payment: 0, reserve: 0, cost_rate: .04, ltv_cap: .7, dsr_cap: .4, mortgage_rate: 4.5, term: 30, allow_credit: false, credit_rate: 7, credit_cap_ratio: .12, area_tolerance: .2, min_year: 2022, max_results: 3, target_surplus: 1_000_000 }
const savedKeys: (keyof Buyer)[] = ['other_funds', 'target_surplus', 'reserve', 'mortgage_rate', 'term', 'allow_credit', 'credit_rate', 'ltv_cap', 'dsr_cap', 'cost_rate']
function band(price: number, bands?: Bands): Exclude<Range, 'all'> | 'outside' {
  if (!bands) return 'outside'
  if (price <= bands.safe) return 'safe'
  if (price <= bands.possible) return 'possible'
  if (price <= bands.maximum) return 'limit'
  return 'outside'
}
function withinRange(price: number, range: Range, bands?: Bands): boolean {
  if (range === 'all') return true
  if (!bands) return false
  return price <= bands[range === 'safe' ? 'safe' : range === 'possible' ? 'possible' : 'maximum']
}
function BandBar({ price, bands }: { price?: number; bands: Bands }) {
  const total = Math.max(bands.maximum * 1.12, price ?? 0, 1)
  const ticks = [
    { value: 0, label: '0', name: '시작' },
    ...(hasPriceRange(0, bands.safe) ? [{ value: bands.safe, label: boundaryMoney(bands.safe), name: '안정권 상한' }] : []),
    ...(hasPriceRange(bands.safe, bands.possible) ? [{ value: bands.possible, label: boundaryMoney(bands.possible, bands.possible - bands.safe < 1_000_000), name: '가능권 상한' }] : []),
    ...(hasPriceRange(bands.possible, bands.maximum) ? [{ value: bands.maximum, label: boundaryMoney(bands.maximum, bands.maximum - bands.possible < 1_000_000), name: '한계권 상한' }] : []),
  ]
  return <div className="band-wrap"><div className="band-bar"><i className="safe" style={{ width: `${bands.safe / total * 100}%` }} /><i className="possible" style={{ width: `${Math.max(0, bands.possible - bands.safe) / total * 100}%` }} /><i className="limit" style={{ width: `${Math.max(0, bands.maximum - bands.possible) / total * 100}%` }} /><i className="outside" style={{ flex: 1 }} />{price != null && <span className="band-pointer" style={{ left: `${Math.min(100, price / total * 100)}%` }}>▼</span>}</div><div className="band-ends">{ticks.map(tick => <span key={tick.name} title={tick.name} style={{ left: `${tick.value / total * 100}%` }}>{tick.label}</span>)}</div></div>
}
function NumberInput({ label, value, onChange, unit, step = 1, max }: { label: string; value: number; onChange: (n: number) => void; unit: string; step?: number; max?: number }) {
  const [text, setText] = useState(String(value))
  useEffect(() => setText(String(value)), [value])
  return <label className="mobile-field"><span>{label}</span><span className="mobile-number"><input type="number" min="0" max={max} step={step} value={text} onChange={e => {
    const next = e.target.value
    setText(next)
    if (next !== '' && Number.isFinite(Number(next))) onChange(Number(next))
  }} onBlur={() => setText(String(value))} /><em>{unit}</em></span></label>
}
function ChatRecommendation({ trade, reason, onOpen }: { trade: Trade; reason: string; onOpen: () => void }) {
  return <button className="chat-recommendation" onClick={onOpen}>
    <strong>{trade.apt_name}</strong><span>{trade.address} · 전용 {trade.exclusive_area_m2}㎡</span>
    <span>거래 참조가격 {money(trade.purchase_reference_price)} · {trade.reference_deal_date}</span>
    <span>예상 대출 {money(trade.plan?.loan)} (주담대 {money(trade.plan?.mortgage)}{trade.plan?.credit ? `, 한도대출 ${money(trade.plan.credit)}` : ''})</span>
    <span>예상 월 상환 {money(trade.plan?.payment)} · 월 잔여금 {money(trade.plan?.surplus)}</span>
    <small>{reason}</small>
  </button>
}
export default function MobileApp() {
  const [restoredChat] = useState(savedChatSession)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [customerId, setCustomerId] = useState<number | null>(null)
  const [customerQuery, setCustomerQuery] = useState('')
  const [customerOptions, setCustomerOptions] = useState<DemoCustomer[]>([])
  const [customerDetail, setCustomerDetail] = useState<DemoCustomerDetail | null>(null)
  const [pattern, setPattern] = useState<PatternResult | null>(null)
  const [buyer, setBuyer] = useState<Buyer>(initialBuyer)
  const [draft, setDraft] = useState<Buyer>(initialBuyer)
  const [screen, setScreen] = useState<Screen>('home')
  const [previous, setPrevious] = useState<Screen>('explore')
  const [menu, setMenu] = useState(false)
  const [chat, setChat] = useState(false)
  const [chatText, setChatText] = useState('')
  const [messages, setMessages] = useState<Message[]>(restoredChat?.messages ?? [])
  const [threadId, setThreadId] = useState(() => restoredChat?.threadId ?? crypto.randomUUID())
  const [chatBusy, setChatBusy] = useState(false)
  const [mapView, setMapView] = useState(false)
  const [mapMarkers, setMapMarkers] = useState<Trade[]>([])
  const [selected, setSelected] = useState<Trade | null>(null)
  const [plan, setPlan] = useState<PlanResult | null>(null)
  const [explore, setExplore] = useState<ExploreResult | null>(null)
  const [range, setRange] = useState<Range>('all')
  const [sort, setSort] = useState('low')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [stress, setStress] = useState(false)
  const [mapError, setMapError] = useState('')
  const menuButton = useRef<HTMLButtonElement>(null)
  const requestVersion = useRef(0)
  const customerVersion = useRef(0)
  const chatVersion = useRef(0)
  // Home's '+1%p' switch recalculates every screen at the stressed rate without saving it.
  const calcBuyer = useMemo(() => stress ? { ...buyer, mortgage_rate: rateLabel(buyer.mortgage_rate + 1) } : buyer, [buyer, stress])
  const updateDraft = <K extends keyof Buyer>(key: K, value: Buyer[K]) => setDraft(current => ({ ...current, [key]: value }))

  useEffect(() => {
    api<Meta>('/meta').then(value => {
      setMeta(value)
      setBuyer(value.defaults); setDraft(value.defaults)
    }).catch(e => setError(String(e)))
  }, [])
  useEffect(() => {
    let active = true
    api<DemoCustomer[]>('/demo-customers?q=' + encodeURIComponent(customerQuery))
      .then(rows => { if (active) setCustomerOptions(rows) })
      .catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [customerQuery])
  const selectCustomer = async (id: number, restore = false) => {
    const version = ++customerVersion.current
    try {
      const detail = await api<DemoCustomerDetail>(`/demo-customers/${id}`)
      if (version !== customerVersion.current) return
      const c = detail.customer
      if ([c.household_annual_income, c.financial_assets_estimated, c.avg_monthly_consumption].some(v => v == null)) throw new Error('이 고객은 계산에 필요한 재무정보가 부족합니다.')
      let saved: Partial<Buyer> = {}
      try { saved = JSON.parse(localStorage.getItem(`housing-assumptions-${id}`) ?? '{}') as Partial<Buyer> } catch { /* invalid local draft */ }
      const safeSaved = Object.fromEntries(savedKeys.filter(key => saved[key] != null).map(key => [key, saved[key]]))
      const defaults = meta?.defaults ?? initialBuyer
      const sido = meta?.regions[c.sido]?.length ? c.sido : defaults.sido
      const sigungu = c.sigungu && meta?.regions[sido]?.includes(c.sigungu) ? c.sigungu : (meta?.regions[sido]?.[0] ?? defaults.sigungu)
      const next = { ...defaults, ...safeSaved, sido, sigungu, price: c.purchase_reference_price ?? defaults.price, area: c.exclusive_area_m2 ?? defaults.area, ...(restore && restoredChat ? { sido: restoredChat.sido, sigungu: restoredChat.sigungu } : {}), age: c.age, income: c.household_annual_income, assets: c.consumption_source === 'budget' ? c.account_balance_total : c.financial_assets_estimated, consumption: c.avg_monthly_consumption, existing_payment: c.monthly_debt_service ?? 0 } as Buyer
      requestVersion.current += 1
      chatVersion.current += 1
      if (!restore) { void api(`/chat/${threadId}`, { method: 'DELETE' }).catch(() => undefined); setThreadId(crypto.randomUUID()) }
      setPlan(null); setExplore(null); setCustomerId(id); setCustomerDetail(detail); setBuyer(next); setDraft(next); setMessages(restore ? restoredChat?.messages ?? [] : []); setChatBusy(false); setSelected(null); setMapMarkers([]); setMenu(false); go('home')
    } catch (e) { if (version === customerVersion.current) setError(e instanceof Error ? e.message : '고객 정보를 불러오지 못했습니다.') }
  }
  useEffect(() => { if (meta && restoredChat) void selectCustomer(restoredChat.customerId, true) }, [meta])
  useEffect(() => {
    if (customerId == null) return
    const history = messages.map(({ role, content, caveat }) => ({ role, content, caveat }))
    try { sessionStorage.setItem('housing-chat-session', JSON.stringify({ customerId, threadId, sido: buyer.sido, sigungu: buyer.sigungu, messages: history })) } catch { /* browser storage unavailable */ }
  }, [customerId, threadId, buyer.sido, buyer.sigungu, messages])
  useEffect(() => {
    if (!meta || customerId == null) return
    const version = ++requestVersion.current
    setPlan(null); setExplore(null); setPattern(null)
    Promise.all([post<PlanResult>('/plan', calcBuyer), post<ExploreResult>('/explore', calcBuyer), post<PatternResult>('/patterns', calcBuyer)]).then(([p, x, predicted]) => {
      if (version === requestVersion.current) { setPlan(p); setExplore(x); setPattern(predicted); setError('') }
    }).catch(e => { if (version === requestVersion.current) setError(e.message) })
  }, [calcBuyer, meta, customerId])
  useEffect(() => {
    if (!mapView || screen !== 'explore' || !meta || !explore || !plan) return
    let active = true
    const query = `?sido=${encodeURIComponent(buyer.sido)}&sigungu=${encodeURIComponent(buyer.sigungu)}`
    const complex_ids = explore.rows.filter(row => withinRange(row.purchase_reference_price, range, plan.bands)).slice(0, 30).map(row => row.complex_id)
    setMapMarkers([]); setMapError('')
    post<{ markers: Trade[]; missing: number }>('/map/resolve' + query, { complex_ids, customer_id: customerId })
      .then(data => { if (active) { setMapMarkers(data.markers); if (data.missing) setMapError(`주소로 좌표를 확인하지 못한 단지 ${data.missing}곳`) } })
      .catch(e => { if (active) setMapError(e.message) })
    return () => { active = false }
  }, [mapView, screen, buyer.sido, buyer.sigungu, meta, explore, plan, range, customerId])
  useEffect(() => {
    document.body.style.overflow = menu || chat ? 'hidden' : ''
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') { setMenu(false); setChat(false) } }
    document.addEventListener('keydown', escape)
    return () => { document.body.style.overflow = ''; document.removeEventListener('keydown', escape) }
  }, [menu, chat])

  const go = (next: Screen) => { setMenu(false); setScreen(next); window.scrollTo(0, 0); menuButton.current?.focus() }
  const save = async () => {
    setSaving(true); setError('')
    try {
      await post<PlanResult>('/plan', draft)
      if (customerId != null) localStorage.setItem(`housing-assumptions-${customerId}`, JSON.stringify(Object.fromEntries(savedKeys.map(key => [key, draft[key]]))))
      chatVersion.current += 1
      void api(`/chat/${threadId}`, { method: 'DELETE' }).catch(() => undefined)
      setThreadId(crypto.randomUUID())
      setBuyer(draft); setMessages([]); setChatBusy(false); setChatText(''); setSelected(null); go('home')
    } catch (e) { setError(e instanceof Error ? e.message : '저장 실패') }
    finally { setSaving(false) }
  }
  const send = async (text = chatText) => {
    const input = text.trim()
    if (!input || chatBusy) return
    const version = ++chatVersion.current
    setChatText(''); setChatBusy(true)
    const next: Message[] = [...messages, { role: 'user', content: input }]
    setMessages(next)
    try {
      const reply = await post<{ answer: string; choices: Message['choices']; recommendations: Message['recommendations']; caveat: string; applied_region: { sido: string; sigungu: string } | null }>('/chat', { buyer: calcBuyer, thread_id: threadId, message: input })
      if (version === chatVersion.current) {
        if (reply.applied_region) {
          const updated = { ...buyer, ...reply.applied_region }
          setBuyer(updated); setDraft(updated); setSelected(null); setMapMarkers([]); setRange('all')
        }
        setMessages([...next, { role: 'assistant', content: reply.answer, choices: reply.choices, recommendations: reply.recommendations, caveat: reply.caveat }])
      }
    } catch (e) { if (version === chatVersion.current) { setThreadId(crypto.randomUUID()); setMessages([...next, { role: 'assistant', content: `${e instanceof Error ? e.message : '응답을 받지 못했습니다.'} 대화 문맥을 초기화했습니다. 질문을 다시 보내주세요.` }]) } }
    finally { if (version === chatVersion.current) setChatBusy(false) }
  }
  const choose = (row: Trade) => { setPrevious('explore'); setSelected(row); go('detail') }
  const rows = useMemo(() => {
    const filtered = (explore?.rows ?? []).filter(row => withinRange(row.purchase_reference_price, range, plan?.bands))
    return sort === 'new' ? [...filtered].sort((a, b) => b.reference_deal_date.localeCompare(a.reference_deal_date)) : filtered
  }, [explore, range, sort, plan])
  const lowestPrice = explore?.rows.length ? Math.min(...explore.rows.map(row => row.purchase_reference_price)) : null
  const emptyMessage = range === 'all'
    ? '현재 지역·면적·거래 기간에 맞는 단지가 없습니다. 조건을 바꿔 보세요.'
    : `${labels[range]} 상한 이하 단지가 0곳입니다. ${lowestPrice != null && plan && lowestPrice > plan.bands[range === 'safe' ? 'safe' : range === 'possible' ? 'possible' : 'maximum'] ? `이 지역 최저 참조가격 ${money(lowestPrice)}이 ${labels[range]} 상한보다 높습니다.` : '현재 지역·면적·기간에 해당하는 단지가 없습니다.'} 전체 목록에서 다른 단지를 확인할 수 있습니다.`
  const selectedPlan = selected?.plan
  const rangeLabel = selected ? labels[band(selected.purchase_reference_price, plan?.bands)] : ''
  const detailStress = selected?.stress_plan
  const mapSelect = useCallback((row: Trade) => {
    setSelected(row)
  }, [])
  const visibleMapMarkers = useMemo(() => {
    if (!explore) return []
    const byComplex = new Map(explore.rows.map(row => [row.complex_id, row]))
    return mapMarkers.flatMap(marker => {
      if (marker.is_owned) return [marker]
      const trade = byComplex.get(marker.complex_id)
      if (!trade) return []
      if (!withinRange(trade.purchase_reference_price, range, plan?.bands)) return []
      return [{ ...trade, latitude: marker.latitude, longitude: marker.longitude, loan_summary: marker.loan_summary }]
    })
  }, [mapMarkers, explore, range, plan])
  return <div className="mobile-shell"><div className="mobile-app">
    <header className="mobile-header">
      {screen === 'detail' ? <button className="plain-icon" aria-label="뒤로가기" onClick={() => go(previous)}><ArrowLeft size={22} /></button> : <button className="header-home" type="button" aria-label="내 구매력 홈으로" onClick={() => go('home')}><House size={20} /></button>}
      <strong>{names[screen]}</strong>
      {screen === 'explore' ? <div className="view-tabs"><button className={!mapView ? 'active' : ''} onClick={() => setMapView(false)}>목록</button><button className={mapView ? 'active' : ''} onClick={() => setMapView(true)}>지도</button></div> : screen === 'assumptions' ? <button className="text-link" onClick={() => setDraft(meta?.defaults ?? initialBuyer)}>기본값으로</button> : null}
      <button ref={menuButton} className="plain-icon header-menu" aria-label="메뉴 열기" onClick={() => setMenu(true)}><Menu size={22} /></button>
    </header>
    {error && <div className="mobile-error" role="alert">{error}<button aria-label="오류 닫기" onClick={() => setError('')}><X size={15} /></button></div>}
    <main className="mobile-content">
      {screen !== 'connections' && <p className="data-badge">{customerId == null ? '고객을 선택하세요' : `${customerDetail?.customer.name ?? '고객'} · 고객 ID ${customerId}`}</p>}
      {customerId == null ? <section className="mobile-card empty"><h2>고객을 선택하세요</h2><p>DB에 있는 고객을 선택하면 해당 고객의 재무정보로 구매력을 계산합니다.</p><button className="primary" onClick={() => setMenu(true)}>고객 선택하기</button></section> : <>
      {screen === 'home' && <>
        <section className="mobile-card hero"><span>지금 소비를 유지하며 감당할 수 있는 집값 · 안정권 상한</span>{stress && <p className="warning">금리 +1%p 적용 중 · 주담대 {calcBuyer.mortgage_rate}%</p>}<strong>{plan && !hasPriceRange(0, plan.bands.safe) ? '해당 가격 없음' : <>{eok(plan?.bands.safe)} <small>이하</small></>}</strong>{plan && <p className="hint">가능권 {tierCap(plan.bands.safe, plan.bands.possible)} · 한계권 {tierCap(plan.bands.possible, plan.bands.maximum)}</p>}{plan && <BandBar bands={plan.bands} />}</section>
        {customerDetail?.customer.consumption_source === 'budget' && <p className="hint">이 고객의 구매력 계산에는 계좌 잔액 합계와 제공된 월 소비 예산을 사용합니다. 시·군·구와 희망 주택 가격·면적은 기본 검색값이므로 지역·단지 찾기에서 조정해 주세요.</p>}
        {plan && <section className="mobile-card"><h2>내 구매력 구간</h2><div className="band-grid"><div><b className="dot safe" /> 안정권 <strong>{tierCap(0, plan.bands.safe)}</strong><small>목표 여유자금 유지 · DSR {Math.round(plan.band_assumptions.safe_dsr_cap * 100)}% 이하</small></div><div><b className="dot possible" /> 가능권 <strong>{tierCap(plan.bands.safe, plan.bands.possible)}</strong><small>월 적자 없음 · DSR {Math.round(plan.band_assumptions.possible_dsr_cap * 100)}% 이하</small></div><div><b className="dot limit" /> 한계권 <strong>{tierCap(plan.bands.possible, plan.bands.maximum)}</strong><small>월 잔여금 {money(plan.band_assumptions.limit_monthly_surplus)} 경계 · DSR 상한 초과 가능</small></div><div><b className="dot outside" /> 범위 밖 <strong>{boundaryMoney(plan.bands.maximum)} 초과</strong><small>한계권 시나리오의 자금·월 잔여금 기준 초과</small></div></div></section>}
        <section className="mobile-card"><h2>매달 남는 돈 <small>안정권 상단 기준</small></h2><div className="amount-row"><span>월 소득 · 연소득÷12</span><b>{money(buyer.income / 12)}</b></div><div className="amount-row"><span>월 총지출</span><b>− {money(buyer.consumption)}</b></div><div className="amount-row"><span>기존 대출 상환</span><b>− {money(buyer.existing_payment)}</b></div><div className="amount-row"><span>예상 월 상환</span><b>− {money(plan?.safe_plan?.payment)}</b></div><div className="amount-row total"><span>남는 돈</span><b>{money(plan?.safe_plan?.surplus)}</b></div><p className="hint">목표 여유자금 월 {money(buyer.target_surplus)}과 비교해서 구간을 나눠요.</p></section>
        {pattern?.loan_prediction && <section className="mobile-card"><h2>AI의 예상 대출 <small>안정권 상한 {money(pattern.loan_prediction.basis_price)} 기준</small></h2><div className="amount-row"><span>주택담보대출 · 집값의 {pct(pattern.loan_prediction.mortgage_ratio)}</span><b>{money(pattern.loan_prediction.mortgage)}</b></div><div className="amount-row"><span>마이너스통장 · 집값의 {pct(pattern.loan_prediction.credit_ratio)}</span><b>{money(pattern.loan_prediction.credit)}</b></div><div className="amount-row total"><span>예상 대출 합계</span><b>{money(pattern.loan_prediction.total)}</b></div><p className="hint">고객 {customerId}의 재무정보로 안정권 상한 가격의 집을 살 때 AI가 예측한 대출 비율입니다. 승인 한도가 아닙니다.</p></section>}
        {customerDetail && <section className="mobile-card"><h2>내 자산</h2>{customerDetail.accounts.map((account, i) => <div className="amount-row" key={i}><span>{accountName(account.account_type)}</span><b>{money(account.balance)}</b></div>)}<div className="amount-row total"><span>계좌 잔액 합계</span><b>{money(customerDetail.customer.account_balance_total)}</b></div>{customerDetail.customer.consumption_source !== 'budget' && <div className="amount-row"><span>금융 자산</span><b>{money(buyer.assets)}</b></div>}{customerDetail.loans.map((loan, i) => <div className="amount-row" key={i}><span>{loanName(loan.loan_type)} 잔액</span><b>− {money(loan.outstanding_balance)}</b></div>)}{customerDetail.loans.length > 0 && <div className="amount-row total"><span>대출 잔액 합계</span><b>− {money(customerDetail.loans.reduce((sum, loan) => sum + loan.outstanding_balance, 0))}</b></div>}</section>}
        <label className="switch-row">금리 +1%p로 다시 계산 <input type="checkbox" checked={stress} onChange={e => setStress(e.target.checked)} /></label>{stress && <p className="hint">설정 금리 {buyer.mortgage_rate}% 대신 {calcBuyer.mortgage_rate}%로 모든 구간·대출·단지 계산을 다시 했어요. 끄면 원래 금리로 돌아가요.</p>}
        <button className="primary" onClick={() => go('explore')}>이 범위에서 지역 찾기</button>
      </>}
      {screen === 'explore' && <>
        <section className="mobile-card compact"><div className="title-row"><h2>내 구매력 구간</h2><button className="text-link" onClick={() => go('home')}>자세히 <ChevronRight size={15} /></button></div>{plan && <><BandBar bands={plan.bands} /><p className="hint">안정권 {tierCap(0, plan.bands.safe)} · 가능권 {tierCap(plan.bands.safe, plan.bands.possible)} · 한계권 {tierCap(plan.bands.possible, plan.bands.maximum)} · 범위 밖 {boundaryMoney(plan.bands.maximum)} 초과</p></>}</section>
        <div className="filter-row"><label>시·도<select value={buyer.sido} onChange={e => { const sido = e.target.value; const sigungu = meta?.regions[sido]?.[0] ?? buyer.sigungu; setBuyer(v => ({ ...v, sido, sigungu })); setDraft(v => ({ ...v, sido, sigungu })) }}>{Object.keys(meta?.regions ?? {}).map(v => <option key={v}>{v}</option>)}</select></label><label>지역<select value={draft.sigungu} onChange={e => { const sigungu = e.target.value; setDraft(v => ({ ...v, sigungu })); setBuyer(v => ({ ...v, sigungu })) }}>{(meta?.regions[buyer.sido] ?? [buyer.sigungu]).map(v => <option key={v}>{v}</option>)}</select></label><label>전용면적<select value={buyer.area} onChange={e => { const area = Number(e.target.value); setBuyer(v => ({ ...v, area })); setDraft(v => ({ ...v, area })) }}>{Array.from(new Set([buyer.area, 59, 84, 99, 114])).sort((a, b) => a - b).map(v => <option value={v} key={v}>{Number(v.toFixed(1))}㎡ ±{Math.round(buyer.area_tolerance * 100)}%</option>)}</select></label><label>거래 시작연도<select value={buyer.min_year} onChange={e => { const min_year = Number(e.target.value); setBuyer(v => ({ ...v, min_year })); setDraft(v => ({ ...v, min_year })) }}>{Array.from({ length: 9 }, (_, i) => 2026 - i).map(v => <option value={v} key={v}>{v}년 이후</option>)}</select></label></div>
        
        {!mapView ? <><div className="range-tabs">{(['all', 'possible', 'safe', 'limit'] as Range[]).map(v => <button key={v} className={range === v ? 'active' : ''} onClick={() => setRange(v)}>{v === 'all' ? '전체' : v === 'safe' ? labels[v] : labels[v] + '까지'}</button>)}</div><div className="title-row results"><b>단지 {rows.length}곳</b><select aria-label="정렬" value={sort} onChange={e => setSort(e.target.value)}><option value="low">가격 낮은 순</option><option value="new">최근 거래 순</option></select></div>{rows.length ? rows.map(row => <button className="mobile-card result-card" key={row.complex_id} onClick={() => choose(row)}><div className="title-row"><h2>{row.apt_name}</h2><span className={'status ' + band(row.purchase_reference_price, plan?.bands)}>{labels[band(row.purchase_reference_price, plan?.bands)]}</span></div>{plan && <BandBar bands={plan.bands} price={row.purchase_reference_price} />}<div className="amount-row"><span>최근 실거래 · 전용 {row.exclusive_area_m2}㎡</span><b>{money(row.purchase_reference_price)}</b></div><div className="amount-row"><span>이 집을 사면 매달 남는 돈</span><b>{money(row.plan?.surplus)}</b></div>{row.plan?.loan_basis === 'limit_scenario' && <p className="warning">한계권 가정: 모델 예측 대출 비율·설정 DSR을 넘길 수 있어요. 실제 승인 가능액이 아닙니다.</p>}{row.plan && row.plan.surplus < 0 && <p className="warning">월 적자 예상 · 추천 대상이 아닙니다.</p>}</button>) : <div className="mobile-card empty">{emptyMessage}</div>}</> : <><div className="map-range"><button className={range === 'all' ? 'active' : ''} onClick={() => setRange('all')}>전체</button>{(['possible', 'safe', 'limit'] as const).map(v => <button key={v} className={range === v ? 'active' : ''} onClick={() => setRange(v)}>{labels[v]}까지</button>)}</div><NaverMap clientId={meta?.naver_client_id ?? ''} markers={visibleMapMarkers} onSelect={mapSelect} />{mapError && <p className="hint">지도 좌표를 불러오지 못했습니다: {mapError}</p>}<div className="mobile-card"><h2>{(selected?.is_owned ? '내 주택 · ' : '') + (selected?.apt_name ?? buyer.sigungu)}</h2>{selected ? <><div className="amount-row"><span>최근 실거래</span><b>{money(selected.purchase_reference_price)}</b></div><button className="primary" onClick={() => selected.is_owned ? go('finance') : choose(selected)}>{selected.is_owned ? '내 재무 정보 보기' : '단지 상세 보기'}</button></> : <><p>{explore?.rows.filter(row => withinRange(row.purchase_reference_price, range, plan?.bands)).length ? '지도 마커를 선택해 단지를 확인하세요.' : '선택한 구간에 단지가 없습니다. 내 주택 표식은 별도로 표시됩니다.'}</p><button className="secondary" onClick={() => setMapView(false)}>목록</button></>}</div></>}
      </>}
      {screen === 'detail' && selected && <><section className="mobile-card hero"><span>{buyer.sigungu} · 전용 {selected.exclusive_area_m2}㎡</span><h1>{selected.apt_name}</h1><span className={'status ' + band(selected.purchase_reference_price, plan?.bands)}>{rangeLabel}</span><p>최근 실거래</p><strong>{money(selected.purchase_reference_price)}</strong>{plan && <BandBar bands={plan.bands} price={selected.purchase_reference_price} />}{selectedPlan?.loan_basis === 'limit_scenario' && <p className="warning">한계권 가정: 모델 예측 대출 비율·설정 DSR을 넘길 수 있어요. 실제 승인 가능액이 아닙니다.</p>}{selectedPlan && selectedPlan.surplus < 0 && <p className="warning">월 적자 예상 · 추천 대상이 아닙니다.</p>}</section><section className="mobile-card"><h2>자금 계획</h2><div className="amount-row"><span>필요 자기자금</span><b>{money(selectedPlan ? selectedPlan.price + selectedPlan.costs - selectedPlan.loan : null)}</b></div><div className="amount-row"><span>내 가용 자금 · 예비비 제외</span><b>{money(selectedPlan?.available)}</b></div><div className="amount-row"><span>예상 대출</span><b>{money(selectedPlan?.loan)}</b></div>{!!selectedPlan?.shortfall && <p className="warning">{money(selectedPlan.shortfall)}이 부족해요.</p>}</section><section className="mobile-card"><h2>매달 남는 돈</h2><div className="amount-row"><span>월 소득</span><b>{money(buyer.income / 12)}</b></div><div className="amount-row"><span>월 총지출</span><b>− {money(buyer.consumption)}</b></div><div className="amount-row"><span>예상 월 상환</span><b>− {money(selectedPlan?.payment)}</b></div><div className="amount-row total"><span>남는 돈</span><b>{money(selectedPlan?.surplus)}</b></div></section><section className="mobile-card"><h2>금리가 1%p 오르면</h2><div className="comparison"><span>지금 {calcBuyer.mortgage_rate}%</span><span>{rateLabel(calcBuyer.mortgage_rate + 1)}%</span><b>{money(selectedPlan?.payment)}</b><b>{money(detailStress?.payment)}</b><b>{money(selectedPlan?.surplus)}</b><b>{money(detailStress?.surplus)}</b></div><p className="hint">대출 원금과 만기는 그대로 두고 금리만 바꿔 계산해요.</p></section><section className="mobile-card"><h2>데이터 기준</h2><p>제공 CSV 거래 참조값 · {selected.reference_deal_date}</p><p className="hint">실제 매물이나 금융기관의 대출 심사 결과와 다를 수 있어요.</p></section></>}
      {screen === 'finance' && <><p className="intro">{customerId == null ? '메뉴에서 고객을 선택하면 DB 재무정보를 보여줍니다.' : `고객 ${customerId}의 제공 CSV 재무정보입니다. 현금흐름 관측기간: ${customerDetail?.customer.cf_months == null ? '정보 없음' : `${customerDetail.customer.cf_months}개월`}입니다.`}</p>{customerDetail?.customer.consumption_source === 'budget' && <p className="hint">월 지출은 관측 거래액이 아닌 제공된 소비 예산입니다. 주소는 시·도까지만 제공되어 검색 시 시·군·구를 선택해 주세요.</p>}<section className="mobile-card"><h2>월 소득·지출</h2><div className="amount-row"><span>월 소득 · 가구 연소득÷12</span><b>{money(customerId == null ? null : buyer.income / 12)}</b></div><div className="amount-row"><span>{customerDetail?.customer.consumption_source === 'budget' ? '월 소비 예산' : '월 총지출'}</span><b>{money(customerId == null ? null : buyer.consumption)}</b></div><div className="amount-row"><span>기존 대출 월 상환</span><b>{money(customerId == null ? null : buyer.existing_payment)}</b></div></section><section className="mobile-card"><h2>자산</h2><div className="amount-row"><span>{customerDetail?.customer.consumption_source === 'budget' ? '계산에 사용한 계좌 잔액 합계' : '금융 자산'}</span><b>{money(customerId == null ? null : buyer.assets)}</b></div>{customerDetail?.customer.consumption_source === 'budget' && <div className="amount-row"><span>금융 자산</span><b>{money(customerDetail.customer.financial_assets_estimated)}</b></div>}<p className="hint">계좌 잔액 합계와 금융 자산은 서로 다른 값입니다.</p></section><section className="mobile-card"><h2>연결된 계좌</h2>{customerDetail?.accounts.map((account, i) => <div className="amount-row" key={i}><span>{accountName(account.account_type)}</span><b>{money(account.balance)}</b></div>)}</section><section className="mobile-card"><h2>대출 잔액</h2>{customerDetail?.loans.length ? customerDetail.loans.map((loan, i) => <div className="amount-row" key={i}><span>{loanName(loan.loan_type)}</span><b>{money(loan.outstanding_balance)}</b></div>) : <p>대출 기록 없음</p>}</section>{customerDetail?.property && <section className="mobile-card"><h2>보유 주택 참조</h2><div className="amount-row"><span>단지</span><b>{customerDetail.property.apt_name}</b></div><div className="amount-row"><span>전용면적 · 층</span><b>{customerDetail.property.exclusive_area_m2}㎡ · {customerDetail.property.floor == null ? '정보 없음' : customerDetail.property.floor + '층'}</b></div><div className="amount-row"><span>거래 참조가격</span><b>{money(customerDetail.property.purchase_reference_price)}</b></div><p className="hint">참조 거래일 {customerDetail.property.reference_deal_date}</p></section>}<section className="mobile-card"><h2>직접 입력</h2><NumberInput label="기타 동원 자금" value={draft.other_funds / 1e4} onChange={v => updateDraft('other_funds', v * 1e4)} unit="만원" step={10} /><p className="hint">금융자산 원천값과 별도로 계산에 사용합니다.</p></section><button className="primary" disabled={saving || customerId == null} onClick={save}>저장하고 다시 계산</button></>}
      {screen === 'assumptions' && <><p className="intro">대출 규제 기준이 아니라 계산에 쓰는 가정이에요. 저장하면 구간을 다시 계산해요.</p><section className="mobile-card"><h2>내 기준</h2><NumberInput label="목표 여유자금" value={draft.target_surplus / 1e4} onChange={v => updateDraft('target_surplus', v * 1e4)} unit="만원/월" step={10} /><NumberInput label="예비비" value={draft.reserve / 1e4} onChange={v => updateDraft('reserve', v * 1e4)} unit="만원" step={100} /></section><section className="mobile-card"><h2>대출 조건</h2><NumberInput label="주담대 금리" value={draft.mortgage_rate} onChange={v => updateDraft('mortgage_rate', v)} unit="%" step={0.1} max={25} /><NumberInput label="만기" value={draft.term} onChange={v => updateDraft('term', v)} unit="년" max={50} /><div className="amount-row"><span>상환 방식</span><b>원리금균등</b></div><label className="switch-row">한도대출도 포함 <input type="checkbox" checked={draft.allow_credit} onChange={e => updateDraft('allow_credit', e.target.checked)} /></label>{draft.allow_credit && <NumberInput label="한도대출 금리" value={draft.credit_rate} onChange={v => updateDraft('credit_rate', v)} unit="%" step={0.1} max={25} />}</section><section className="mobile-card"><h2>계산 기준</h2><NumberInput label="주담대 비율 상한" value={draft.ltv_cap * 100} onChange={v => updateDraft('ltv_cap', v / 100)} unit="%" max={100} /><NumberInput label="상환 부담 비율 상한" value={draft.dsr_cap * 100} onChange={v => updateDraft('dsr_cap', v / 100)} unit="%" max={100} /><NumberInput label="부대비용 적립률" value={draft.cost_rate * 100} onChange={v => updateDraft('cost_rate', v / 100)} unit="%" step={0.5} max={30} /></section><button className="primary" disabled={saving} onClick={save}>저장하고 다시 계산</button><p className="hint">저장하면 AI 대화가 새로 시작돼요.</p></>}
      {screen === 'connections' && <><p className="intro">고객 프로필·부채 요약·계좌 CSV를 기존 주택·대출 DB에 보강해 고객별 조회와 계산에 사용하고 있습니다.</p><section className="mobile-card"><h2>연결된 데이터</h2><div className="amount-row"><span>주택 구매 이력</span><b>연결됨</b></div><div className="amount-row"><span>고객 재무·현금흐름</span><b>연결됨</b></div><div className="amount-row"><span>부동산 상세·거래 참조</span><b>연결됨</b></div><div className="amount-row"><span>대출 이력</span><b>연결됨</b></div><div className="amount-row"><span>고객 프로필·부채 요약·계좌</span><b>연결됨</b></div><p className="hint">고객 ID와 부동산 ID로 고객 프로필·계좌·구매·부동산 상세·대출 기록을 연결합니다. 현재 화면의 고객 정보와 단지 검색은 이 데이터에서 가져옵니다.</p></section><section className="mobile-card"><h2>선택한 고객</h2>{customerId == null ? <p>메뉴에서 고객을 선택하면 연결된 기록을 확인할 수 있습니다.</p> : <><div className="amount-row"><span>고객 ID</span><b>{customerId}</b></div><div className="amount-row"><span>대출 기록</span><b>{customerDetail?.loans.length ?? 0}건</b></div><button className="secondary" onClick={() => go('finance')}>내 재무 정보 보기</button></>}</section><p className="hint">현재 연결은 제공 CSV를 로컬 DB로 가져온 방식입니다. 금융기관의 실시간 마이데이터 연동이나 동의 내역은 포함되지 않습니다.</p></>}
      {screen !== 'connections' && <><p className="mobile-disclaimer">제공 CSV와 학습 모델 기반 참고 계산이며 실제 매물이나 대출 승인을 보장하지 않아요.</p><form className="mobile-chat-entry" onSubmit={e => { e.preventDefault(); setChat(true); if (chatText.trim()) void send() }}><input aria-label="채팅 질문" placeholder="조건을 말로 바꿔 보세요" value={chatText} onChange={e => setChatText(e.target.value)} onFocus={() => setChat(true)} /><button aria-label="채팅 열기 또는 전송" type="submit"><Send size={18} /></button></form></>}
      </>}
    </main>
  </div>
   {menu && <div className="overlay" onClick={() => { setMenu(false); menuButton.current?.focus() }}><nav className="drawer" aria-label="메인 메뉴" onClick={e => e.stopPropagation()}><div className="title-row"><button className="header-home" type="button" aria-label="내 구매력 홈으로" onClick={() => go('home')}><House size={20} /></button><h2>내 집 마련</h2><button className="plain-icon" aria-label="메뉴 닫기" onClick={() => { setMenu(false); menuButton.current?.focus() }}><X /></button></div><p>감당할 수 있는 집부터 찾기</p><div className="menu-card"><strong>{customerId == null ? '고객을 선택하세요' : `${customerDetail?.customer.name ?? '고객'} · 고객 ID ${customerId}`}</strong><span>{customerDetail ? (customerDetail.customer.is_home_owner ? '주택 보유' : '무주택') : '제공 CSV 고객'}</span><label>사용자 바꾸기<input type="search" inputMode="numeric" placeholder="고객 ID 또는 이름 검색" value={customerQuery} onChange={e => setCustomerQuery(e.target.value)} /></label><div className="customer-options">{customerOptions.map(c => <button key={c.customer_id} onClick={() => void selectCustomer(c.customer_id)}>고객 {c.display_name ? `${c.display_name} · ` : ''}{c.customer_id} · {c.age}세 · {c.household_size}인 가구</button>)}</div></div><small>찾기</small><button onClick={() => go('home')}>내 구매력</button><button onClick={() => go('explore')}>지역·단지 찾기</button><small>내 정보</small><button onClick={() => go('finance')}>내 재무 정보</button><button onClick={() => go('assumptions')}>계산 가정</button><small>근거와 설정</small><button onClick={() => go('connections')}>데이터 연결 현황</button><p className="drawer-note">● 제공 CSV 기반 서비스<br />실제 매물이나 대출 승인을 보장하지 않아요.</p></nav></div>}
  {chat && <div className="overlay chat-overlay" onClick={() => setChat(false)}><section className="chat-sheet" role="dialog" aria-modal="true" aria-label="조건을 말로 바꿔 보세요" onClick={e => e.stopPropagation()}><div className="sheet-handle" /><div className="title-row"><h2>조건을 말로 바꿔 보세요</h2><button className="text-link" onClick={() => { chatVersion.current += 1; void api(`/chat/${threadId}`, { method: 'DELETE' }).catch(() => undefined); setThreadId(crypto.randomUUID()); setChatBusy(false); setMessages([]); setChatText('') }}>새로 시작</button><button className="plain-icon" aria-label="채팅 닫기" onClick={() => setChat(false)}><X /></button></div><div className="chat-body">{messages.length === 0 && <p className="hint">아파트와 자금 조건을 물어보세요. 금액은 계산기가 계산해요.</p>}{messages.map((m, i) => <div key={i} className="chat-message"><p className={'chat-bubble ' + m.role}>{m.content}</p>{m.recommendations?.map(({ trade, reason }) => <ChatRecommendation key={trade.complex_id} trade={trade} reason={reason} onOpen={() => { setChat(false); choose(trade) }} />)}{m.caveat && <p className="hint">{m.caveat}</p>}</div>)}{chatBusy && <p className="hint">답변을 확인하는 중…</p>}</div>{messages.length > 0 && <div className="chat-actions"><button onClick={() => { setChat(false); go('explore') }}>바뀐 결과 보기</button></div>}<div className="suggestions">{['성동구에서 내 조건에 맞는 집을 찾아줘', '금리가 1%p 올라도 괜찮은 곳은?', '예비비를 남기려면 어떻게 해야 해?'].map(v => <button key={v} onClick={() => setChatText(v)}>{v}</button>)}</div><form className="sheet-form" onSubmit={e => { e.preventDefault(); void send() }}><input aria-label="질문 입력" value={chatText} placeholder="예: 월 상환을 더 낮추고 싶어" onChange={e => setChatText(e.target.value)} /><button type="submit" disabled={chatBusy || !chatText.trim()} aria-label="질문 보내기"><Send size={18} /></button></form><p className="hint">금액은 AI가 아니라 계산기가 계산해요. AI는 결과를 설명해요.</p></section></div>}
  </div>
}







