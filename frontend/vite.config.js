
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],

  // GitHub Pages 使用仓库子路径
  // 本地开发仍使用根路径 /
  base:
    process.env.VITE_DEMO_MODE === 'true'
      ? '/ResearchCopilot/'
      : '/',
})
