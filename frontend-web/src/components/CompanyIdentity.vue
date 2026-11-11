<script setup>
import { RouterLink } from 'vue-router'
import { COMPANY, callCostNote } from '@/lib/constants'

const phoneCost = callCostNote(COMPANY.phoneDisplay)
</script>

<template>
  <!-- Identificação permanente do prestador (DL 7/2004, art. 10.º): rodapé e Informação legal. -->
  <address class="company-identity">
    <strong>{{ COMPANY.legalName }}</strong
    ><br />
    Sociedade unipessoal por quotas<br />
    Sede: {{ COMPANY.address }}, <span class="nowrap">{{ COMPANY.postal }}</span
    >, {{ COMPANY.municipality }}<br />
    Matrícula na {{ COMPANY.registry }} e <span class="nowrap">NIPC {{ COMPANY.nif }}</span
    ><br />
    <template v-if="COMPANY.shareCapital">
      Capital social <span class="nowrap">{{ COMPANY.shareCapital }}</span
      ><br />
    </template>
    Telefone <a class="nowrap" :href="`tel:${COMPANY.phoneTel}`">{{ COMPANY.phoneDisplay }}</a>
    <template v-if="phoneCost"> ({{ phoneCost }})</template><br />
    <template v-if="COMPANY.email">
      Email <a :href="`mailto:${COMPANY.email}`">{{ COMPANY.email }}</a
      ><br />
    </template>
    Contacto electrónico: <RouterLink to="/contacto">formulário de contacto</RouterLink>
  </address>
</template>

<style scoped>
.company-identity {
  font-style: normal;
}

/* O código postal, o NIPC e o telefone não se partem a meio. */
.nowrap {
  white-space: nowrap;
}

/* Ligações no meio do texto: só a cor não as distingue no rodapé escuro. */
.company-identity a {
  text-decoration: underline;
  text-underline-offset: 2px;
}
</style>
