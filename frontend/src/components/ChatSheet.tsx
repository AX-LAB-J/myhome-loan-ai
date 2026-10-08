import { useEffect, useRef } from 'react'
import { MessageCircle, RotateCcw, Send, X } from 'lucide-react'
import type { Message, Trade } from '../api'
import { ChatRecommendation } from './ui'

const SUGGESTIONS = ['성동구에서 내 조건에 맞는 집을 찾아줘', '금리가 1%p 올라도 괜찮은 곳은?', '예비비를 남기려면 어떻게 해야 해?']

export default function ChatSheet({ messages, busy, text, onText, onSend, onReset, onClose, onOpenTrade, onShowResults }: {
  messages: Message[]; busy: boolean; text: string; onText: (text: string) => void; onSend: () => void
  onReset: () => void; onClose: () => void; onOpenTrade: (trade: Trade) => void; onShowResults: () => void
}) {
  const overlay = useRef<HTMLDivElement>(null)
  const body = useRef<HTMLDivElement>(null)
  // iOS keeps the layout viewport full height when the keyboard opens; follow the visible
  // area instead so the sheet sits right above the keyboard instead of sliding under it.
  useEffect(() => {
    const view = window.visualViewport
    const el = overlay.current
    if (!view || !el) return
    const fit = () => { el.style.top = `${view.offsetTop}px`; el.style.height = `${view.height}px`; el.style.bottom = 'auto' }
    fit()
    view.addEventListener('resize', fit)
    view.addEventListener('scroll', fit)
    return () => { view.removeEventListener('resize', fit); view.removeEventListener('scroll', fit) }
  }, [])
  // Keep the newest message (or the "thinking" line) in view.
  const first = useRef(true)
  useEffect(() => {
    body.current?.scrollTo({ top: body.current.scrollHeight, behavior: first.current ? 'auto' : 'smooth' })
    first.current = false
  }, [messages.length, busy])
  return <div className="overlay chat-overlay" ref={overlay} onClick={onClose}>
    <section className="chat-sheet" role="dialog" aria-modal="true" aria-label="조건을 말로 바꿔 보세요" onClick={e => e.stopPropagation()}>
      <div className="sheet-handle" />
      <div className="title-row chat-title">
        <h2>조건을 말로 바꿔 보세요</h2>
        {messages.length > 0 && <button className="chat-reset" onClick={onReset}><RotateCcw size={13} />새로 시작</button>}
        <button className="plain-icon" aria-label="채팅 닫기" onClick={onClose}><X /></button>
      </div>
      <div className="chat-body" ref={body}>
        {messages.length === 0 && <div className="chat-empty">
          <MessageCircle size={30} strokeWidth={1.6} />
          <p>지역, 금리, 월 상환처럼 궁금한 조건을 물어보세요.</p>
          <div className="suggestions">{SUGGESTIONS.map(v => <button key={v} onClick={() => onText(v)}>{v}</button>)}</div>
        </div>}
        {messages.map((m, i) => <div key={i} className="chat-message">
          <p className={'chat-bubble ' + m.role}>{m.content}</p>
          {m.recommendations?.map(({ trade, reason }) => <ChatRecommendation key={trade.complex_id} trade={trade} reason={reason} onOpen={() => onOpenTrade(trade)} />)}
          {m.caveat && <p className="hint">{m.caveat}</p>}
        </div>)}
        {busy && <p className="hint">답변을 확인하는 중…</p>}
      </div>
      {messages.length > 0 && <div className="chat-actions"><button onClick={onShowResults}>바뀐 결과 보기</button></div>}
      <form className="sheet-form" onSubmit={e => { e.preventDefault(); onSend() }}>
        <input aria-label="질문 입력" value={text} placeholder="예: 월 상환을 더 낮추고 싶어" onChange={e => onText(e.target.value)} />
        <button type="submit" disabled={busy || !text.trim()} aria-label="질문 보내기"><Send size={18} /></button>
      </form>
      <p className="hint">금액은 AI가 아니라 계산기가 계산해요. AI는 결과를 설명해요.</p>
    </section>
  </div>
}
