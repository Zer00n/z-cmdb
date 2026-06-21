/**
 * Cost accounting currency composable
 * Reads default_currency from cost_rates, provides unified currency formatting functions
 * All cost pages should use this composable, no more hardcoding ¥ / CNY
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
  /** Load currency setting (called once on app init or entering cost page) */
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

  /** Force refresh currency (called after saving rates) */
  function refreshCurrency() {
    loaded = false
    return loadCurrency()
  }

  /** Current currency code, e.g. 'CNY' / 'USD' */
  const currency = computed(() => currencyCode.value)

  /** Current currency symbol, e.g. ¥ / $ */
  const symbol = computed(() => CURRENCY_SYMBOLS[currencyCode.value] || currencyCode.value)

  /** Format amount: ¥1,234 / $1,234 */
  function formatMoney(val: number): string {
    return symbol.value + val.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
  }

  /** Format amount (with 1 decimal): ¥1,234.5 / $1,234.5 */
  function formatMoneyDecimal(val: number): string {
    return symbol.value + val.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
  }

  /** Format large amounts (wan/K unit): ¥12.3W / $123K */
  function formatCompact(val: number): string {
    if (currencyCode.value === 'CNY') {
      return symbol.value + (val / 10000).toFixed(1) + 'W'
    }
    return symbol.value + (val / 1000).toFixed(1) + 'K'
  }

  /** Format very large amounts: ¥12W / $123K */
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
