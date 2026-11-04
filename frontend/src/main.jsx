
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import './index.css'

import App from './App.jsx'
import DemoApp from './DemoApp.jsx'

// VITE_DEMO_MODE=true 代表使用静态演示页面
// 默认不设置时，继续运行原来的真实 RAG 系统
const isDemo = import.meta.env.VITE_DEMO_MODE === 'true'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {isDemo ? <DemoApp /> : <App />}
  </StrictMode>
)
