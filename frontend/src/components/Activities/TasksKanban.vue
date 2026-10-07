<template>
  <div class="grid min-h-[50vh] grid-cols-1 gap-3 px-3 pb-6 sm:px-10 md:grid-cols-3 xl:grid-cols-5">
    <div
      v-for="col in columns"
      :key="col.value"
      class="flex flex-col rounded-lg bg-surface-gray-2 p-2"
      :class="over === col.value ? 'ring-2 ring-outline-gray-4' : ''"
      @dragover.prevent="over = col.value"
      @dragleave="over = null"
      @drop.prevent="onDrop(col.value)"
    >
      <div class="mb-2 flex items-center justify-between px-1 text-sm-medium text-ink-gray-8">
        <span class="flex items-center gap-1.5"><TaskStatusIcon :status="col.value" />{{ col.label }}</span>
        <span class="text-ink-gray-5">{{ byStatus(col.value).length }}</span>
      </div>
      <div
        v-for="task in byStatus(col.value)"
        :key="task.name"
        draggable="true"
        class="mb-2 cursor-grab rounded-md border bg-surface-white p-2.5 shadow-sm"
        @dragstart="dragging = task"
        @dragend="(dragging = null), (over = null)"
        @click="modalRef.showTask(task)"
      >
        <div class="truncate text-base text-ink-gray-9">{{ task.title }}</div>
        <div class="mt-1.5 flex flex-wrap items-center gap-x-2 text-xs text-ink-gray-6">
          <span v-if="task.assigned_to" class="flex items-center gap-1">
            <UserAvatar :user="task.assigned_to" size="xs" />{{ getUser(task.assigned_to).full_name }}
          </span>
          <span v-if="task.due_date" :class="late(task) ? 'text-ink-red-4' : ''">{{ dia(task.due_date) }}</span>
          <span class="flex items-center gap-1"><TaskPriorityIcon class="!h-2 !w-2" :priority="task.priority" />{{ task.priority }}</span>
        </div>
      </div>
      <div v-if="!byStatus(col.value).length" class="px-1 py-3 text-xs text-ink-gray-4">{{ __('Drop tasks here') }}</div>
    </div>
  </div>
</template>

<script setup>
import TaskStatusIcon from '@/components/Icons/TaskStatusIcon.vue'
import TaskPriorityIcon from '@/components/Icons/TaskPriorityIcon.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { usersStore } from '@/stores/users'
import { computed, ref } from 'vue'

const props = defineProps({
  tasks: { type: Array, default: () => [] },
  modalRef: { type: Object, default: () => ({}) },
})
const { getUser } = usersStore()
const dragging = ref(null)
const over = ref(null)

// Colunas padrão: A fazer, Em andamento, Em revisão, Concluído.
// Pendências e Canceladas só aparecem se existirem tarefas nesses estados.
const columns = computed(() =>
  [
    { value: 'Backlog', label: __('Backlog'), extra: true },
    { value: 'Todo', label: __('Todo') },
    { value: 'In Progress', label: __('In Progress') },
    { value: 'In Review', label: __('In Review') },
    { value: 'Done', label: __('Done') },
    { value: 'Canceled', label: __('Canceled'), extra: true },
  ].filter((c) => !c.extra || props.tasks.some((t) => t.status === c.value)),
)
const byStatus = (s) => props.tasks.filter((t) => t.status === s)
const dia = (d) => (d ? d.slice(0, 10).split('-').reverse().join('/') : '')
const late = (t) => t.due_date && t.status !== 'Done' && t.status !== 'Canceled' && new Date(t.due_date) < new Date()

function onDrop(status) {
  const task = dragging.value
  over.value = null
  dragging.value = null
  if (task && task.status !== status) props.modalRef.updateTaskStatus(status, task)
}
</script>
