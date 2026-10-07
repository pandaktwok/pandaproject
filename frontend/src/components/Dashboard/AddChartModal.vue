<template>
  <Dialog v-model:open="show" :title="__('Add Chart')" @close="show = false">
    <template #default>
      <div class="flex flex-col gap-4">
        <FormControl
          v-model="chartType"
          type="select"
          :label="__('Chart Type')"
          :options="chartTypes"
        />
        <FormControl
          v-if="chartType === 'number_chart'"
          v-model="numberChart"
          type="select"
          :label="__('Number Chart')"
          :options="numberCharts"
        />
        <FormControl
          v-if="chartType === 'axis_chart'"
          v-model="axisChart"
          type="select"
          :label="__('Axis Chart')"
          :options="axisCharts"
        />
        <FormControl
          v-if="chartType === 'donut_chart'"
          v-model="donutChart"
          type="select"
          :label="__('Donut Chart')"
          :options="donutCharts"
        />
      </div>
    </template>
    <template #actions>
      <div class="flex items-center justify-end gap-2">
        <Button variant="outline" :label="__('Cancel')" @click="show = false" />
        <Button variant="solid" :label="__('Add')" @click="addChart" />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { getRandom } from '@/utils'
import { createResource, Dialog, FormControl } from 'frappe-ui'
import { ref, reactive, inject } from 'vue'

const show = defineModel({
  type: Boolean,
  default: false,
})

const items = defineModel('items', {
  type: Array,
  default: () => [],
})

const fromDate = inject('fromDate', ref(''))
const toDate = inject('toDate', ref(''))
const filters = inject('filters', reactive({ period: '', deal: '' }))

const chartType = ref('spacer')
const chartTypes = [
  { label: __('Spacer'), value: 'spacer' },
  { label: __('Number Chart'), value: 'number_chart' },
  { label: __('Axis Chart'), value: 'axis_chart' },
  { label: __('Donut Chart'), value: 'donut_chart' },
  { label: __('Project activity feed'), value: 'feed' },
]

const numberChart = ref('')
const numberCharts = [
  { label: __('Total projects'), value: 'projetos_total' },
  { label: __('Projects in progress'), value: 'projetos_andamento' },
  { label: __('Finished projects'), value: 'projetos_encerrados' },
  { label: __('Total value of projects'), value: 'valor_total_projetos' },
  { label: __('Average value per project'), value: 'valor_medio_projeto' },
  { label: __('Suppliers'), value: 'qtd_fornecedores' },
  { label: __('Average spent per supplier'), value: 'media_por_fornecedor' },
  { label: __('Total Leads'), value: 'total_leads' },
  { label: __('Ongoing Deals'), value: 'ongoing_deals' },
  { label: __('Avg Ongoing Deal Value'), value: 'average_ongoing_deal_value' },
  { label: __('Won Deals'), value: 'won_deals' },
  { label: __('Avg Won Deal Value'), value: 'average_won_deal_value' },
  { label: __('Avg Deal Value'), value: 'average_deal_value' },
  {
    label: __('Avg Time to Close a Lead'),
    value: 'average_time_to_close_a_lead',
  },
  {
    label: __('Avg Time to Close a Deal'),
    value: 'average_time_to_close_a_deal',
  },
]

const axisChart = ref('projetos_por_tipo_mes')
const axisCharts = [
  { label: __('Projects by type'), value: 'projetos_por_tipo_mes' },
  { label: __('Payments'), value: 'pagamentos_por_mes' },
  { label: __('Sales Trend'), value: 'sales_trend' },
  { label: __('Forecasted Revenue'), value: 'forecasted_revenue' },
  { label: __('Funnel Conversion'), value: 'funnel_conversion' },
  { label: __('Deals by Ongoing & Won Stage'), value: 'deals_by_stage_axis' },
  { label: __('Lost Deal Reasons'), value: 'lost_deal_reasons' },
  { label: __('Deals by Territory'), value: 'deals_by_territory' },
  { label: __('Deals by Salesperson'), value: 'deals_by_salesperson' },
]

const donutChart = ref('deals_by_stage_donut')
const donutCharts = [
  { label: __('Deals by Stage'), value: 'deals_by_stage_donut' },
  { label: __('Leads by Source'), value: 'leads_by_source' },
  { label: __('Deals by Source'), value: 'deals_by_source' },
]

async function addChart() {
  show.value = false
  if (chartType.value == 'spacer') {
    items.value.push({
      name: 'spacer',
      type: 'spacer',
      layout: { x: 0, y: 0, w: 4, h: 2, i: 'spacer_' + getRandom(4) },
    })
  } else {
    await getChart(chartType.value)
  }
}

async function getChart(type: string) {
  let name =
    type == 'feed'
      ? 'atividades'
      : type == 'number_chart'
      ? numberChart.value
      : type == 'axis_chart'
        ? axisChart.value
        : donutChart.value

  await createResource({
    url: 'crm.api.dashboard.get_chart',
    params: {
      name,
      type,
      from_date: fromDate.value,
      to_date: toDate.value,
      deal: filters.deal,
    },
    auto: true,
    onSuccess: (data = {}) => {
      let width = 4
      let height = 2

      if (['axis_chart', 'donut_chart'].includes(type)) {
        width = 10
        height = 7
      }
      if (type == 'feed') {
        width = 20
        height = 12
      }

      items.value.push({
        name,
        type,
        layout: {
          x: 0,
          y: 0,
          w: width,
          h: height,
          i: name + '_' + getRandom(4),
        },
        data: data,
      })
    },
  })
}
</script>
