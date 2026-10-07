<template>
  <div class="px-3 pb-6 pt-2 sm:px-10">
    <div v-if="loading" class="py-10 text-center text-ink-gray-4">{{ __('Loading...') }}</div>
    <div v-else-if="!items.length" class="py-10 text-center text-ink-gray-4">
      {{ __('No activity yet') }}
    </div>
    <ol v-else class="relative ml-2 border-l border-outline-gray-2">
      <li v-for="(item, i) in items" :key="i" class="mb-4 ml-5">
        <span
          class="absolute -left-[7px] mt-1.5 size-3.5 rounded-full border-2 border-surface-white"
          :class="dot[item.severity]"
        />
        <div class="flex flex-wrap items-baseline gap-x-3">
          <span class="text-base text-ink-gray-9">{{ item.text }}</span>
          <span class="text-xs text-ink-gray-5">{{ when(item.date) }}</span>
        </div>
      </li>
    </ol>
  </div>
</template>

<script setup>
import { call } from 'frappe-ui'
import { ref } from 'vue'

const props = defineProps({ deal: { type: String, required: true } })
const items = ref([])
const loading = ref(true)
const dot = {
  info: 'bg-surface-gray-5',
  success: 'bg-surface-green-3',
  warning: 'bg-surface-amber-3',
  danger: 'bg-surface-red-5',
}
const when = (d) => {
  if (!d) return ''
  const [data, hora] = d.split(' ')
  const br = data.split('-').reverse().join('/')
  return hora && hora.slice(0, 5) !== '00:00' ? `${br} ${hora.slice(0, 5)}` : br
}
call('crm.panda.activity.get_project_log', { deal: props.deal })
  .then((r) => (items.value = r))
  .finally(() => (loading.value = false))
</script>
