<template>
  <div class="flex w-full flex-col gap-6 px-3 pb-6 pt-2 sm:px-10">
    <!-- Resumo -->
    <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <div v-for="card in cards" :key="card.label" class="rounded-lg border p-3">
        <div class="text-sm text-ink-gray-5">{{ card.label }}</div>
        <div class="mt-1 text-xl-semibold text-ink-gray-9">
          {{ money(card.value) }}
        </div>
      </div>
    </div>

    <!-- Etiquetas financeiras -->
    <section>
      <div class="mb-2 flex items-center justify-between">
        <button type="button" class="flex items-center gap-1.5" @click="alternar('tags')">
          <LucideChevronDown class="h-4 w-4 text-ink-gray-6 transition-transform" :class="fechado.tags ? '-rotate-90' : ''" />
          <h3 class="text-lg-semibold text-ink-gray-9">{{ __('Finance Tags') }}</h3>
          <span v-if="fechado.tags && data?.tags?.length" class="text-sm text-ink-gray-5">({{ data.tags.length }})</span>
        </button>
        <Button variant="subtle" :label="__('New tag')" @click="openTag()">
          <template #prefix><LucideTag class="h-4 w-4" /></template>
        </Button>
      </div>
      <div v-show="!fechado.tags">
      <div v-if="!data?.tags?.length" class="text-sm text-ink-gray-4">
        {{ __('No finance tags yet') }}
      </div>
      <div v-else class="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
        <div
          v-for="tag in data.tags"
          :key="tag.name"
          class="flex items-center justify-between rounded-lg border p-3"
        >
          <div>
            <Badge :label="tag.tag_name" :theme="tagOver(tag) ? 'red' : tag.color" variant="subtle" />
            <div class="mt-1 text-sm text-ink-gray-6">
              {{ __('Tag value') }}: {{ money(tag.value) }}
            </div>
            <div class="text-xs" :class="tagOver(tag) ? 'text-ink-red-4' : 'text-ink-gray-5'">
              {{ __('In payment lines') }}: {{ money(tag.used) }}
            </div>
            <div v-if="tagOver(tag)" class="text-xs-medium text-ink-red-4">
              {{ __('Above the tag value by') }} {{ money(tag.used - tag.value) }}
            </div>
          </div>
          <div class="flex gap-1">
            <Button variant="ghost" icon="lucide-pencil" @click="openTag(tag)" />
            <Button variant="ghost" icon="lucide-trash-2" @click="removeTag(tag)" />
          </div>
        </div>
      </div>
      </div>
    </section>

    <!-- Cronograma de pagamentos (tabela) -->
    <section>
      <div class="mb-2 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <button type="button" class="flex items-center gap-1.5" @click="alternar('cron')">
            <LucideChevronDown class="h-4 w-4 text-ink-gray-6 transition-transform" :class="fechado.cron ? '-rotate-90' : ''" />
            <h3 class="text-lg-semibold text-ink-gray-9">{{ __('Payment schedule') }}</h3>
          </button>
          <Button variant="ghost" :title="__('Open project folder in Google Drive')" :loading="abrindoPasta" @click="abrirPasta">
            <template #icon><LucideFolder class="h-4 w-4" /></template>
          </Button>
        </div>
        <Button variant="solid" :label="__('New payment line')" @click="openLine()">
          <template #prefix><LucideTable class="h-4 w-4" /></template>
        </Button>
      </div>
      <div v-show="!fechado.cron">
      <div v-if="!data?.lines?.length" class="text-sm text-ink-gray-4">
        {{ __('No payment lines yet') }}
      </div>
      <!-- Três blocos alinhados por linhas de altura fixa: fornecedor (fixo) | parcelas (rola) | totais (fixo).
           O cabeçalho fica fora da rolagem vertical; o do meio acompanha a rolagem horizontal. -->
      <div v-else>
      <div class="mb-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
        <span class="flex items-center gap-1.5 text-ink-red-4"><LucideTriangleAlert class="h-3.5 w-3.5" />{{ __('Red: last 3 installments of each supplier') }}</span>
        <span class="flex items-center gap-1.5 text-ink-amber-3"><LucideTriangleAlert class="h-3.5 w-3.5" />{{ __('Yellow: after the project end') }}</span>
      </div>
      <div class="overflow-hidden rounded-lg border">
        <div class="flex h-10 w-full bg-surface-gray-2 text-sm text-ink-gray-6">
          <div class="flex w-56 shrink-0 items-center border-r px-3">{{ __('Supplier') }}</div>
          <div ref="headScroller" class="min-w-0 flex-1 overflow-hidden">
            <div class="grid h-10 min-w-full" :style="gridStyle">
              <div
                v-for="m in months"
                :key="m.key"
                class="flex items-center px-3 capitalize"
                :class="m.after ? 'bg-surface-amber-1 text-ink-amber-3' : ''"
                :title="m.after ? __('After the project end') : ''"
              >
                {{ m.label }}
              </div>
            </div>
          </div>
          <div class="flex w-44 shrink-0 items-center border-l px-3 sm:w-52">{{ __('Totals') }}</div>
        </div>

        <div class="max-h-[60vh] overflow-y-auto border-t">
          <div class="flex w-full">
            <!-- esquerda -->
            <div class="w-56 shrink-0 border-r">
              <div
                v-for="(line, i) in data.lines"
                :key="line.name"
                class="relative flex h-[7.5rem] flex-col justify-between px-3 py-2"
                :class="i ? 'border-t' : ''"
              >
                <div class="flex items-start justify-between gap-1">
                  <div class="min-w-0">
                    <div class="truncate text-base-medium text-ink-gray-9">{{ line.supplier }}</div>
                    <Badge
                      v-if="line.tag_name"
                      class="mt-1"
                      :label="line.tag_name"
                      :theme="tagTheme(line.finance_tag)"
                      variant="subtle"
                    />
                  </div>
                  <div class="flex shrink-0">
                    <Button size="sm" variant="ghost" icon="lucide-pencil" :tooltip="__('Edit supplier')" @click="openEditLine(line)" />
                    <Button size="sm" variant="ghost" icon="lucide-trash-2" @click="removeLine(line)" />
                  </div>
                </div>
                <div class="flex items-center gap-1">
                  <Button
                    v-if="line.description"
                    size="sm"
                    variant="ghost"
                    :tooltip="__('Description')"
                    @click="openDesc = openDesc === line.name ? '' : line.name"
                  >
                    <LucideChevronDown class="h-4 w-4 transition-transform" :class="openDesc === line.name ? '' : '-rotate-90'" />
                  </Button>
                  <Button size="sm" variant="ghost" icon="lucide-copy" :tooltip="__('Copy')" @click="copyLine(line)" />
                  <Button size="sm" variant="ghost" :tooltip="__('Send by WhatsApp')" @click="openSend(line)">
                    <WhatsAppIcon class="h-4 w-4" />
                  </Button>
                  <Button
                    v-if="line.supplier_phone"
                    size="sm"
                    variant="ghost"
                    icon="lucide-message-circle"
                    :tooltip="__('Chat on WhatsApp')"
                    @click="chatWith(line)"
                  />
                  <Button
                    v-if="line.supplier_contact"
                    size="sm"
                    variant="ghost"
                    icon="lucide-link"
                    :tooltip="__('Linked to Contacts')"
                    @click="router.push({ name: 'Contact', params: { contactId: line.supplier_contact } })"
                  />
                </div>
                <div
                  v-if="openDesc === line.name"
                  class="absolute left-2 right-2 top-[5.25rem] z-10 max-h-40 overflow-y-auto whitespace-pre-wrap rounded-md border bg-surface-white p-2 text-xs text-ink-gray-8 shadow-lg"
                >
                  {{ line.description }}
                </div>
              </div>
            </div>

            <!-- meio: ocupa o espaço que sobrar; 4 parcelas por vez, o resto rola -->
            <div ref="scroller" class="min-w-0 flex-1 overflow-x-auto" @scroll="syncHead">
              <div
                v-for="(line, i) in data.lines"
                :key="line.name"
                class="grid h-[7.5rem] min-w-full"
                :class="i ? 'border-t' : ''"
                :style="gridStyle"
              >
                <div v-for="(p, j) in cellsOf(line)" :key="j" class="px-2 py-2" :class="months[j]?.after ? 'bg-surface-amber-1' : ''">
                  <div
                    v-if="p"
                    class="h-full rounded-md border p-2"
                    :class="cellClass(line, p)"
                  >
                    <div class="flex items-center justify-between gap-1 text-xs" :class="isRed(line, p) ? 'text-ink-red-4' : afterEnd(p) && !p.paid ? 'text-ink-amber-3' : 'text-ink-gray-5'">
                      <span>{{ day(p.due_date) }} · {{ p.number }}/{{ line.installments.length }}</span>
                      <span v-if="afterEnd(p)" :title="__('Due after the project end date')">
                        <LucideTriangleAlert class="h-3.5 w-3.5 text-ink-amber-3" />
                      </span>
                    </div>
                    <div class="text-base-medium text-ink-gray-9">
                      {{ money(p.paid ? p.paid_value : p.expected_value) }}
                    </div>
                    <div v-if="line.mode === 'Variable' && !p.paid" class="text-xs" :class="spent(line, p.number) > p.expected_value ? 'text-ink-red-4' : 'text-ink-gray-6'">
                      {{ __('Spent') }}: {{ money(spent(line, p.number)) }}
                    </div>
                    <div v-if="p.paid" class="text-xs text-ink-green-3">
                      {{ __('Paid On') }} {{ day(p.paid_on) }}
                    </div>
                    <Button
                      v-if="line.mode === 'Variable'"
                      class="mt-1 w-full"
                      size="sm"
                      :variant="p.paid ? 'ghost' : 'subtle'"
                      :label="`${__('Payments')} (${entriesOf(line, p.number).length})`"
                      @click="openMonth(line, p)"
                    />
                    <Button
                      v-else-if="!p.paid"
                      class="mt-1 w-full"
                      size="sm"
                      variant="subtle"
                      :label="__('Register payment')"
                      @click="openPay(line, p)"
                    />
                    <Button
                      v-else
                      class="mt-1 w-full"
                      size="sm"
                      variant="ghost"
                      :label="__('Undo payment')"
                      @click="undo(line, p)"
                    />
                  </div>
                </div>
              </div>
            </div>

            <!-- direita: totais sempre visíveis -->
            <div class="w-44 shrink-0 border-l sm:w-52">
              <div
                v-for="(line, i) in data.lines"
                :key="line.name"
                class="flex h-[7.5rem] flex-col justify-center gap-1.5 px-3 py-2"
                :class="i ? 'border-t' : ''"
              >
                <div class="flex items-baseline justify-between gap-2">
                  <span class="text-xs text-ink-gray-5">{{ __('Total') }}</span>
                  <span class="text-base-semibold" :class="over(line) ? 'text-ink-red-4' : 'text-ink-gray-9'">{{ money(line.total) }}</span>
                </div>
                <div class="flex items-baseline justify-between gap-2">
                  <span class="text-xs text-ink-gray-5">{{ __('Paid') }}</span>
                  <span class="text-base-semibold" :class="over(line) ? 'text-ink-red-4' : 'text-ink-green-3'">{{ money(spentTotal(line)) }}</span>
                </div>
                <div
                  class="flex items-baseline justify-between gap-2 rounded-md px-1.5 py-1"
                  :class="alertReason(line) ? 'bg-surface-red-2' : 'bg-surface-gray-2'"
                  :title="alertReason(line)"
                >
                  <span class="text-xs-medium" :class="alertReason(line) ? 'text-ink-red-4' : 'text-ink-gray-7'">{{ __('Remaining') }}</span>
                  <span class="text-lg-semibold" :class="alertReason(line) ? 'text-ink-red-4' : 'text-ink-gray-9'">{{ money(line.remaining) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      </div>
      </div>
    </section>

    <!-- Arquivos dos pagamentos: Financeiro > Parcela N - MM-AAAA -->
    <section v-if="files?.folders?.length">
      <div class="mb-2 flex items-center justify-between">
        <h3 class="text-lg-semibold text-ink-gray-9">{{ __('Finance') }} · {{ __('Payment files') }}</h3>
        <a :href="zipUrl()" class="text-sm text-ink-gray-7 underline">{{ __('Download all (ZIP)') }}</a>
      </div>
      <div class="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
        <div v-for="f in files.folders" :key="f.line + f.number" class="rounded-lg border p-3">
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-1.5 text-base-medium text-ink-gray-9">
              <LucideFolder class="h-4 w-4" /> {{ f.label }}
            </div>
            <a :href="zipUrl(f)" class="text-xs text-ink-gray-6 underline">ZIP</a>
          </div>
          <div class="mt-1 text-xs text-ink-gray-5">{{ f.supplier }}</div>
          <a
            v-for="x in f.files"
            :key="x.name"
            :href="`/api/method/crm.panda.files.download?file=${encodeURIComponent(x.name)}`"
            class="mt-1 flex items-center gap-1.5 truncate text-sm text-ink-gray-8 hover:underline"
          >
            <LucideFileText class="h-4 w-4 shrink-0" />
            <span class="truncate">{{ x.file_name }}</span>
            <span v-if="x.undone" class="shrink-0 text-xs text-ink-red-4">({{ __('undone') }})</span>
          </a>
          <div v-for="x in f.files.filter((y) => badges[y.name])" :key="'b' + x.name" class="mt-0.5 flex items-center gap-1.5 text-xs">
            <Badge
              :label="{ Copied: __('Copied'), Pending: __('Pending'), Failed: __('Failed') }[badges[x.name].status]"
              :theme="{ Copied: 'green', Pending: 'orange', Failed: 'red' }[badges[x.name].status]"
              variant="subtle"
            />
            <span class="truncate text-ink-gray-5">Drive · {{ x.file_name }}</span>
            <Button v-if="badges[x.name].status === 'Failed' && badges[x.name].error" size="sm" variant="ghost" :label="__('Try again')" :title="badges[x.name].error" @click="retryCopy(badges[x.name].copy)" />
          </div>
        </div>
      </div>
    </section>
  </div>

  <!-- Diálogo: etiqueta -->
  <Dialog v-model:open="tagDialog" :size="'md'">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pb-4 pt-5 sm:px-6">
        <h3 class="mb-4 text-2xl-semibold text-ink-gray-9">
          {{ tagForm.name ? __('Edit tag') : __('New tag') }}
        </h3>
        <div class="flex flex-col gap-3">
          <FormControl v-model="tagForm.tag_name" :label="__('Tag Name')" type="text" />
          <MoneyInput v-model="tagForm.value" :label="__('Tag value')" />
          <FormControl v-model="tagForm.color" :label="__('Color')" type="select" :options="colors" />
        </div>
        <ErrorMessage v-if="error" class="mt-3" :message="error" />
      </div>
      <div class="flex flex-row-reverse gap-2 px-4 pb-6 pt-3 sm:px-6">
        <Button variant="solid" :label="__('Save')" :loading="busy" @click="saveTag" />
        <Button :label="__('Cancel')" @click="tagDialog = false" />
      </div>
    </template>
  </Dialog>


  <!-- Diálogo: enviar pedido de nota por WhatsApp -->
  <Dialog v-model:open="sendDialog" :size="'lg'">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pb-4 pt-5 sm:px-6">
        <h3 class="mb-4 text-2xl-semibold text-ink-gray-9">{{ __('Send by WhatsApp') }} — {{ sendLine?.supplier }}</h3>
        <div class="flex flex-col gap-3">
          <FormControl v-model="sendPhone" :label="__('WhatsApp (with country code)')" type="text" />
          <div>
            <FormControl v-model="sendEmail" :label="__('Email to receive the invoice')" type="text" placeholder="nome@empresa.com" list="panda-emails" />
            <datalist id="panda-emails"><option v-for="e in sendEmails" :key="e" :value="e" /></datalist>
          </div>
          <FormControl v-model="sendMsg" :label="__('Message')" type="textarea" :rows="10" />
          <p class="text-xs text-ink-gray-5">{{ __('The message is sent from inside the program, through the connected WhatsApp.') }}</p>
        </div>
      </div>
      <div class="flex flex-row-reverse gap-2 px-4 pb-6 pt-3 sm:px-6">
        <Button variant="solid" :loading="sending" :label="__('Send')" @click="doSend" />
        <Button :label="__('Cancel')" @click="sendDialog = false" />
      </div>
    </template>
  </Dialog>

  <!-- Diálogo: nova linha de pagamento -->
  <Dialog v-model:open="lineDialog" :size="'xl'">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pb-4 pt-5 sm:px-6">
        <h3 class="mb-4 text-2xl-semibold text-ink-gray-9">
          {{ editingName ? __('Edit supplier') : __('New payment line') }}
        </h3>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div class="sm:col-span-2">
            <FormControl v-model="lineForm.supplier" :label="__('Supplier') + ' *'" type="text" />
          </div>
          <FormControl
            v-model="lineForm.supplier_phone"
            :label="__('WhatsApp')"
            type="text"
            placeholder="(48) 99999-9999"
            @blur="lineForm.supplier_phone = fmtTel(lineForm.supplier_phone)"
          />
          <FormControl v-model="lineForm.supplier_email" :label="__('Email')" type="text" placeholder="nome@empresa.com" />
          <FormControl v-model="lineForm.supplier_document" :label="__('CPF/CNPJ')" type="text" />
          <div class="flex items-end">
            <Button class="w-full" :label="__('Pick from contacts')" iconLeft="lucide-users" @click="togglePicker" />
          </div>
          <div v-if="pickerOpen" class="rounded-md border p-2 sm:col-span-2">
            <FormControl v-model="pickerQ" type="text" :placeholder="__('Search by name, number or email')" @update:modelValue="searchPicker" />
            <div class="mt-2 max-h-48 overflow-y-auto">
              <div v-if="!pickerRows.length" class="px-2 py-3 text-center text-xs text-ink-gray-5">{{ __('No contacts found') }}</div>
              <button
                v-for="c in pickerRows"
                :key="c.name"
                type="button"
                class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left hover:bg-surface-gray-2"
                @click="pickContact(c)"
              >
                <Avatar :image="c.image" :label="c.full_name" size="md" />
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-sm text-ink-gray-9">{{ c.full_name }}</span>
                  <span class="block truncate text-xs text-ink-gray-5">{{ [c.phone_br, c.email].filter(Boolean).join(' · ') || __('No phone or email') }}</span>
                </span>
              </button>
            </div>
          </div>
          <p v-if="lineForm.supplier_contact" class="flex items-center gap-1 text-xs text-ink-green-3 sm:col-span-2">
            <LucideLink class="h-3.5 w-3.5" /> {{ __('Linked to Contacts') }}
          </p>
          <p v-else class="text-xs text-ink-gray-5 sm:col-span-2">
            {{ __('If you fill in a WhatsApp or email, the supplier is linked to Contacts (or created there automatically).') }}
          </p>
          <div class="sm:col-span-2">
            <FormControl v-model="lineForm.description" :label="__('Description')" type="textarea" :rows="3" />
          </div>
          <FormControl
            v-model="lineForm.finance_tag"
            :label="__('Finance Tag')"
            type="select"
            :options="tagOptions"
          />
          <FormControl
            v-model="lineForm.mode"
            :label="__('Amount Mode')"
            type="select"
            :options="modeOptions"
          />
          <MoneyInput v-model="lineForm.amount" :label="__('Amount')" />
          <div v-if="lineForm.mode !== 'Variable' && lineForm.mode !== 'Single'">
            <FormControl v-model="lineForm.installments_count" :label="__('Installments')" type="number" />
            <p v-if="maxParcelas" class="mt-1 text-xs" :class="Number(lineForm.installments_count) > maxParcelas ? 'text-ink-amber-3' : 'text-ink-gray-5'">
              {{ __('The project ends in') }} {{ monthLabel(endDate) }}: {{ __('at most') }} {{ maxParcelas }} {{ __('installments from this first due date') }}
            </p>
          </div>
          <div v-else-if="lineForm.mode === 'Single'" class="self-end pb-1 text-sm text-ink-gray-6">
            {{ __('A single payment with the full amount.') }}
          </div>
          <div v-else class="text-sm text-ink-gray-6 sm:col-span-2">
            {{ __('The total is divided by the months from the first due date to the project end. Each month you add the real payments (several suppliers allowed).') }}
          </div>
          <div>
            <div class="mb-1.5 text-xs text-ink-gray-5">{{ __('First Due Date') }}</div>
            <DatePicker :value="lineForm.first_due_date" :format="'DD/MM/YYYY'" @change="(v) => (lineForm.first_due_date = v)" />
          </div>
        </div>
        <div v-if="editingName" class="mt-3 text-sm text-ink-gray-6">
          {{ __('Paid installments are kept; the pending ones are recalculated.') }}
        </div>
        <div v-if="preview" class="mt-4 rounded-lg bg-surface-gray-2 p-3 text-sm text-ink-gray-8">
          {{ previewText }}
        </div>
        <ErrorMessage v-if="error" class="mt-3" :message="error" />
      </div>
      <div class="flex flex-row-reverse gap-2 px-4 pb-6 pt-3 sm:px-6">
        <Button variant="solid" :label="__('Save')" :loading="busy" @click="saveLine" />
        <Button :label="__('Cancel')" @click="lineDialog = false" />
      </div>
    </template>
  </Dialog>

  <!-- Diálogo: pagamentos do mês (valor variável) -->
  <Dialog v-model:open="monthDialog" :size="'xl'">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pt-5 sm:px-6">
        <h3 class="mb-1 text-2xl-semibold text-ink-gray-9">{{ monthLine?.supplier }} — {{ day(monthParcela?.due_date) }}</h3>
        <div class="mb-3 text-sm text-ink-gray-6">
          {{ __('Monthly budget') }}: {{ money(monthParcela?.expected_value) }} · {{ __('Spent') }}: {{ money(monthSpent) }}
        </div>
        <div class="max-h-[55vh] overflow-y-auto pb-4">
          <div v-for="e in monthEntries" :key="e.name" class="flex items-center justify-between gap-2 border-b py-1.5 text-sm">
            <div class="min-w-0">
              <div class="truncate text-ink-gray-9">{{ e.supplier }}</div>
              <div class="text-xs text-ink-gray-5">{{ day(e.paid_on) }}<span v-if="e.file"> · PDF</span></div>
            </div>
            <div class="flex shrink-0 items-center gap-2">
              <span class="text-base-medium">{{ money(e.value) }}</span>
              <Button v-if="!monthParcela?.paid" size="sm" variant="ghost" icon="lucide-trash-2" @click="removeEntry(e)" />
            </div>
          </div>
          <div v-if="!monthEntries.length" class="py-2 text-sm text-ink-gray-4">{{ __('No payments in this month yet') }}</div>

          <div v-if="!monthParcela?.paid" class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <FormControl v-model="entryForm.supplier" :label="__('Supplier')" type="text" />
            <MoneyInput v-model="entryForm.value" :label="__('Paid Value')" />
            <div>
              <div class="mb-1.5 text-xs text-ink-gray-5">{{ __('Paid On') }}</div>
              <DatePicker :value="entryForm.paid_on" :format="'DD/MM/YYYY'" @change="(v) => (entryForm.paid_on = v)" />
            </div>
            <div />
            <div>
              <div class="mb-1.5 text-xs text-ink-gray-5">{{ __('Payment receipt') }}</div>
              <input ref="entryComp" type="file" accept=".pdf,.jpg,.jpeg,.png" class="block w-full text-sm" />
            </div>
            <div>
              <div class="mb-1.5 text-xs text-ink-gray-5">{{ __('Invoice (NF)') }}</div>
              <input ref="entryNf" type="file" accept=".pdf,.jpg,.jpeg,.png" class="block w-full text-sm" />
            </div>
            <div class="sm:col-span-2">
              <Button variant="solid" :label="__('Add payment')" :loading="busy" @click="addEntry" />
            </div>
          </div>
          <ErrorMessage v-if="error" class="mt-3" :message="error" />
        </div>
      </div>
      <div class="flex flex-row-reverse gap-2 border-t px-4 pb-6 pt-3 sm:px-6">
        <Button v-if="!monthParcela?.paid" variant="solid" :label="__('Close month')" :loading="busy" @click="closeMonth" />
        <Button v-else :label="__('Reopen month')" :loading="busy" @click="reopenMonth" />
        <Button :label="__('Close')" @click="monthDialog = false" />
      </div>
    </template>
  </Dialog>

  <!-- Diálogo: registrar pagamento (corpo rola; rodapé sempre visível) -->
  <Dialog v-model:open="payDialog" :size="'xl'">
    <template #body>
      <div class="bg-surface-elevation-1 px-4 pt-5 sm:px-6">
        <h3 class="mb-4 text-2xl-semibold text-ink-gray-9">
          {{ __('Register payment') }} — {{ payForm.supplier }} ({{ payForm.number }})
        </h3>
        <div class="max-h-[55vh] overflow-y-auto pb-4">
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <MoneyInput v-model="payForm.paid_value" :label="__('Paid Value')" />
            <div>
              <div class="mb-1.5 text-xs text-ink-gray-5">{{ __('Paid On') }}</div>
              <DatePicker :value="payForm.paid_on" :format="'DD/MM/YYYY'" @change="(v) => (payForm.paid_on = v)" />
            </div>
          </div>
          <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <div class="mb-1.5 text-xs text-ink-gray-5">{{ __('Payment receipt') }}</div>
              <input type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" class="block w-full text-sm" @change="(e) => (payFiles.comprovante = e.target.files[0] || null)" />
            </div>
            <div>
              <div class="mb-1.5 text-xs text-ink-gray-5">{{ __('Invoice (NF)') }}</div>
              <input type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" class="block w-full text-sm" @change="(e) => (payFiles.nota_fiscal = e.target.files[0] || null)" />
            </div>
            <div class="text-xs text-ink-gray-5 sm:col-span-2">
              {{ __('PDF, JPG or PNG. Both are merged into a single PDF (receipt first). WebP and HEIC are not accepted.') }}
            </div>
          </div>
          <div v-if="payPreview && payDiffers" class="mt-4">
            <div class="mb-2 text-sm text-ink-gray-6">
              {{ __('The value differs from the expected one. The remaining installments will be readjusted:') }}
            </div>
            <table class="w-full text-sm">
              <thead class="text-left text-ink-gray-5">
                <tr>
                  <th class="py-1">#</th>
                  <th class="py-1">{{ __('Due Date') }}</th>
                  <th class="py-1 text-right">{{ __('Before') }}</th>
                  <th class="py-1 text-right">{{ __('After') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in payPreview.installments.filter((i) => !i.paid)" :key="r.number" class="border-t">
                  <td class="py-1">{{ r.number }}</td>
                  <td class="py-1">{{ day(r.due_date) }}</td>
                  <td class="py-1 text-right">{{ money(r.before) }}</td>
                  <td class="py-1 text-right">{{ money(r.after) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <ErrorMessage v-if="error" class="mt-3" :message="error" />
        </div>
      </div>
      <div class="flex flex-row-reverse gap-2 border-t px-4 pb-6 pt-3 sm:px-6">
        <Button variant="solid" :label="__('Confirm')" :loading="busy" @click="confirmPay" />
        <Button :label="__('Cancel')" @click="payDialog = false" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import MoneyInput from '@/components/Controls/MoneyInput.vue'
import { call, toast, DatePicker, Avatar } from 'frappe-ui'
import { getFormat } from '@/utils'
import WhatsAppIcon from '@/components/Icons/WhatsAppIcon.vue'
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({ deal: { type: String, required: true } })

// recolher/expandir (cada secao separada; lembra a escolha neste navegador)
const CHAVE_FECHADO = 'pp_finance_fechado'
function lerFechado() {
  try {
    return JSON.parse(localStorage.getItem(CHAVE_FECHADO) || '{}') || {}
  } catch (e) {
    return {}
  }
}
const fechado = reactive({ tags: false, cron: false, ...lerFechado() })
function alternar(k) {
  fechado[k] = !fechado[k]
  try {
    localStorage.setItem(CHAVE_FECHADO, JSON.stringify({ tags: fechado.tags, cron: fechado.cron }))
  } catch (e) {}
}

const abrindoPasta = ref(false)
async function abrirPasta() {
  abrindoPasta.value = true
  try {
    const r = await call('crm.panda.drive.pasta_projeto', { deal: props.deal })
    window.open(r.url, '_blank', 'noopener')
  } catch (e) {
    toast.error(msg(e))
  } finally {
    abrindoPasta.value = false
  }
}

const data = ref(null)
const scroller = ref(null)
const headScroller = ref(null)
const VISIBLE = 4
const dateFormat = getFormat('', '', true, false, false)
const busy = ref(false)
const error = ref('')

const colors = ['gray', 'blue', 'green', 'pink', 'orange', 'amber', 'yellow', 'cyan', 'teal', 'violet', 'purple'].map((c) => ({ label: c, value: c }))
const modeOptions = computed(() => [
  { label: __('Single payment (full amount)'), value: 'Single' },
  { label: __('Total split into installments'), value: 'Line Total' },
  { label: __('Amount of each installment'), value: 'Per Installment' },
  { label: __('Variable value (by project month)'), value: 'Variable' },
])
const tagOptions = computed(() => [
  { label: __('No tag'), value: '' },
  ...(data.value?.tags || []).map((t) => ({ label: t.tag_name, value: t.name })),
])

const cards = computed(() => {
  const s = data.value?.summary || {}
  return [
    { label: __('Project value'), value: s.project_value },
    { label: __('Total'), value: s.total },
    { label: __('Paid'), value: s.paid },
    { label: __('Remaining'), value: s.remaining },
  ]
})

const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const money = (v) => brl.format(Number(v || 0))
const day = (d) => (d ? d.split('-').reverse().join('/') : '')

const files = ref(null)
const badges = ref({})
async function retryCopy(c) {
  try {
    await call('crm.panda.drive.retry', { name: c })
    load()
  } catch (e) {
    toast.error(msg(e))
  }
}
const zipUrl = (f) =>
  `/api/method/crm.panda.files.download_zip?deal=${encodeURIComponent(props.deal)}` +
  (f ? `&line=${encodeURIComponent(f.line)}&number=${f.number}` : '')

async function load() {
  call('crm.panda.files.get_files', { deal: props.deal }).then((r) => (files.value = r)).catch(() => {})
  call('crm.panda.drive.get_badges', { deal: props.deal }).then((r) => (badges.value = r || {})).catch(() => {})
  data.value = await call('crm.panda.finance.get_finance', { deal: props.deal })
  await nextTick()
  scrollToPending()
}

// colunas = meses do projeto (do inicio ate o fim; se algum pagamento passar do fim, a coluna fica amarela)
const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
const mkey = (d) => (d ? String(d).slice(0, 7) : '')
const monthLabel = (d) => (d ? `${MESES[Number(String(d).slice(5, 7)) - 1]}/${String(d).slice(0, 4)}` : '')
const months = computed(() => {
  const lines = data.value?.lines || []
  const dues = lines.flatMap((l) => l.installments.map((p) => mkey(p.due_date))).filter(Boolean)
  const start = [mkey(data.value?.summary?.start_date), ...dues].filter(Boolean).sort()[0]
  const fim = [mkey(endDate.value), ...dues].filter(Boolean).sort().pop()
  if (!start || !fim) return []
  const out = []
  let [y, m] = start.split('-').map(Number)
  for (let i = 0; i < 120; i++) {
    const key = `${y}-${String(m).padStart(2, '0')}`
    out.push({ key, label: monthLabel(key + '-01'), after: !!(endDate.value && key > mkey(endDate.value)) })
    if (key >= fim) break
    m += 1
    if (m > 12) ((m = 1), (y += 1))
  }
  return out
})
const maxInstallments = computed(() => Math.max(1, months.value.length))
const cellsOf = (line) => months.value.map((m) => line.installments.find((p) => mkey(p.due_date) === m.key) || null)
const maxParcelas = computed(() => {
  if (!endDate.value || !lineForm.first_due_date) return 0
  const [y1, m1] = mkey(lineForm.first_due_date).split('-').map(Number)
  const [y2, m2] = mkey(endDate.value).split('-').map(Number)
  return Math.max(0, (y2 - y1) * 12 + m2 - m1 + 1)
})
// 4 parcelas ocupam a largura disponível (mín. 9,5rem cada); o resto rola. Acompanha o tamanho da tela.
const gridStyle = computed(() => ({
  gridAutoFlow: 'column',
  gridAutoColumns: `minmax(9.5rem, ${100 / VISIBLE}%)`,
  gridTemplateRows: 'auto',
}))
const parcela = (line, n) => line.installments.find((p) => p.number === n)
// Alertas do total da linha (tudo em vermelho):
// - gastou mais que o total; - falta pagar R$ 150 ou menos; - restam só os 3 últimos meses a pagar.
const LOW_REMAINING = 150
const spentTotal = (line) => Number(line.paid_total || 0) + (line.entries || []).filter((e) => !line.installments.find((p) => p.number === e.number)?.paid).reduce((a, e) => a + Number(e.value || 0), 0)
const over = (line) => spentTotal(line) > Number(line.total || 0) + 0.004
const alertReason = (line) => {
  const rest = Number(line.remaining || 0)
  const pend = line.installments.filter((p) => !p.paid).length
  if (over(line)) return __('Spent above the total')
  if (rest > 0 && rest <= LOW_REMAINING) return __('Only a small amount left to pay')
  if (pend > 0 && pend <= 3) return __('Last 3 months to pay')
  return ''
}
const endDate = computed(() => data.value?.summary?.end_date || null)
const afterEnd = (p) => !!(endDate.value && p.due_date && p.due_date > endDate.value)
const lastThree = (line, p) => p.number > line.installments.length - 3
const isRed = (line, p) => !p.paid && lastThree(line, p) && !afterEnd(p)
const cellClass = (line, p) =>
  p.paid
    ? 'border-outline-green-2 bg-surface-green-1'
    : afterEnd(p)
      ? 'border-2 border-outline-amber-2 bg-surface-amber-1'
      : isRed(line, p)
        ? 'border-outline-red-2 bg-surface-red-1'
        : isLate(p)
          ? 'border-outline-amber-2 bg-surface-amber-1'
          : ''
const isLate = (p) => !p.paid && p.due_date && new Date(p.due_date) < new Date(new Date().toDateString())

// parcelas já pagas deslizam para a esquerda: começa na primeira coluna com algo pendente
function syncHead() {
  if (headScroller.value && scroller.value) headScroller.value.scrollLeft = scroller.value.scrollLeft
}

function scrollToPending() {
  const el = scroller.value
  if (!el) return
  let first = maxInstallments.value
  for (const l of data.value.lines) {
    const i = cellsOf(l).findIndex((p) => p && !p.paid)
    if (i !== -1) first = Math.min(first, i)
  }
  const w = el.scrollWidth / maxInstallments.value
  el.scrollLeft = first >= maxInstallments.value ? el.scrollWidth : first * w
  syncHead()
}

// etiqueta vermelha = ultrapassou o valor da etiqueta (cor exclusiva desse aviso)
const tagOver = (t) => Number(t.value) > 0 && Math.round(Number(t.used) * 100) > Math.round(Number(t.value) * 100)
const tagTheme = (id) => {
  const t = data.value?.tags?.find((x) => x.name === id)
  if (!t) return 'gray'
  return tagOver(t) ? 'red' : t.color
}
load()

function msg(e) {
  return e?.messages?.[0] || e?.message || String(e)
}

async function run(fn) {
  busy.value = true
  error.value = ''
  try {
    await fn()
    return true
  } catch (e) {
    error.value = msg(e)
    return false
  } finally {
    busy.value = false
  }
}

// ---- etiquetas
const tagDialog = ref(false)
const tagForm = reactive({ name: '', tag_name: '', value: 0, color: 'gray' })
function openTag(tag) {
  Object.assign(tagForm, tag ? { name: tag.name, tag_name: tag.tag_name, value: tag.value, color: tag.color } : { name: '', tag_name: '', value: 0, color: 'gray' })
  error.value = ''
  tagDialog.value = true
}
async function saveTag() {
  const ok = await run(() => call('crm.panda.finance.save_tag', { deal: props.deal, ...tagForm, name: tagForm.name || null }))
  if (ok) {
    tagDialog.value = false
    load()
  }
}
async function removeTag(tag) {
  try {
    await call('crm.panda.finance.delete_tag', { name: tag.name })
    load()
  } catch (e) {
    toast.error(msg(e))
  }
}


// ---- descrição, copiar e enviar por WhatsApp
const openDesc = ref('')
const pickerOpen = ref(false)
const pickerQ = ref('')
const pickerRows = ref([])
let pickerTimer
async function searchPicker() {
  clearTimeout(pickerTimer)
  pickerTimer = setTimeout(async () => {
    try {
      pickerRows.value = await call('crm.panda.contatos.buscar', { q: pickerQ.value })
    } catch {
      pickerRows.value = []
    }
  }, 250)
}
function togglePicker() {
  pickerOpen.value = !pickerOpen.value
  if (pickerOpen.value) {
    pickerQ.value = ''
    searchPicker()
  }
}
// preenche so o que o contato tem (so telefone -> so telefone; telefone e e-mail -> os dois)
function pickContact(c) {
  if (!lineForm.supplier) lineForm.supplier = c.full_name
  if (c.phone_br || c.phone) lineForm.supplier_phone = c.phone_br || c.phone
  if (c.email) lineForm.supplier_email = c.email
  lineForm.supplier_contact = c.name
  pickerOpen.value = false
}
// telefone brasileiro na tela: (48) 99654-5728
function fmtTel(v) {
  let d = String(v || '').replace(/\D/g, '')
  if (d.startsWith('55') && d.length > 11) d = d.slice(2)
  if (d.length === 11) return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`
  if (d.length === 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
  return v || ''
}
async function chatWith(line) {
  try {
    const conv = await call('crm.panda.chat.open_whatsapp', { number: line.supplier_phone, title: line.supplier, deal: props.deal })
    router.push({ name: 'WhatsApp', query: { conversa: conv } })
  } catch (e) {
    toast.error(msg(e))
  }
}
const router = useRouter()
const nextOpen = (line) => [...line.installments].sort((a, b) => a.number - b.number).find((p) => !p.paid)
function lineText(line) {
  const p = nextOpen(line)
  return [line.supplier, p ? money(p.expected_value) : '', line.description || ''].filter(Boolean).join('\n')
}
async function copyLine(line) {
  try {
    await navigator.clipboard.writeText(buildMsg(line, data.value.invoice_email))
    toast.success(__('Copied'))
  } catch {
    toast.error(__('Could not copy'))
  }
}
const sendDialog = ref(false)
const sendLine = ref(null)
const sendEmail = ref('')
const sendPhone = ref('')
const sendMsg = ref('')
const sendEmails = ref([])
const chosenEmail = computed(() => (sendEmail.value || '').trim())
function saudacao() {
  const h = new Date().getHours()
  return h < 12 ? 'Bom dia' : h < 18 ? 'Boa tarde' : 'Boa noite'
}
function buildMsg(line = sendLine.value, email = chosenEmail.value) {
  return (
    `${saudacao()},\n\nO próximo pagamento do projeto ${data.value.deal_name}, você já pode tirar a nota.\n\n\n` +
    lineText(line) +
    `\n\nAguardo a nota enviada para o e-mail ${email || '…'}.`
  )
}
async function openSend(line) {
  sendLine.value = line
  sendPhone.value = fmtTel(line.supplier_phone || '')
  let o = { saved: data.value.invoice_email || '', accounts: [] }
  try {
    o = await call('crm.panda.finance.get_send_options', { deal: props.deal })
  } catch {}
  sendEmails.value = [...new Set([o.saved, ...o.accounts].filter(Boolean))]
  sendEmail.value = o.saved || ''
  sendMsg.value = buildMsg()
  sendDialog.value = true
}
watch(sendEmail, () => {
  if (sendDialog.value) sendMsg.value = buildMsg()
})
const sending = ref(false)
async function doSend() {
  if (!chosenEmail.value) return toast.error(__('Choose the email for the invoice'))
  sending.value = true
  try {
    await call('crm.panda.finance.send_whatsapp', {
      deal: props.deal,
      phone: sendPhone.value,
      text: sendMsg.value,
      email: chosenEmail.value,
    })
    data.value.invoice_email = chosenEmail.value
    toast.success(__('Message sent'))
    sendDialog.value = false
  } catch (e) {
    toast.error(msg(e))
  } finally {
    sending.value = false
  }
}

// ---- linha
const lineDialog = ref(false)
const lineForm = reactive({ supplier: '', description: '', supplier_phone: '', supplier_email: '', supplier_document: '', supplier_contact: '', finance_tag: '', mode: 'Line Total', amount: '', installments_count: 1, first_due_date: '' })
const preview = ref(null)
const editingName = ref('')
function openLine() {
  editingName.value = ''
  Object.assign(lineForm, { supplier: '', description: '', supplier_phone: '', supplier_email: '', supplier_document: '', supplier_contact: '', finance_tag: '', mode: 'Line Total', amount: '', installments_count: 1, first_due_date: new Date().toISOString().slice(0, 10) })
  preview.value = null
  error.value = ''
  lineDialog.value = true
  pickerOpen.value = false
}
let timer
watch(lineForm, () => {
  clearTimeout(timer)
  timer = setTimeout(async () => {
    if (!lineForm.amount || !lineForm.installments_count || !lineForm.first_due_date) return (preview.value = null)
    try {
      preview.value = await call('crm.panda.finance.preview_line', {
        amount: lineForm.amount,
        mode: lineForm.mode === 'Single' ? 'Line Total' : lineForm.mode,
        installments_count: lineForm.mode === 'Single' ? 1 : lineForm.installments_count,
        first_due_date: lineForm.first_due_date,
        deal: props.deal,
      })
    } catch {
      preview.value = null
    }
  }, 250)
})
const previewText = computed(() => {
  const p = preview.value
  if (!p) return ''
  const n = p.installments.length
  const first = p.installments[0].expected_value
  const last = p.installments[n - 1].expected_value
  const each = first === last ? money(first) : `${money(first)} (${__('last')}: ${money(last)})`
  return `${n} ${__('installments of')} ${each} = ${__('total')} ${money(p.total)}`
})
// "Pagamento unico" e o modo total da linha com 1 parcela
const modeArgs = () => (lineForm.mode === 'Single' ? { mode: 'Line Total', installments_count: 1 } : {})
async function saveLine() {
  const ok = await run(() =>
    editingName.value
      ? call('crm.panda.finance.update_line_full', { name: editingName.value, ...lineForm, ...modeArgs(), finance_tag: lineForm.finance_tag || null })
      : call('crm.panda.finance.create_line', { deal: props.deal, ...lineForm, ...modeArgs(), finance_tag: lineForm.finance_tag || null }),
  )
  if (ok) {
    lineDialog.value = false
    load()
  }
}
async function removeLine(line) {
  try {
    await call('crm.panda.finance.delete_line', { name: line.name })
    load()
  } catch (e) {
    toast.error(msg(e))
  }
}

// ---- editar fornecedor (edição completa, reaproveita o diálogo da linha)
function openEditLine(line) {
  Object.assign(lineForm, {
    supplier: line.supplier,
    description: line.description || '',
    supplier_phone: line.supplier_phone_br || line.supplier_phone || '',
    supplier_email: line.supplier_email || '',
    supplier_document: line.supplier_document || '',
    supplier_contact: line.supplier_contact || '',
    finance_tag: line.finance_tag || '',
    mode: line.mode,
    amount: line.amount,
    installments_count: line.installments_count,
    ...(line.mode === 'Line Total' && Number(line.installments_count) === 1 ? { mode: 'Single' } : {}),
    first_due_date: line.first_due_date || line.installments[0]?.due_date || '',
  })
  editingName.value = line.name
  preview.value = null
  error.value = ''
  lineDialog.value = true
  pickerOpen.value = false
}

// ---- valor variável: pagamentos do mês
const spent = (line, n) => entriesOf(line, n).reduce((a, e) => a + Number(e.value || 0), 0)
const entriesOf = (line, n) => (line.entries || []).filter((e) => e.number === n)
const monthDialog = ref(false)
const monthLineName = ref('')
const monthNumber = ref(0)
const monthLine = computed(() => data.value?.lines.find((l) => l.name === monthLineName.value))
const monthParcela = computed(() => monthLine.value?.installments.find((p) => p.number === monthNumber.value))
const monthEntries = computed(() => (monthLine.value ? entriesOf(monthLine.value, monthNumber.value) : []))
const monthSpent = computed(() => monthEntries.value.reduce((a, e) => a + Number(e.value || 0), 0))
const entryForm = reactive({ supplier: '', value: 0, paid_on: '' })
const entryComp = ref(null)
const entryNf = ref(null)
function openMonth(line, p) {
  monthLineName.value = line.name
  monthNumber.value = p.number
  Object.assign(entryForm, { supplier: '', value: 0, paid_on: new Date().toISOString().slice(0, 10) })
  error.value = ''
  monthDialog.value = true
}
async function postForm(method, fd) {
  const r = await fetch(`/api/method/${method}`, { method: 'POST', headers: { 'X-Frappe-CSRF-Token': window.csrf_token }, body: fd })
  if (!r.ok) {
    let m = __('Error')
    try {
      const j = await r.json()
      m = (j._server_messages && JSON.parse(JSON.parse(j._server_messages)[0]).message) || j.exc_type || m
    } catch {}
    throw new Error(m.replace(/<[^>]+>/g, ''))
  }
}
async function addEntry() {
  const fd = new FormData()
  fd.append('line', monthLineName.value)
  fd.append('number', monthNumber.value)
  fd.append('supplier', entryForm.supplier)
  fd.append('value', entryForm.value)
  fd.append('paid_on', entryForm.paid_on)
  if (entryComp.value?.files[0]) fd.append('comprovante', entryComp.value.files[0])
  if (entryNf.value?.files[0]) fd.append('nota_fiscal', entryNf.value.files[0])
  const ok = await run(() => postForm('crm.panda.files.add_entry', fd))
  if (ok) {
    Object.assign(entryForm, { supplier: '', value: 0 })
    if (entryComp.value) entryComp.value.value = ''
    if (entryNf.value) entryNf.value.value = ''
    await load()
  }
}
async function removeEntry(e) {
  const ok = await run(() => call('crm.panda.files.delete_entry', { line: monthLineName.value, entry: e.name }))
  if (ok) load()
}
async function closeMonth() {
  const ok = await run(() => call('crm.panda.files.close_month', { line: monthLineName.value, number: monthNumber.value }))
  if (ok) {
    monthDialog.value = false
    load()
  }
}
async function reopenMonth() {
  const ok = await run(() => call('crm.panda.finance.undo_payment', { line: monthLineName.value, number: monthNumber.value }))
  if (ok) load()
}

// ---- pagamento
const payDialog = ref(false)
const payForm = reactive({ line: '', supplier: '', number: 0, expected: 0, paid_value: 0, paid_on: '' })
const payPreview = ref(null)
const payDiffers = computed(() => Math.round(Number(payForm.paid_value) * 100) !== Math.round(Number(payForm.expected) * 100))
function openPay(line, p) {
  Object.assign(payForm, { line: line.name, supplier: line.supplier, number: p.number, expected: p.expected_value, paid_value: p.expected_value, paid_on: new Date().toISOString().slice(0, 10) })
  payPreview.value = null
  payFiles.comprovante = null
  payFiles.nota_fiscal = null
  error.value = ''
  payDialog.value = true
}
watch(
  () => payForm.paid_value,
  async () => {
    if (!payDialog.value || !(Number(payForm.paid_value) > 0)) return (payPreview.value = null)
    try {
      payPreview.value = await call('crm.panda.finance.preview_payment', { line: payForm.line, number: payForm.number, paid_value: payForm.paid_value })
    } catch {
      payPreview.value = null
    }
  },
)
const payFiles = reactive({ comprovante: null, nota_fiscal: null })
async function confirmPay() {
  const fd = new FormData()
  fd.append('line', payForm.line)
  fd.append('number', payForm.number)
  fd.append('paid_value', payForm.paid_value)
  fd.append('paid_on', payForm.paid_on)
  if (payFiles.comprovante) fd.append('comprovante', payFiles.comprovante)
  if (payFiles.nota_fiscal) fd.append('nota_fiscal', payFiles.nota_fiscal)
  const ok = await run(async () => {
    const r = await fetch('/api/method/crm.panda.files.register_with_files', {
      method: 'POST',
      headers: { 'X-Frappe-CSRF-Token': window.csrf_token },
      body: fd,
    })
    if (!r.ok) {
      let m = __('Error')
      try {
        const j = await r.json()
        m = (j._server_messages && JSON.parse(JSON.parse(j._server_messages)[0]).message) || j.exc_type || m
      } catch {}
      throw new Error(m.replace(/<[^>]+>/g, ''))
    }
  })
  if (ok) {
    payDialog.value = false
    load()
  }
}
async function undo(line, p) {
  try {
    await call('crm.panda.finance.undo_payment', { line: line.name, number: p.number })
    load()
  } catch (e) {
    toast.error(msg(e))
  }
}
</script>
