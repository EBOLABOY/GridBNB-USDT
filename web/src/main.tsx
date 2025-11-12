import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { injectModernTheme, modernGlobalStyles } from './styles/modernGlobal'

// 注入现代化主题CSS变量
injectModernTheme();

// 注入全局样式
const styleElement = document.createElement('style');
styleElement.innerHTML = modernGlobalStyles;
document.head.appendChild(styleElement);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
