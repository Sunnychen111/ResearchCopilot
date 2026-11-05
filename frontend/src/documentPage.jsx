
import { useEffect, useRef, useState } from 'react'

import {
    Upload,
    RefreshCw,
    FileText,
    Database,
} from 'lucide-react'

import './documentPage.css'

// FastAPI 后端地址
const API_BASE = 'http://127.0.0.1:8000'

// ==========================================
// 1. 通用工具函数
// ==========================================

// 数据库处理状态转中文
const STATUS_LABELS = {
    uploaded: '等待解析',
    processing: '解析中',
    parsed: '已解析',
    ready: '可检索',
    failed: '解析失败',
}

// 获取有效文本，避免 null、undefined 和空字符串
function getText(value) {
    if (typeof value !== 'string') {
        return null
    }

    return value.trim() || null
}

// 格式化 PDF 文件大小
function formatSize(bytes) {
    if (bytes == null) {
        return '—'
    }

    return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

// 格式化数据库上传时间
function formatTime(value) {
    if (!value) {
        return '—'
    }

    return String(value)
        .replace('T', ' ')
        .slice(0, 16)
}

// 格式化论文等级
// 例如：rank_system="CCF", rank_value="A"
// 最终显示：CCF · A
function formatRank(doc) {

    const system = getText(doc.rank_system)
    const value = getText(doc.rank_value)

    if (!system && !value) {
        return null
    }

    return [system, value]
        .filter(Boolean)
        .join(' · ')
}

// 作者没有识别出来时，显示对应的提示
function getAuthorsPlaceholder(status) {

    if (
        status === 'uploaded' ||
        status === 'processing'
    ) {
        return '正在等待作者信息提取...'
    }

    if (status === 'failed') {
        return '作者信息未能识别'
    }

    return '暂无作者信息'
}


// ==========================================
// 2. 文献库主组件
// ==========================================

export default function DocumentsPage() {

    // --------------------------------------
    // 文献数据
    // --------------------------------------

    const [documents, setDocuments] = useState([])

    // --------------------------------------
    // 页面状态
    // --------------------------------------

    const [loading, setLoading] = useState(true)
    const [uploading, setUploading] = useState(false)

    // --------------------------------------
    // 消息和错误提示
    // --------------------------------------

    const [listError, setListError] = useState('')
    const [uploadError, setUploadError] = useState('')
    const [message, setMessage] = useState('')

    // 自动恢复任务的提示
    const [recoveryMessage, setRecoveryMessage] = useState('')

    // 是否正在检查未完成论文
    const [checkingRecovery, setCheckingRecovery] = useState(false)

    // --------------------------------------
    // 手动刷新控制
    // --------------------------------------

    const [refreshVersion, setRefreshVersion] = useState(0)

    // --------------------------------------
    // 防止 React StrictMode 重复触发恢复检查
    // --------------------------------------

    const recoveryTriggered = useRef(false)


    // ======================================
    // 3. 页面打开时自动恢复未完成论文
    // ======================================

    useEffect(() => {

        // 只在本次页面挂载时触发一次
        // 不跟随 3 秒轮询重复执行
        if (recoveryTriggered.current) {
            return
        }

        recoveryTriggered.current = true

        async function checkUnfinishedDocuments() {

            setCheckingRecovery(true)

            try {

                // 请求后端检查尚未完成解析的文献
                const response = await fetch(
                    `${API_BASE}/api/documents/recover`,
                    {
                        method: 'POST',
                    }
                )

                const data = await response
                    .json()
                    .catch(() => null)

                if (!response.ok) {

                    const detail =
                        typeof data?.detail === 'string'
                            ? data.detail
                            : `HTTP ${response.status}`

                    throw new Error(detail)
                }

                // 情况 1：发现未完成论文并提交恢复任务
                if (data.started && data.queued > 0) {

                    setRecoveryMessage(
                        `检测到 ${data.queued} 篇未完成解析的论文，`
                        + '已提交后台恢复任务。'
                    )

                }

                // 情况 2：已有一批恢复任务正在执行
                else if (
                    data.message?.includes('正在执行')
                ) {

                    setRecoveryMessage(
                        '文献恢复任务正在后台执行，'
                        + '列表会自动更新解析状态。'
                    )

                }

                // 情况 3：所有论文都正常
                else {

                    setRecoveryMessage('')
                }

                // 检查结束后立即刷新文献列表
                setRefreshVersion(
                    (old) => old + 1
                )

            } catch (error) {

                console.error(
                    '自动恢复检查失败：',
                    error
                )

                // 恢复检查失败不会影响文献列表的正常展示
                setRecoveryMessage(
                    `自动恢复检查失败：${error.message}`
                )

            } finally {

                setCheckingRecovery(false)
            }
        }

        checkUnfinishedDocuments()

    }, [])


    // ======================================
    // 4. 获取数据库文献列表 + 3秒轮询
    // ======================================

    useEffect(() => {

        // 防止组件卸载后继续更新数据
        let stopped = false

        // 保存当前正在执行的请求
        let activeRequest = null

        async function loadDocuments() {

            // 不重复发起相同的请求
            if (activeRequest) {
                return
            }

            const controller = new AbortController()

            activeRequest = controller

            try {

                const response = await fetch(
                    `${API_BASE}/api/documents`,
                    {
                        signal: controller.signal,
                        cache: 'no-store',
                    }
                )

                if (!response.ok) {
                    throw new Error(
                        `获取文献失败：HTTP ${response.status}`
                    )
                }

                const data = await response.json()

                if (!Array.isArray(data)) {
                    throw new Error(
                        '后端接口没有返回文献列表'
                    )
                }

                if (!stopped) {

                    setDocuments(data)

                    setListError('')
                }

            } catch (error) {

                if (
                    !stopped &&
                    error.name !== 'AbortError'
                ) {
                    setListError(error.message)
                }

            } finally {

                activeRequest = null

                if (!stopped) {
                    setLoading(false)
                }
            }
        }

        // 第一次进入页面立即加载文献
        loadDocuments()

        // 每 3 秒重新读取一次 SQLite 中的文献状态
        const timer = setInterval(
            loadDocuments,
            3000
        )

        // 组件卸载时清理请求与定时器
        return () => {

            stopped = true

            clearInterval(timer)

            activeRequest?.abort()
        }

    }, [refreshVersion])


    // ======================================
    // 5. 上传 PDF 文件
    // ======================================

    async function handleUpload(event) {

        // 获取用户选择的文件
        const file = event.target.files?.[0]

        // 允许下次选择相同的 PDF
        event.target.value = ''

        if (!file) {
            return
        }

        setUploadError('')
        setMessage('')

        // PDF 扩展名检查
        if (!file.name.toLowerCase().endsWith('.pdf')) {

            setUploadError(
                '只能上传 PDF 文件'
            )

            return
        }

        // 20MB 文件大小限制
        if (file.size > 20 * 1024 * 1024) {

            setUploadError(
                'PDF 文件不能超过 20 MB'
            )

            return
        }

        setUploading(true)

        try {

            const formData = new FormData()

            // 与 FastAPI 的 file 参数保持一致
            formData.append('file', file)

            const response = await fetch(
                `${API_BASE}/api/documents/upload`,
                {
                    method: 'POST',
                    body: formData,
                }
            )

            const data = await response
                .json()
                .catch(() => null)

            if (!response.ok) {

                throw new Error(
                    typeof data?.detail === 'string'
                        ? data.detail
                        : `上传失败：HTTP ${response.status}`
                )
            }

            // 上传成功不代表后台已经解析完成
            setMessage(
                `${data.filename || file.name} `
                + '上传成功，正在等待后台解析。'
            )

            // 上传成功后立即刷新列表
            setRefreshVersion(
                (old) => old + 1
            )

        } catch (error) {

            setUploadError(
                error.message || '上传发生未知错误'
            )

        } finally {

            setUploading(false)
        }
    }


    // ======================================
    // 6. 文献统计
    // ======================================

    // 已完成 PDF 解析的文献
    const parsedCount = documents.filter(
        (doc) =>
            doc.status === 'parsed' ||
            doc.status === 'ready'
    ).length

    // 正在处理或等待处理的文献
    const processingCount = documents.filter(
        (doc) =>
            doc.status === 'uploaded' ||
            doc.status === 'processing'
    ).length

    // 解析失败的文献
    const failedCount = documents.filter(
        (doc) => doc.status === 'failed'
    ).length


    // ======================================
    // 7. 渲染页面
    // ======================================

    return (

        <section className="library-page">

            {/* ==================================
                顶部：标题 + 上传按钮
               ================================== */}

            <div className="library-header">

                <div>

                    <span className="library-kicker">
                        DOCUMENT LIBRARY
                    </span>

                    <h1>我的文献库</h1>

                    <p>
                        管理科研论文，自动提取标题与作者，
                        支持未完成文献自动恢复解析。
                    </p>

                </div>

                {/* PDF 上传入口 */}
                <label
                    className={
                        uploading
                            ? 'library-upload is-uploading'
                            : 'library-upload'
                    }
                >

                    <Upload size={17} />

                    {uploading ? '上传中...' : '上传 PDF'}

                    <input
                        type="file"
                        accept=".pdf,application/pdf"
                        onChange={handleUpload}
                        disabled={uploading}
                        hidden
                    />

                </label>

            </div>


            {/* ==================================
                操作结果与提示信息
               ================================== */}

            {message && (

                <div className="library-message">
                    {message}
                </div>

            )}

            {uploadError && (

                <div className="library-error">
                    {uploadError}
                </div>

            )}

            {listError && (

                <div className="library-error">
                    文献列表更新失败：{listError}
                </div>

            )}

            {/* 自动恢复检查中 */}
            {checkingRecovery && (

                <div className="library-message">
                    正在检查是否有未完成解析的论文...
                </div>

            )}

            {/* 自动恢复检查结果 */}
            {!checkingRecovery && recoveryMessage && (

                <div className="library-message">
                    {recoveryMessage}
                </div>

            )}


            {/* ==================================
                文献数量统计
               ================================== */}

            <div className="library-stats">

                <div className="library-stat">

                    <Database size={20} />

                    <span>全部文献</span>

                    <strong>
                        {documents.length}
                    </strong>

                </div>

                <div className="library-stat">

                    <FileText size={20} />

                    <span>已解析</span>

                    <strong>
                        {parsedCount}
                    </strong>

                </div>

                <div className="library-stat">

                    <RefreshCw size={20} />

                    <span>处理中</span>

                    <strong>
                        {processingCount}
                    </strong>

                    {failedCount > 0 && (
                        <small
                            style={{
                                color: '#be123c',
                                fontSize: '11px',
                            }}
                        >
                            {failedCount} 篇解析失败
                        </small>
                    )}

                </div>

            </div>


            {/* ==================================
                文献列表工具栏
               ================================== */}

            <div className="library-toolbar">

                <strong>
                    文献列表
                </strong>

                <button
                    type="button"
                    onClick={() => {
                        // 仅刷新列表，不重新触发恢复任务
                        setRefreshVersion(
                            (old) => old + 1
                        )
                    }}
                >

                    <RefreshCw size={15} />

                    立即刷新

                </button>

            </div>


            {/* ==================================
                文献数据表格
               ================================== */}

            <div className="library-table-wrap">

                <table className="library-table">

                    <thead>

                        <tr>
                            <th>论文信息</th>
                            <th>发表来源</th>
                            <th>论文等级</th>
                            <th>PDF 信息</th>
                            <th>解析状态</th>
                            <th>上传时间</th>
                        </tr>

                    </thead>

                    <tbody>

                        {/* 加载状态 */}
                        {loading ? (

                            <tr>
                                <td colSpan={6}>
                                    正在读取文献数据库...
                                </td>
                            </tr>

                        ) : documents.length === 0 ? (

                            /* 数据库没有论文 */
                            <tr>
                                <td colSpan={6}>
                                    暂无文献，请先上传 PDF。
                                </td>
                            </tr>

                        ) : (

                            /* 展示数据库中的全部论文 */
                            documents.map((doc) => {

                                // 读取数据库元数据
                                const title = getText(doc.title)

                                const authors = getText(doc.authors)

                                const venue = getText(doc.venue)

                                const rank = formatRank(doc)

                                // 标题识别失败时，使用 PDF 文件名
                                const displayTitle =
                                    title ||
                                    doc.filename ||
                                    '未命名文献'

                                return (

                                    <tr key={doc.id}>

                                        {/* =====================
                                            标题、作者、PDF 文件名
                                           ===================== */}

                                        <td className="library-paper-cell">

                                            <div className="library-paper">

                                                <div className="library-paper-icon">

                                                    <FileText size={19} />

                                                </div>

                                                <div className="library-paper-content">

                                                    {/* 论文标题 */}
                                                    <div
                                                        className={
                                                            title
                                                                ? 'library-paper-title'
                                                                : 'library-paper-title is-fallback'
                                                        }
                                                        title={displayTitle}
                                                    >

                                                        {displayTitle}

                                                    </div>

                                                    {/* 作者信息 */}
                                                    <div className="library-paper-authors">

                                                        {authors ||
                                                            getAuthorsPlaceholder(
                                                                doc.status
                                                            )}

                                                    </div>

                                                    {/* 原始 PDF 文件名 */}
                                                    <div className="library-paper-filename">

                                                        {title
                                                            ? `PDF · ${doc.filename || '未命名文件'}`
                                                            : '尚未获取论文正式标题'}

                                                    </div>

                                                </div>

                                            </div>

                                        </td>


                                        {/* =====================
                                            会议 / 期刊
                                           ===================== */}

                                        <td>

                                            {venue ? (

                                                <span className="library-venue">
                                                    {venue}
                                                </span>

                                            ) : (

                                                <span className="library-muted">
                                                    未填写
                                                </span>

                                            )}

                                        </td>


                                        {/* =====================
                                            CCF / 中科院等级
                                           ===================== */}

                                        <td>

                                            {rank ? (

                                                <span className="library-rank">
                                                    {rank}
                                                </span>

                                            ) : (

                                                <span className="library-muted">
                                                    未评级
                                                </span>

                                            )}

                                        </td>


                                        {/* =====================
                                            PDF 页数和大小
                                           ===================== */}

                                        <td>

                                            <div className="library-file-meta">

                                                <span>

                                                    {doc.page_count != null
                                                        ? `${doc.page_count} 页`
                                                        : '页数未知'}

                                                </span>

                                                <span className="library-muted">

                                                    {formatSize(
                                                        doc.file_size
                                                    )}

                                                </span>

                                            </div>

                                        </td>


                                        {/* =====================
                                            PDF 解析状态
                                           ===================== */}

                                        <td>

                                            <span
                                                className={
                                                    `library-status status-${doc.status}`
                                                }
                                            >

                                                {STATUS_LABELS[doc.status] ||
                                                    doc.status ||
                                                    '未知状态'}

                                            </span>

                                        </td>


                                        {/* =====================
                                            上传日期
                                           ===================== */}

                                        <td className="library-date">

                                            {formatTime(
                                                doc.created_at
                                            )}

                                        </td>

                                    </tr>

                                )
                            })

                        )}

                    </tbody>

                </table>

            </div>


            {/* ==================================
                底部说明
               ================================== */}

            <p className="library-note">

                页面打开时自动检查未完成的文献解析任务。
                文献列表每 3 秒自动刷新。
                已完成解析的论文不会重复处理。

            </p>

        </section>
    )
}
