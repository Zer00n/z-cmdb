/**
 * 成本核算币种 composable
 * 从 cost_rates 读取 default_currency，提供统一的货币格式化函数
 * 所有成本页面应使用此 composable，不再硬编码 ¥ / CNY
 */
import { ref, computed } from 'vue'
import { fetchCostRates } from '@/api/cost'

const currencyCode = ref<string>('CNY')
let loaded = false

const CURRENCY_SYMBOLS: Record<string, string> = {
  CNY: '¥',
  USD: '$',
  EUR: '€',
  GBP: '£',
  JPY: '¥',
}

export function useCostCurrency() {
  /** 加载币种设置（应用初始化或进入成本页面时调用一次） */
  async function loadCurrency() {
    if (loaded) return
    try {
      const rates = await fetchCostRates()
      const raw = rates['default_currency']
      if (raw) {
        currencyCode.value = typeof raw === 'string' ? raw : (raw as { value: string }).value || 'CNY'
      }
    } catch {
      // fallback to CNY
    }
    loaded = true
  }

  /** 强制刷新币种（保存费率后调用） */
  function refreshCurrency() {
    loaded = false
    return loadCurrency()
  }

  /** 当前币种代码，如 'CNY' / 'USD' */
  const currency = computed(() => currencyCode.value)

  /** 当前币种符号，如 ¥ / $ */
  const symbol = computed(() => CURRENCY_SYMBOLS[currencyCode.value] || currencyCode.value)

  /** 格式化金额：¥1,234 / $1,234 */
  function formatMoney(val: number): string {
    return symbol.value + val.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
  }

  /** 格式化金额（带1位小数）：¥1,234.5 / $1,234.5 */
  function formatMoneyDecimal(val: number): string {
    return symbol.value + val.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
  }

  /** 格式化大金额（万/K 单位）：¥12.3W / $123K */
  function formatCompact(val: number): string {
    if (currencyCode.value === 'CNY') {
      return symbol.value + (val / 10000).toFixed(1) + 'W'
    }
    return symbol.value + (val / 1000).toFixed(1) + 'K'
  }

  /** 格式化超大金额：¥12W / $123K */
  function formatCompactInt(val: number): string {
    if (currencyCode.value === 'CNY') {
      return symbol.value + (val / 10000).toFixed(0) + 'W'
    }
    return symbol.value + (val / 1000).toFixed(0) + 'K'
  }

  return {
    currency,
    symbol,
    loadCurrency,
    refreshCurrency,
    formatMoney,
    formatMoneyDecimal,
    formatCompact,
    formatCompactInt,
  }
}
