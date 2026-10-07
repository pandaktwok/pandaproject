<template>
  <div class="flex h-full flex-col gap-6 overflow-y-auto p-8 text-ink-gray-8">
    <div>
      <h2 class="text-xl-semibold text-ink-gray-9">{{ __('AI Agent') }}</h2>
      <p class="mt-1 text-sm text-ink-gray-6">
        {{ __('Help-only assistant. It never reads program data.') }}
      </p>
    </div>
    <section class="rounded-lg border p-4 text-ink-gray-8">
      <h3 class="text-lg-semibold text-ink-gray-9">{{ __('Connector') }}</h3>
      <div class="mt-3 grid gap-3 md:grid-cols-2">
        <FormControl v-model="f.provider" type="select" :options="provs" :label="__('Provider')" />
        <FormControl v-model="f.model" type="text" :label="__('Model')" placeholder="gpt-4o-mini / claude-sonnet-4-5 / gemini-2.0-flash" />
        <FormControl v-model="f.base_url" type="text" :label="__('Address (optional; required for OpenAI-compatible servers)')" />
        <FormControl v-model="f.api_key" type="password" :label="__('API key')" :placeholder="cfg?.key_set ? '••••••••' : ''" />
      </div>
      <div class="mt-3 flex gap-2">
        <Button variant="solid" :label="__('Save')" :loading="busy" @click="save" />
        <Button :label="__('Test connection')" :loading="busy" @click="test" />
      </div>
    </section>
    <section class="rounded-lg border p-4 text-ink-gray-8">
      <h3 class="text-lg-semibold text-ink-gray-9">{{ __('Permission levels') }}</h3>
      <ul class="mt-2 text-sm text-ink-gray-7">
        <li>✔ {{ __('Help (how do I do X): on') }}</li>
        <li>✖ {{ __('Read program data: off') }}</li>
        <li>✖ {{ __('Take actions: coming in V2.1') }}</li>
      </ul>
    </section>
    <section class="rounded-lg border p-4 text-ink-gray-8">
      <h3 class="text-lg-semibold text-ink-gray-9">MCP ({{ __('help tools only') }})</h3>
      <p class="mt-1 text-sm text-ink-gray-6">{{ __('Lets another AI tool consult the help documents. It never returns program data.') }}</p>
      <div class="mt-2 text-xs text-ink-gray-6">{{ __('Address') }}: <code class="text-ink-gray-9">{{ cfg?.mcp_url }}</code></div>
      <div class="mt-3 flex items-center gap-2">
        <Button :label="cfg?.mcp_token_set ? __('Generate new token') : __('Generate token')" @click="genToken" />
        <span v-if="token" class="text-xs"><code class="text-ink-gray-9">{{ token }}</code> <a class="underline" @click="copy(token)">{{ __('Copy') }}</a> ({{ __('shown once') }})</span>
      </div>
    </section>
  </div>
</template>

<script setup>
import { Button, FormControl, call, toast } from 'frappe-ui'
import { onMounted, reactive, ref } from 'vue'

const cfg = ref(null)
const busy = ref(false)
const token = ref('')
const f = reactive({ provider: 'OpenAI', model: '', base_url: '', api_key: '' })
const provs = [
  { label: 'OpenAI / compatível', value: 'OpenAI' },
  { label: 'Claude', value: 'Claude' },
  { label: 'Gemini', value: 'Gemini' },
]
const msg = (e) => e?.messages?.[0] || e?.message || String(e)
async function load() {
  cfg.value = await call('crm.panda.agente.get_config')
  f.provider = cfg.value.provider
  f.model = cfg.value.model
  f.base_url = cfg.value.base_url
}
async function save() {
  busy.value = true
  try {
    await call('crm.panda.agente.save_config', { provider: f.provider, base_url: f.base_url, model: f.model, api_key: f.api_key })
    f.api_key = ''
    toast.success(__('Saved'))
    await load()
  } catch (e) {
    toast.error(msg(e))
  } finally {
    busy.value = false
  }
}
async function test() {
  busy.value = true
  try {
    await save()
    await call('crm.panda.agente.test_connection')
    toast.success(__('Connection works'))
  } catch (e) {
    toast.error(msg(e))
  } finally {
    busy.value = false
  }
}
async function genToken() {
  token.value = await call('crm.panda.agente.generate_mcp_token')
  await load()
}
const copy = async (t) => {
  await navigator.clipboard.writeText(t)
  toast.success(__('Copied'))
}
onMounted(load)
</script>
