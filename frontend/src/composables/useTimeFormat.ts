/**
 * 时间格式化 composable
 * 根据当前语言自动切换时区：zh → Asia/Shanghai (UTC+8)，en → America/New_York
 * 所有页面显示时间应使用此 composable，不再直接 dayjs().format() 或 new Date()
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

  /** 当前时间（指定时区） */
  function now(): dayjs.Dayjs {
    return dayjs().tz(tz.value)
  }

  /**
   * 格式化后端时间戳（UTC ISO string）为用户时区
   * @param time 后端返回的 ISO 时间字符串
   * @param fmt dayjs 格式，默认 'YYYY-MM-DD HH:mm'
   */
  function formatTime(time: string | null | undefined, fmt = 'YYYY-MM-DD HH:mm'): string {
    if (!time) return '-'
    return dayjs.utc(time).tz(tz.value).format(fmt)
  }

  /**
   * 格式化当前时间（用于页面时间戳、数据截至等）
   * @param fmt dayjs 格式，默认 'YYYY-MM-DD HH:mm'
   */
  function nowFormatted(fmt = 'YYYY-MM-DD HH:mm'): string {
    return now().format(fmt)
  }

  /**
   * 当前日期 YYYY-MM-DD
   */
  function today(): string {
    return now().format('YYYY-MM-DD')
  }

  /**
   * 当前月份 YYYY-MM
   */
  function currentMonth(): string {
    return now().format('YYYY-MM')
  }

  /**
   * 获取最近 N 个月份列表
   */
  function recentMonths(count = 12): string[] {
    const base = now()
    return Array.from({ length: count }, (_, i) =>
      base.subtract(i, 'month').format('YYYY-MM'),
    )
  }

  return { tz, now, formatTime, nowFormatted, today, currentMonth, recentMonths }
}
