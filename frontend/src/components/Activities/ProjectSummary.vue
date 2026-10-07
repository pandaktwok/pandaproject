<template>
  <div v-if="s" class="flex w-full flex-col gap-5 px-3 pb-6 pt-2 sm:px-10">
    <div
      v-if="s.last_notice"
      class="flex items-center gap-2 rounded-lg border border-outline-red-2 bg-surface-red-1 p-3 text-sm text-ink-red-4"
    >
      <LucideTriangleAlert class="h-4 w-4 shrink-0" />
      <span>{{ s.last_notice.message }}</span>
      <span class="ml-auto shrink-0 text-xs">{{ __('Last notice') }}: {{ day(String(s.last_notice.sent_on).slice(0, 10)) }}</span>
    </div>
    <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <div class="rounded-lg border p-3">
        <div class="text-sm text-ink-gray-5">{{ __('Status') }}</div>
        <div class="mt-1 text-lg-semibold text-ink-gray-9">{{ s.status }}</div>
      </div>
      <div class="rounded-lg border p-3">
        <div class="text-sm text-ink-gray-5">{{ __('Project Type') }}</div>
        <div class="mt-1">
          <Badge v-if="s.project_type" :label="s.project_type" :theme="typeColor(s.project_type)" variant="subtle" size="lg" />
          <span v-else class="text-lg-semibold text-ink-gray-9">—</span>
        </div>
      </div>
      <div class="rounded-lg border p-3">
        <div class="text-sm text-ink-gray-5">{{ __('Expected Closure Date') }}</div>
        <div class="mt-1 text-lg-semibold text-ink-gray-9">{{ day(s.expected_closure_date) }}</div>
      </div>
      <div class="rounded-lg border p-3" :class="endClass">
        <div class="text-sm text-ink-gray-5">{{ __('Days to end') }}</div>
        <div class="mt-1 text-lg-semibold">{{ s.days_to_end ?? '—' }}</div>
      </div>
    </div>

    <div class="rounded-lg border p-4">
      <div class="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <div class="text-lg-semibold text-ink-gray-9">{{ __('Payments') }}</div>
        <div class="text-sm text-ink-gray-6">
          {{ __('Paid') }} {{ money(s.paid) }} {{ __('of') }} {{ money(s.total) }}
          · {{ __('Remaining') }} {{ money(s.remaining) }}
        </div>
      </div>
      <div class="h-3 w-full overflow-hidden rounded-full bg-surface-gray-3">
        <div class="h-3 rounded-full bg-surface-green-3" :style="{ width: Math.min(s.percent_paid, 100) + '%' }" />
      </div>
      <div class="mt-1 text-right text-xs text-ink-gray-5">{{ s.percent_paid }}%</div>
    </div>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div class="rounded-lg border p-4">
        <div class="mb-2 text-lg-semibold text-ink-gray-9">{{ __('Tasks') }}</div>
        <div v-if="!Object.keys(s.tasks).length" class="text-sm text-ink-gray-4">
          {{ __('No tasks') }}
        </div>
        <div v-for="(n, status) in s.tasks" :key="status" class="flex justify-between py-1 text-sm text-ink-gray-8">
          <span>{{ status }}</span><b>{{ n }}</b>
        </div>
      </div>
      <div class="rounded-lg border p-4">
        <div class="mb-2 text-lg-semibold text-ink-gray-9">{{ __('Next payments') }}</div>
        <div v-if="!s.next_payments.length" class="text-sm text-ink-gray-4">
          {{ __('No pending payments') }}
        </div>
        <div v-for="p in s.next_payments" :key="p.supplier + p.number" class="flex justify-between py-1 text-sm">
          <span :class="p.late ? 'text-ink-red-4' : 'text-ink-gray-8'">
            {{ day(p.due_date) }} · {{ p.supplier }} ({{ p.number }})
          </span>
          <b>{{ money(p.value) }}</b>
        </div>
      </div>
    </div>

    <div v-if="s.tags.length" class="rounded-lg border p-4">
      <div class="mb-2 text-lg-semibold text-ink-gray-9">{{ __('Finance Tags') }}</div>
      <div v-for="t in s.tags" :key="t.name" class="flex items-center justify-between py-1 text-sm">
        <Badge :label="t.tag_name" :theme="over(t) ? 'red' : t.color" variant="subtle" />
        <span :class="over(t) ? 'text-ink-red-4' : 'text-ink-gray-7'">{{ money(t.used) }} / {{ money(t.value) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { call, Badge } from 'frappe-ui'
import { useProjectTypes } from '@/stores/projectTypes'
const { typeColor } = useProjectTypes()
import { computed, ref } from 'vue'

const props = defineProps({ deal: { type: String, required: true } })
const s = ref(null)
call('crm.panda.activity.get_project_summary', { deal: props.deal }).then((r) => (s.value = r))
const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const money = (v) => brl.format(Number(v || 0))
const over = (t) => Number(t.value) > 0 && Math.round(t.used * 100) > Math.round(t.value * 100)
const day = (d) => (d ? d.split('-').reverse().join('/') : '—')
const endClass = computed(() => (s.value?.days_to_end != null && s.value.days_to_end <= 90 ? 'border-outline-red-2 bg-surface-red-1' : ''))
</script>
