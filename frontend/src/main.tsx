import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ConfigProvider, App as AntApp, theme } from 'antd'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#5b6abf',
          colorBgContainer: '#1a1a1a',
          colorBgElevated: '#222222',
          colorBgLayout: '#0d0d0d',
          borderRadius: 12,
          colorBorderSecondary: '#2a2a2a',
          fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        },
      }}
    >
      <AntApp>
        <App />
      </AntApp>
    </ConfigProvider>
  </StrictMode>,
)
