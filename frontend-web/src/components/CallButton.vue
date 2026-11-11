<script setup>
// O telefone como ligação `tel:`. O estilo do botão vem de quem o usa (`class`).
import { COMPANY } from '@/lib/constants'
</script>

<template>
  <a :href="`tel:${COMPANY.phoneTel}`"
    ><slot>{{ COMPANY.phoneDisplay }}</slot></a
  >
</template>
