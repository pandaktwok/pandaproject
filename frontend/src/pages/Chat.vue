<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: channel === 'WhatsApp' ? 'WhatsApp' : 'Instagram' }]" />
    </template>
    <template #right-header>
      <Button v-if="channel === 'WhatsApp'" variant="ghost" :loading="syncing" icon="lucide-refresh-cw" :tooltip="__('Check for new messages')" @click="syncNow(true)" />
      <Button variant="ghost" icon="lucide-settings" :tooltip="__('Connection settings')" @click="openSettings" />
    </template>
  </LayoutHeader>

  <!-- canal ainda não conectado -->
  <div v-if="notConnected" class="flex h-[calc(100vh-3.5rem)] items-center justify-center p-6">
    <div class="max-w-md text-center">
      <h2 class="text-xl-semibold text-ink-gray-9">
        {{ channel === 'WhatsApp' ? __('No WhatsApp connected') : __('No Instagram account connected') }}
      </h2>
      <p class="mt-2 text-sm text-ink-gray-6">
        {{
          status.is_admin
            ? channel === 'WhatsApp'
              ? __('Connect a number (QR Code via Evolution API, or the official Meta API) to answer your contacts here.')
              : __('Connect an Instagram Business or Creator account to answer your contacts here.')
            : __('Ask an administrator to connect this channel.')
        }}
      </p>
      <div v-if="status.is_admin" class="mt-4 flex justify-center gap-2">
        <Button
          v-if="channel === 'WhatsApp' && status.configured && status.mode === 'evolution'"
          variant="solid"
          :loading="connecting"
          :label="__('Connect WhatsApp')"
          @click="connectWa"
        />
        <Button
          :variant="channel === 'WhatsApp' && status.configured && status.mode === 'evolution' ? 'outline' : 'solid'"
          :label="channel === 'WhatsApp' ? __('WhatsApp settings') : __('Connect Instagram')"
          @click="openSettings"
        />
      </div>
    </div>
  </div>

  <div v-else class="grid h-[calc(100vh-3.5rem)] grid-cols-1 overflow-hidden md:grid-cols-[22rem_1fr]">
    <!-- lista -->
    <div class="flex min-h-0 flex-col border-r" :class="current ? 'hidden md:flex' : 'flex'">
      <div v-if="!list.length" class="p-4 text-sm text-ink-gray-5">
        {{ __('No conversations yet. They appear here when a contact writes to you.') }}
      </div>
      <div class="min-h-0 flex-1 overflow-y-auto">
        <div
          v-for="c in list"
          :key="c.name"
          class="flex cursor-pointer items-center gap-3 border-b px-3 py-2.5 hover:bg-surface-gray-2"
          :class="current?.name === c.name && 'bg-surface-gray-3'"
          @click="openConv(c.name)"
        >
          <div class="min-w-0 flex-1">
            <div class="flex items-center justify-between gap-2">
              <span class="truncate text-sm font-medium text-ink-gray-9">{{ c.contact_name || c.title }}</span>
              <span class="shrink-0 text-xs text-ink-gray-5">{{ when(c.last_at) }}</span>
            </div>
            <div class="flex items-center justify-between gap-2">
              <span class="truncate text-xs text-ink-gray-6">{{ c.last_message }}</span>
              <span v-if="c.unread" class="shrink-0 rounded-full bg-surface-gray-7 px-1.5 text-xs text-ink-white">{{ c.unread }}</span>
            </div>
            <div v-if="c.deal_name" class="truncate text-xs text-ink-gray-5">{{ c.deal_name }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- conversa -->
    <div v-if="current" class="flex min-h-0 flex-col">
      <div class="flex items-center gap-2 border-b px-3 py-2">
        <Button variant="ghost" class="md:hidden" @click="current = null"><LucideArrowLeft class="h-4 w-4" /></Button>
        <div class="min-w-0 flex-1">
          <div class="truncate text-sm font-semibold text-ink-gray-9">{{ current.title }}</div>
          <div class="truncate text-xs text-ink-gray-5">
            {{ current.contact ? __('Contact') + ': ' + current.contact : __('No contact linked') }}
            <span v-if="current.deal"> · {{ __('Project') }}: {{ current.deal }}</span>
          </div>
        </div>
        <Button v-if="!current.contact" :label="__('Create contact')" @click="makeContact" />
        <Button :label="__('Link')" @click="openLink" />
      </div>
      <div ref="box" class="min-h-0 flex-1 space-y-2 overflow-y-auto bg-surface-gray-1 p-4">
        <div v-for="m in messages" :key="m.name" class="flex" :class="m.direction === 'Out' ? 'justify-end' : 'justify-start'">
          <div
            class="max-w-[75%] whitespace-pre-wrap rounded-lg px-3 py-1.5 text-sm"
            :class="m.direction === 'Out' ? 'bg-surface-gray-4 text-ink-gray-9' : 'bg-surface-white text-ink-gray-9 border'"
          >
            {{ m.text }}
            <div class="mt-0.5 text-right text-[10px] opacity-70">
              {{ when(m.sent_at) }}<span v-if="m.status === 'Failed'"> · {{ __('Failed to send') }}</span>
            </div>
          </div>
        </div>
      </div>
      <div class="flex gap-2 border-t p-2">
        <FormControl v-model="text" class="flex-1" type="text" :placeholder="__('Type a message')" @keyup.enter="send" />
        <Button variant="solid" :label="__('Send')" :loading="busy" @click="send" />
      </div>
    </div>
    <div v-else class="hidden items-center justify-center text-sm text-ink-gray-5 md:flex">
      {{ __('Select a conversation') }}
    </div>
  </div>

  <Dialog v-model:open="qrDialog" :size="'sm'">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pb-6 pt-5 text-center sm:px-6">
        <h3 class="mb-3 text-2xl-semibold text-ink-gray-9">{{ __('Read the QR Code') }}</h3>
        <img v-if="qr" :src="qr.startsWith('data:') ? qr : 'data:image/png;base64,' + qr" class="mx-auto h-56 w-56 rounded border bg-white p-2" />
        <p class="mt-2 text-xs text-ink-gray-6">{{ __('On your phone: WhatsApp > Linked devices > Link a device, then read this code.') }}</p>
      </div>
    </template>
  </Dialog>

  <Dialog v-model:open="linkDialog" :size="'md'">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pb-4 pt-5 sm:px-6">
        <h3 class="mb-4 text-2xl-semibold text-ink-gray-9">{{ __('Link conversation') }}</h3>
        <div class="flex flex-col gap-3">
          <FormControl v-model="pickContact" type="select" :options="contactOptions" :label="__('Contact')" />
          <FormControl v-model="pickDeal" type="select" :options="dealOptions" :label="__('Project')" />
        </div>
      </div>
      <div class="flex flex-row-reverse gap-2 px-4 pb-6 pt-3 sm:px-6">
        <Button variant="solid" :label="__('Save')" @click="saveLink" />
        <Button :label="__('Cancel')" @click="linkDialog = false" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { Breadcrumbs, Button, Dialog, FormControl, call, toast } from 'frappe-ui'
import { globalStore } from '@/stores/global'
import { showSettings, activeSettingsPage } from '@/composables/settings'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps({ channel: { type: String, required: true } })
const route = useRoute()
const { $socket } = globalStore()

const list = ref([])
const current = ref(null)
const messages = ref([])
const text = ref('')
const busy = ref(false)
const box = ref(null)
const linkDialog = ref(false)
const pickContact = ref('')
const pickDeal = ref('')
const deals = ref([])
const contacts = ref([])
const status = ref(null)
const syncing = ref(false)
async function syncNow(manual = false) {
  if (props.channel !== 'WhatsApp' || syncing.value) return
  syncing.value = true
  try {
    const r = await call('crm.panda.chat.wa_sync')
    if (manual) toast.success(r.new ? `${r.new} ${__('new messages')}` : __('No new messages'))
    await loadList()
  } catch (e) {
    if (manual) toast.error(msg(e))
  } finally {
    syncing.value = false
  }
}
const qrDialog = ref(false)
const qr = ref('')
const connecting = ref(false)
const notConnected = computed(() => status.value && !status.value.connected && !list.value.length)
async function loadStatus() {
  status.value = await call('crm.panda.chat.channel_status', { channel: props.channel })
}
function openSettings() {
  showSettings.value = true
  activeSettingsPage.value = __('Connections')
}
async function connectWa() {
  connecting.value = true
  try {
    const r = await call('crm.panda.chat.wa_connect')
    if (r.qr) {
      qr.value = r.qr
      qrDialog.value = true
      pollStatus()
    } else await loadStatus()
  } catch (e) {
    toast.error(msg(e))
  } finally {
    connecting.value = false
  }
}
let poll
function pollStatus() {
  clearInterval(poll)
  let n = 0
  poll = setInterval(async () => {
    n++
    try {
      const r = await call('crm.panda.chat.wa_state')
      if (r.status === 'conectado' || n > 40) {
        clearInterval(poll)
        qrDialog.value = false
        await loadStatus()
        if (r.status === 'conectado') toast.success(__('WhatsApp connected'))
      }
    } catch {
      clearInterval(poll)
    }
  }, 3000)
}
const msg = (e) => e?.messages?.[0] || e?.message || String(e)
const when = (d) => (d ? new Date(d.replace(' ', 'T')).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '')

const dealOptions = computed(() => [{ label: '—', value: '' }, ...deals.value.map((d) => ({ label: d.project_name || d.name, value: d.name }))])
const contactOptions = computed(() => [{ label: '—', value: '' }, ...contacts.value.map((c) => ({ label: c.full_name || c.name, value: c.name }))])

async function loadList() {
  list.value = await call('crm.panda.chat.get_conversations', { channel: props.channel })
}
async function openConv(name) {
  const r = await call('crm.panda.chat.get_thread', { conversation: name })
  current.value = r.conversation
  messages.value = r.messages
  await nextTick()
  if (box.value) box.value.scrollTop = box.value.scrollHeight
  loadList()
}
async function send() {
  if (!text.value.trim()) return
  busy.value = true
  try {
    await call('crm.panda.chat.send_message', { conversation: current.value.name, text: text.value })
    text.value = ''
  } catch (e) {
    toast.error(msg(e))
  } finally {
    busy.value = false
    openConv(current.value.name)
  }
}
async function makeContact() {
  try {
    await call('crm.panda.chat.create_contact_from', { conversation: current.value.name })
    openConv(current.value.name)
  } catch (e) {
    toast.error(msg(e))
  }
}
async function openLink() {
  deals.value = await call('frappe.client.get_list', { doctype: 'CRM Deal', fields: ['name', 'project_name'], limit_page_length: 200 })
  contacts.value = await call('frappe.client.get_list', { doctype: 'Contact', fields: ['name', 'full_name'], limit_page_length: 300 })
  pickContact.value = current.value.contact || ''
  pickDeal.value = current.value.deal || ''
  linkDialog.value = true
}
async function saveLink() {
  try {
    await call('crm.panda.chat.link_conversation', { conversation: current.value.name, contact: pickContact.value || null, deal: pickDeal.value || null })
    linkDialog.value = false
    openConv(current.value.name)
  } catch (e) {
    toast.error(msg(e))
  }
}

function onNew(d) {
  loadList()
  if (current.value && d?.conversation === current.value.name) openConv(current.value.name)
  else toast.info(__('New message'))
}
onMounted(async () => {
  loadList()
  await loadStatus()
  if (route.query.conversa) openConv(String(route.query.conversa))
  syncNow()
  $socket.on('panda_chat', onNew)
})
onUnmounted(() => {
  $socket.off('panda_chat', onNew)
  clearInterval(poll)
})
watch(() => props.channel, () => {
  current.value = null
  loadList()
  loadStatus()
})
</script>
