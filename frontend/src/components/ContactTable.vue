<template>
  <div class="overflow-hidden rounded-md border">
    <div class="grid grid-cols-[minmax(10rem,2fr)_minmax(8rem,1fr)_minmax(10rem,1.5fr)_minmax(8rem,1.5fr)] gap-3 border-b bg-surface-gray-2 px-3 py-2 text-xs-medium text-ink-gray-6">
      <div>{{ __('Name') }}</div>
      <div>{{ __('WhatsApp') }}</div>
      <div>{{ __('Email') }}</div>
      <div>{{ __('Origin') }}</div>
    </div>
    <div v-if="!rows.length" class="px-3 py-6 text-center text-sm text-ink-gray-5">
      {{ loading ? __('Loading...') : __('No contacts here yet') }}
    </div>
    <button
      v-for="c in rows"
      :key="c.name"
      type="button"
      class="grid w-full grid-cols-[minmax(10rem,2fr)_minmax(8rem,1fr)_minmax(10rem,1.5fr)_minmax(8rem,1.5fr)] items-center gap-3 border-b px-3 py-2 text-left last:border-b-0 hover:bg-surface-gray-2"
      @click="$emit('open', c)"
    >
      <div class="flex min-w-0 items-center gap-2">
        <Avatar :image="c.image" :label="c.full_name" size="md" />
        <div class="min-w-0">
          <div class="truncate text-sm text-ink-gray-9">{{ c.full_name }}</div>
          <div v-if="c.grupos" class="truncate text-xs text-ink-gray-5">{{ c.grupos.split('\n').join(' · ') }}</div>
        </div>
      </div>
      <div class="truncate text-sm text-ink-gray-8">{{ c.phone || '—' }}</div>
      <div class="truncate text-sm text-ink-gray-8">{{ c.email || '—' }}</div>
      <div class="flex flex-wrap gap-1">
        <Badge v-for="o in c.origens" :key="o" :label="o" :theme="theme(o)" variant="subtle" />
      </div>
    </button>
  </div>
</template>

<script setup>
import { Avatar, Badge } from 'frappe-ui'

defineProps({ rows: { type: Array, default: () => [] }, loading: Boolean })
defineEmits(['open'])
const theme = (o) =>
  ({ WhatsApp: 'green', Instagram: 'orange', Fornecedor: 'blue', Newsletter: 'purple', 'E-mail': 'gray', Manual: 'gray' })[o] || 'gray'
</script>
