import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'sentinel-theme'

export function getInitialTheme(): Theme {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch {}
  if (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark'
  return 'light'
}

export function applyTheme(theme: Theme) {
  if (typeof document !== 'undefined') document.documentElement.dataset.theme = theme
  try { localStorage.setItem(STORAGE_KEY, theme) } catch {}
}

export function useTheme(): [Theme, (t: Theme) => void] {
  const [theme, setTheme] = useState<Theme>(getInitialTheme)
  useEffect(() => { applyTheme(theme) }, [theme])
  return [theme, setTheme]
}
