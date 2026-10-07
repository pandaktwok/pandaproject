<template>
  <LayoutHeader>
    <template #left-header><Breadcrumbs :items="[{ label: __('AI Agent') }]" /></template>
    <template #right-header>
      <Button :label="__('Clear history')" @click="clear" />
    </template>
  </LayoutHeader>

  <div class="mx-auto flex h-[calc(100vh-3.5rem)] max-w-3xl flex-col">
    <div class="border-b bg-surface-gray-1 px-4 py-2 text-xs text-ink-gray-6">
      {{ __('Help assistant: it teaches how to use the program and cannot see your projects, contacts or amounts.') }}
    </div>
    <div v-if="ready === false" class="p-6 text-sm text-ink-gray-6">
      {{ __('The AI Agent is not set up yet. An administrator can do it in Settings > AI Agent.') }}
    </div>
    <div ref="box" class="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
      <div v-if="!items.length && ready" class="text-sm text-ink-gray-5">
        {{ __('Ask something like: how do I register a payment?') }}
      </div>
      <div v-for="(m, i) in items" :key="i" class="flex" :class="m.role === 'user' ? 'justify-end' : 'justify-start'">
        <div
          class="max-w-[85%] rounded-lg px-3 py-2 text-sm"
          :class="m.role === 'user' ? 'bg-surface-gray-4 text-ink-gray-9' : 'border bg-surface-white text-ink-gray-9'"
        >
          <template v-for="(p, j) in parse(m.content)" :key="j">
            <div v-if="p.t === 'text'" class="whitespace-pre-wrap">{{ p.v }}</div>
            <Button v-else-if="p.t === 'open'" class="mt-2 mr-2" variant="subtle" :label="p.label" @click="go(p.path)">
              <template #prefix><LucideExternalLink class="h-3.5 w-3.5" /></template>
            </Button>
            <div v-else class="mt-2 rounded-md border bg-surface-gray-1 p-2">
              <div class="whitespace-pre-wrap text-ink-gray-9">{{ p.v }}</div>
              <Button class="mt-2" size="sm" :label="__('Copy')" @click="copy(p.v)" />
            </div>
          </template>
        </div>
      </div>
      <div v-if="busy" class="text-sm text-ink-gray-5">{{ __('Thinking…') }}</div>
    </div>
    <div class="flex gap-2 border-t p-3">
      <FormControl v-model="q" class="flex-1" type="text" :placeholder="__('Type your question')" :disabled="!ready" @keyup.enter="ask" />
      <Button variant="solid" :label="__('Send')" :loading="busy" :disabled="!ready" @click="ask" />
    </div>
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { Breadcrumbs, Button, FormControl, call, toast } from 'frappe-ui'
import { showSettings, activeSettingsPage } from '@/composables/settings'
import { nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const items = ref([])
const q = ref('')
const busy = ref(false)
const ready = ref(null)
const box = ref(null)
const msg = (e) => e?.messages?.[0] || e?.message || String(e)

// Divide a resposta em texto, botoes "Abrir" ([[abrir:/caminho|Texto]]) e blocos copiaveis (<<<texto ... >>>)
function parse(s) {
  const out = []
  const re = /\[\[abrir:([^|\]]+)\|([^\]]+)\]\]|<<<([\s\S]*?)>>>/g
  let last = 0
  let m
  while ((m = re.exec(s || ''))) {
    if (m.index > last) out.push({ t: 'text', v: s.slice(last, m.index).trim() })
    if (m[3] !== undefined) out.push({ t: 'copy', v: m[3].trim() })
    else out.push({ t: 'open', path: m[1].trim(), label: m[2].trim() })
    last = re.lastIndex
  }
  if (last < (s || '').length) out.push({ t: 'text', v: s.slice(last).trim() })
  return out.filter((p) => p.t !== 'text' || p.v)
}
function go(path) {
  if (path.startsWith('settings:')) {
    showSettings.value = true
    activeSettingsPage.value = __(path.slice(9))
    return
  }
  router.push(path.replace(/^\/crm/, '') || '/')
}
const copy = async (t) => {
  await navigator.clipboard.writeText(t)
  toast.success(__('Copied'))
}
async function scroll() {
  await nextTick()
  if (box.value) box.value.scrollTop = box.value.scrollHeight
}
async function ask() {
  const text = q.value.trim()
  if (!text) return
  q.value = ''
  items.value.push({ role: 'user', content: text })
  busy.value = true
  scroll()
  try {
    const r = await call('crm.panda.agente.ask', { question: text })
    items.value.push({ role: 'assistant', content: r })
  } catch (e) {
    toast.error(msg(e))
  } finally {
    busy.value = false
    scroll()
  }
}
async function clear() {
  await call('crm.panda.agente.clear_history')
  items.value = []
}
onMounted(async () => {
  ready.value = await call('crm.panda.agente.available')
  items.value = await call('crm.panda.agente.history')
  scroll()
})
</script>
