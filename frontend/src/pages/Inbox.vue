<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __('Email'), route: { name: 'Inbox' } }]" />
    </template>
    <template #right-header>
      <Button variant="ghost" :loading="syncing" icon="lucide-refresh-cw" :tooltip="__('Check for new email')" @click="syncNow(true)" />
      <Dropdown :options="gearOptions" placement="right">
        <Button variant="ghost" icon="lucide-settings" :tooltip="__('Email settings')" />
      </Dropdown>
      <Button variant="solid" :label="__('Compose')" :disabled="!accounts?.can_send?.length" @click="openCompose()">
        <template #prefix><LucidePenSquare class="h-4 w-4" /></template>
      </Button>
    </template>
  </LayoutHeader>

  <div v-if="accounts && !accounts.accounts.length" class="flex h-[calc(100vh-3.5rem)] items-center justify-center p-6">
    <div class="max-w-md text-center">
      <h2 class="text-xl-semibold text-ink-gray-9">{{ __('No email account connected') }}</h2>
      <p class="mt-2 text-sm text-ink-gray-6">{{ __('Add a Hostinger, Gmail or Outlook account to read and send email here.') }}</p>
      <Button class="mt-4" variant="solid" :label="__('Add new account')" @click="addAccount" />
    </div>
  </div>

  <div v-else class="grid h-[calc(100vh-3.5rem)] grid-cols-1 overflow-hidden md:grid-cols-[14rem_22rem_1fr]">
    <!-- Coluna 1: contas -->
    <div class="hidden overflow-y-auto border-r p-2 md:block">
      <div
        class="flex cursor-pointer items-center justify-between rounded-md px-2 py-1.5 text-sm text-ink-gray-7 hover:bg-surface-gray-2"
        :class="!account && 'bg-surface-gray-3 font-medium text-ink-gray-9'"
        @click="pick(null, 'Received')"
      >
        <span>{{ __('All inboxes') }}</span>
        <span v-if="accounts?.total_unread" class="text-xs text-ink-gray-6">{{ accounts.total_unread }}</span>
      </div>
      <div v-for="(a, i) in accounts?.accounts" :key="a.name" class="mt-1">
        <div class="flex cursor-pointer items-center gap-2 px-2 py-1.5 text-sm text-ink-gray-8" @click="open[a.name] = !open[a.name]">
          <i class="h-2.5 w-2.5 shrink-0 rounded-full" :style="{ background: color(i) }" />
          <span class="min-w-0 flex-1 truncate" :title="a.email_id">{{ a.email_account_name || a.email_id }}</span>
          <LucideChevronDown class="h-3.5 w-3.5 transition-transform" :class="open[a.name] ? '' : '-rotate-90'" />
        </div>
        <div v-if="open[a.name]" class="ml-4">
          <div
            class="flex cursor-pointer items-center justify-between rounded-md px-2 py-1 text-sm text-ink-gray-7 hover:bg-surface-gray-2"
            :class="account === a.name && folder === 'Received' && 'bg-surface-gray-3 font-medium text-ink-gray-9'"
            @click="pick(a.name, 'Received')"
          >
            <span>{{ __('Inbox') }}</span><span v-if="a.unread" class="text-xs text-ink-gray-6">{{ a.unread }}</span>
          </div>
          <div
            class="cursor-pointer rounded-md px-2 py-1 text-sm text-ink-gray-7 hover:bg-surface-gray-2"
            :class="account === a.name && folder === 'Sent' && 'bg-surface-gray-3 font-medium text-ink-gray-9'"
            @click="pick(a.name, 'Sent')"
          >
            {{ __('Sent') }}
          </div>
        </div>
      </div>
    </div>

    <!-- Coluna 2: lista -->
    <div class="flex min-h-0 flex-col border-r" :class="selected ? 'hidden md:flex' : 'flex'">
      <div class="border-b p-2">
        <FormControl v-model="search" type="text" :placeholder="__('Search')" @keyup.enter="loadMessages" />
      </div>
      <div class="min-h-0 flex-1 overflow-y-auto">
        <div v-if="!messages.length" class="p-4 text-sm text-ink-gray-4">{{ __('No messages') }}</div>
        <div
          v-for="m in messages"
          :key="m.name"
          class="cursor-pointer border-b px-3 py-2 hover:bg-surface-gray-2"
          :class="selected?.name === m.name && 'bg-surface-gray-3'"
          @click="read(m)"
        >
          <div class="flex items-center gap-2">
            <i class="h-2 w-2 shrink-0 rounded-full" :style="{ background: m.seen ? 'transparent' : '#3b82f6' }" />
            <span class="min-w-0 flex-1 truncate text-sm" :class="m.seen ? 'text-ink-gray-7' : 'font-semibold text-ink-gray-9'">
              {{ folder === 'Sent' ? m.to : m.from }}
            </span>
            <LucidePaperclip v-if="m.has_attachment" class="h-3.5 w-3.5 text-ink-gray-5" />
            <span class="shrink-0 text-xs text-ink-gray-5">{{ when(m.date) }}</span>
          </div>
          <div class="truncate text-sm text-ink-gray-8">{{ m.subject }}</div>
          <div class="flex items-center gap-1.5">
            <span class="min-w-0 flex-1 truncate text-xs text-ink-gray-5">{{ m.preview }}</span>
            <span class="shrink-0 rounded px-1.5 text-[10px] text-ink-white" :style="{ background: colorOf(m.account) }">{{ m.account_name }}</span>
          </div>
        </div>
        <div v-if="messages.length >= 50" class="p-2 text-center">
          <Button variant="ghost" :label="__('Load more')" @click="loadMore" />
        </div>
      </div>
    </div>

    <!-- Coluna 3: leitor -->
    <div class="min-h-0 overflow-y-auto" :class="selected ? 'block' : 'hidden md:block'">
      <div v-if="!detail" class="p-8 text-sm text-ink-gray-4">{{ __('Select a message') }}</div>
      <div v-else class="flex flex-col gap-3 p-4">
        <div class="flex flex-wrap items-center gap-2">
          <Button class="md:hidden" variant="ghost" icon="lucide-arrow-left" @click="selected = null; detail = null" />
          <Button :label="__('Reply')" @click="openCompose(detail)">
            <template #prefix><LucideReply class="h-4 w-4" /></template>
          </Button>
          <Button :label="__('Forward')" @click="openCompose(detail, true)">
            <template #prefix><LucideForward class="h-4 w-4" /></template>
          </Button>
          <Button :label="__('Create contact')" :loading="busy" @click="createContact">
            <template #prefix><LucideUserPlus class="h-4 w-4" /></template>
          </Button>
          <Button :label="__('Link to project')" @click="openLink">
            <template #prefix><LucideLink class="h-4 w-4" /></template>
          </Button>
          <Button :label="__('Create task')" @click="openTask">
            <template #prefix><LucideListChecks class="h-4 w-4" /></template>
          </Button>
          <Button variant="ghost" :label="__('Mark unread')" @click="markUnread" />
        </div>
        <div>
          <h2 class="text-xl-semibold text-ink-gray-9">{{ detail.subject }}</h2>
          <div class="mt-1 text-sm text-ink-gray-6">
            {{ detail.from }} &lt;{{ detail.sender }}&gt; → {{ detail.to }}<span v-if="detail.cc"> · cc {{ detail.cc }}</span>
          </div>
          <div class="text-xs text-ink-gray-5">{{ detail.date }}</div>
          <div v-if="detail.deal" class="mt-1 text-xs">
            {{ __('Project') }}:
            <router-link :to="{ name: 'Deal', params: { dealId: detail.deal } }" class="underline">{{ detail.deal_name || detail.deal }}</router-link>
          </div>
          <div v-if="detail.contacts?.length" class="text-xs text-ink-gray-6">{{ __('Contact') }}: {{ detail.contacts.join(', ') }}</div>
        </div>
        <div class="prose max-w-none rounded-lg border bg-surface-white p-4 text-sm text-ink-gray-9" v-html="detail.content" />
        <div v-if="detail.attachments?.length" class="flex flex-wrap gap-2">
          <a v-for="a in detail.attachments" :key="a.name" :href="a.file_url" download class="flex items-center gap-1 rounded border px-2 py-1 text-xs hover:bg-surface-gray-2">
            <LucidePaperclip class="h-3.5 w-3.5" />{{ a.file_name }}
          </a>
        </div>
      </div>
    </div>
  </div>

  <!-- Escrever / responder (De: define a conta) -->
  <Dialog v-model:open="composeDialog" :size="'3xl'">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pb-4 pt-5 sm:px-6">
        <h3 class="mb-4 text-2xl-semibold text-ink-gray-9">{{ __('Compose') }}</h3>
        <div class="flex flex-col gap-3">
          <FormControl v-model="compose.from_account" :label="__('From')" type="select" :options="fromOptions" />
          <FormControl v-model="compose.to" :label="__('To')" type="text" />
          <FormControl v-model="compose.cc" label="Cc" type="text" />
          <FormControl v-model="compose.subject" :label="__('Subject')" type="text" />
          <FormControl v-model="compose.content" :label="__('Message')" type="textarea" :rows="10" />
        </div>
        <ErrorMessage v-if="error" class="mt-3" :message="error" />
      </div>
      <div class="flex flex-row-reverse gap-2 px-4 pb-6 pt-3 sm:px-6">
        <Button variant="solid" :label="__('Send')" :loading="busy" @click="sendMail" />
        <Button :label="__('Cancel')" @click="composeDialog = false" />
      </div>
    </template>
  </Dialog>

  <!-- Vincular a projeto -->
  <Dialog v-model:open="linkDialog" :size="'md'">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pb-4 pt-5 sm:px-6">
        <h3 class="mb-4 text-2xl-semibold text-ink-gray-9">{{ __('Link to project') }}</h3>
        <FormControl v-model="pickDeal" type="select" :options="dealOptions" :label="__('Project')" />
      </div>
      <div class="flex flex-row-reverse gap-2 px-4 pb-6 pt-3 sm:px-6">
        <Button variant="solid" :label="__('Save')" :loading="busy" @click="saveLink" />
        <Button :label="__('Cancel')" @click="linkDialog = false" />
      </div>
    </template>
  </Dialog>

  <!-- Criar tarefa -->
  <Dialog v-model:open="taskDialog" :size="'md'">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pb-4 pt-5 sm:px-6">
        <h3 class="mb-4 text-2xl-semibold text-ink-gray-9">{{ __('Create task') }}</h3>
        <div class="flex flex-col gap-3">
          <FormControl v-model="pickDeal" type="select" :options="dealOptions" :label="__('Project')" />
          <div>
            <div class="mb-1.5 text-xs text-ink-gray-5">{{ __('Due Date') }}</div>
            <DatePicker :value="taskDue" :format="dateFormat" @change="(v) => (taskDue = v)" />
          </div>
        </div>
      </div>
      <div class="flex flex-row-reverse gap-2 px-4 pb-6 pt-3 sm:px-6">
        <Button variant="solid" :label="__('Create task')" :loading="busy" @click="saveTask" />
        <Button :label="__('Cancel')" @click="taskDialog = false" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { getFormat } from '@/utils'
import { Breadcrumbs, Button, Dropdown, call, DatePicker, Dialog, ErrorMessage, FormControl, toast } from 'frappe-ui'
import { showSettings, activeSettingsPage } from '@/composables/settings'
import { computed, onMounted, reactive, ref } from 'vue'

const palette = ['#2563eb', '#16a34a', '#d97706', '#9333ea', '#0891b2', '#db2777', '#4b5563']
const dateFormat = getFormat('', '', true, false, false)
const accounts = ref(null)
function addAccount() {
  showSettings.value = true
  activeSettingsPage.value = __('Accounts')
}
const gearOptions = [
  { label: __('Add new account'), icon: 'lucide-plus', onClick: addAccount },
  { label: __('Manage accounts'), icon: 'lucide-settings', onClick: addAccount },
]
const messages = ref([])
const account = ref(null)
const folder = ref('Received')
const search = ref('')
const selected = ref(null)
const detail = ref(null)
const open = reactive({})
const busy = ref(false)
const error = ref('')

const msg = (e) => e?.messages?.[0] || e?.message || String(e)
const idx = (name) => (accounts.value?.accounts || []).findIndex((a) => a.name === name)
const color = (i) => palette[i % palette.length]
const colorOf = (name) => color(Math.max(idx(name), 0))
const when = (d) => {
  const x = new Date(d.replace(' ', 'T'))
  const hoje = new Date()
  return x.toDateString() === hoje.toDateString()
    ? d.slice(11, 16)
    : `${String(x.getDate()).padStart(2, '0')}/${String(x.getMonth() + 1).padStart(2, '0')}`
}

async function loadAccounts() {
  accounts.value = await call('crm.panda.inbox.get_accounts')
  accounts.value.accounts.forEach((a) => (open[a.name] ??= true))
}
async function loadMessages() {
  messages.value = await call('crm.panda.inbox.get_messages', { account: account.value, folder: folder.value, search: search.value || null, start: 0 })
}
async function loadMore() {
  const more = await call('crm.panda.inbox.get_messages', { account: account.value, folder: folder.value, search: search.value || null, start: messages.value.length })
  messages.value = [...messages.value, ...more]
}
function pick(a, f) {
  account.value = a
  folder.value = f
  selected.value = null
  detail.value = null
  loadMessages()
}
async function read(m) {
  selected.value = m
  detail.value = await call('crm.panda.inbox.get_message', { name: m.name })
  if (!m.seen) {
    m.seen = true
    loadAccounts()
  }
}
async function markUnread() {
  await call('crm.panda.inbox.mark_unread', { name: detail.value.name })
  if (selected.value) selected.value.seen = false
  loadAccounts()
}

// ---- escrever
const composeDialog = ref(false)
const compose = reactive({ from_account: '', to: '', cc: '', subject: '', content: '', reply_to: null })
const fromOptions = computed(() => (accounts.value?.can_send || []).map((a) => ({ label: `${a.email_account_name || a.email_id} <${a.email_id}>`, value: a.name })))
function openCompose(orig, forward = false) {
  const padrao = orig?.account && accounts.value.can_send.some((a) => a.name === orig.account) ? orig.account : accounts.value.can_send[0]?.name || ''
  Object.assign(compose, {
    from_account: padrao,
    to: orig && !forward ? (orig.sent_or_received === 'Sent' ? orig.to : orig.sender) : '',
    cc: '',
    subject: orig ? `${forward ? 'Enc: ' : 'Re: '}${(orig.subject || '').replace(/^(re|enc|fwd):\s*/i, '')}` : '',
    content: forward && orig ? `\n\n---------- ${__('Forwarded message')} ----------\n${orig.from} <${orig.sender}>\n${orig.subject}\n\n${stripHtml(orig.content)}` : '',
    reply_to: orig && !forward ? orig.name : null,
  })
  error.value = ''
  composeDialog.value = true
}
const stripHtml = (h) => {
  const d = document.createElement('div')
  d.innerHTML = h || ''
  return d.innerText
}
async function sendMail() {
  busy.value = true
  error.value = ''
  try {
    const html = compose.content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\n/g, '<br>')
    await call('crm.panda.inbox.send', { ...compose, content: html, cc: compose.cc || null, reply_to: compose.reply_to })
    composeDialog.value = false
    toast.success(__('Email queued for sending'))
    if (folder.value === 'Sent') loadMessages()
  } catch (e) {
    error.value = msg(e)
  } finally {
    busy.value = false
  }
}

// ---- ações do leitor
const dealOptions = ref([{ label: __('No project'), value: '' }])
const pickDeal = ref('')
async function loadDeals() {
  const rows = await call('frappe.client.get_list', { doctype: 'CRM Deal', fields: ['name', 'project_name', 'organization'], limit_page_length: 200, order_by: 'modified desc' })
  dealOptions.value = [{ label: __('No project'), value: '' }, ...rows.map((r) => ({ label: r.project_name || r.organization || r.name, value: r.name }))]
}
async function createContact() {
  busy.value = true
  try {
    const c = await call('crm.panda.inbox.create_contact', { name: detail.value.name })
    toast.success(`${__('Contact')}: ${c}`)
    detail.value = await call('crm.panda.inbox.get_message', { name: detail.value.name })
  } catch (e) {
    toast.error(msg(e))
  } finally {
    busy.value = false
  }
}
const linkDialog = ref(false)
function openLink() {
  pickDeal.value = detail.value.deal || ''
  linkDialog.value = true
}
async function saveLink() {
  busy.value = true
  try {
    await call('crm.panda.inbox.link_deal', { name: detail.value.name, deal: pickDeal.value || null })
    linkDialog.value = false
    detail.value = await call('crm.panda.inbox.get_message', { name: detail.value.name })
  } catch (e) {
    toast.error(msg(e))
  } finally {
    busy.value = false
  }
}
const taskDialog = ref(false)
const taskDue = ref('')
function openTask() {
  pickDeal.value = detail.value.deal || ''
  taskDue.value = ''
  taskDialog.value = true
}
async function saveTask() {
  busy.value = true
  try {
    await call('crm.panda.inbox.create_task', { name: detail.value.name, deal: pickDeal.value || null, due_date: taskDue.value || null })
    taskDialog.value = false
    toast.success(__('Task created'))
  } catch (e) {
    toast.error(msg(e))
  } finally {
    busy.value = false
  }
}

const syncing = ref(false)
async function syncNow(manual = false) {
  if (syncing.value) return
  syncing.value = true
  try {
    const r = await call('crm.panda.inbox.sync', {})
    if (r.errors?.length) toast.error(r.errors.join('\n'))
    else if (manual) toast.success(__('Inbox updated'))
    await loadAccounts()
    await loadMessages()
  } catch (e) {
    toast.error(msg(e))
  } finally {
    syncing.value = false
  }
}
onMounted(async () => {
  await loadAccounts()
  await Promise.all([loadMessages(), loadDeals()])
  syncNow()
})
</script>
