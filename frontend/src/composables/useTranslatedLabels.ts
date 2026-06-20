import { useI18n } from 'vue-i18n'

export function useTranslatedLabels() {
  const { t } = useI18n()

  function zoneLabel(zone: string): string {
    const key = `constants.zones.${zone}`
    const translated = t(key)
    return translated !== key ? translated : zone
  }

  function importanceLabel(imp: string): string {
    const key = `constants.importance.${imp}`
    const translated = t(key)
    return translated !== key ? translated : imp
  }

  function statusLabel(s: string): string {
    const map: Record<string, string> = {
      online: t('common.status.online'),
      offline: t('common.status.offline'),
      decommissioned: t('common.status.decommissioned'),
    }
    return map[s] || s
  }

  function typeLabel(type: string): string {
    const key = `constants.assetTypes.${type}`
    const translated = t(key)
    return translated !== key ? translated : type
  }

  function roleLabel(role: string): string {
    const key = `common.roles.${role}`
    const translated = t(key)
    return translated !== key ? translated : role
  }

  function scanStatusLabel(s: string): string {
    const key = `constants.scanStatus.${s}`
    const translated = t(key)
    return translated !== key ? translated : s
  }

  return { zoneLabel, importanceLabel, statusLabel, typeLabel, roleLabel, scanStatusLabel }
}
