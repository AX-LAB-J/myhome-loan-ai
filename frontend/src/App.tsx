import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, House, Menu, Send, X } from 'lucide-react'
import { api, deleteChat, post } from './api'
import type {
  Buyer, ChatReply, CustomerDetail, DemoCustomer, ExploreResult, MapResult, Message, Meta,
  PatternResult, PlanResult, Trade,
} from './api'
import ChatSheet from './components/ChatSheet'
import Drawer from './components/Drawer'
import { rateLabel, withinRange, type Range } from './format'
import { screenTitles, type Screen } from './screens'
import AssumptionsScreen from './screens/AssumptionsScreen'
import ConnectionsScreen from './screens/ConnectionsScreen'
import DetailScreen from './screens/DetailScreen'
import ExploreScreen, { type Sort } from './screens/ExploreScreen'
import FinanceScreen from './screens/FinanceScreen'
import HomeScreen from './screens/HomeScreen'
import './styles.css'

const initialBuyer: Buyer = { age: 31, income: 70_000_000, assets: 100_000_000, other_funds: 0, consumption: 2_500_000, price: 500_000_000, area: 59, sido: '서울특별시', sigungu: '노원구', existing_payment: 0, reserve: 0, cost_rate: .04, ltv_cap: .7, dsr_cap: .4, mortgage_rate: 4.5, term: 30, allow_credit: false, credit_rate: 7, credit_cap_ratio: .12, area_tolerance: .2, min_year: 2022, max_results: 3, target_surplus: 1_000_000 }
// Assumptions the user may save per customer (browser localStorage).
const savedKeys: (keyof Buyer)[] = ['other_funds', 'target_surplus', 'reserve', 'mortgage_rate', 'term', 'allow_credit', 'credit_rate', 'ltv_cap', 'dsr_cap', 'cost_rate']
const MAP_MARKER_LIMIT = 30
const CHAT_SESSION_KEY = 'housing-chat-session'

type ChatSession = { customerId: number; threadId: string; sido: string; sigungu: string; messages: Message[] }
function savedChatSession(): ChatSession | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(CHAT_SESSION_KEY) ?? 'null') as ChatSession | null
    return value && Number.isInteger(value.customerId) && /^[0-9a-f-]{36}$/i.test(value.threadId) && Array.isArray(value.messages) ? value : null
  } catch { return null }
}
function savedAssumptions(customerId: number): Partial<Buyer> {
  try {
    const saved = JSON.parse(localStorage.getItem(`housing-assumptions-${customerId}`) ?? '{}') as Partial<Buyer>
    return Object.fromEntries(savedKeys.filter(key => saved[key] != null).map(key => [key, saved[key]]))
  } catch { return {} }
}
// crypto.randomUUID exists only on HTTPS/localhost; plain-HTTP deployments need this fallback.
function newThreadId(): string {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  const b = crypto.getRandomValues(new Uint8Array(16))
  b[6] = (b[6] & 0x0f) | 0x40
  b[8] = (b[8] & 0x3f) | 0x80
  const hex = Array.from(b, x => x.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
const errorText = (e: unknown, fallback: string) => e instanceof Error ? e.message : fallback

export default function App() {
  const [restoredChat] = useState(savedChatSession)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [customerId, setCustomerId] = useState<number | null>(null)
  const [customerQuery, setCustomerQuery] = useState('')
  const [customerOptions, setCustomerOptions] = useState<DemoCustomer[]>([])
  const [customer, setCustomer] = useState<CustomerDetail | null>(null)
  const [buyer, setBuyer] = useState<Buyer>(initialBuyer)
  const [draft, setDraft] = useState<Buyer>(initialBuyer)
  const [plan, setPlan] = useState<PlanResult | null>(null)
  const [explore, setExplore] = useState<ExploreResult | null>(null)
  const [pattern, setPattern] = useState<PatternResult | null>(null)
  const [screen, setScreen] = useState<Screen>('home')
  const [previous, setPrevious] = useState<Screen>('explore')
  const [menu, setMenu] = useState(false)
  const [chat, setChat] = useState(false)
  const [chatText, setChatText] = useState('')
  const [messages, setMessages] = useState<Message[]>(restoredChat?.messages ?? [])
  const [threadId, setThreadId] = useState(() => restoredChat?.threadId ?? newThreadId())
  const [chatBusy, setChatBusy] = useState(false)
  const [mapView, setMapView] = useState(false)
  const [mapMarkers, setMapMarkers] = useState<Trade[]>([])
  const [mapError, setMapError] = useState('')
  const [selected, setSelected] = useState<Trade | null>(null)
  const [range, setRange] = useState<Range>('all')
  const [sort, setSort] = useState<Sort>('low')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [stress, setStress] = useState(false)
  const menuButton = useRef<HTMLButtonElement>(null)
  // Version counters drop responses that arrive after the inputs they were for changed.
  const requestVersion = useRef(0)
  const customerVersion = useRef(0)
  const chatVersion = useRef(0)
  const scrollAfterUnlock = useRef<number | null>(null)
  // Home's '+1%p' switch recalculates every screen at the stressed rate without saving it.
  const calcBuyer = useMemo(() => stress ? { ...buyer, mortgage_rate: rateLabel(buyer.mortgage_rate + 1) } : buyer, [buyer, stress])
  const updateDraft = <K extends keyof Buyer>(key: K, value: Buyer[K]) => setDraft(current => ({ ...current, [key]: value }))
  const customerLabel = customerId == null ? '고객을 선택하세요' : `${customer?.customer.name ?? '고객'} · 고객 ID ${customerId}`

  const go = (next: Screen) => {
    if (menu || chat) scrollAfterUnlock.current = 0
    setMenu(false); setScreen(next); window.scrollTo(0, 0); menuButton.current?.focus()
  }
  const closeMenu = () => { setMenu(false); menuButton.current?.focus() }
  const startNewChat = () => {
    chatVersion.current += 1
    void deleteChat(threadId)
    setThreadId(newThreadId()); setChatBusy(false); setMessages([]); setChatText('')
  }

  useEffect(() => {
    api<Meta>('/meta').then(value => {
      setMeta(value); setBuyer(value.defaults); setDraft(value.defaults)
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
      const detail = await api<CustomerDetail>(`/demo-customers/${id}`)
      if (version !== customerVersion.current) return
      const c = detail.customer
      if ([c.household_annual_income, c.financial_assets_estimated, c.avg_monthly_consumption].some(v => v == null)) throw new Error('이 고객은 계산에 필요한 재무정보가 부족합니다.')
      const defaults = meta?.defaults ?? initialBuyer
      const sido = meta?.regions[c.sido]?.length ? c.sido : defaults.sido
      const sigungu = c.sigungu && meta?.regions[sido]?.includes(c.sigungu) ? c.sigungu : (meta?.regions[sido]?.[0] ?? defaults.sigungu)
      const next: Buyer = {
        ...defaults, ...savedAssumptions(id), sido, sigungu,
        price: c.purchase_reference_price ?? defaults.price, area: c.exclusive_area_m2 ?? defaults.area,
        ...(restore && restoredChat ? { sido: restoredChat.sido, sigungu: restoredChat.sigungu } : {}),
        age: c.age, income: c.household_annual_income,
        assets: c.consumption_source === 'budget' ? c.account_balance_total : c.financial_assets_estimated,
        consumption: c.avg_monthly_consumption, existing_payment: c.monthly_debt_service ?? 0,
      }
      requestVersion.current += 1
      chatVersion.current += 1
      if (!restore) { void deleteChat(threadId); setThreadId(newThreadId()) }
      setPlan(null); setExplore(null); setCustomerId(id); setCustomer(detail); setBuyer(next); setDraft(next)
      setMessages(restore ? restoredChat?.messages ?? [] : []); setChatBusy(false); setSelected(null); setMapMarkers([])
      go('home')
    } catch (e) { if (version === customerVersion.current) setError(errorText(e, '고객 정보를 불러오지 못했습니다.')) }
  }
  useEffect(() => { if (meta && restoredChat) void selectCustomer(restoredChat.customerId, true) }, [meta])

  // Same-tab refresh restores the conversation id and its visible history.
  useEffect(() => {
    if (customerId == null) return
    const history = messages.map(({ role, content, caveat }) => ({ role, content, caveat }))
    try { sessionStorage.setItem(CHAT_SESSION_KEY, JSON.stringify({ customerId, threadId, sido: buyer.sido, sigungu: buyer.sigungu, messages: history })) } catch { /* storage unavailable */ }
  }, [customerId, threadId, buyer.sido, buyer.sigungu, messages])

  useEffect(() => {
    if (!meta || customerId == null) return
    const version = ++requestVersion.current
    setPlan(null); setExplore(null); setPattern(null)
    Promise.all([post<PlanResult>('/plan', calcBuyer), post<ExploreResult>('/explore', calcBuyer), post<PatternResult>('/patterns', calcBuyer)])
      .then(([p, x, predicted]) => { if (version === requestVersion.current) { setPlan(p); setExplore(x); setPattern(predicted); setError('') } })
      .catch(e => { if (version === requestVersion.current) setError(e.message) })
  }, [calcBuyer, meta, customerId])

  useEffect(() => {
    if (!mapView || screen !== 'explore' || !meta || !explore || !plan) return
    let active = true
    const query = `?sido=${encodeURIComponent(buyer.sido)}&sigungu=${encodeURIComponent(buyer.sigungu)}`
    const complex_ids = explore.rows.filter(row => withinRange(row.purchase_reference_price, range, plan.bands)).slice(0, MAP_MARKER_LIMIT).map(row => row.complex_id)
    setMapMarkers([]); setMapError('')
    post<MapResult>('/map/resolve' + query, { complex_ids, customer_id: customerId })
      .then(data => { if (active) { setMapMarkers(data.markers); if (data.missing) setMapError(`주소로 좌표를 확인하지 못한 단지 ${data.missing}곳`) } })
      .catch(e => { if (active) setMapError(e.message) })
    return () => { active = false }
  }, [mapView, screen, buyer.sido, buyer.sigungu, meta, explore, plan, range, customerId])

  // Freeze the page behind the menu/chat. iOS Safari ignores overflow:hidden on body, so pin
  // the body in place and restore the scroll position (or the new screen's top) afterwards.
  const overlayOpen = menu || chat
  useEffect(() => {
    if (!overlayOpen) return
    const y = window.scrollY
    const body = document.body.style
    Object.assign(body, { position: 'fixed', top: `-${y}px`, left: '0', right: '0', overflow: 'hidden' })
    return () => {
      Object.assign(body, { position: '', top: '', left: '', right: '', overflow: '' })
      window.scrollTo(0, scrollAfterUnlock.current ?? y)
      scrollAfterUnlock.current = null
    }
  }, [overlayOpen])
  useEffect(() => {
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') { setMenu(false); setChat(false) } }
    document.addEventListener('keydown', escape)
    return () => document.removeEventListener('keydown', escape)
  }, [])

  const save = async () => {
    setSaving(true); setError('')
    try {
      await post<PlanResult>('/plan', draft)
      if (customerId != null) localStorage.setItem(`housing-assumptions-${customerId}`, JSON.stringify(Object.fromEntries(savedKeys.map(key => [key, draft[key]]))))
      startNewChat()
      setBuyer(draft); setSelected(null); go('home')
    } catch (e) { setError(errorText(e, '저장 실패')) }
    finally { setSaving(false) }
  }

  const send = async () => {
    const input = chatText.trim()
    if (!input || chatBusy) return
    const version = ++chatVersion.current
    setChatText(''); setChatBusy(true)
    const next: Message[] = [...messages, { role: 'user', content: input }]
    setMessages(next)
    try {
      const reply = await post<ChatReply>('/chat', { buyer: calcBuyer, thread_id: threadId, message: input })
      if (version !== chatVersion.current) return
      if (reply.applied_region) {
        const updated = { ...buyer, ...reply.applied_region }
        setBuyer(updated); setDraft(updated); setSelected(null); setMapMarkers([]); setRange('all')
      }
      setMessages([...next, { role: 'assistant', content: reply.answer, choices: reply.choices, recommendations: reply.recommendations, caveat: reply.caveat }])
    } catch (e) {
      if (version === chatVersion.current) {
        setThreadId(newThreadId())
        setMessages([...next, { role: 'assistant', content: `${errorText(e, '응답을 받지 못했습니다.')} 대화 문맥을 초기화했습니다. 질문을 다시 보내주세요.` }])
      }
    } finally { if (version === chatVersion.current) setChatBusy(false) }
  }

  const choose = (row: Trade) => { setPrevious('explore'); setSelected(row); go('detail') }
  const applyFilter = (patch: Partial<Buyer>) => { setBuyer(v => ({ ...v, ...patch })); setDraft(v => ({ ...v, ...patch })) }
  const mapSelect = useCallback((row: Trade) => setSelected(row), [])

  return <div className="mobile-shell"><div className="mobile-app">
    <header className="mobile-header">
      {screen === 'detail'
        ? <button className="plain-icon" aria-label="뒤로가기" onClick={() => go(previous)}><ArrowLeft size={22} /></button>
        : <button className="header-home" type="button" aria-label="내 구매력 홈으로" onClick={() => go('home')}><House size={20} /></button>}
      <strong>{screenTitles[screen]}</strong>
      {screen === 'explore' && <div className="view-tabs">
        <button className={!mapView ? 'active' : ''} onClick={() => setMapView(false)}>목록</button>
        <button className={mapView ? 'active' : ''} onClick={() => setMapView(true)}>지도</button>
      </div>}
      {screen === 'assumptions' && <button className="text-link" onClick={() => setDraft(meta?.defaults ?? initialBuyer)}>기본값으로</button>}
      <button ref={menuButton} className="plain-icon header-menu" aria-label="메뉴 열기" onClick={() => setMenu(true)}><Menu size={22} /></button>
    </header>
    {error && <div className="mobile-error" role="alert">{error}<button aria-label="오류 닫기" onClick={() => setError('')}><X size={15} /></button></div>}
    <main className="mobile-content">
      {screen !== 'connections' && <p className="data-badge">{customerLabel}</p>}
      {customerId == null ? <section className="mobile-card empty">
        <h2>고객을 선택하세요</h2>
        <p>DB에 있는 고객을 선택하면 해당 고객의 재무정보로 구매력을 계산합니다.</p>
        <button className="primary" onClick={() => setMenu(true)}>고객 선택하기</button>
      </section> : <>
        {screen === 'home' && <HomeScreen buyer={buyer} calcBuyer={calcBuyer} plan={plan} pattern={pattern} customer={customer} customerId={customerId} stress={stress} onStress={setStress} onExplore={() => go('explore')} />}
        {screen === 'explore' && <ExploreScreen buyer={buyer} regions={meta?.regions ?? {}} plan={plan} explore={explore}
          range={range} onRange={setRange} sort={sort} onSort={setSort} mapView={mapView} onListView={() => setMapView(false)}
          mapMarkers={mapMarkers} mapError={mapError} naverClientId={meta?.naver_client_id ?? ''} selected={selected}
          onMapSelect={mapSelect} onChoose={choose} onFilter={applyFilter} onHome={() => go('home')} onOwnedHome={() => go('finance')} />}
        {screen === 'detail' && selected && <DetailScreen trade={selected} buyer={buyer} calcBuyer={calcBuyer} plan={plan} />}
        {screen === 'finance' && <FinanceScreen customerId={customerId} customer={customer} buyer={buyer} draft={draft} onDraft={updateDraft} saving={saving} onSave={save} />}
        {screen === 'assumptions' && <AssumptionsScreen draft={draft} onDraft={updateDraft} saving={saving} onSave={save} />}
        {screen === 'connections' && <ConnectionsScreen customerId={customerId} customer={customer} onFinance={() => go('finance')} />}
        {screen !== 'connections' && <>
          <p className="mobile-disclaimer">제공 CSV와 학습 모델 기반 참고 계산이며 실제 매물이나 대출 승인을 보장하지 않아요.</p>
          {/* A button, not an input: the keyboard should open once, inside the chat sheet. */}
          <div className="mobile-chat-entry">
            <button type="button" className="chat-entry-open" onClick={() => setChat(true)}>{chatText || '조건을 말로 바꿔 보세요'}</button>
            <button type="button" aria-label="채팅 열기" onClick={() => setChat(true)}><Send size={18} /></button>
          </div>
        </>}
      </>}
    </main>
  </div>
    {menu && <Drawer customerLabel={customerLabel} customer={customer} query={customerQuery} onQuery={setCustomerQuery}
      options={customerOptions} onPick={id => void selectCustomer(id)} onGo={go} onClose={closeMenu} />}
    {chat && <ChatSheet messages={messages} busy={chatBusy} text={chatText} onText={setChatText} onSend={() => void send()}
      onReset={startNewChat} onClose={() => setChat(false)}
      onOpenTrade={trade => { setChat(false); choose(trade) }} onShowResults={() => { setChat(false); go('explore') }} />}
  </div>
}
