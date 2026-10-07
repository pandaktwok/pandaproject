import { createResource } from 'frappe-ui'
import { reactive } from 'vue'

// Cores dos tipos de projeto (CRM Project Type), usadas nas etiquetas coloridas.
const colors = reactive({})
let started = false

export function useProjectTypes() {
  if (!started) {
    started = true
    createResource({
      url: 'frappe.client.get_list',
      params: { doctype: 'CRM Project Type', fields: ['name', 'color'], limit_page_length: 100 },
      auto: true,
      onSuccess: (rows) => rows.forEach((r) => (colors[r.name] = r.color || 'gray')),
    })
  }
  return { typeColor: (name) => colors[name] || 'gray' }
}
