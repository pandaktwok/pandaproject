<template>
  <div class="flex h-full flex-col gap-6 overflow-y-auto p-8 text-ink-gray-8">
    <div>
      <h2 class="text-xl-semibold text-ink-gray-9">{{ __('Privacy (LGPD)') }}</h2>
      <p class="mt-1 text-sm text-ink-gray-6">
        {{ __('Privacy policy text, and tools to export or erase the data of a contact.') }}
      </p>
    </div>
    <section class="rounded-lg border p-4 text-ink-gray-8">
      <h3 class="text-lg-semibold text-ink-gray-9">{{ __('Privacy policy') }}</h3>
      <FormControl class="mt-3" v-model="policy" type="textarea" :rows="10" />
      <div class="mt-3 flex items-center gap-3">
        <Button variant="solid" :label="__('Save')" @click="savePolicy" />
        <span class="text-xs text-ink-gray-5">{{ __('Public address for the website') }}: <code class="text-ink-gray-9">/api/method/crm.panda.lgpd.public_policy</code></span>
      </div>
    </section>
    <section class="rounded-lg border p-4 text-ink-gray-8">
      <h3 class="text-lg-semibold text-ink-gray-9">{{ __('Contact data') }}</h3>
      <p class="mt-1 text-sm text-ink-gray-6">
        {{ __('Legal basis and consent date are set on each contact. Erasing removes the contact and its WhatsApp/Instagram conversations. This cannot be undone.') }}
      </p>
      <div class="mt-3 flex flex-wrap items-end gap-3">
        <FormControl class="w-72" v-model="contact" type="select" :options="options" :label="__('Contact')" />
        <Button :label="__('Export data')" :disabled="!contact" @click="doExport" />
        <Button theme="red" :label="__('Erase data')" :disabled="!contact" @click="confirm = true" />
      </div>
    </section>
  </div>
  <Dialog v-model:open="confirm" :size="'sm'">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pb-4 pt-5 sm:px-6">
        <h3 class="mb-2 text-2xl-semibold text-ink-gray-9">{{ __('Erase data') }}</h3>
        <p class="text-sm text-ink-gray-7">{{ __('Erase this contact and its conversations permanently?') }}</p>
      </div>
      <div class="flex flex-row-reverse gap-2 px-4 pb-6 pt-3 sm:px-6">
        <Button variant="solid" theme="red" :label="__('Erase')" @click="doErase" />
        <Button :label="__('Cancel')" @click="confirm = false" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { Button, Dialog, FormControl, call, toast } from 'frappe-ui'
import { onMounted, ref } from 'vue'

const policy = ref('')
const contact = ref('')
const options = ref([])
const confirm = ref(false)
const msg = (e) => e?.messages?.[0] || e?.message || String(e)

onMounted(async () => {
  policy.value = await call('crm.panda.lgpd.get_policy')
  const l = await call('frappe.client.get_list', { doctype: 'Contact', fields: ['name', 'full_name'], limit_page_length: 500 })
  options.value = [{ label: '—', value: '' }, ...l.map((c) => ({ label: c.full_name || c.name, value: c.name }))]
})
async function savePolicy() {
  try {
    await call('crm.panda.lgpd.save_policy', { text: policy.value })
    toast.success(__('Saved'))
  } catch (e) {
    toast.error(msg(e))
  }
}
async function doExport() {
  try {
    const d = await call('crm.panda.lgpd.export_contact', { contact: contact.value })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' }))
    a.download = `dados-${contact.value}.json`
    a.click()
  } catch (e) {
    toast.error(msg(e))
  }
}
async function doErase() {
  try {
    await call('crm.panda.lgpd.erase_contact', { contact: contact.value })
    toast.success(__('Erased'))
    options.value = options.value.filter((o) => o.value !== contact.value)
    contact.value = ''
  } catch (e) {
    toast.error(msg(e))
  } finally {
    confirm.value = false
  }
}
</script>
