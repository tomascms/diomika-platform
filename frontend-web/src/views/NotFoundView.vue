<template>
  <div class="not-found page-shell">
    <div class="not-found-card surface-card surface-card--elevated">
      <p class="code">404</p>
      <h1>Página não encontrada</h1>
      <p>O endereço que procurou não existe ou foi movido.</p>
      <div class="actions">
        <RouterLink to="/" class="btn btn-primary">Voltar ao início</RouterLink>
        <RouterLink to="/contacto" class="btn btn-secondary">Contacto</RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  padding-top: 3rem;
  padding-bottom: 4rem;
}

.not-found-card {
  max-width: 440px;
  margin: 0 auto;
  padding: 2.5rem 2rem;
  text-align: center;
}

.code {
  margin: 0;
  font-size: 4rem;
  line-height: 1;
  font-weight: 700;
  color: var(--color-accent);
}

.not-found-card h1 {
  margin: 0.5rem 0;
  font-size: 1.65rem;
}

.not-found-card p {
  margin: 0 0 1.5rem;
  color: var(--color-muted);
  line-height: 1.5;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  justify-content: center;
}
</style>
