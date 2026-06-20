import { createI18n } from 'vue-i18n'
import en from './locales/en'
import zh from './locales/zh'

const STORAGE_KEY = 'cmdb-locale'

function getDefaultLocale(): string {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored && ['en', 'zh'].includes(stored)) return stored
  return 'en'
}

const i18n = createI18n({
  legacy: false,
  locale: getDefaultLocale(),
  fallbackLocale: 'en',
  messages: { en, zh },
})

export function setLocale(locale: 'en' | 'zh') {
  i18n.global.locale.value = locale
  localStorage.setItem(STORAGE_KEY, locale)
  document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en'
}

export default i18n
