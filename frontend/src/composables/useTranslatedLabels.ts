import { useI18n } from 'vue-i18n'

export function useTranslatedLabels() {
  const { t } = useI18n()

  function zoneLabel(zone: string): string {
    if (!zone) return zone || ''
    const key = `constants.zones.${zone}`
    const translated = t(key)
    return translated !== key ? translated : zone
  }

  function importanceLabel(imp: string): string {
    if (!imp) return imp || ''
    const key = `constants.importance.${imp}`
    const translated = t(key)
    return translated !== key ? translated : imp
  }

  function statusLabel(s: string): string {
    if (!s) return s || ''
    const map: Record<string, string> = {
      online: t('common.status.online'),
      offline: t('common.status.offline'),
      decommissioned: t('common.status.decommissioned'),
    }
    return map[s] || s
  }

  function typeLabel(type: string): string {
    if (!type) return type || ''
    const key = `constants.assetTypes.${type}`
    const translated = t(key)
    return translated !== key ? translated : type
  }

  function roleLabel(role: string): string {
    if (!role) return role || ''
    const key = `common.roles.${role}`
    const translated = t(key)
    return translated !== key ? translated : role
  }

  function scanStatusLabel(s: string): string {
    if (!s) return s || ''
    const key = `constants.scanStatus.${s}`
    const translated = t(key)
    return translated !== key ? translated : s
  }

  return { zoneLabel, importanceLabel, statusLabel, typeLabel, roleLabel, scanStatusLabel }
}
