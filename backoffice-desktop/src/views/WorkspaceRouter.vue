<script setup>
defineOptions({ name: 'WorkspaceRouter' })

import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useWorkspace } from '@/composables/useWorkspace'
import TableView from '@/views/TableView.vue'
import EncomendasView from '@/views/EncomendasView.vue'
import OrderDetailView from '@/views/OrderDetailView.vue'
import ContactView from '@/views/ContactView.vue'

const route = useRoute()
const { workspace } = useWorkspace()

const table = computed(() => route.params.table)
const uiMode = computed(() => workspace.value?.sidebar?.[table.value]?.ui_mode || 'table')

const component = computed(() => {
  if (uiMode.value === 'order_create') return EncomendasView
  if (uiMode.value === 'order_view') return OrderDetailView
  if (uiMode.value === 'conversation') return ContactView
  return TableView
})
</script>

<template>
  <KeepAlive :max="8">
    <component :is="component" :key="table" />
  </KeepAlive>
</template>
