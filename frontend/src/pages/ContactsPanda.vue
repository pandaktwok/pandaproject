<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="[{ label: __('Contacts'), route: { name: 'Contacts' } }]" />
    </template>
    <template #right-header>
      <Button
        v-if="canImport"
        :label="__('Import WhatsApp groups')"
        iconLeft="lucide-download"
        :loading="imp.estado === 'rodando'"
        @click="startImport"
      />
      <Button variant="solid" :label="__('Create')" iconLeft="plus" @click="showContactModal = true" />
    </template>
  </LayoutHeader>

  <div class="flex flex-wrap items-center gap-2 border-b px-5 py-3">
    <div class="w-72 max-w-full">
      <FormControl v-model="q" type="text" :placeholder="__('Search by name, number or email')" @update:modelValue="debouncedLoad" />
    </div>
    <div class="w-48">
      <FormControl v-model="origem" type="select" :options="origemOptions" @update:modelValue="load" />
    </div>
    <div v-if="imp.estado && imp.estado !== 'parado'" class="text-xs text-ink-gray-6">
      <template v-if="imp.estado === 'rodando'">
        {{ __('Importing') }}: {{ imp.grupos }}/{{ imp.grupos_total || '…' }} {{ __('groups') }} · {{ imp.criados }} {{ __('new') }}
      </template>
      <template v-else-if="imp.estado === 'concluido'">
        {{ __('Import finished') }}: {{ imp.criados }} {{ __('new') }}, {{ imp.atualizados }} {{ __('updated') }}<template v-if="imp.sem_numero">
          · {{ imp.sem_numero }} {{ __('without a visible number') }}</template>
      </template>
      <template v-else-if="imp.estado === 'erro'">
        <span class="text-ink-red-4">{{ imp.erro }}</span>
      </template>
    </div>
  </div>

  <div class="h-[calc(100%-7.5rem)] overflow-y-auto px-5 pb-8">
    <!-- Contatos -->
    <section>
      <h2 class="sticky top-0 z-10 bg-surface-white py-3 text-lg-semibold text-ink-gray-9">
        {{ __('Contacts') }}
        <span class="ml-1 text-sm font-normal text-ink-gray-5">({{ data.contatos.length }})</span>
      </h2>
      <ContactTable :rows="data.contatos" :loading="loading" @open="open" />
    </section>

    <hr class="my-6 border-t-2 border-outline-gray-2" />

    <!-- Newsletters -->
    <section>
      <h2 class="py-3 text-lg-semibold text-ink-gray-9">
        {{ __('Newsletters') }}
        <span class="ml-1 text-sm font-normal text-ink-gray-5">({{ data.newsletters.length }})</span>
      </h2>
      <ContactTable :rows="data.newsletters" :loading="loading" @open="open" />
    </section>

    <hr class="my-6 border-t-2 border-outline-gray-2" />

    <!-- E-mails recebidos de quem ainda nao esta em Contatos -->
    <section>
      <h2 class="py-3 text-lg-semibold text-ink-gray-9">
        {{ __('Pending registration') }}
        <span class="ml-1 text-sm font-normal text-ink-gray-5">({{ data.pendentes.length }})</span>
      </h2>
      <p class="-mt-2 mb-3 text-xs text-ink-gray-5">
        {{ __('People who sent emails and are not in Contacts yet. When the sender name matches a contact, the email is added to that contact automatically.') }}
      </p>
      <div class="overflow-hidden rounded-md border">
        <div v-if="!data.pendentes.length" class="px-3 py-6 text-center text-sm text-ink-gray-5">{{ __('Nothing pending') }}</div>
        <div
          v-for="e in data.pendentes"
          :key="e.email"
          class="flex items-center gap-3 border-b px-3 py-2 last:border-b-0"
        >
          <Avatar :label="e.nome || e.email" size="md" />
          <div class="min-w-0 flex-1">
            <div class="truncate text-sm text-ink-gray-9">{{ e.nome || e.email }}</div>
            <div class="truncate text-xs text-ink-gray-5">{{ e.email }} · {{ e.qtd }} {{ __('emails') }}</div>
          </div>
          <Button size="sm" :label="__('Create contact')" iconLeft="lucide-user-plus" @click="criarDeEmail(e)" />
        </div>
      </div>
    </section>
  </div>

  <ContactModal v-if="showContactModal" v-model="showContactModal" :contact="{}" />
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import ContactModal from '@/components/Modals/ContactModal.vue'
import ContactTable from '@/components/ContactTable.vue'
import { Avatar, Breadcrumbs, Button, FormControl, call, toast } from 'frappe-ui'
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { usersStore } from '@/stores/users'

const router = useRouter()
const { isAdmin } = usersStore()
const q = ref('')
const origem = ref('')
const loading = ref(false)
const showContactModal = ref(false)
const data = reactive({ contatos: [], newsletters: [], pendentes: [], origens: [] })
const imp = reactive({ estado: '' })

const origemOptions = computed(() => [
  { label: __('All origins'), value: '' },
  ...data.origens.map((o) => ({ label: o, value: o })),
])
const canImport = computed(() => (typeof isAdmin === 'function' ? isAdmin() : true))

async function load() {
  loading.value = true
  try {
    const r = await call('crm.panda.contatos.listar', { q: q.value, origem: origem.value })
    data.contatos = r.contatos
    data.newsletters = r.newsletters
    data.pendentes = r.pendentes || []
    if (!data.origens.length) data.origens = r.origens
  } catch (e) {
    toast.error(e?.messages?.[0] || e?.message || String(e))
  } finally {
    loading.value = false
  }
}
let t
function debouncedLoad() {
  clearTimeout(t)
  t = setTimeout(load, 300)
}
async function criarDeEmail(e) {
  try {
    const nome = await call('crm.panda.contatos.criar_de_email', { email: e.email, nome: e.nome })
    toast.success(__('Contact created'))
    router.push({ name: 'Contact', params: { contactId: nome } })
  } catch (err) {
    toast.error(err?.messages?.[0] || err?.message || String(err))
  }
}
const open = (c) => router.push({ name: 'Contact', params: { contactId: c.name } })

let poll
async function refreshImport() {
  try {
    Object.assign(imp, await call('crm.panda.chat.wa_importar_status'))
  } catch {}
  if (imp.estado === 'rodando') {
    clearTimeout(poll)
    poll = setTimeout(refreshImport, 3000)
  } else if (imp.estado === 'concluido') load()
}
async function startImport() {
  try {
    Object.assign(imp, await call('crm.panda.chat.wa_importar_grupos'))
    toast.success(__('Import started. You can keep using the program.'))
    refreshImport()
  } catch (e) {
    toast.error(e?.messages?.[0] || e?.message || String(e))
  }
}
onMounted(() => {
  load()
  if (canImport.value) refreshImport()
})
onUnmounted(() => clearTimeout(poll))
</script>
