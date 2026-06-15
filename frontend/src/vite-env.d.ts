/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BASE_PATH?: string
  readonly VITE_ANALYTICS_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
