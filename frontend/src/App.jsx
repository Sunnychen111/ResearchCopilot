import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  ArrowUp,
  BookOpen,
  Bot,
  BrainCircuit,
  ChevronDown,
  Database,
  FileText,
  MessageSquare,
  Plus,
  RefreshCw,
  Sparkles,
  Wifi,
  WifiOff,
} from 'lucide-react'

import DocumentsPage from './documentPage.jsx'
import './conversation.css'

const API_BASE = 'http://127.0.0.1:8000'
const ACTIVE_CONVERSATION_KEY = 'researchcopilot.activeConversationId'

// 左栏每次展示两条，定时自动轮换；不从服务器请求推荐问题。
const EXAMPLES = [
  'DPTracker 与 3DPT 在融合方式上有什么不同？',
  '哪些论文讨论了深度信息的可靠性？',
  'DFormerv2 如何利用深度几何信息？',
  'RGB-D 跟踪中的负迁移问题有哪些？',
  'MPDTrack 如何解决相似目标身份歧义？',
  '不同 RGB-D 跟踪方法怎样利用深度先验？',
]
const EXAMPLES_PER_PAGE = 2
const RECOMMEND_ROTATE_MS = 9000
const EXAMPLE_PAGE_COUNT = Math.ceil(EXAMPLES.length / EXAMPLES_PER_PAGE)

// 统一处理 FastAPI 返回结果，便于提示准确的错误信息。
async function requestJson(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      cache: 'no-store',
      ...options,
    })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw new Error('无法连接 FastAPI，请确认后端已启动、端口为 8000，且允许前端跨域访问')
  }

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const detail = typeof data?.detail === 'string'
      ? data.detail
      : `HTTP ${response.status}`
    throw new Error(detail)
  }

  return data
}

// 后端 serialize_message 返回 text 和 docs；兼容未来可能出现的 content。
function normalizeMessage(message) {
  return {
    id: message.id,
    role: message.role,
    text: message.text ?? message.content ?? '',
    docs: Array.isArray(message.docs)
      ? message.docs
      : Array.isArray(message.retrieved_docs)
        ? message.retrieved_docs
        : [],
  }
}

function EvidenceList({ docs }) {
  if (!docs?.length) return null

  return (
    <div className="evidence">
      <div className="evidence-heading">
        <BookOpen size={16} />
        <span>检索证据</span>
        <span className="evidence-count">{docs.length} 条</span>
      </div>

      <div className="evidence-items">
        {docs.map((doc, index) => {
          const sources = Array.isArray(doc.source)
            ? doc.source
            : Array.isArray(doc.sources)
              ? doc.sources
              : []

          return (
            <details className="evidence-card" key={`${doc.id || index}-${index}`}>
              <summary>
                <span className="doc-label">
                  <span className="doc-id">{doc.id || `文档 ${index + 1}`}</span>
                  <span className="doc-section">{doc.section || doc.filename || '未命名章节'}</span>
                </span>
                <span className="doc-score">
                  {typeof doc.rrf_score === 'number'
                    ? `RRF ${doc.rrf_score.toFixed(4)}`
                    : ''}
                  <ChevronDown size={15} />
                </span>
              </summary>

              <div className="evidence-detail">
                <div className="source-tags">
                  {sources.map((source, i) => (
                    <span key={`${source}-${i}`} className="source-tag">{source}</span>
                  ))}
                </div>
                {(doc.filename || doc.page_number != null) && (
                  <div className="evidence-source-meta">
                    {doc.filename || '未知文献'}
                    {doc.page_number != null ? ` · 第 ${doc.page_number} 页` : ''}
                  </div>
                )}
                <div className="evidence-content">{doc.content || '暂无文档内容'}</div>
              </div>
            </details>
          )
        })}
      </div>
    </div>
  )
}

function App() {
  // 原有聊天与页面状态
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [apiStatus, setApiStatus] = useState('checking')
  const [activePage, setActivePage] = useState('chat')

  // 新增：对话管理状态
  const [conversations, setConversations] = useState([])
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [historyLoading, setHistoryLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [historyError, setHistoryError] = useState('')
  const [examplePage, setExamplePage] = useState(0)

  const inputRef = useRef(null)
  const bottomRef = useRef(null)
  const detailControllerRef = useRef(null)
  const sendingRef = useRef(false) // 避免快速按两次 Enter 产生重复请求

  // 获取历史对话列表。
  async function refreshConversations(signal) {
    const data = await requestJson('/api/conversations', { signal })
    if (!Array.isArray(data)) {
      throw new Error('历史对话接口没有返回数组')
    }
    if (!signal?.aborted) {
      setConversations(data)
      setHistoryError('')
    }
    return data
  }

  // 读取指定话题中的所有历史消息。
  async function loadConversation(conversationId, externalSignal = null) {
    // 取消上一次尚未完成的历史详情请求，防止快速切换导致内容串话。
    detailControllerRef.current?.abort()
    const controller = new AbortController()
    detailControllerRef.current = controller
    setDetailLoading(true)
    setError('')

    // 初始加载使用独立 signal；必要时一起终止请求。
    const abortFromParent = () => controller.abort()
    if (externalSignal) {
      if (externalSignal.aborted) controller.abort()
      else externalSignal.addEventListener('abort', abortFromParent, { once: true })
    }

    try {
      const data = await requestJson(`/api/conversations/${conversationId}`, {
        signal: controller.signal,
      })
      if (controller.signal.aborted) return
      if (!Array.isArray(data?.messages)) {
        throw new Error('对话详情没有返回 messages 数组')
      }

      setActiveConversationId(conversationId)
      setMessages(data.messages.map(normalizeMessage))
      setQuestion('')
      window.localStorage.setItem(ACTIVE_CONVERSATION_KEY, String(conversationId))
    } catch (err) {
      if (err.name !== 'AbortError' && !controller.signal.aborted) {
        setError(`读取聊天记录失败：${err.message}`)
      }
    } finally {
      if (externalSignal) {
        externalSignal.removeEventListener('abort', abortFromParent)
      }
      if (detailControllerRef.current === controller) {
        setDetailLoading(false)
      }
    }
  }

  // 页面初始化：先加载历史话题，再恢复上次打开的对话。
  useEffect(() => {
    const controller = new AbortController()

    async function initialize() {
      try {
        const health = await requestJson('/health', { signal: controller.signal })
        if (!controller.signal.aborted && health) setApiStatus('online')
      } catch (err) {
        if (err.name !== 'AbortError') setApiStatus('offline')
      }

      try {
        const list = await refreshConversations(controller.signal)
        if (controller.signal.aborted) return

        const storedId = Number(window.localStorage.getItem(ACTIVE_CONVERSATION_KEY))
        const remembered = Number.isInteger(storedId) && storedId > 0
          ? list.find((item) => item.id === storedId)
          : null
        const initial = remembered || list[0]

        if (initial) {
          await loadConversation(initial.id, controller.signal)
        } else {
          window.localStorage.removeItem(ACTIVE_CONVERSATION_KEY)
          setActiveConversationId(null)
          setMessages([])
        }
      } catch (err) {
        if (err.name !== 'AbortError' && !controller.signal.aborted) {
          setHistoryError(`无法加载历史话题：${err.message}`)
        }
      } finally {
        if (!controller.signal.aborted) setHistoryLoading(false)
      }
    }

    initialize()
    return () => {
      controller.abort()
      detailControllerRef.current?.abort()
    }
    // 只在 App 初次挂载时初始化；StrictMode 下可安全取消重复请求。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 推荐问题每 9 秒轮换一批，最多展示两条，不出现滚动条。
  useEffect(() => {
    if (activePage !== 'chat') return undefined
    const timer = window.setInterval(() => {
      setExamplePage((page) => (page + 1) % EXAMPLE_PAGE_COUNT)
    }, RECOMMEND_ROTATE_MS)
    return () => window.clearInterval(timer)
  }, [activePage])

  const sidebarExamples = EXAMPLES.slice(
    examplePage * EXAMPLES_PER_PAGE,
    (examplePage + 1) * EXAMPLES_PER_PAGE
  )

  // 收到消息或切换历史对话时自动滚动到底部。
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading, detailLoading, error])

  // 新建对话：先进入空白聊天界面，用户首次发送问题时才真正写入数据库。
  // 这样可以避免反复点击按钮生成大量没有消息的空话题。
  function newChat() {
    if (sendingRef.current || detailLoading) return
    detailControllerRef.current?.abort()
    window.localStorage.removeItem(ACTIVE_CONVERSATION_KEY)
    setActiveConversationId(null)
    setMessages([])
    setQuestion('')
    setError('')
    setActivePage('chat')
    inputRef.current?.focus()
  }

  async function selectConversation(id) {
    if (sendingRef.current || detailLoading) return
    setActivePage('chat')
    await loadConversation(id)
  }

  function selectExample(text) {
    if (sendingRef.current || detailLoading) return
    setActivePage('chat')
    setQuestion(text)
    inputRef.current?.focus()
  }

  // 发送问题：必须经过带 conversation_id 的新接口，不再直接调用 /api/chat。
  async function submitQuestion(event) {
    event?.preventDefault()
    const text = question.trim()
    if (!text || sendingRef.current || detailLoading || historyLoading) return

    sendingRef.current = true
    setLoading(true)
    setError('')
    setQuestion('')

    const optimisticId = `pending-${Date.now()}`
    setMessages((prev) => [
      ...prev,
      { id: optimisticId, role: 'user', text, docs: [] },
    ])

    try {
      let conversationId = activeConversationId

      // 只有首次提问才创建话题，标题取当前问题前 30 个字符。
      if (conversationId == null) {
        const newConversation = await requestJson('/api/conversations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: text.slice(0, 30) }),
        })

        conversationId = newConversation.id
        if (!Number.isInteger(conversationId)) {
          throw new Error('创建聊天话题时未返回有效 ID')
        }
        setActiveConversationId(conversationId)
        window.localStorage.setItem(ACTIVE_CONVERSATION_KEY, String(conversationId))
        setConversations((prev) => [newConversation, ...prev])
      }

      // 你的 FastAPI 接口会同时保存用户问题、AI 回答与检索证据。
      const data = await requestJson(`/api/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text }),
      })

      if (!data?.user_message || !data?.assistant_message) {
        throw new Error('接口没有返回完整的 user_message 和 assistant_message')
      }

      // 使用数据库真实 ID 替换临时消息；后续刷新页面仍能恢复。
      setMessages((prev) => [
        ...prev.filter((msg) => msg.id !== optimisticId),
        normalizeMessage(data.user_message),
        normalizeMessage(data.assistant_message),
      ])
      setApiStatus('online')

      // 历史列表更新失败不应该把本次成功问答当成失败。
      try {
        await refreshConversations()
      } catch (err) {
        setHistoryError(`话题列表刷新失败：${err.message}`)
      }
    } catch (err) {
      // 发送失败时移除未入库的临时消息，并恢复输入内容。
      setMessages((prev) => prev.filter((msg) => msg.id !== optimisticId))
      setQuestion(text)
      setError(`发送失败：${err.message || '未知错误'}`)
      if (err instanceof TypeError) setApiStatus('offline')
    } finally {
      sendingRef.current = false
      setLoading(false)
    }
  }

  async function manuallyRefreshHistory() {
    if (sendingRef.current) return
    setHistoryLoading(true)
    try {
      await refreshConversations()
    } catch (err) {
      setHistoryError(`刷新失败：${err.message}`)
    } finally {
      setHistoryLoading(false)
    }
  }

  return (
    <div className="app-layout">
      {/* 始终显示侧栏，不在主窗口提供切换按钮 */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon"><BrainCircuit size={24} /></div>
          <div>
            <div className="brand-title">ResearchCopilot</div>
            <div className="brand-subtitle">科研知识库助手</div>
          </div>
        </div>

        <button
          className="new-chat-button"
          type="button"
          onClick={newChat}
          disabled={loading || detailLoading}
        >
          <Plus size={18} /> 新建对话
        </button>

        <button
          type="button"
          className={`sidebar-example ${activePage === 'documents' ? 'sidebar-nav-active' : ''}`}
          onClick={() => {
            if (sendingRef.current) return
            setActivePage('documents')
                  }}
          disabled={loading}
        >
          <Database size={18} />
          <span>我的文献库</span>
        </button>

        {/* 没有历史话题时，整个“历史对话”区域都不渲染。 */}
        {conversations.length > 0 && (
          <section className="sidebar-history-section" aria-label="历史对话">
            <div className="sidebar-heading conversation-heading">
              <span>历史对话</span>
              <button
                className="sidebar-refresh"
                type="button"
                title="刷新历史对话"
                aria-label="刷新历史对话"
                disabled={historyLoading || loading}
                onClick={manuallyRefreshHistory}
              >
                <RefreshCw size={14} />
              </button>
            </div>
            <div className="sidebar-history" aria-label="历史对话列表">
              {conversations.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  title={item.title}
                  className={`history-item ${
                    activePage === 'chat' && activeConversationId === item.id ? 'is-active' : ''
                  }`}
                  onClick={() => selectConversation(item.id)}
                  disabled={loading || detailLoading}
                >
                  <MessageSquare size={16} />
                  <span className="history-item-title">{item.title || '未命名对话'}</span>
                  <span className="history-item-count">{item.message_count ?? ''}</span>
                </button>
              ))}
            </div>
          </section>
        )}

        <div className="sidebar-heading sidebar-example-heading">
          <span>推荐问题</span>
          <button
            className="sidebar-refresh"
            type="button"
            title="换一批推荐问题"
            aria-label="换一批推荐问题"
            onClick={() => setExamplePage((page) => (page + 1) % EXAMPLE_PAGE_COUNT)}
          >
            <RefreshCw size={14} />
          </button>
        </div>
        <div className="sidebar-examples" key={examplePage}>
          {sidebarExamples.map((example) => (
            <button
              key={example}
              type="button"
              className="sidebar-example"
              onClick={() => selectExample(example)}
              disabled={loading || detailLoading}
            >
              <FileText size={16} />
              <span>{example}</span>
            </button>
          ))}
        </div>

        <div className="sidebar-bottom">
          <div className="knowledge-card">
            <Database size={19} />
            <div>
              <strong>当前知识库</strong>
              <span>科研论文知识库</span>
            </div>
          </div>
          <div className="connection-status">
            {apiStatus === 'online' ? <Wifi size={16} /> : <WifiOff size={16} />}
            <span>
              {apiStatus === 'online'
                ? 'FastAPI 已连接'
                : apiStatus === 'checking'
                  ? '正在检查后端'
                  : 'FastAPI 未连接'}
            </span>
          </div>
          {historyError && (
            <button
              type="button"
              className="sidebar-history-retry"
              title={historyError}
              disabled={historyLoading || loading}
              onClick={manuallyRefreshHistory}
            >
              <RefreshCw size={13} />
              历史记录获取失败 · 重试
            </button>
          )}
        </div>
      </aside>

      <main className="workspace">
        {activePage === 'documents' ? (
          <>
            <DocumentsPage />
          </>
        ) : (
          <>
            <header className="topbar">
              <div className="topbar-main">
                <div>
                  <span className="topbar-caption">RESEARCH WORKSPACE</span>
                  <h1>
                    {conversations.find((item) => item.id === activeConversationId)?.title
                      || '科研知识库问答'}
                  </h1>
                </div>
              </div>
              <div className="model-label">
                <Sparkles size={15} /> BGE · BM25 · RRF · DeepSeek
              </div>
            </header>

            <section className="chat-area">
              {detailLoading ? (
                <div className="conversation-loading">正在恢复历史对话…</div>
              ) : messages.length === 0 ? (
                <div className="welcome">
                  <div className="welcome-icon"><BrainCircuit size={32} /></div>
                  <div className="welcome-kicker">YOUR RESEARCH ASSISTANT</div>
                  <h2>让科研问题更容易找到答案</h2>
                  <p>
                    基于本地科研文献知识库，通过混合检索与大模型生成，
                    帮助你理解论文方法、比较技术路线，并查看对应的检索证据。
                  </p>
                  <div className="welcome-examples">
                    {EXAMPLES.map((example, index) => (
                      <button key={index} type="button" onClick={() => selectExample(example)}>
                        <FileText size={17} /> <span>{example}</span>
                      </button>
                    ))}
                  </div>
                  {error && <div className="error-message" role="alert">{error}</div>}
                </div>
              ) : (
                <div className="message-list">
                  {messages.map((message) => (
                    <div key={message.id} className={`message-row ${message.role}`}>
                      {message.role === 'assistant' && (
                        <div className="assistant-avatar"><Bot size={20} /></div>
                      )}
                      <div className="message-body">
                        {message.role === 'user' ? (
                          <div className="user-bubble">{message.text}</div>
                        ) : (
                          <div className="assistant-response">
                            <div className="assistant-name">ResearchCopilot</div>
                            <div className="markdown-body">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {message.text}
                              </ReactMarkdown>
                            </div>
                            <EvidenceList docs={message.docs} />
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {loading && (
                    <div className="message-row assistant">
                      <div className="assistant-avatar"><Bot size={20} /></div>
                      <div className="loading-message">
                        <span className="loading-dots"><i /><i /><i /></span>
                        正在检索文献并生成回答……
                      </div>
                    </div>
                  )}
                  {error && <div className="error-message" role="alert">{error}</div>}
                </div>
              )}
              <div ref={bottomRef} />
            </section>

            <footer className="composer">
              <form onSubmit={submitQuestion}>
                <div className="composer-box">
                  <textarea
                    ref={inputRef}
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="输入你的科研问题，例如：MPDTrack 的主要创新是什么？"
                    rows={2}
                    maxLength={2000}
                    disabled={loading || detailLoading || historyLoading}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                        e.preventDefault()
                        submitQuestion()
                      }
                    }}
                  />
                  <button
                    type="submit"
                    className="send-button"
                    disabled={!question.trim() || loading || detailLoading || historyLoading}
                    aria-label="发送问题"
                  >
                    <ArrowUp size={21} />
                  </button>
                </div>
                <div className="composer-footer">
                  <span>Enter 发送 · Shift + Enter 换行</span>
                  <span>{question.length} / 2000</span>
                </div>
              </form>
            </footer>
          </>
        )}
      </main>
    </div>
  )
}

export default App
