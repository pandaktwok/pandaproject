<template>
  <div class="flex flex-col h-full overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <ViewBreadcrumbs routeName="Dashboard" />
      </template>
      <template #right-header>
        <Button
          v-if="!editing"
          :label="__('Refresh')"
          :iconLeft="LucideRefreshCcw"
          @click="dashboardItems.reload"
        />
        <Button
          v-if="!editing"
          :label="__('Print / Save PDF')"
          iconLeft="lucide-printer"
          @click="printReport"
        />
        <Button
          v-if="!editing && isAdmin()"
          :label="__('Edit')"
          :iconLeft="LucidePenLine"
          @click="enableEditing"
        />
        <Button
          v-if="editing"
          :label="__('Chart')"
          iconLeft="plus"
          @click="showAddChartModal = true"
        />
        <Button
          v-if="editing && isAdmin()"
          :label="__('Reset to Default')"
          :iconLeft="LucideUndo2"
          @click="resetToDefault"
        />
        <Button v-if="editing" :label="__('Cancel')" @click="cancel" />
        <Button
          v-if="editing"
          variant="solid"
          :label="__('Save')"
          :disabled="!dirty"
          :loading="saveDashboard.loading"
          @click="save"
        />
      </template>
    </LayoutHeader>

    <div class="p-5 pb-2 flex items-center gap-4">
      <Dropdown
        v-if="!showDatePicker"
        v-model="preset"
        :options="options"
        class="form-control"
        :placeholder="__('Select Range')"
        :button="{
          label: __(preset),
          class:
            '!w-full justify-start [&>span]:mr-auto [&>svg]:text-ink-gray-5',
          variant: 'outline',
          iconRight: 'chevron-down',
          iconLeft: 'calendar',
        }"
      />
      <DateRangePicker
        v-else
        ref="datePickerRef"
        class="!w-48"
        :value="filters.period"
        variant="outline"
        :placeholder="__('Period')"
        :formatter="formatRange"
        @change="
          (v) =>
            updateFilter('period', v, () => {
              showDatePicker = false
              if (!v) {
                filters.period = getLastXDays()
                preset = 'Last 30 Days'
              } else {
                preset = formatter(v)
              }
            })
        "
      >
        <template #prefix>
          <LucideCalendar class="size-4 text-ink-gray-5 mr-2" />
        </template>
      </DateRangePicker>
      <Link
        class="form-control w-56"
        variant="outline"
        :value="filters.deal"
        doctype="CRM Deal"
        :placeholder="__('Project')"
        @change="(v) => updateFilter('deal', v)"
      />
    </div>

    <div class="w-full overflow-y-scroll">
      <DashboardGrid
        v-if="!dashboardItems.loading && dashboardItems.data"
        v-model="dashboardItems.data"
        class="pt-1"
        :editing="editing"
      />
    </div>
  </div>
  <AddChartModal
    v-if="showAddChartModal"
    v-model="showAddChartModal"
    v-model:items="dashboardItems.data"
  />
</template>

<script setup lang="ts">
import AddChartModal from '@/components/Dashboard/AddChartModal.vue'
import LucideRefreshCcw from '~icons/lucide/refresh-ccw'
import LucideUndo2 from '~icons/lucide/undo-2'
import LucidePenLine from '~icons/lucide/pen-line'
import DashboardGrid from '@/components/Dashboard/DashboardGrid.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import Link from '@/components/Controls/Link.vue'
import { usersStore } from '@/stores/users'
import { copy } from '@/utils'
import {
  getLastXDays,
  formatter,
  formatRange,
  parseDateRange,
} from '@/utils/dashboard'
import {
  usePageMeta,
  createResource,
  DateRangePicker,
  Dropdown,
  Tooltip,
} from 'frappe-ui'
import { ref, reactive, computed, provide } from 'vue'

const { users, getUser, isManager, isAdmin } = usersStore()

const editing = ref(false)

const showDatePicker = ref(false)
const datePickerRef = ref(null)
const preset = ref('Last 30 Days')
const showAddChartModal = ref(false)

const filters = reactive({
  period: getLastXDays(),
  deal: null,
})

const fromDate = computed(() => {
  return parseDateRange(filters.period)[0] || null
})

const toDate = computed(() => {
  return parseDateRange(filters.period)[1] || null
})

function updateFilter(key: string, value: unknown, callback?: () => void) {
  filters[key] = value
  callback?.()
  dashboardItems.reload()
}

const options = computed(() => [
  {
    group: 'Presets',
    hideLabel: true,
    items: [
      {
        label: __('Last 7 Days'),
        onClick: () => {
          preset.value = 'Last 7 Days'
          filters.period = getLastXDays(7)
          dashboardItems.reload()
        },
      },
      {
        label: __('Last 30 Days'),
        onClick: () => {
          preset.value = 'Last 30 Days'
          filters.period = getLastXDays(30)
          dashboardItems.reload()
        },
      },
      {
        label: __('Last 60 Days'),
        onClick: () => {
          preset.value = 'Last 60 Days'
          filters.period = getLastXDays(60)
          dashboardItems.reload()
        },
      },
      {
        label: __('Last 90 Days'),
        onClick: () => {
          preset.value = 'Last 90 Days'
          filters.period = getLastXDays(90)
          dashboardItems.reload()
        },
      },
    ],
  },
  {
    label: __('Custom Range'),
    onClick: () => {
      showDatePicker.value = true
      setTimeout(() => datePickerRef.value?.open(), 0)
      preset.value = 'Custom Range'
      filters.period = null // Reset period to allow custom date selection
    },
  },
])

const dashboardItems = createResource({
  url: 'crm.api.dashboard.get_dashboard',
  makeParams() {
    return {
      from_date: fromDate.value,
      to_date: toDate.value,
      deal: filters.deal,
    }
  },
  auto: true,
})

const dirty = computed(() => {
  if (!editing.value) return false
  return JSON.stringify(dashboardItems.data) !== JSON.stringify(oldItems.value)
})

const oldItems = ref([])

provide('fromDate', fromDate)
provide('toDate', toDate)
provide('filters', filters)

// Relatório de números: abre uma página limpa (cartões, tabelas dos gráficos e feed) e chama a impressão;
// no diálogo do navegador dá para escolher "Salvar como PDF".
function printReport() {
  const esc = (t: unknown) =>
    String(t ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c] as string)
  const money = (v: number) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(v || 0))
  const items = (dashboardItems.data || []) as any[]
  const cards = items
    .filter((i) => i.type === 'number_chart' && i.data)
    .map((i) => {
      const v = i.data.prefix ? money(i.data.value) : new Intl.NumberFormat('pt-BR').format(Number(i.data.value || 0))
      return `<div class="card"><div class="t">${esc(i.data.title)}</div><div class="v">${esc(v)}</div></div>`
    })
    .join('')
  const tables = items
    .filter((i) => i.type === 'axis_chart' && i.data?.data?.length)
    .map((i) => {
      const d = i.data
      const key = d.xAxis?.key
      const cols = d.series.map((s: any) => s.name)
      const fmt = (v: any) => (typeof v === 'number' && /Valor|Revenue/.test(d.yAxis?.title || '') ? money(v) : esc(v ?? ''))
      const head = `<tr><th>${esc(d.xAxis?.title || '')}</th>${cols.map((c: string) => `<th>${esc(c)}</th>`).join('')}</tr>`
      const body = d.data
        .map((r: any) => `<tr><td>${esc(r[key])}</td>${cols.map((c: string) => `<td>${fmt(r[c])}</td>`).join('')}</tr>`)
        .join('')
      return `<h2>${esc(d.title)}</h2><p class="s">${esc(d.subtitle || '')}</p><table>${head}${body}</table>`
    })
    .join('')
  const feed = items.find((i) => i.type === 'feed')?.data?.items || []
  const feedHtml = feed.length
    ? `<h2>${__('Project activity')}</h2><ul>${feed
        .slice(0, 60)
        .map((f: any) => `<li>${esc(f.text)} <span class="s">— ${esc(f.deal_name)}</span></li>`)
        .join('')}</ul>`
    : ''
  const w = window.open('', '_blank')
  if (!w) return
  w.document.write(`<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Relatório — Panda Project</title>
<style>
body{font-family:Inter,Arial,sans-serif;color:#111;margin:24px}
h1{font-size:20px;margin:0}h2{font-size:15px;margin:22px 0 2px}.s{color:#666;font-size:12px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:14px}
.card{border:1px solid #ccc;border-radius:8px;padding:10px}.t{font-size:11px;color:#555}.v{font-size:18px;font-weight:600;margin-top:4px}
table{border-collapse:collapse;width:100%;margin-top:6px;font-size:12px}th,td{border:1px solid #ddd;padding:4px 6px;text-align:right}
th:first-child,td:first-child{text-align:left}th{background:#f3f3f3}ul{padding-left:18px;font-size:12px}li{margin:3px 0}
</style></head><body>
<h1>Panda Project — ${__('Report')}</h1><div class="s">${new Date().toLocaleDateString('pt-BR')}</div>
<div class="grid">${cards}</div>${tables}${feedHtml}
<script>window.onload=()=>setTimeout(()=>window.print(),300)<\/script></body></html>`)
  w.document.close()
}

function enableEditing() {
  editing.value = true
  oldItems.value = copy(dashboardItems.data)
}

function cancel() {
  editing.value = false
  dashboardItems.data = copy(oldItems.value)
}

const saveDashboard = createResource({
  url: 'frappe.client.set_value',
  method: 'POST',
  onSuccess: () => {
    dashboardItems.reload()
    editing.value = false
  },
})

function save() {
  const dashboardItemsCopy = copy(dashboardItems.data)

  dashboardItemsCopy.forEach((item: Record<string, unknown>) => {
    delete item.data
  })

  saveDashboard.submit({
    doctype: 'CRM Dashboard',
    name: 'Manager Dashboard',
    fieldname: 'layout',
    value: JSON.stringify(dashboardItemsCopy),
  })
}

function resetToDefault() {
  createResource({
    url: 'crm.api.dashboard.reset_to_default',
    auto: true,
    onSuccess: () => {
      dashboardItems.reload()
      editing.value = false
    },
  })
}

usePageMeta(() => {
  return { title: __('CRM Dashboard') }
})
</script>
