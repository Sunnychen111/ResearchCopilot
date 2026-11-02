
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
  Plus,
  Sparkles,
  Wifi,
  WifiOff,
} from 'lucide-react'

import DocumentsPage from './documentPage.jsx'

const API_BASE = 'http://127.0.0.1:8000'

const EXAMPLES = [
  'DPTracker 与 3DPT 在融合方式上有什么不同？',
  '哪些论文讨论了深度信息的可靠性？',
  'DFormerv2 如何利用深度几何信息？',
  'RGB-D 跟踪中的负迁移问题有哪些？',
]

// 检索证据组件
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
          // 兼容你当前后端的 source，以及未来可能使用的 sources
          const sources = Array.isArray(doc.source)
            ? doc.source
            : Array.isArray(doc.sources)
              ? doc.sources
              : []

          return (
            <details
              className="evidence-card"
              key={`${doc.id || index}-${index}`}
            >
              <summary>
                <span className="doc-label">
                  <span className="doc-id">
                    {doc.id || `文档 ${index + 1}`}
                  </span>
                  <span className="doc-section">
                    {doc.section || '未命名章节'}
                  </span>
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
                    <span key={`${source}-${i}`} className="source-tag">
                      {source}
                    </span>
                  ))}
                </div>

                <div className="evidence-content">
                  {doc.content || '暂无文档内容'}
                </div>
              </div>
            </details>
          )
        })}
      </div>
    </div>
  )
}

function App() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [apiStatus, setApiStatus] = useState('checking')
  // 当前页面：chat 或 documents
  const [activePage, setActivePage] = useState('chat')

  const inputRef = useRef(null)
  const bottomRef = useRef(null)

  // 页面启动后检查 FastAPI 是否可用
  useEffect(() => {
    const controller = new AbortController()

    fetch(`${API_BASE}/health`, {
      signal: controller.signal,
    })
      .then((response) => {
        setApiStatus(response.ok ? 'online' : 'offline')
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setApiStatus('offline')
        }
      })

    return () => controller.abort()
  }, [])

  // 收到新消息后自动滚动到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: 'smooth',
    })
  }, [messages, loading, error])

  // 向 FastAPI 发送问题
  async function submitQuestion(event) {
    event?.preventDefault()

    const text = question.trim()

    if (!text || loading) return

    setLoading(true)
    setError('')
    setQuestion('')

    const userMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      text,
    }

    setMessages((prev) => [...prev, userMessage])

    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: text,
        }),
      })

      const data = await response.json().catch(() => null)

      if (!response.ok) {
        const detail =
          typeof data?.detail === 'string'
            ? data.detail
            : `HTTP ${response.status}`

        throw new Error(`请求失败：${detail}`)
      }

      const assistantMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        text: data?.answer || '服务已响应，但没有生成回答。',
        docs: Array.isArray(data?.retrieved_docs)
          ? data.retrieved_docs
          : [],
      }

      setMessages((prev) => [...prev, assistantMessage])
      setApiStatus('online')
    } catch (err) {
      console.error('API 请求失败:', err)

      if (err instanceof TypeError) {
        setApiStatus('offline')
        setError('无法连接 FastAPI，请检查后端是否启动。')
      } else {
        setError(err.message || '发生未知错误')
      }

      // 失败后恢复用户的问题，方便重新发送
      setQuestion(text)
    } finally {
      setLoading(false)
    }
  }

  // 新建对话，仅清除当前页面的对话记录
  function newChat() {
    setActivePage('chat')
    setMessages([])
    setQuestion('')
    setError('')
    inputRef.current?.focus()
  }


  function selectExample(text) {
    setActivePage('chat')
    setQuestion(text)
    inputRef.current?.focus()
  }

  return (
    <div className="app-layout">
      {/* 左侧导航栏 */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <BrainCircuit size={24} />
          </div>
          <div>
            <div className="brand-title">ResearchCopilot</div>
            <div className="brand-subtitle">科研知识库助手</div>
          </div>
        </div>

        <button
          className="new-chat-button"
          type="button"
          onClick={newChat}
        >
          <Plus size={18} />
          新建对话
        </button>

        <button
          type="button"
          className="sidebar-example"
          onClick={() => setActivePage('documents')}
        >
          <Database size={18} />
          <span>我的文献库</span>
        </button>

        <div className="sidebar-heading">推荐问题</div>

        <div className="sidebar-examples">
          {EXAMPLES.map((example, index) => (
            <button
              key={index}
              type="button"
              className="sidebar-example"
              onClick={() => selectExample(example)}
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
              <span>RGB-D 视觉跟踪文献报告</span>
            </div>
          </div>

          <div className="connection-status">
            {apiStatus === 'online' ? (
              <Wifi size={16} />
            ) : (
              <WifiOff size={16} />
            )}

            <span>
              {apiStatus === 'online'
                ? 'FastAPI 已连接'
                : apiStatus === 'checking'
                  ? '正在检查后端'
                  : 'FastAPI 未连接'}
            </span>
          </div>
        </div>
      </aside>

      {/* 主工作区 */}
      <main className="workspace">
        {activePage == 'documents' ?
          (<DocumentsPage />) : (<>
            <header className="topbar">
              <div>
                <span className="topbar-caption">RESEARCH WORKSPACE</span>
                <h1>科研知识库问答</h1>
              </div>

              <div className="model-label">
                <Sparkles size={15} />
                BGE · BM25 · RRF · DeepSeek
              </div>
            </header>

            <section className="chat-area">
              {messages.length === 0 ? (
                <div className="welcome">
                  <div className="welcome-icon">
                    <BrainCircuit size={32} />
                  </div>

                  <div className="welcome-kicker">
                    YOUR RESEARCH ASSISTANT
                  </div>

                  <h2>让科研问题更容易找到答案</h2>

                  <p>
                    基于本地科研文献知识库，通过混合检索与大模型生成，
                    帮助你理解论文方法、比较技术路线，并查看对应的检索证据。
                  </p>

                  <div className="welcome-examples">
                    {EXAMPLES.map((example, index) => (
                      <button
                        key={index}
                        type="button"
                        onClick={() => selectExample(example)}
                      >
                        <FileText size={17} />
                        <span>{example}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="message-list">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`message-row ${message.role}`}
                    >
                      {message.role === 'assistant' && (
                        <div className="assistant-avatar">
                          <Bot size={20} />
                        </div>
                      )}

                      <div className="message-body">
                        {message.role === 'user' ? (
                          <div className="user-bubble">
                            {message.text}
                          </div>
                        ) : (
                          <div className="assistant-response">
                            <div className="assistant-name">
                              ResearchCopilot
                            </div>

                            <div className="markdown-body">
                              <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                              >
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
                      <div className="assistant-avatar">
                        <Bot size={20} />
                      </div>

                      <div className="loading-message">
                        <span className="loading-dots">
                          <i />
                          <i />
                          <i />
                        </span>
                        正在检索文献并生成回答……
                      </div>
                    </div>
                  )}

                  {error && (
                    <div className="error-message" role="alert">
                      {error}
                    </div>
                  )}
                </div>
              )}

              <div ref={bottomRef} />
            </section>

            {/* 底部输入区域 */}
            <footer className="composer">
              <form onSubmit={submitQuestion}>
                <div className="composer-box">
                  <textarea
                    ref={inputRef}
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="输入你的科研问题，例如：DPTracker 与 3DPT 有什么区别？"
                    rows={2}
                    maxLength={2000}
                    disabled={loading}
                    onKeyDown={(e) => {
                      if (
                        e.key === 'Enter' &&
                        !e.shiftKey &&
                        !e.nativeEvent.isComposing
                      ) {
                        e.preventDefault()
                        submitQuestion()
                      }
                    }}
                  />

                  <button
                    type="submit"
                    className="send-button"
                    disabled={!question.trim() || loading}
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
          </>)}
      </main>
    </div>
  )
}

export default App
