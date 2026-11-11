<script setup>
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import AppErrorBoundary from '@/components/AppErrorBoundary.vue'
import { useCart } from '@/composables/useCart'
import { useCategories } from '@/composables/useCategories'
import { useCookieBanner } from '@/composables/useCookieBanner'
import { useCatalog } from '@/composables/useCatalog'
import { captureEvent } from '@/lib/posthog'
import { prefetchRoute } from '@/router'
import { COMPANY, COMPLAINTS_BOOK_URL, whatsappUrl } from '@/lib/constants'
import { cartSummaryText } from '@/lib/quoteLines'
import WhatsAppFab from '@/components/WhatsAppFab.vue'

const CookieBanner = defineAsyncComponent(() => import('@/components/CookieBanner.vue'))

const isMenuOpen = ref(false)
const route = useRoute()
const router = useRouter()
// A pesquisa do cabeçalho (RP-07): nas larguras em que cabe, em vez da ligação «Pesquisar». Na página de pesquisa mostra o que se procura.
const headerQuery = ref('')
watch(
  () => (route.name === 'search' ? String(route.query.q || '') : ''),
  (q) => (headerQuery.value = q),
  { immediate: true },
)
const submitHeaderSearch = () => {
  const q = headerQuery.value.trim()
  router.push({ name: 'search', query: q ? { q } : {} })
}
// As categorias carregam aqui, uma só vez, para o início e o catálogo.
const { load: loadCategories } = useCategories()
const cartSummary = ref({ lines: 0, units: 0 })
const cart = useCart()
const cookieBanner = useCookieBanner()

// O contador do pedido conta artigos (linhas), não unidades (RP-17, FE-07); as unidades ficam no nome e na dica.
const cartLabel = computed(() =>
  cartSummary.value.lines
    ? `Pedido de orçamento: ${cartSummaryText(cartSummary.value)}`
    : 'Pedido de orçamento (vazio)',
)

const refreshCartCount = () => {
  cartSummary.value = cart.summary()
}

const menuBtn = ref(null)

const closeMenu = () => {
  isMenuOpen.value = false
}

// Esc com o menu aberto devolve o foco ao botão do menu: o menu fica `display: none` e o foco cairia no `body` (A11Y-10).
const onEscape = (e) => {
  if (e.key !== 'Escape') return
  const wasOpen = isMenuOpen.value
  closeMenu()
  if (wasOpen) menuBtn.value?.focus()
}

// Depois de mudar de página o foco vai para o <h1> da nova, que o leitor de ecrã lê (A11Y-10). A página monta e carrega os dados
// depois da navegação, por isso espera-se pelo <h1>. Só quando o caminho muda: a pesquisa troca a query ao escrever.
let stopFocusWatch = null
const focusNewPage = (to, from) => {
  if (stopFocusWatch) stopFocusWatch()
  if (!from.name || to.path === from.path || to.hash) return
  const main = document.getElementById('main-content')
  const previous = main?.querySelector('h1') // o da página que sai: ainda lá está quando a navegação termina
  let timer = null
  const observer = new MutationObserver(() => tryFocus())
  const stop = () => {
    observer.disconnect()
    clearTimeout(timer)
    stopFocusWatch = null
  }
  const tryFocus = () => {
    const h1 = main?.querySelector('h1')
    if (!h1 || h1 === previous) return
    stop()
    if (
      document.activeElement?.matches?.('input, textarea, select') &&
      main.contains(document.activeElement)
    )
      return
    h1.setAttribute('tabindex', '-1')
    h1.focus({ preventScroll: true })
  }
  stopFocusWatch = stop
  timer = setTimeout(stop, 4000)
  if (main) observer.observe(main, { childList: true, subtree: true })
  tryFocus()
}
const removeAfterEach = router.afterEach((to, from) => focusNewPage(to, from))

// Tocar fora do menu aberto fecha-o (FE-17). O caminho do evento (e não `e.target.closest`): o ícone do botão troca
// de `<path>` ao abrir, o Vue já o tinha substituído quando este ouvinte corre, e o alvo solto não tem ascendentes.
const onOutsideClick = (e) => {
  if (!isMenuOpen.value) return
  const inside = e
    .composedPath()
    .some((el) => el.classList?.contains('main-nav') || el.classList?.contains('menu-btn'))
  if (!inside) closeMenu()
}

// Cada clique numa ligação do WhatsApp conta (RP-10), do botão flutuante ou de qualquer página: mostra que páginas levam as
// pessoas a escrever. Só com consentimento (captureEvent não faz nada sem ele).
const onWhatsAppClick = (e) => {
  const link = e.composedPath().find((el) => el.matches?.('a[href^="https://wa.me/"]'))
  if (link) {
    captureEvent('whatsapp_click', {
      page: window.location.pathname,
      button: link.classList.contains('whatsapp-fab') ? 'flutuante' : 'ligação',
    })
  }
}

onMounted(async () => {
  void useCatalog().loadMeta()
  // O pedido aparece no cabeçalho logo, sem esperar pelas categorias.
  refreshCartCount()
  window.addEventListener('storage', refreshCartCount)
  window.addEventListener('diomika-cart-updated', refreshCartCount)
  window.addEventListener('keydown', onEscape)
  window.addEventListener('click', onOutsideClick)
  window.addEventListener('click', onWhatsAppClick)
  try {
    await loadCategories()
  } catch {
    /* o início e o catálogo mostram o estado */
  }
})

onUnmounted(() => {
  removeAfterEach()
  stopFocusWatch?.()
  window.removeEventListener('storage', refreshCartCount)
  window.removeEventListener('diomika-cart-updated', refreshCartCount)
  window.removeEventListener('keydown', onEscape)
  window.removeEventListener('click', onOutsideClick)
  window.removeEventListener('click', onWhatsAppClick)
})
</script>

<template>
  <div class="app-container">
    <a href="#main-content" class="skip-link">Saltar para o conteúdo</a>
    <!-- Logo a seguir ao skip link: quem navega por teclado chega-lhe primeiro e o banner não tapa o foco mais abaixo (A11Y-01). -->
    <CookieBanner />

    <header class="app-header">
      <div class="header-inner">
        <RouterLink
          to="/"
          class="logo-link"
          aria-label="Diomika — página inicial"
          @click="closeMenu"
        >
          <img
            src="/brand/logo.svg"
            alt="Diomika"
            class="brand-logo"
            width="188"
            height="34"
            fetchpriority="high"
            decoding="async"
          />
        </RouterLink>

        <nav id="main-nav" class="main-nav" :class="{ open: isMenuOpen }" aria-label="Principal">
          <RouterLink
            to="/categorias"
            @click="closeMenu"
            @pointerenter="prefetchRoute('categories')"
            >Catálogo</RouterLink
          >
          <RouterLink to="/pesquisa" @click="closeMenu">Pesquisar</RouterLink>
          <RouterLink to="/sobre" @click="closeMenu">Sobre nós</RouterLink>
          <RouterLink to="/contacto" @click="closeMenu">Contacto</RouterLink>
        </nav>

        <div class="header-actions">
          <form
            class="header-search"
            role="search"
            aria-label="Pesquisa no cabeçalho"
            @submit.prevent="submitHeaderSearch"
          >
            <label class="visually-hidden" for="header-search">Pesquisar no catálogo</label>
            <input
              id="header-search"
              v-model="headerQuery"
              class="header-search__input"
              type="search"
              name="q"
              placeholder="Ex.: almofada, 45x45…"
              autocomplete="off"
              enterkeyhint="search"
            />
            <button class="header-search__btn" type="submit" aria-label="Pesquisar">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-3.5-3.5" />
              </svg>
            </button>
          </form>
          <!-- O pedido fica à vista em todas as larguras, fora do menu (FE-07): no telemóvel o menu está fechado. -->
          <RouterLink
            to="/carrinho"
            class="cart-link"
            :aria-label="cartLabel"
            :title="cartLabel"
            @click="closeMenu"
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <circle cx="9" cy="20" r="1.4" />
              <circle cx="18" cy="20" r="1.4" />
              <path d="M2 3h3l2.7 12.4a1.5 1.5 0 0 0 1.5 1.2h8.6a1.5 1.5 0 0 0 1.5-1.1L21 8H6.2" />
            </svg>
            <span class="cart-link__text" aria-hidden="true">Pedido de orçamento</span>
            <span v-if="cartSummary.lines > 0" class="cart-badge" aria-hidden="true">{{
              cartSummary.lines
            }}</span>
          </RouterLink>

          <button
            ref="menuBtn"
            type="button"
            class="menu-btn"
            :aria-label="isMenuOpen ? 'Fechar menu' : 'Abrir menu'"
            :aria-expanded="isMenuOpen"
            aria-controls="main-nav"
            @click="isMenuOpen = !isMenuOpen"
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              aria-hidden="true"
            >
              <path v-if="isMenuOpen" d="M6 6l12 12M18 6 6 18" />
              <path v-else d="M4 7h16M4 12h16M4 17h16" />
            </svg>
          </button>
        </div>
      </div>
    </header>

    <main id="main-content" class="app-main">
      <AppErrorBoundary>
        <RouterView v-slot="{ Component, route }">
          <!-- Sem <Transition>: com ele a página que sai ficava dois fotogramas ao lado da nova. Só uma entrada curta em CSS (PERF-04). -->
          <component :is="Component" :key="route.path" class="page-enter" />
        </RouterView>
      </AppErrorBoundary>
    </main>

    <footer class="app-footer">
      <div class="footer-inner">
        <div class="footer-grid">
          <div class="footer-brand">
            <img
              src="/brand/logo.svg"
              alt="Diomika"
              class="footer-logo"
              width="150"
              height="27"
              loading="lazy"
            />
            <p class="footer-tagline">Têxteis para o lar, com proposta à medida.</p>
            <!-- Identificação mínima do prestador (DL 7/2004, art. 10.º); a completa está em «Informação legal». -->
            <address class="footer-identity">
              <p>
                <strong>{{ COMPANY.legalName }}</strong> ·
                <span class="nowrap">NIPC {{ COMPANY.nif }}</span>
              </p>
              <p>
                {{ COMPANY.address }}, <span class="nowrap">{{ COMPANY.postal }}</span>
              </p>
            </address>
          </div>

          <nav class="footer-col" aria-labelledby="footer-shop">
            <h2 id="footer-shop" class="footer-title">Loja</h2>
            <ul>
              <li><RouterLink to="/categorias">Catálogo</RouterLink></li>
              <li><RouterLink to="/pesquisa">Pesquisar</RouterLink></li>
              <li><RouterLink to="/carrinho">Pedido de orçamento</RouterLink></li>
              <li><RouterLink to="/sobre">Sobre nós</RouterLink></li>
            </ul>
          </nav>

          <nav class="footer-col" aria-labelledby="footer-help">
            <h2 id="footer-help" class="footer-title">Ajuda</h2>
            <ul>
              <li><RouterLink to="/perguntas-frequentes">Perguntas frequentes</RouterLink></li>
              <li><RouterLink to="/condicoes-de-venda">Condições de venda</RouterLink></li>
              <li><RouterLink to="/privacidade">Privacidade</RouterLink></li>
              <li><RouterLink to="/cookies">Cookies</RouterLink></li>
              <li><RouterLink to="/termos">Informação legal</RouterLink></li>
              <!-- Permanente, em todas as páginas: retirar o consentimento tão fácil como dá-lo (LEGAL-07). -->
              <li>
                <button
                  type="button"
                  class="ph-no-capture"
                  @click="cookieBanner.open($event.currentTarget)"
                >
                  Preferências de cookies
                </button>
              </li>
            </ul>
          </nav>

          <div class="footer-col">
            <h2 class="footer-title">Fale connosco</h2>
            <ul>
              <li>
                <a class="nowrap" :href="`tel:${COMPANY.phoneTel}`">{{ COMPANY.phoneDisplay }}</a>
              </li>
              <li>
                <a :href="whatsappUrl()" target="_blank" rel="noopener">WhatsApp</a>
              </li>
              <li><RouterLink to="/contacto">Contacto</RouterLink></li>
            </ul>
          </div>
        </div>

        <div class="footer-bottom">
          <p>
            © {{ new Date().getFullYear() }} {{ COMPANY.legalName }}. Todos os direitos reservados.
          </p>
          <!-- Livro de Reclamações: sempre visível, em todas as páginas (DL 156/2005). -->
          <a
            class="complaints-book"
            :href="COMPLAINTS_BOOK_URL"
            target="_blank"
            rel="noopener noreferrer"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <span>Livro de Reclamações Eletrónico</span>
          </a>
        </div>
      </div>
    </footer>

    <WhatsAppFab />
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
  background: var(--color-header-bg);
  border-bottom: 1px solid var(--color-border);
  backdrop-filter: saturate(1.4) blur(8px);
}

.app-header::before,
.app-footer::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 4px;
  background: var(--brand-stripe);
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
  margin-left: auto;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
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

.header-search {
  display: none;
  align-items: center;
  position: relative;
}

.header-search__input {
  width: 15rem;
  min-height: 40px;
  padding: 0 2.5rem 0 0.8rem;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-ink);
  font: inherit;
  font-size: 0.95rem;
}

.header-search__input:focus-visible {
  border-color: var(--color-accent);
  outline: 2px solid var(--color-accent-glow);
}

.header-search__btn {
  position: absolute;
  right: 0.15rem;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-ink-soft);
  cursor: pointer;
}

.header-search__btn:hover {
  color: var(--color-accent);
}

/* Só onde cabe: abaixo disto fica a ligação «Pesquisar» do menu, que leva à página de pesquisa. */
@media (min-width: 1181px) {
  .header-search {
    display: flex;
  }

  .main-nav > a[href='/pesquisa'] {
    display: none;
  }
}

.cart-link {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 44px;
  min-height: 44px;
  padding: 0 0.8rem;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  color: var(--color-ink);
  font-size: 0.95rem;
  font-weight: 550;
  white-space: nowrap;
}

.cart-link:hover {
  border-color: var(--color-ink-soft);
  background: var(--color-surface);
  color: var(--color-ink);
}

.cart-link.router-link-active {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

/* O único uso do vermelho da marca: quantos artigos estão no pedido. */
.cart-badge {
  display: inline-grid;
  place-items: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: var(--radius-pill);
  background: #c4362f; /* 5,36:1 com o texto branco; o vermelho da marca dava 4,38:1 (A11Y-06) */
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
/* Claro e em colunas (marca · loja · ajuda · contacto): a faixa azul de contacto fica por cima sem chocar. */
.app-footer {
  position: relative;
  background: var(--color-footer-bg);
  color: var(--color-ink-soft);
  font-size: 0.95rem;
}

.footer-inner {
  max-width: calc(var(--content-max) + 2 * var(--page-pad));
  margin: 0 auto;
  padding: 3rem var(--page-pad) 1.5rem;
}

.footer-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) repeat(3, minmax(0, 1fr));
  gap: 2rem;
}

.footer-logo {
  display: block;
  width: 150px;
  height: auto;
}

.footer-tagline {
  max-width: 30ch;
  margin: 0.9rem 0 1rem;
  color: var(--color-ink);
}

.footer-identity {
  font-style: normal;
  color: var(--color-muted);
  font-size: 0.88rem;
}

.footer-identity p {
  margin: 0;
}

.footer-identity strong {
  color: var(--color-ink-soft);
  font-weight: 600;
}

.nowrap {
  white-space: nowrap;
}

.footer-title {
  margin: 0 0 0.75rem;
  color: var(--brand-blue-deep);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.footer-col ul {
  display: grid;
  gap: 0.1rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

/* Alvo de toque com mais de 24 px de altura (WCAG 2.5.8, FE-18). */
.footer-col a,
.footer-col button {
  display: inline-block;
  padding: 4px 0;
  border: 0;
  background: none;
  color: var(--color-ink-soft);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.footer-col a:hover,
.footer-col button:hover {
  color: var(--color-accent);
}

.footer-bottom {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem 1.5rem;
  margin-top: 2.5rem;
  /* À direita fica o botão fixo do WhatsApp: sem este espaço tapava o Livro de Reclamações. */
  padding: 1.25rem 72px 0 0;
  border-top: 1px solid var(--color-border-accent);
}

.footer-bottom p {
  margin: 0;
  color: var(--color-muted);
  font-size: 0.85rem;
}

.complaints-book {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.9rem;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-ink);
  font-size: 0.88rem;
  font-weight: 600;
  line-height: 1.25;
}

.complaints-book:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

@media (max-width: 900px) {
  .footer-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .footer-brand {
    grid-column: 1 / -1;
  }
}

@media (max-width: 480px) {
  .footer-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 1.5rem;
  }
}

/* ---------- Entrada de página ---------- */
/* Só opacidade e só 120 ms; a página nova monta logo, sem esperar que a antiga saia (PERF-04). */
.page-enter {
  animation: page-in 0.12s ease;
}

@keyframes page-in {
  from {
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .page-enter {
    animation: none;
  }
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

  /* Só o ícone e o contador: o texto fica no nome acessível. */
  .cart-link {
    justify-content: center;
    padding: 0 0.6rem;
  }

  .cart-link__text {
    display: none;
  }
}
</style>
