<template>
  <!-- WhatsApp -->
  <section class="rounded-lg border p-4 text-ink-gray-8">
    <h3 class="text-lg-semibold text-ink-gray-9">WhatsApp</h3>
    <p class="mt-1 text-sm text-ink-gray-6">
      {{ __('One number per connection. Only replies to conversations that contacts start; no mass messages.') }}
    </p>
    <div class="mt-3 max-w-sm">
      <FormControl v-model="wa.mode" type="select" :label="__('How to connect')" :options="modeOptions" />
    </div>

    <!-- Evolution (QR Code) -->
    <template v-if="wa.mode === 'Evolution'">
      <div class="mt-3 grid gap-3 md:grid-cols-3">
        <FormControl v-model="wa.url" type="text" :label="__('Evolution API address')" placeholder="https://evolution.seudominio.com" />
        <FormControl v-model="wa.key" type="password" :label="__('API key')" :placeholder="cfg?.wa?.key_set ? '••••••••' : ''" />
        <FormControl v-model="wa.instance" type="text" :label="__('Instance name')" />
      </div>
      <div class="mt-3">
        <FormControl v-model="wa.public_url" type="text" :label="__('Public address of this program (for webhooks)')" placeholder="https://painel.seudominio.com" />
        <p class="mt-1 text-xs text-ink-gray-5">
          {{ __('The Evolution API must be able to open this address to deliver new messages. localhost does not work from another server: use your domain or a tunnel (Cloudflare Tunnel, ngrok). Without it, messages are fetched every few minutes instead.') }}
        </p>
      </div>
      <div v-if="diag" class="mt-3 rounded-md border p-3 text-xs text-ink-gray-8">
        <div>{{ __('Expected webhook') }}: <code class="text-ink-gray-9">{{ diag.expected }}</code></div>
        <div>{{ __('Registered at Evolution') }}: <code class="text-ink-gray-9">{{ diag.at_evolution || '—' }}</code></div>
        <div v-if="diag.local" class="mt-1 font-medium text-ink-red-4">{{ __('This address is local: the Evolution API cannot reach it.') }}</div>
      </div>
      <div class="mt-3 flex flex-wrap items-center gap-2">
        <Button :label="__('Diagnose')" @click="diagnose" />
        <Button :label="__('Re-register webhook')" @click="resetHook" />
        <Button :label="__('Save')" :loading="busy" @click="saveWa" />
        <Button variant="solid" :label="__('Connect WhatsApp')" :loading="busy" @click="connectWa" />
        <Button :label="__('Check status')" @click="checkWa" />
        <Button theme="red" :label="__('Disconnect')" @click="disconnectWa" />
        <span class="text-sm text-ink-gray-7">{{ __('Status') }}: <b>{{ waStatus }}</b></span>
      </div>
      <div class="mt-3 max-w-sm">
        <FormControl v-model="wa.pair_number" type="text" :label="__('Number for pairing code (optional, with country code)')" placeholder="5548999999999" />
        <p class="mt-1 text-xs text-ink-gray-5">{{ __('If you cannot read a QR Code, fill this and click Connect: a code appears to type in WhatsApp > Linked devices > Link with phone number.') }}</p>
      </div>
      <div v-if="pairing" class="mt-3 rounded-md border p-3 text-center">
        <div class="text-xs text-ink-gray-5">{{ __('Pairing code') }}</div>
        <div class="text-2xl-semibold tracking-widest text-ink-gray-9">{{ pairing }}</div>
      </div>
      <div v-if="qr" class="mt-3">
        <img :src="qr.startsWith('data:') ? qr : 'data:image/png;base64,' + qr" class="h-56 w-56 rounded border bg-white p-2" />
        <p class="mt-1 text-xs text-ink-gray-6">{{ __('On your phone: WhatsApp > Linked devices > Link a device, then read this code.') }}</p>
      </div>
    </template>

    <!-- API oficial da Meta (sem QR Code) -->
    <template v-else>
      <p class="mt-3 rounded-md bg-surface-gray-2 p-3 text-xs text-ink-gray-7">
        {{ __('No QR Code needed: the number is registered at Meta (code by SMS or phone call) and this program talks to the official API. Good for virtual numbers (BRDID etc.). Free text can be sent only within 24h after the contact writes; the number stops working in the WhatsApp phone app.') }}
      </p>
      <div class="mt-3 grid gap-3 md:grid-cols-2">
        <FormControl v-model="wa.cloud_phone" type="text" :label="__('Phone number ID (from Meta > WhatsApp > API setup)')" />
        <FormControl v-model="wa.cloud_token" type="password" :label="__('Permanent access token')" :placeholder="cfg?.wa?.cloud_token_set ? '••••••••' : ''" />
        <FormControl v-model="ig.app_secret" type="password" label="App Secret" :placeholder="cfg?.ig?.secret_set ? '••••••••' : ''" />
      </div>
      <div class="mt-3 space-y-1 text-xs text-ink-gray-6">
        <div>{{ __('Webhook address') }}: <code class="text-ink-gray-9">{{ cloud.webhook_url }}</code> <a class="underline" @click="copy(cloud.webhook_url)">{{ __('Copy') }}</a></div>
        <div>{{ __('Verify token') }}: <code class="text-ink-gray-9">{{ cloud.verify_token }}</code> <a class="underline" @click="copy(cloud.verify_token)">{{ __('Copy') }}</a></div>
        <div>{{ __('In Meta > WhatsApp > Configuration > Webhook, paste both and subscribe to "messages".') }}</div>
      </div>
      <div class="mt-3 flex flex-wrap items-center gap-2">
        <Button :label="__('Save')" :loading="busy" @click="saveCloud" />
        <Button variant="solid" :label="__('Check connection')" :loading="busy" @click="connectCloud" />
        <Button theme="red" :label="__('Disconnect')" @click="disconnectWa" />
        <span class="text-sm text-ink-gray-7">
          {{ __('Status') }}: <b>{{ waStatus }}</b><span v-if="cfg?.wa?.cloud_display"> · {{ cfg.wa.cloud_display }}</span>
        </span>
      </div>
    </template>
    <FormControl
      class="mt-3"
      v-model="wa.notify"
      type="textarea"
      :rows="2"
      :label="__('Numbers that receive the end-of-project notice (one per line, with country code)')"
    />
  </section>

  <!-- Instagram -->
  <section class="rounded-lg border p-4 text-ink-gray-8">
    <h3 class="text-lg-semibold text-ink-gray-9">Instagram (Meta)</h3>
    <p class="mt-1 text-sm text-ink-gray-6">
      {{ __('Requires an Instagram Business or Creator account linked to a Facebook page.') }}
    </p>
    <div class="mt-3 grid gap-3 md:grid-cols-2">
      <FormControl v-model="ig.app_id" type="text" label="App ID" />
      <FormControl v-model="ig.app_secret" type="password" label="App Secret" :placeholder="cfg?.ig?.secret_set ? '••••••••' : ''" />
    </div>
    <div class="mt-3 space-y-1 text-xs text-ink-gray-6">
      <div>{{ __('OAuth redirect address') }}: <code class="text-ink-gray-9">{{ ig.status?.redirect_uri }}</code> <a class="underline" @click="copy(ig.status?.redirect_uri)">{{ __('Copy') }}</a></div>
      <div>{{ __('Webhook address') }}: <code class="text-ink-gray-9">{{ ig.status?.webhook_url }}</code> <a class="underline" @click="copy(ig.status?.webhook_url)">{{ __('Copy') }}</a></div>
      <div>{{ __('Verify token') }}: <a class="underline" @click="showVerify">{{ __('Show and copy') }}</a></div>
    </div>
    <div class="mt-3 flex flex-wrap items-center gap-2">
      <Button :label="__('Save')" :loading="busy" @click="saveIg" />
      <Button variant="solid" :label="__('Connect Instagram')" @click="connectIg" />
      <Button v-if="ig.status?.connected" theme="red" :label="__('Disconnect')" @click="disconnectIg" />
      <span class="text-sm text-ink-gray-7">
        {{ ig.status?.connected ? __('Connected') + ' @' + ig.status.username : __('Not connected') }}
      </span>
    </div>
  </section>
</template>

<script setup>
import { Button, FormControl, call, toast } from 'frappe-ui'
import { onMounted, reactive, ref } from 'vue'

const cfg = ref(null)
const busy = ref(false)
const qr = ref('')
const diag = ref(null)
const pairing = ref('')
const waStatus = ref(__('disconnected'))
const wa = reactive({ url: '', key: '', instance: 'panda', notify: '', mode: 'Evolution', public_url: '', pair_number: '', cloud_phone: '', cloud_token: '' })
const cloud = reactive({ webhook_url: '', verify_token: '' })
const modeOptions = [
  { label: __('Evolution API (QR Code)'), value: 'Evolution' },
  { label: __('Official Meta API (no QR Code)'), value: 'Cloud API' },
]
const ig = reactive({ app_id: '', app_secret: '', status: null })
const msg = (e) => e?.messages?.[0] || e?.message || String(e)
const copy = async (t) => {
  await navigator.clipboard.writeText(t || '')
  toast.success(__('Copied'))
}

async function run(fn, ok) {
  busy.value = true
  try {
    await fn()
    if (ok) toast.success(ok)
  } catch (e) {
    toast.error(msg(e))
  } finally {
    busy.value = false
  }
}
async function load() {
  cfg.value = await call('crm.panda.integracoes.get_config')
  const m = cfg.value.messaging || {}
  wa.url = m.wa?.url || ''
  wa.instance = m.wa?.instance || 'panda'
  wa.notify = m.wa?.notify || ''
  wa.mode = m.wa?.mode || 'Evolution'
  wa.public_url = m.wa?.public_url || ''
  wa.cloud_phone = m.wa?.cloud_phone_id || ''
  waStatus.value = m.wa?.status || 'desconectado'
  ig.app_id = m.ig?.app_id || ''
  cfg.value.wa = m.wa
  cfg.value.ig = m.ig
  ig.status = await call('crm.panda.chat.ig_status')
  Object.assign(cloud, await call('crm.panda.chat.wa_cloud_info'))
}
const saveWa = () =>
  run(async () => {
    await call('crm.panda.integracoes.save_messaging', { evo_url: wa.url, evo_key: wa.key, evo_instance: wa.instance, notify: wa.notify, mode: wa.mode, public_url: wa.public_url })
    wa.key = ''
    await load()
  }, __('Saved'))
const connectWa = () =>
  run(async () => {
    await call('crm.panda.integracoes.save_messaging', { evo_url: wa.url, evo_key: wa.key, evo_instance: wa.instance, notify: wa.notify, mode: wa.mode, public_url: wa.public_url })
    const r = await call('crm.panda.chat.wa_connect', { number: wa.pair_number })
    waStatus.value = r.status
    qr.value = r.qr || ''
    pairing.value = r.pairing || ''
  })
const checkWa = () =>
  run(async () => {
    const r = await call('crm.panda.chat.wa_state')
    waStatus.value = r.status
    if (r.status === 'conectado') qr.value = ''
  })
const disconnectWa = () =>
  run(async () => {
    await call('crm.panda.chat.wa_disconnect')
    waStatus.value = 'desconectado'
    qr.value = ''
  }, __('Disconnected'))
const saveCloud = () =>
  run(async () => {
    await call('crm.panda.integracoes.save_messaging', { evo_url: wa.url, evo_instance: wa.instance, notify: wa.notify, mode: 'Cloud API' })
    await call('crm.panda.chat.wa_cloud_save', { phone_id: wa.cloud_phone, token: wa.cloud_token })
    if (ig.app_secret) await call('crm.panda.chat.ig_save', { app_id: ig.app_id, app_secret: ig.app_secret })
    wa.cloud_token = ''
    ig.app_secret = ''
    await load()
  }, __('Saved'))
const connectCloud = () =>
  run(async () => {
    await saveCloudQuiet()
    const r = await call('crm.panda.chat.wa_cloud_connect')
    waStatus.value = r.status
    await load()
  })
async function saveCloudQuiet() {
  await call('crm.panda.integracoes.save_messaging', { evo_url: wa.url, evo_instance: wa.instance, notify: wa.notify, mode: 'Cloud API' })
  await call('crm.panda.chat.wa_cloud_save', { phone_id: wa.cloud_phone, token: wa.cloud_token })
  if (ig.app_secret) await call('crm.panda.chat.ig_save', { app_id: ig.app_id, app_secret: ig.app_secret })
  wa.cloud_token = ''
  ig.app_secret = ''
}
const diagnose = () =>
  run(async () => {
    diag.value = await call('crm.panda.chat.wa_diagnose')
  })
const resetHook = () =>
  run(async () => {
    await call('crm.panda.integracoes.save_messaging', { evo_url: wa.url, evo_key: wa.key, evo_instance: wa.instance, notify: wa.notify, mode: wa.mode, public_url: wa.public_url })
    await call('crm.panda.chat.wa_set_webhook')
    diag.value = await call('crm.panda.chat.wa_diagnose')
  }, __('Webhook registered'))
const saveIg = () =>
  run(async () => {
    await call('crm.panda.chat.ig_save', { app_id: ig.app_id, app_secret: ig.app_secret })
    ig.app_secret = ''
    await load()
  }, __('Saved'))
const showVerify = async () => copy(await call('crm.panda.chat.ig_verify_token'))
const connectIg = () =>
  run(async () => {
    await call('crm.panda.chat.ig_save', { app_id: ig.app_id, app_secret: ig.app_secret })
    window.location.href = await call('crm.panda.chat.ig_auth_url')
  })
const disconnectIg = () =>
  run(async () => {
    await call('crm.panda.chat.ig_disconnect')
    await load()
  }, __('Disconnected'))

onMounted(async () => {
  await load()
  const p = new URLSearchParams(window.location.search)
  if (p.get('instagram') === 'ok') toast.success(__('Instagram connected'))
  if (p.get('instagram') === 'erro') toast.error(p.get('motivo') || __('Instagram connection failed'))
})
</script>
