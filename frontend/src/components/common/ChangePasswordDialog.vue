<script setup lang="ts">
/**
 * Change password dialog
 */
import { ref, reactive } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { changePassword } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const rules: FormRules = {
  old_password: [{ required: true, message: () => t('components.changePassword.validation.currentRequired'), trigger: 'blur' }],
  new_password: [
    { required: true, message: () => t('components.changePassword.validation.newRequired'), trigger: 'blur' },
    { min: 12, message: () => t('components.changePassword.newPlaceholder'), trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (!value) return callback()
        const hasUpper = /[A-Z]/.test(value)
        const hasLower = /[a-z]/.test(value)
        const hasDigit = /\d/.test(value)
        const hasSymbol = /[^A-Za-z0-9]/.test(value)
        if (!(hasUpper && hasLower && hasDigit && hasSymbol)) {
          callback(new Error(t('components.changePassword.newPlaceholder')))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  confirm_password: [
    { required: true, message: () => t('components.changePassword.validation.confirmRequired'), trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.new_password) {
          callback(new Error(t('components.changePassword.validation.mismatch')))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

function handleClose() {
  formRef.value?.resetFields()
  emit('update:modelValue', false)
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await changePassword({
        old_password: form.old_password,
        new_password: form.new_password,
      })
      // Password changed successfully, clear the forced change flag
      authStore.mustChangePassword = false
      ElMessage.success(t('components.changePassword.success'))
      handleClose()
    } finally {
      loading.value = false
    }
  })
}
</script>

<template>
  <el-dialog
    :model-value="props.modelValue"
    :title="t('components.changePassword.title')"
    width="440px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item :label="t('components.changePassword.currentPassword')" prop="old_password">
        <el-input v-model="form.old_password" type="password" show-password :placeholder="t('components.changePassword.currentPlaceholder')" />
      </el-form-item>
      <el-form-item :label="t('components.changePassword.newPassword')" prop="new_password">
        <el-input v-model="form.new_password" type="password" show-password :placeholder="t('components.changePassword.newPlaceholder')" />
      </el-form-item>
      <el-form-item :label="t('components.changePassword.confirmPassword')" prop="confirm_password">
        <el-input v-model="form.confirm_password" type="password" show-password :placeholder="t('components.changePassword.confirmPlaceholder')" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">{{ t('components.changePassword.submit') }}</el-button>
    </template>
  </el-dialog>
</template>
