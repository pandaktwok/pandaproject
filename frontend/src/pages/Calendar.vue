<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __('Calendar'), route: { name: 'Calendar' } }]" />
    </template>
    <template #right-header>
      <Button v-if="state?.calendars?.some((c) => c.authorized)" variant="ghost" :loading="syncing" :label="__('Sync now')" @click="syncNow">
        <template #prefix><LucideRefreshCw class="h-4 w-4" /></template>
      </Button>
      <Button variant="solid" :label="__('New event')" @click="openNew(selected)">
        <template #prefix><LucidePlus class="h-4 w-4" /></template>
      </Button>
    </template>
  </LayoutHeader>

  <div class="flex h-full flex-col gap-3 overflow-y-auto p-4 sm:p-6">
    <!-- Conexão com o Google -->
    <div v-if="state && !state.calendars.length" class="flex flex-wrap items-center gap-3 rounded-lg border bg-surface-gray-1 p-3 text-sm text-ink-gray-7">
      <LucideCalendarSync class="h-4 w-4" />
      <span class="min-w-0 flex-1">
        {{ state.google_enabled ? __('Connect your Google Calendar to see and create events here.') : __('Google is not configured yet. Ask an administrator to paste the Google key in Connections.') }}
      </span>
      <Button v-if="state.google_enabled" :label="__('Connect Google Calendar')" :loading="connecting" @click="connect" />
    </div>
    <div v-else-if="pending.length" class="flex flex-wrap items-center gap-3 rounded-lg border border-outline-amber-2 bg-surface-amber-1 p-3 text-sm">
      <span class="min-w-0 flex-1">{{ __('A calendar connection is not authorized yet.') }}</span>
      <Button :label="__('Authorize')" @click="authorize(pending[0].name)" />
    </div>

    <!-- Navegação do mês -->
    <div class="flex items-center gap-2">
      <Button variant="ghost" icon="lucide-chevron-left" @click="go(-1)" />
      <div class="min-w-40 text-center text-lg-semibold text-ink-gray-9">{{ title }}</div>
      <Button variant="ghost" icon="lucide-chevron-right" @click="go(1)" />
      <Button variant="subtle" :label="__('Today')" @click="today" />
      <div class="ml-auto hidden flex-wrap items-center gap-3 text-xs text-ink-gray-6 md:flex">
        <span class="flex items-center gap-1"><i class="h-2 w-2 rounded-full bg-blue-500" />{{ __('Events') }}</span>
        <span class="flex items-center gap-1"><i class="h-2 w-2 rounded-full bg-purple-500" />{{ __('Tasks') }}</span>
        <span class="flex items-center gap-1"><i class="h-2 w-2 rounded-full bg-amber-500" />{{ __('Payments') }}</span>
        <span class="flex items-center gap-1"><i class="h-2 w-2 rounded-full bg-red-500" />{{ __('Project end') }}</span>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_20rem]">
      <!-- Grade do mês -->
      <div class="overflow-hidden rounded-lg border">
        <div class="grid grid-cols-7 bg-surface-gray-2 text-center text-xs text-ink-gray-6">
          <div v-for="w in weekdays" :key="w" class="py-2">{{ w }}</div>
        </div>
        <div class="grid grid-cols-7">
          <div
            v-for="c in cells"
            :key="c.key"
            class="min-h-[5.5rem] cursor-pointer border-l border-t p-1 text-xs"
            :class="[
              c.other ? 'opacity-50' : '',
              dayClass(c.key),
              selected === c.key ? 'ring-2 ring-inset ring-outline-gray-4' : '',
            ]"
            @click="selected = c.key"
          >
            <div class="mb-0.5 flex items-center justify-between">
              <span :class="c.key === todayKey ? 'rounded-full bg-surface-gray-7 px-1.5 text-ink-white' : 'text-ink-gray-7'">{{ c.day }}</span>
              <LucideTriangleAlert v-if="data?.days?.[c.key]" class="h-3.5 w-3.5" :class="data.days[c.key] === 'red' ? 'text-ink-red-4' : 'text-ink-amber-3'" />
            </div>
            <div v-for="it in itemsOf(c.key).slice(0, 3)" :key="it.kind + it.id" class="flex items-center gap-1 truncate">
              <i class="h-1.5 w-1.5 shrink-0 rounded-full" :class="dot(it)" />
              <span class="truncate text-ink-gray-8">{{ it.all_day ? '' : hora(it.start) + ' ' }}{{ it.title }}</span>
              <LucideTriangleAlert v-if="it.conflict" class="h-3 w-3 shrink-0" :class="it.conflict === 'time' ? 'text-ink-red-4' : 'text-ink-amber-3'" />
            </div>
            <div v-if="itemsOf(c.key).length > 3" class="text-ink-gray-5">+{{ itemsOf(c.key).length - 3 }}</div>
          </div>
        </div>
      </div>

      <!-- Dia selecionado -->
      <div class="rounded-lg border p-3">
        <div class="mb-2 text-base-semibold text-ink-gray-9">{{ dia(selected) }}</div>
        <div v-if="data?.days?.[selected]" class="mb-2 rounded-md p-2 text-xs" :class="data.days[selected] === 'red' ? 'bg-surface-red-2 text-ink-red-4' : 'bg-surface-amber-1 text-ink-amber-3'">
          {{ data.days[selected] === 'red' ? __('Conflict: different events at the same time.') : __('Attention: same event name with different times.') }}
        </div>
        <div v-if="!itemsOf(selected).length" class="text-sm text-ink-gray-4">{{ __('Nothing scheduled') }}</div>
        <div v-for="it in itemsOf(selected)" :key="it.kind + it.id" class="flex items-start gap-2 border-b py-2 last:border-0">
          <i class="mt-1.5 h-2 w-2 shrink-0 rounded-full" :class="dot(it)" />
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1 text-sm text-ink-gray-9">
              <span class="truncate">{{ it.title }}</span>
              <LucideTriangleAlert v-if="it.conflict" class="h-3.5 w-3.5 shrink-0" :class="it.conflict === 'time' ? 'text-ink-red-4' : 'text-ink-amber-3'" />
            </div>
            <div class="text-xs text-ink-gray-5">
              {{ it.all_day ? __('All day') : hora(it.start) + (it.end ? ' – ' + hora(it.end) : '') }} · {{ it.origins.join(', ') }}
            </div>
            <router-link v-if="it.deal" :to="{ name: 'Deal', params: { dealId: it.deal } }" class="text-xs text-ink-gray-7 underline">{{ __('Open project') }}</router-link>
          </div>
          <Button v-if="it.kind === 'event'" size="sm" variant="ghost" icon="lucide-trash-2" @click="removeEvent(it)" />
        </div>
      </div>
    </div>
  </div>

  <!-- Novo compromisso -->
  <Dialog v-model:open="newDialog" :size="'lg'">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pb-4 pt-5 sm:px-6">
        <h3 class="mb-4 text-2xl-semibold text-ink-gray-9">{{ __('New event') }}</h3>
        <div class="flex flex-col gap-3">
          <FormControl v-model="form.title" :label="__('Title')" type="text" />
          <FormControl v-model="form.all_day" type="checkbox" :label="__('All day')" />
          <div class="grid grid-cols-2 gap-3">
            <div>
              <div class="mb-1.5 text-xs text-ink-gray-5">{{ __('Date') }}</div>
              <DatePicker :value="form.date" :format="dateFormat" @change="(v) => (form.date = v)" />
            </div>
            <div v-if="!form.all_day" class="grid grid-cols-2 gap-2">
              <FormControl v-model="form.start" :label="__('Start')" type="time" />
              <FormControl v-model="form.end" :label="__('End')" type="time" />
            </div>
          </div>
          <FormControl v-model="form.calendar" :label="__('Calendar')" type="select" :options="calendarOptions" />
          <FormControl v-if="form.calendar" v-model="form.meet" type="checkbox" :label="__('Add Google Meet link')" />
          <FormControl v-model="form.description" :label="__('Description')" type="textarea" :rows="2" />
        </div>
        <ErrorMessage v-if="error" class="mt-3" :message="error" />
      </div>
      <div class="flex flex-row-reverse gap-2 px-4 pb-6 pt-3 sm:px-6">
        <Button variant="solid" :label="__('Save')" :loading="busy" @click="saveEvent" />
        <Button :label="__('Cancel')" @click="newDialog = false" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { getFormat } from '@/utils'
import { Breadcrumbs, Button, call, DatePicker, Dialog, ErrorMessage, FormControl, toast } from 'frappe-ui'
import { computed, onMounted, reactive, ref, watch } from 'vue'

const pad = (n) => String(n).padStart(2, '0')
const key = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const dateFormat = getFormat('', '', true, false, false)
const weekdays = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
const meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

const now = new Date()
const todayKey = key(now)
const cursor = ref(new Date(now.getFullYear(), now.getMonth(), 1))
const selected = ref(todayKey)
const data = ref(null)
const state = ref(null)
const busy = ref(false)
const syncing = ref(false)
const connecting = ref(false)
const error = ref('')

const title = computed(() => `${meses[cursor.value.getMonth()]} ${cursor.value.getFullYear()}`)
const cells = computed(() => {
  const first = new Date(cursor.value)
  const start = new Date(first)
  start.setDate(1 - first.getDay())
  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(start)
    d.setDate(start.getDate() + i)
    return { key: key(d), day: d.getDate(), other: d.getMonth() !== first.getMonth() }
  })
})
const pending = computed(() => (state.value?.calendars || []).filter((c) => !c.authorized))
const byDay = computed(() => {
  const m = {}
  for (const it of data.value?.items || []) (m[it.start.slice(0, 10)] ||= []).push(it)
  return m
})
const itemsOf = (k) => byDay.value[k] || []
const hora = (s) => (s || '').slice(11, 16)
const dia = (k) => k.split('-').reverse().join('/')
const dot = (it) => ({ event: 'bg-blue-500', task: 'bg-purple-500', payment: 'bg-amber-500', end: 'bg-red-500' })[it.kind]
const dayClass = (k) => (data.value?.days?.[k] === 'red' ? 'bg-surface-red-1' : data.value?.days?.[k] === 'yellow' ? 'bg-surface-amber-1' : '')

async function load() {
  const c = cells.value
  data.value = await call('crm.panda.calendario.get_events', { start: c[0].key, end: c[41].key })
}
async function loadState() {
  state.value = await call('crm.panda.calendario.get_state')
}
const go = (n) => (cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + n, 1))
const today = () => {
  cursor.value = new Date(now.getFullYear(), now.getMonth(), 1)
  selected.value = todayKey
}
watch(cursor, load)

const msg = (e) => e?.messages?.[0] || e?.message || String(e)
async function connect() {
  connecting.value = true
  try {
    const r = await call('crm.panda.calendario.connect', { calendar_name: 'Google' })
    if (r.url) window.location.href = r.url
  } catch (e) {
    toast.error(msg(e))
  } finally {
    connecting.value = false
  }
}
async function authorize(name) {
  try {
    const r = await call('crm.panda.calendario.reauthorize', { name })
    if (r.url) window.location.href = r.url
  } catch (e) {
    toast.error(msg(e))
  }
}
async function syncNow() {
  syncing.value = true
  try {
    await call('crm.panda.calendario.sync_now')
    await load()
    toast.success(__('Synced'))
  } catch (e) {
    toast.error(msg(e))
  } finally {
    syncing.value = false
  }
}

// ---- novo compromisso
const newDialog = ref(false)
const form = reactive({ title: '', date: '', all_day: false, start: '09:00', end: '10:00', calendar: '', meet: false, description: '' })
const calendarOptions = computed(() => [
  { label: __('Only in the program'), value: '' },
  ...(state.value?.calendars || []).filter((c) => c.authorized).map((c) => ({ label: `Google — ${c.calendar_name}`, value: c.name })),
])
function openNew(k) {
  Object.assign(form, { title: '', date: k || todayKey, all_day: false, start: '09:00', end: '10:00', calendar: '', meet: false, description: '' })
  error.value = ''
  newDialog.value = true
}
async function saveEvent() {
  busy.value = true
  error.value = ''
  try {
    const ini = form.all_day ? `${form.date} 00:00:00` : `${form.date} ${form.start}:00`
    const fim = form.all_day ? `${form.date} 23:59:59` : `${form.date} ${form.end}:00`
    await call('crm.panda.calendario.create_event', {
      title: form.title,
      starts_on: ini,
      ends_on: fim,
      all_day: form.all_day ? 1 : 0,
      calendar: form.calendar || null,
      meet: form.meet ? 1 : 0,
      description: form.description,
    })
    newDialog.value = false
    await load()
  } catch (e) {
    error.value = msg(e)
  } finally {
    busy.value = false
  }
}
async function removeEvent(it) {
  try {
    await call('crm.panda.calendario.delete_event', { name: it.id })
    await load()
  } catch (e) {
    toast.error(msg(e))
  }
}

onMounted(async () => {
  await Promise.all([load(), loadState()])
})
</script>
