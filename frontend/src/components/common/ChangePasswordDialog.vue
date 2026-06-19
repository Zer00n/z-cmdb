<script setup lang="ts">
/**
 * 修改密码弹窗
 */
import { ref, reactive } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { changePassword } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

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
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 12, message: '密码至少 12 位', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (!value) return callback()
        const hasUpper = /[A-Z]/.test(value)
        const hasLower = /[a-z]/.test(value)
        const hasDigit = /\d/.test(value)
        const hasSymbol = /[^A-Za-z0-9]/.test(value)
        if (!(hasUpper && hasLower && hasDigit && hasSymbol)) {
          callback(new Error('必须包含大写字母、小写字母、数字和特殊符号'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.new_password) {
          callback(new Error('两次密码不一致'))
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
      // 改密成功，重置强制改密标记
      authStore.mustChangePassword = false
      ElMessage.success('密码修改成功')
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
    title="修改密码"
    width="440px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="旧密码" prop="old_password">
        <el-input v-model="form.old_password" type="password" show-password placeholder="请输入旧密码" />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="form.new_password" type="password" show-password placeholder="至少 12 位，含大小写数字符号" />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirm_password">
        <el-input v-model="form.confirm_password" type="password" show-password placeholder="再次输入新密码" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">确认修改</el-button>
    </template>
  </el-dialog>
</template>
