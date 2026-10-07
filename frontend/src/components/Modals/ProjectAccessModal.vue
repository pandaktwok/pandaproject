<template>
  <Dialog v-model:open="open" :size="'lg'">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pb-4 pt-5 sm:px-6">
        <h3 class="text-2xl-semibold text-ink-gray-9">{{ __('Project access') }}</h3>
        <p class="mb-4 mt-1 text-sm text-ink-gray-6">
          {{ __('With no people listed, every internal user can see this project. Once someone is listed, only the listed people, the owner and administrators can open it.') }}
        </p>
        <div v-if="!data" class="text-sm text-ink-gray-5">{{ __('Loading...') }}</div>
        <template v-else>
          <div v-if="!entries.length" class="rounded-lg bg-surface-gray-2 p-3 text-sm text-ink-gray-7">
            {{ __('Open to all internal users') }}
          </div>
          <div v-for="(e, i) in entries" :key="e.user" class="flex items-center gap-2 border-b py-2">
            <div class="min-w-0 flex-1 truncate text-sm text-ink-gray-9">{{ nameOf(e.user) }}</div>
            <FormControl
              v-model="e.access"
              type="select"
              class="w-36"
              :disabled="!data.can_manage"
              :options="[{ label: __('Can edit'), value: 'Edit' }, { label: __('View only'), value: 'View' }]"
            />
            <Button v-if="data.can_manage" variant="ghost" icon="lucide-x" @click="entries.splice(i, 1)" />
          </div>
          <div v-if="data.can_manage" class="mt-3 flex items-end gap-2">
            <FormControl
              v-model="toAdd"
              type="select"
              class="flex-1"
              :label="__('Add person')"
              :options="available"
            />
            <Button :label="__('Add')" :disabled="!toAdd" @click="add" />
          </div>
          <div v-else class="mt-3 text-xs text-ink-gray-5">
            {{ __('Only the owner or an administrator can change access.') }}
          </div>
          <ErrorMessage v-if="error" class="mt-3" :message="error" />
        </template>
      </div>
      <div class="flex flex-row-reverse gap-2 px-4 pb-6 pt-3 sm:px-6">
        <Button v-if="data?.can_manage" variant="solid" :label="__('Save')" :loading="busy" @click="save" />
        <Button :label="__('Close')" @click="open = false" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { call, Dialog, FormControl, Button, ErrorMessage, toast } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const props = defineProps({ deal: { type: String, required: true } })
const open = defineModel({ type: Boolean })
const data = ref(null)
const entries = ref([])
const toAdd = ref('')
const busy = ref(false)
const error = ref('')

const nameOf = (u) => data.value?.users.find((x) => x.name === u)?.full_name || u
const available = computed(() => [
  { label: __('Select a person'), value: '' },
  ...(data.value?.users || [])
    .filter((u) => !entries.value.some((e) => e.user === u.name))
    .map((u) => ({ label: u.full_name || u.name, value: u.name })),
])

async function load() {
  data.value = null
  error.value = ''
  data.value = await call('crm.panda.acesso.get_access', { deal: props.deal })
  entries.value = data.value.entries.map((e) => ({ user: e.user, access: e.access }))
}
function add() {
  if (!toAdd.value) return
  entries.value.push({ user: toAdd.value, access: 'Edit' })
  toAdd.value = ''
}
async function save() {
  busy.value = true
  error.value = ''
  try {
    data.value = await call('crm.panda.acesso.set_access', { deal: props.deal, entries: entries.value })
    entries.value = data.value.entries.map((e) => ({ user: e.user, access: e.access }))
    toast.success(__('Saved'))
    open.value = false
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || String(e)
  } finally {
    busy.value = false
  }
}
watch(open, (v) => v && load())
</script>
