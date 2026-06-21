/**
 * Time formatting composable
 * Auto-switches timezone based on current language: zh -> Asia/Shanghai (UTC+8), en -> America/New_York
 * All pages should use this composable for time display, instead of dayjs().format() or new Date() directly
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'

dayjs.extend(utc)
dayjs.extend(timezone)

const TIMEZONE_MAP: Record<string, string> = {
  zh: 'Asia/Shanghai',
  en: 'America/New_York',
}

export function useTimeFormat() {
  const { locale } = useI18n()

  const tz = computed(() => TIMEZONE_MAP[locale.value] || 'Asia/Shanghai')

  /** Current time (in the configured timezone) */
  function now(): dayjs.Dayjs {
    return dayjs().tz(tz.value)
  }

  /**
   * Format backend timestamp (UTC ISO string) to user's timezone
   * @param time ISO time string from backend
   * @param fmt dayjs format, default 'YYYY-MM-DD HH:mm'
   */
  function formatTime(time: string | null | undefined, fmt = 'YYYY-MM-DD HH:mm'): string {
    if (!time) return '-'
    return dayjs.utc(time).tz(tz.value).format(fmt)
  }

  /**
   * Format current time (for page timestamps, data as-of, etc.)
   * @param fmt dayjs format, default 'YYYY-MM-DD HH:mm'
   */
  function nowFormatted(fmt = 'YYYY-MM-DD HH:mm'): string {
    return now().format(fmt)
  }

  /**
   * Current date YYYY-MM-DD
   */
  function today(): string {
    return now().format('YYYY-MM-DD')
  }

  /**
   * Current month YYYY-MM
   */
  function currentMonth(): string {
    return now().format('YYYY-MM')
  }

  /**
   * Get a list of recent N months
   */
  function recentMonths(count = 12): string[] {
    const base = now()
    return Array.from({ length: count }, (_, i) =>
      base.subtract(i, 'month').format('YYYY-MM'),
    )
  }

  return { tz, now, formatTime, nowFormatted, today, currentMonth, recentMonths }
}
