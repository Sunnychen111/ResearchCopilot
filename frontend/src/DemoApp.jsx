
import { useEffect, useRef, useState } from 'react'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import {
    BookOpen,
    Bot,
    BrainCircuit,
    ChevronDown,
    Database,
    FileText,
    MessageSquare,
    Sparkles,
} from 'lucide-react'

// 导入你已经建立的演示聊天数据
import { demoConversations } from './DemoApp.js'

// 复用正式版 CSS
import './conversation.css'


// ==========================================
// 1. 演示用检索证据组件
// ==========================================

function DemoEvidenceList({ docs }) {

    // 第一层：整个证据列表是否展开
    const [isOpen, setIsOpen] = useState(false)

    // 第二层：记录哪些 Chunk 已展开
    const [openedChunks, setOpenedChunks] = useState({})

    if (!docs?.length) return null

    function toggleChunk(key) {
        setOpenedChunks((prev) => ({
            ...prev,
            [key]: !prev[key],
        }))
    }

    return (
        <section className="rc-evidence">

            {/* 整个证据列表的展开按钮 */}
            <button
                type="button"
                className="rc-evidence-header"
                aria-expanded={isOpen}
                onClick={() => setIsOpen((prev) => !prev)}
            >
                <BookOpen size={17} />

                <span>查看检索证据</span>

                <span className="rc-evidence-count">
                    {docs.length} 条
                </span>

                <ChevronDown
                    size={17}
                    className={
                        isOpen
                            ? 'rc-evidence-chevron rotated'
                            : 'rc-evidence-chevron'
                    }
                />
            </button>

            {/* 仅在展开时渲染所有 Chunk */}
            {isOpen && (
                <div className="rc-evidence-list">

                    {docs.map((doc, index) => {

                        const key = `${doc.id || index}-${index}`
                        const expanded = Boolean(openedChunks[key])

                        const sources = Array.isArray(doc.source)
                            ? doc.source
                            : []

                        return (
                            <article
                                key={key}
                                className="rc-evidence-card"
                            >

                                {/* 当前 Chunk 标题 */}
                                <button
                                    type="button"
                                    className="rc-evidence-item-header"
                                    aria-expanded={expanded}
                                    onClick={() => toggleChunk(key)}
                                >
                                    <span className="rc-evidence-item-name">

                                        <span className="rc-evidence-id">
                                            {doc.id || `Chunk ${index + 1}`}
                                        </span>

                                        <span className="rc-evidence-filename">
                                            {doc.filename || '未知文献'}
                                        </span>

                                        {doc.page_number != null && (
                                            <span className="rc-evidence-page">
                                                第 {doc.page_number} 页
                                            </span>
                                        )}

                                    </span>

                                    <ChevronDown
                                        size={15}
                                        className={
                                            expanded
                                                ? 'rc-evidence-chevron rotated'
                                                : 'rc-evidence-chevron'
                                        }
                                    />
                                </button>

                                {/* 当前 Chunk 详细信息 */}
                                {expanded && (
                                    <div className="rc-evidence-detail">

                                        <div className="rc-evidence-tags">
                                            {sources.map((source, i) => (
                                                <span
                                                    key={`${source}-${i}`}
                                                    className="rc-evidence-tag"
                                                >
                                                    {source}
                                                </span>
                                            ))}
                                        </div>

                                        <div className="rc-evidence-content">
                                            {doc.content || '暂无演示内容'}
                                        </div>

                                    </div>
                                )}

                            </article>
                        )
                    })}

                </div>
            )}

        </section>
    )
}


// ==========================================
// 2. 静态 Demo 主界面
// ==========================================

export default function DemoApp() {

    // 当前选中的话题 ID
    const [activeConversationId, setActiveConversationId] =
        useState(demoConversations[0]?.id ?? null)

    // 当前页面：chat 或 documents
    const [activePage, setActivePage] = useState('chat')

    // 聊天区域的滚动容器
    const chatAreaRef = useRef(null)

    // 从演示数据中找到当前话题
    const activeConversation = demoConversations.find(
        (item) => item.id === activeConversationId
    )

    // 获取当前话题的全部消息
    const messages = activeConversation?.messages ?? []

    // 收集 Demo 中出现过的论文名称
    // 仅用于静态文献库展示
    const demoDocuments = [
        ...new Set(
            demoConversations.flatMap((conversation) =>
                conversation.messages.flatMap((message) =>
                    (message.docs || [])
                        .map((doc) => doc.filename)
                        .filter(Boolean)
                )
            )
        ),
    ]

    // 切换话题时，滚动到聊天顶部
    useEffect(() => {
        if (activePage === 'chat') {
            chatAreaRef.current?.scrollTo({
                top: 0,
                behavior: 'instant',
            })
        }
    }, [activeConversationId, activePage])


    // ==========================================
    // 3. 话题切换
    // ==========================================

    function selectConversation(id) {
        setActiveConversationId(id)
        setActivePage('chat')
    }


    // ==========================================
    // 4. 页面渲染
    // ==========================================

    return (
        <div className="app-layout">

            {/* ========== 左侧栏 ========== */}
            <aside className="sidebar">

                <div className="brand">

                    <div className="brand-icon">
                        <BrainCircuit size={24} />
                    </div>

                    <div>
                        <div className="brand-title">
                            ResearchCopilot
                        </div>

                        <div className="brand-subtitle">
                            科研知识库助手 · Demo
                        </div>
                    </div>

                </div>

                {/* 显示静态演示话题 */}
                <div className="sidebar-history-section">

                    <div className="sidebar-heading conversation-heading">
                        <span>演示对话</span>
                    </div>

                    <div className="sidebar-history">

                        {demoConversations.map((conversation) => (

                            <button
                                key={conversation.id}
                                type="button"
                                className={
                                    `history-item ${activePage === 'chat' &&
                                        activeConversationId === conversation.id
                                        ? 'is-active'
                                        : ''
                                    }`
                                }
                                onClick={() => selectConversation(
                                    conversation.id
                                )}
                            >

                                <MessageSquare size={16} />

                                <span className="history-item-title">
                                    {conversation.title}
                                </span>

                            </button>

                        ))}

                    </div>
                </div>

                {/* 静态文献库导航 */}
                <button
                    type="button"
                    className={
                        `sidebar-example ${activePage === 'documents'
                            ? 'sidebar-nav-active'
                            : ''
                        }`
                    }
                    onClick={() => setActivePage('documents')}
                >
                    <Database size={18} />
                    <span>演示文献库</span>
                </button>

                {/* 明确标注当前不是实时 AI 服务 */}
                <div className="sidebar-bottom">

                    <div className="knowledge-card">
                        <Database size={19} />

                        <div>
                            <strong>静态演示模式</strong>
                            <span>预设问答 · 无需连接后端</span>
                        </div>
                    </div>

                </div>

            </aside>


            {/* ========== 右侧主窗口 ========== */}
            <main className="workspace">

                {activePage === 'documents' ? (

                    // ==================================
                    // 静态文献库页面
                    // ==================================

                    <section className="chat-area">

                        <div className="message-list">

                            <h2>演示文献库</h2>

                            <p>
                                以下是静态演示中使用的论文资料。
                                此页面不连接真实数据库。
                            </p>

                            {demoDocuments.map((filename) => (

                                <div
                                    key={filename}
                                    className="evidence-card"
                                    style={{
                                        padding: '18px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '12px',
                                    }}
                                >
                                    <FileText size={20} color="#0d9488" />

                                    <span>{filename}</span>
                                </div>

                            ))}

                            {demoDocuments.length === 0 && (
                                <p>暂无演示论文。</p>
                            )}

                            <p style={{
                                color: '#64748b',
                                fontSize: '12px',
                            }}>
                                PDF 上传、自动解析及真实检索功能，
                                请查看 GitHub 项目源码。
                            </p>

                        </div>

                    </section>

                ) : (

                    <>
                        {/* ========== 顶部标题栏 ========== */}

                        <header className="topbar">

                            <div>
                                <span className="topbar-caption">
                                    RESEARCH WORKSPACE · DEMO
                                </span>

                                <h1>
                                    {activeConversation?.title ||
                                        'ResearchCopilot 演示'}
                                </h1>
                            </div>

                            <div className="model-label">
                                <Sparkles size={15} />
                                静态演示 · 预设回答
                            </div>

                        </header>


                        {/* ========== 聊天消息 ========== */}

                        <section
                            className="chat-area"
                            ref={chatAreaRef}
                        >

                            <div className="message-list">

                                {messages.map((message) => (

                                    <div
                                        key={message.id}
                                        className={`message-row ${message.role}`}
                                    >

                                        {/* 助手头像 */}
                                        {message.role === 'assistant' && (
                                            <div className="assistant-avatar">
                                                <Bot size={20} />
                                            </div>
                                        )}

                                        <div className="message-body">

                                            {message.role === 'user' ? (

                                                // 用户消息
                                                <div className="user-bubble">
                                                    {message.text}
                                                </div>

                                            ) : (

                                                // 助手回答
                                                <div className="assistant-response">

                                                    <div className="assistant-name">
                                                        ResearchCopilot
                                                    </div>

                                                    {/* Markdown 渲染 */}
                                                    <div className="markdown-body">

                                                        <ReactMarkdown
                                                            remarkPlugins={[remarkGfm]}
                                                        >
                                                            {message.text || ''}
                                                        </ReactMarkdown>

                                                    </div>

                                                    {/* 检索证据两级折叠 */}
                                                    <DemoEvidenceList
                                                        key={
                                                            `${activeConversationId}-${message.id}`
                                                        }
                                                        docs={message.docs}
                                                    />

                                                </div>

                                            )}

                                        </div>

                                    </div>

                                ))}

                                {messages.length === 0 && (
                                    <p>请选择左侧演示话题。</p>
                                )}

                            </div>

                        </section>


                        {/* ========== 底部输入区域 ========== */}

                        <footer className="composer">

                            <div className="composer-box">

                                <textarea
                                    value=""
                                    readOnly
                                    disabled
                                    rows={2}
                                    placeholder={
                                        '当前为静态演示模式，暂不支持实时 AI 提问'
                                    }
                                />

                                <button
                                    type="button"
                                    className="send-button"
                                    disabled
                                    title="静态 Demo 不支持实时提问"
                                >
                                    <MessageSquare size={20} />
                                </button>

                            </div>

                            <div className="composer-footer">
                                <span>
                                    Demo Mode · 预设回答，不调用 DeepSeek API
                                </span>
                            </div>

                        </footer>
                    </>

                )}

            </main>

        </div>
    )
}
