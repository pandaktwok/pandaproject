<template>
  <div class="flex h-full w-full flex-col">
    <div class="border-b px-4 py-3">
      <div class="text-base-semibold text-ink-gray-9">{{ __('Project activity') }}</div>
      <div class="text-xs text-ink-gray-5">{{ __('Payments, finished tasks and notices from all projects') }}</div>
    </div>
    <div v-if="!items.length" class="p-4 text-sm text-ink-gray-5">{{ __('Nothing happened yet.') }}</div>
    <div class="min-h-0 flex-1 divide-y overflow-y-auto">
      <router-link
        v-for="(it, i) in items"
        :key="i"
        :to="{ name: 'Deal', params: { dealId: it.deal } }"
        class="flex items-start gap-3 px-4 py-2.5 hover:bg-surface-gray-2"
      >
        <span class="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full" :class="style(it.kind).bg">
          <component :is="style(it.kind).icon" class="h-3.5 w-3.5" :class="style(it.kind).fg" />
        </span>
        <div class="min-w-0 flex-1">
          <div class="text-sm text-ink-gray-9">{{ it.text }}</div>
          <div class="truncate text-xs text-ink-gray-5">{{ it.deal_name }}</div>
        </div>
        <div class="shrink-0 text-xs text-ink-gray-5">{{ day(it.when) }}</div>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import LucideBanknote from '~icons/lucide/banknote'
import LucideCircleCheck from '~icons/lucide/circle-check'
import LucideBell from '~icons/lucide/bell'
import LucideFolderPlus from '~icons/lucide/folder-plus'

defineProps({ items: { type: Array, default: () => [] } })

const styles = {
  payment: { icon: LucideBanknote, bg: 'bg-surface-green-2', fg: 'text-ink-green-3' },
  task: { icon: LucideCircleCheck, bg: 'bg-surface-blue-2', fg: 'text-ink-blue-3' },
  notice: { icon: LucideBell, bg: 'bg-surface-amber-2', fg: 'text-ink-amber-3' },
  project: { icon: LucideFolderPlus, bg: 'bg-surface-gray-3', fg: 'text-ink-gray-7' },
}
const style = (k) => styles[k] || styles.project
const day = (d) => {
  const t = new Date(String(d).replace(' ', 'T'))
  return isNaN(t) ? '' : t.toLocaleDateString('pt-BR')
}
</script>
