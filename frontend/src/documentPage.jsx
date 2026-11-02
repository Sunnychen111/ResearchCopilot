
import { useEffect, useState } from 'react'
import {
    Upload,
    RefreshCw,
    FileText,
    Database,
} from 'lucide-react'

import './documentPage.css'

const API_BASE = 'http://127.0.0.1:8000'

// 将数据库中的状态转换为中文
const STATUS_LABELS = {
    uploaded: '等待解析',
    processing: '解析中',
    parsed: '已解析',
    ready: '可检索',
    failed: '解析失败',
}

// 文件大小转换为 MB
function formatSize(bytes) {
    if (bytes == null) return '—'

    return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

// 时间格式化
function formatTime(value) {
    if (!value) return '—'

    return String(value).replace('T', ' ').slice(0, 16)
}

export default function DocumentsPage() {

    // 1. 数据库中的文献列表
    const [documents, setDocuments] = useState([])

    // 2. 页面与上传状态
    const [loading, setLoading] = useState(true)
    const [uploading, setUploading] = useState(false)

    // 3. 错误提示和成功提示
    const [listError, setListError] = useState('')
    const [uploadError, setUploadError] = useState('')
    const [message, setMessage] = useState('')

    // 修改此值可以立即触发列表刷新
    const [refreshVersion, setRefreshVersion] = useState(0)

    // ======================================
    // 4. 读取数据库 + 实时轮询
    // ======================================

    useEffect(() => {

        // 防止组件卸载后继续更新状态
        let stopped = false

        // 避免上一次查询尚未完成时重复发送请求
        let activeRequest = null

        async function loadDocuments() {

            if (activeRequest) return

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
                    throw new Error('接口未返回文献列表')
                }

                if (!stopped) {
                    setDocuments(data)
                    setListError('')
                }

            } catch (err) {

                if (!stopped && err.name !== 'AbortError') {
                    setListError(err.message)
                }

            } finally {

                activeRequest = null

                if (!stopped) {
                    setLoading(false)
                }
            }
        }

        // 页面打开时立即加载一次
        loadDocuments()

        // 每 3 秒重新读取一次数据库
        const timer = setInterval(loadDocuments, 3000)

        // 组件卸载时释放定时器和网络请求
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

        // 允许用户再次选择同一个文件
        event.target.value = ''

        if (!file) return

        setUploadError('')
        setMessage('')

        // PDF 类型检查
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            setUploadError('只能上传 PDF 文件')
            return
        }

        // 与后端保持相同的 20MB 限制
        if (file.size > 20 * 1024 * 1024) {
            setUploadError('PDF 文件不能超过 20MB')
            return
        }

        setUploading(true)

        try {

            // FormData 用于发送二进制文件
            const formData = new FormData()

            // "file" 必须与 FastAPI 参数名一致
            formData.append('file', file)

            const response = await fetch(
                `${API_BASE}/api/documents/upload`,
                {
                    method: 'POST',
                    body: formData,
                }
            )

            const data = await response.json().catch(
                () => null
            )

            if (!response.ok) {

                throw new Error(
                    typeof data?.detail === 'string'
                        ? data.detail
                        : `上传失败：HTTP ${response.status}`
                )
            }

            // 这里仅代表上传成功
            // PDF 解析由后端异步执行
            setMessage(
                `${data.filename} 上传成功，正在等待解析`
            )

            // 立即刷新列表，不必等待下一次轮询
            setRefreshVersion((old) => old + 1)

        } catch (err) {

            setUploadError(
                err.message || '上传发生未知错误'
            )

        } finally {

            setUploading(false)
        }
    }


    // ======================================
    // 6. 计算文献统计
    // ======================================

    const parsedCount = documents.filter(
        (doc) =>
            doc.status === 'parsed' ||
            doc.status === 'ready'
    ).length

    const processingCount = documents.filter(
        (doc) =>
            doc.status === 'uploaded' ||
            doc.status === 'processing'
    ).length


    // ======================================
    // 7. 渲染界面
    // ======================================

    return (
        <section className="library-page">

            <div className="library-header">

                <div>
                    <span className="library-kicker">
                        DOCUMENT LIBRARY
                    </span>

                    <h1>我的文献库</h1>

                    <p>
                        上传 PDF，自动解析并保存到科研知识库。
                    </p>
                </div>

                {/* 隐藏 input，点击标签即可选择文件 */}
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


            {/* 文献统计 */}
            <div className="library-stats">

                <div className="library-stat">
                    <Database size={20} />
                    <span>全部文献</span>
                    <strong>{documents.length}</strong>
                </div>

                <div className="library-stat">
                    <FileText size={20} />
                    <span>已解析</span>
                    <strong>{parsedCount}</strong>
                </div>

                <div className="library-stat">
                    <RefreshCw size={20} />
                    <span>处理中</span>
                    <strong>{processingCount}</strong>
                </div>

            </div>


            <div className="library-toolbar">

                <strong>文献列表</strong>

                <button
                    type="button"
                    onClick={() => {
                        setRefreshVersion((old) => old + 1)
                    }}
                >
                    <RefreshCw size={15} />
                    立即刷新
                </button>

            </div>


            {/* 数据库文献表 */}
            <div className="library-table-wrap">

                <table className="library-table">

                    <thead>
                        <tr>
                            <th>PDF 文件名</th>
                            <th>页数</th>
                            <th>文件大小</th>
                            <th>解析状态</th>
                            <th>上传时间</th>
                        </tr>
                    </thead>

                    <tbody>

                        {loading ? (

                            <tr>
                                <td colSpan={5}>
                                    正在读取文献数据库...
                                </td>
                            </tr>

                        ) : documents.length === 0 ? (

                            <tr>
                                <td colSpan={5}>
                                    暂无文献，请先上传 PDF
                                </td>
                            </tr>

                        ) : (

                            documents.map((doc) => (

                                <tr key={doc.id}>

                                    <td>
                                        <div className="library-filename">
                                            <FileText size={17} />
                                            <span>{doc.filename}</span>
                                        </div>
                                    </td>

                                    <td>{doc.page_count ?? '—'}</td>

                                    <td>
                                        {formatSize(doc.file_size)}
                                    </td>

                                    <td>
                                        <span
                                            className={
                                                `library-status status-${doc.status}`
                                            }
                                        >
                                            {STATUS_LABELS[doc.status] ||
                                                doc.status}
                                        </span>
                                    </td>

                                    <td>
                                        {formatTime(doc.created_at)}
                                    </td>

                                </tr>

                            ))

                        )}

                    </tbody>

                </table>

            </div>

            <p className="library-note">
                文献列表每 3 秒自动刷新。
                “已解析”表示 PDF 已完成文本入库。
            </p>

        </section>
    )
}
