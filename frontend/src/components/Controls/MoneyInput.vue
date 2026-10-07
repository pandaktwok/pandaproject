<template>
  <FormControl
    :label="label"
    type="text"
    inputmode="decimal"
    autocomplete="off"
    placeholder="0,00"
    :modelValue="text"
    @update:modelValue="onInput"
    @blur="onBlur"
  >
    <template #prefix>
      <span class="text-sm text-ink-gray-5">R$</span>
    </template>
  </FormControl>
</template>

<script setup>
// Campo de dinheiro no formato brasileiro: digita 3000 e aparece 3.000,00.
// O valor emitido é número (3000), nunca texto.
import { ref, watch } from 'vue'

defineProps({ label: { type: String, default: '' } })
const model = defineModel({ type: [Number, String], default: '' })

function formatTyped(raw) {
  let s = String(raw ?? '').replace(/[^\d,]/g, '')
  const i = s.indexOf(',')
  let int = i >= 0 ? s.slice(0, i) : s
  let dec = i >= 0 ? s.slice(i + 1).replace(/,/g, '').slice(0, 2) : null
  int = int.replace(/^0+(?=\d)/, '')
  int = int.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  if (dec === null) return int
  return `${int || '0'},${dec}`
}
function toNumber(text) {
  if (!text) return ''
  const n = Number(text.replace(/\./g, '').replace(',', '.'))
  return Number.isFinite(n) ? n : ''
}
function fromNumber(v) {
  if (v === '' || v === null || v === undefined || isNaN(Number(v))) return ''
  return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const text = ref(fromNumber(model.value))

function onInput(v) {
  text.value = formatTyped(v)
  model.value = toNumber(text.value)
}
function onBlur() {
  text.value = fromNumber(toNumber(text.value))
}
// mudanças vindas de fora (abrir o diálogo, limpar)
watch(model, (v) => {
  if (v !== toNumber(text.value)) text.value = fromNumber(v)
})
</script>
