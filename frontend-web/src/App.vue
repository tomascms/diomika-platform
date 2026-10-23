<script setup>
import { ref, onMounted, onUnmounted, defineAsyncComponent } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import AppErrorBoundary from '@/components/AppErrorBoundary.vue'
import { useCart } from '@/composables/useCart'
import { useCategories } from '@/composables/useCategories'
import { useCatalog } from '@/composables/useCatalog'
import { categoryProductsRoute } from '@/lib/catalogRoutes'
import { prefetchRoute } from '@/router'
import { COMPANY } from '@/lib/constants'
import WhatsAppFab from '@/components/WhatsAppFab.vue'

const CookieBanner = defineAsyncComponent(() => import('@/components/CookieBanner.vue'))

const isMenuOpen = ref(false)
const { categories, load: loadCategories } = useCategories()
const cartCount = ref(0)
const cart = useCart()

const pretty = (name) => {
  const t = String(name || '').trim()
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : ''
}

const refreshCartCount = () => {
  cartCount.value = cart.count()
}

const closeMenu = () => {
  isMenuOpen.value = false
}

const onEscape = (e) => {
  if (e.key === 'Escape') closeMenu()
}

onMounted(async () => {
  void useCatalog().loadMeta()
  try {
    await loadCategories()
  } catch {
    /* footer / home mostram o estado */
  }
  refreshCartCount()
  window.addEventListener('storage', refreshCartCount)
  window.addEventListener('diomika-cart-updated', refreshCartCount)
  window.addEventListener('keydown', onEscape)
})

onUnmounted(() => {
  window.removeEventListener('storage', refreshCartCount)
  window.removeEventListener('diomika-cart-updated', refreshCartCount)
  window.removeEventListener('keydown', onEscape)
})
</script>

<template>
  <div class="app-container">
    <a href="#main-content" class="skip-link">Saltar para o conteúdo</a>

    <header class="app-header">
      <div class="header-inner">
        <RouterLink to="/" class="logo-link" aria-label="Diomika — página inicial" @click="closeMenu">
          <img src="/brand/logo.svg" alt="Diomika" class="brand-logo" width="188" height="34" fetchpriority="high" decoding="async" />
        </RouterLink>

        <button
          type="button"
          class="menu-btn"
          :aria-label="isMenuOpen ? 'Fechar menu' : 'Abrir menu'"
          :aria-expanded="isMenuOpen"
          aria-controls="main-nav"
          @click="isMenuOpen = !isMenuOpen"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
            <path v-if="isMenuOpen" d="M6 6l12 12M18 6 6 18" />
            <path v-else d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>

        <nav id="main-nav" class="main-nav" :class="{ open: isMenuOpen }" aria-label="Principal">
          <RouterLink
            to="/categorias"
            @click="closeMenu"
            @pointerenter="prefetchRoute('categories')"
          >Catálogo</RouterLink>
          <RouterLink to="/pesquisa" @click="closeMenu">Pesquisar</RouterLink>
          <RouterLink to="/sobre" @click="closeMenu">Sobre nós</RouterLink>
          <RouterLink to="/contacto" @click="closeMenu">Contacto</RouterLink>
          <RouterLink
            to="/carrinho"
            class="nav-quote"
            @click="refreshCartCount(); closeMenu()"
          >
            Pedido de orçamento
            <span v-if="cartCount > 0" class="cart-badge" :aria-label="`${cartCount} artigos no pedido`">{{ cartCount }}</span>
          </RouterLink>
        </nav>
      </div>
    </header>

    <main id="main-content" class="app-main">
      <AppErrorBoundary>
        <RouterView v-slot="{ Component, route }">
          <Transition name="page-fade" mode="out-in">
            <component :is="Component" :key="route.path" />
          </Transition>
        </RouterView>
      </AppErrorBoundary>
    </main>

    <footer class="app-footer">
      <div class="footer-grid">
        <div class="footer-brand">
          <img src="/brand/logo.svg" alt="Diomika" width="160" height="29" loading="lazy" />
          <p>
            Têxteis para o lar, para revenda: almofadas, assentos, toalhas, aventais e mais.
            Pedido mínimo de 500&nbsp;€ + IVA.
          </p>
        </div>

        <div>
          <h2 class="footer-title">Catálogo</h2>
          <ul class="footer-links">
            <li v-for="cat in categories" :key="cat.id">
              <RouterLink :to="categoryProductsRoute(cat)">{{ pretty(cat.nome) }}</RouterLink>
            </li>
            <li v-if="!categories.length">
              <RouterLink to="/categorias">Ver categorias</RouterLink>
            </li>
          </ul>
        </div>

        <div>
          <h2 class="footer-title">Empresa</h2>
          <ul class="footer-links">
            <li><RouterLink to="/sobre">Sobre nós</RouterLink></li>
            <li><RouterLink to="/contacto">Contacto</RouterLink></li>
            <li><RouterLink to="/carrinho">Pedido de orçamento</RouterLink></li>
            <li><RouterLink to="/privacidade">Privacidade</RouterLink></li>
            <li><RouterLink to="/termos">Aviso legal</RouterLink></li>
            <li><RouterLink to="/cookies">Cookies</RouterLink></li>
          </ul>
        </div>

        <div>
          <h2 class="footer-title">Contacto</h2>
          <ul class="footer-links">
            <li><a :href="`tel:${COMPANY.phoneTel}`">{{ COMPANY.phoneDisplay }}</a></li>
            <li>{{ COMPANY.address }}<br />{{ COMPANY.postal }}</li>
            <li>NIF {{ COMPANY.nif }}</li>
          </ul>
        </div>
      </div>

      <div class="footer-bottom">
        <p>© {{ new Date().getFullYear() }} Diomika. Todos os direitos reservados.</p>
      </div>
    </footer>

    <WhatsAppFab />
    <CookieBanner />
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.skip-link {
  position: absolute;
  left: -9999px;
  top: 0;
  z-index: 2000;
  padding: 0.75rem 1rem;
  background: var(--color-surface);
  color: var(--color-ink-deep);
  font-weight: 600;
}

.skip-link:focus {
  left: 0;
}

/* ---------- Cabeçalho ---------- */
.app-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid var(--color-border);
  backdrop-filter: saturate(1.4) blur(8px);
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  max-width: calc(var(--content-max) + 2 * var(--page-pad));
  height: var(--header-h);
  margin: 0 auto;
  padding: 0 var(--page-pad);
}

.logo-link {
  display: inline-flex;
  flex-shrink: 0;
}

.brand-logo {
  width: min(188px, 48vw);
  height: auto;
}

.menu-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-ink);
  cursor: pointer;
}

.main-nav {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.main-nav > a {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 40px;
  padding: 0 0.8rem;
  border-radius: var(--radius-md);
  color: var(--color-ink-soft);
  font-size: 0.95rem;
  font-weight: 550;
}

.main-nav > a:hover {
  color: var(--color-ink-deep);
  background: var(--color-bg);
}

.main-nav > a.router-link-active {
  color: var(--color-accent);
}

.main-nav > a.router-link-active::after {
  content: '';
  position: absolute;
  left: 0.8rem;
  right: 0.8rem;
  bottom: -14px;
  height: 2px;
  background: var(--color-accent);
}

.main-nav > .nav-quote {
  margin-left: 0.5rem;
  border: 1px solid var(--color-border-strong);
  color: var(--color-ink);
}

.main-nav > .nav-quote:hover {
  border-color: var(--color-ink-soft);
  background: var(--color-surface);
}

.main-nav > .nav-quote.router-link-active::after {
  display: none;
}

/* O único uso do vermelho da marca: quantos artigos estão no pedido. */
.cart-badge {
  display: inline-grid;
  place-items: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: var(--radius-pill);
  background: var(--brand-red);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.app-main {
  flex: 1;
  /* Rodapé começa abaixo da dobra: sem isto saltava quando o conteúdo carregava (CLS 0.9). */
  min-height: 100vh;
  min-height: 100svh;
}

/* ---------- Rodapé ---------- */
.app-footer {
  background: var(--color-ink-deep);
  color: rgba(255, 255, 255, 0.72);
}

.footer-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) repeat(3, minmax(0, 1fr));
  gap: 2.5rem;
  max-width: calc(var(--content-max) + 2 * var(--page-pad));
  margin: 0 auto;
  padding: 3.5rem var(--page-pad) 2.5rem;
}

.footer-brand img {
  width: 160px;
  height: auto;
  margin-bottom: 1rem;
  filter: brightness(0) invert(1);
}

.footer-brand p {
  max-width: 36ch;
  margin: 0;
  font-size: 0.95rem;
}

.footer-title {
  margin: 0 0 0.9rem;
  color: #fff;
  font-size: 0.95rem;
  font-weight: 650;
  font-stretch: 112%;
  letter-spacing: 0.01em;
}

.footer-links {
  display: grid;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 0.95rem;
}

.footer-links a {
  color: rgba(255, 255, 255, 0.72);
}

.footer-links a:hover {
  color: #fff;
}

.footer-bottom {
  max-width: calc(var(--content-max) + 2 * var(--page-pad));
  margin: 0 auto;
  padding: 1.25rem var(--page-pad) 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.5);
}

.footer-bottom p {
  margin: 0;
}

/* ---------- Transição de página ---------- */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.14s ease;
}

.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}

/* ---------- Responsivo ---------- */
@media (max-width: 980px) {
  .menu-btn {
    display: inline-flex;
  }

  .main-nav {
    position: fixed;
    inset: var(--header-h) 0 auto 0;
    display: none;
    flex-direction: column;
    align-items: stretch;
    gap: 0;
    padding: 0.5rem var(--page-pad) 1rem;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    box-shadow: var(--shadow-md);
  }

  .main-nav.open {
    display: flex;
  }

  .main-nav > a {
    min-height: 48px;
    padding: 0 0.25rem;
    border-radius: 0;
    border-bottom: 1px solid var(--color-border);
    font-size: 1.05rem;
  }

  .main-nav > a.router-link-active::after {
    display: none;
  }

  .main-nav > .nav-quote {
    justify-content: center;
    margin: 0.75rem 0 0;
    border-radius: var(--radius-md);
  }

  .footer-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .footer-brand {
    grid-column: 1 / -1;
  }
}

@media (max-width: 560px) {
  .footer-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 2rem;
  }
}
</style>
