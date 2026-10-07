<template>
  <div class="flex h-full flex-col gap-6 overflow-y-auto p-8 text-ink-gray-8">
    <div>
      <h2 class="text-xl-semibold text-ink-gray-9">{{ __('Connections') }}</h2>
      <p class="mt-1 text-sm text-ink-gray-6">
        {{ __('Paste your keys here. Secrets are stored encrypted and are never shown again.') }}
      </p>
    </div>

    <!-- Site / Newsletter -->
    <section class="rounded-lg border p-4 text-ink-gray-8">
      <h3 class="text-lg-semibold text-ink-gray-9">{{ __('Website (newsletter)') }}</h3>
      <p class="mb-3 text-sm text-ink-gray-6">
        {{ __('Sign-ups from your website create a Contact. The site sends this token with each sign-up.') }}
      </p>
      <div class="flex flex-col gap-3">
        <FormControl v-model="siteOrigin" :label="__('Website address')" type="text" placeholder="https://www.seusite.org" />
        <div>
          <div class="mb-1.5 text-xs text-ink-gray-5">{{ __('Endpoint') }}</div>
          <div class="flex items-center gap-2">
            <code class="text-ink-gray-9 min-w-0 flex-1 truncate rounded bg-surface-gray-2 px-2 py-1.5 text-sm">{{ cfg?.site?.endpoint }}</code>
            <Button size="sm" :label="__('Copy')" @click="copy(cfg.site.endpoint)" />
          </div>
        </div>
        <div>
          <div class="mb-1.5 text-xs text-ink-gray-5">{{ __('Token') }}</div>
          <div class="flex items-center gap-2">
            <code class="text-ink-gray-9 min-w-0 flex-1 truncate rounded bg-surface-gray-2 px-2 py-1.5 text-sm">
              {{ newToken || (cfg?.site?.configured ? '••••••••••••••••' : __('Not configured')) }}
            </code>
            <Button v-if="newToken" size="sm" :label="__('Copy')" @click="copy(newToken)" />
            <Button size="sm" :label="cfg?.site?.configured ? __('Generate new token') : __('Generate token')" :loading="busy" @click="genToken" />
          </div>
          <div v-if="newToken" class="mt-1 text-xs text-ink-red-4">{{ __('Copy it now. It will not be shown again.') }}</div>
        </div>
        <div><Button variant="solid" :label="__('Save')" :loading="busy" @click="saveSite" /></div>
      </div>
    </section>

    <!-- Google -->
    <section class="rounded-lg border p-4 text-ink-gray-8">
      <h3 class="text-lg-semibold text-ink-gray-9">Google ({{ __('Calendar') }} / Drive)</h3>
      <p class="mb-3 text-sm text-ink-gray-6">
        {{ __('One OAuth key serves Calendar and Drive. Create it in Google Cloud Console and paste it below.') }}
      </p>
      <div class="flex flex-col gap-3">
        <FormControl v-model="google.client_id" label="Client ID" type="text" />
        <FormControl
          v-model="google.client_secret"
          label="Client Secret"
          type="password"
          :placeholder="cfg?.google?.secret_set ? '••••••••' : ''"
        />
        <div>
          <div class="mb-1.5 text-xs text-ink-gray-5">{{ __('Authorized redirect URIs (paste all in Google)') }}</div>
          <div v-for="u in cfg?.google?.redirect_uris" :key="u" class="mb-1 flex items-center gap-2">
            <code class="text-ink-gray-9 min-w-0 flex-1 truncate rounded bg-surface-gray-2 px-2 py-1.5 text-sm">{{ u }}</code>
            <Button size="sm" :label="__('Copy')" @click="copy(u)" />
          </div>
        </div>
        <div><Button variant="solid" :label="__('Save')" :loading="busy" @click="saveGoogle" /></div>
      </div>
    </section>

    <!-- Google Drive -->
    <section class="rounded-lg border p-4 text-ink-gray-8">
      <h3 class="text-lg-semibold text-ink-gray-9">Google Drive</h3>
      <p class="mb-3 text-sm text-ink-gray-6">
        {{ __('Payment PDFs are mirrored to Drive: Panda Project / Project / Financeiro / Parcela N - MM-YYYY. Only files created by the program are visible to it.') }}
      </p>
      <div class="flex flex-col gap-3">
        <div class="text-sm text-ink-gray-8">
          <span v-if="drive?.connected">{{ __('Connected') }}<span v-if="drive.account"> — {{ drive.account }}</span></span>
          <span v-else class="text-ink-gray-5">{{ __('Not connected') }}</span>
        </div>
        <div v-if="drive?.connected" class="text-xs text-ink-gray-6">
          {{ __('Copied') }}: {{ drive.counts.Copied }} · {{ __('Pending') }}: {{ drive.counts.Pending }} · {{ __('Failed') }}: {{ drive.counts.Failed }}
        </div>
        <div class="flex flex-wrap gap-2">
          <Button variant="solid" :label="drive?.connected ? __('Reconnect') : __('Connect Drive')" @click="connectDrive" />
          <Button v-if="drive?.connected" :label="__('Test')" :loading="busy" @click="testDrive" />
          <Button v-if="drive?.connected" :label="__('Copy old payments')" :loading="busy" @click="copyOld" />
          <Button v-if="drive?.counts?.Failed" :label="__('Try again')" :loading="busy" @click="retryAll" />
          <Button v-if="drive?.connected" theme="red" :label="__('Disconnect')" :loading="busy" @click="disconnectDrive" />
        </div>
      </div>
    </section>

    <!-- Serviços -->
    <section class="rounded-lg border p-4 text-ink-gray-8">
      <h3 class="text-lg-semibold text-ink-gray-9">{{ __('Services') }}</h3>
      <div class="mt-3 flex flex-col gap-3">
        <FormControl v-model="services.calendar_enabled" type="checkbox" :label="__('Google Calendar')" />
        <FormControl v-model="services.drive_enabled" type="checkbox" :label="__('Google Drive mirror of payment files')" />
        <FormControl v-model="services.drive_root_folder" :label="__('Drive root folder')" type="text" />
        <div><Button variant="solid" :label="__('Save')" :loading="busy" @click="saveServices" /></div>
      </div>
    </section>

    <MessagingSettings />

    <!-- E-mail -->
    <section class="rounded-lg border p-4 text-ink-gray-8">
      <h3 class="text-lg-semibold text-ink-gray-9">{{ __('Email') }}</h3>
      <p class="mb-3 text-sm text-ink-gray-6">
        {{ __('Email accounts connected') }}: {{ cfg?.email?.accounts ?? 0 }}.
        {{ __('Add HostGator, Gmail or Outlook accounts in the Accounts page.') }}
      </p>
      <Button :label="__('Open email accounts')" @click="activeSettingsPage = __('Accounts')" />
    </section>
  </div>
</template>

<script setup>
import { call, toast, FormControl, Button } from 'frappe-ui'
import { activeSettingsPage } from '@/composables/settings'
import MessagingSettings from '@/components/Settings/MessagingSettings.vue'
import { onMounted, reactive, ref } from 'vue'

const cfg = ref(null)
const busy = ref(false)
const siteOrigin = ref('')
const newToken = ref('')
const google = reactive({ client_id: '', client_secret: '' })
const services = reactive({ calendar_enabled: false, drive_enabled: false, drive_root_folder: 'Panda Project' })

const drive = ref(null)
const msg = (e) => e?.messages?.[0] || e?.message || String(e)

async function load() {
  cfg.value = await call('crm.panda.integracoes.get_config')
  drive.value = await call('crm.panda.drive.get_status')
  siteOrigin.value = cfg.value.site.origin
  google.client_id = cfg.value.google.client_id
  services.calendar_enabled = cfg.value.calendar.enabled
  services.drive_enabled = cfg.value.drive.enabled
  services.drive_root_folder = cfg.value.drive.root_folder
}
async function run(fn, ok = __('Saved')) {
  busy.value = true
  try {
    await fn()
    toast.success(ok)
    await load()
  } catch (e) {
    toast.error(msg(e))
  } finally {
    busy.value = false
  }
}
const genToken = () =>
  run(async () => {
    newToken.value = await call('crm.panda.integracoes.generate_site_token')
  }, __('Token generated'))
const saveSite = () => run(() => call('crm.panda.integracoes.save_site', { origin: siteOrigin.value }))
const saveGoogle = () =>
  run(async () => {
    await call('crm.panda.integracoes.save_google', { client_id: google.client_id, client_secret: google.client_secret, enabled: 1 })
    google.client_secret = ''
  })
const saveServices = () =>
  run(() =>
    call('crm.panda.integracoes.save_services', {
      calendar_enabled: services.calendar_enabled ? 1 : 0,
      drive_enabled: services.drive_enabled ? 1 : 0,
      drive_root_folder: services.drive_root_folder,
    }),
  )
const connectDrive = async () => {
  try {
    window.location.href = await call('crm.panda.drive.get_auth_url')
  } catch (e) {
    toast.error(msg(e))
  }
}
const testDrive = async () => {
  busy.value = true
  try {
    const r = await call('crm.panda.drive.test')
    r.ok ? toast.success(`${__('Drive connected')} ${r.account || ''}`) : toast.error(r.error)
  } finally {
    busy.value = false
  }
}
const copyOld = () => run(async () => toast.info(`${await call('crm.panda.drive.copy_old')} ${__('files queued')}`), __('Queued'))
const retryAll = () => run(() => call('crm.panda.drive.retry'), __('Queued'))
const disconnectDrive = () => run(() => call('crm.panda.drive.disconnect'), __('Disconnected'))
const copy = async (t) => {
  try {
    await navigator.clipboard.writeText(t)
    toast.success(__('Copied'))
  } catch {
    toast.error(__('Could not copy'))
  }
}
onMounted(load)
</script>
