<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, clearApiCaches } from '@/lib/api'
import { clearSession, isAuthenticated, storeSession } from '@/lib/settings'

const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const totpCode = ref('')
const remember = ref(true)
const mfaRequired = ref(false)
const mfaSetupMode = ref(false)
const mfaSecret = ref('')
const mfaUri = ref('')
const error = ref('')
const loading = ref(false)
const checking = ref(true)

const credentialsLocked = computed(() => mfaSetupMode.value || mfaRequired.value)

const submitLabel = computed(() => {
  if (loading.value) return 'A entrar…'
  if (mfaSetupMode.value) return 'Confirmar código e entrar'
  if (mfaRequired.value) return 'Confirmar código'
  return 'Entrar'
})

function destination() {
  const target = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  return target.startsWith('/') && !target.startsWith('/login')
    ? target
    : { name: 'workspace', params: { table: 'categories' } }
}

onMounted(async () => {
  // Já com sessão guardada → confirma-a e entra directamente.
  if (isAuthenticated()) {
    try {
      await api.me(true)
      await router.replace(destination())
      return
    } catch (e) {
      if (e?.status === 401) {
        clearApiCaches()
        clearSession()
      } else {
        // API em baixo ou sem rede: mantém a sessão; o painel mostra o estado da ligação.
        await router.replace(destination())
        return
      }
    }
  }
  checking.value = false
})

async function completeLogin(res) {
  if (!res?.access_token) throw new Error(res?.detail || 'Resposta de login inválida.')
  storeSession({
    token: res.access_token,
    user: { username: res.username, role: res.role },
    remember: remember.value,
  })
  clearApiCaches()
  await router.replace(destination())
}

function resetMfa() {
  mfaRequired.value = false
  mfaSetupMode.value = false
  mfaSecret.value = ''
  mfaUri.value = ''
  totpCode.value = ''
  error.value = ''
}

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const user = username.value.trim()
    const pass = password.value
    const code = totpCode.value.replace(/\s+/g, '')

    if (mfaSetupMode.value) {
      if (!code) {
        error.value = 'Introduza o código de 6 dígitos da aplicação de autenticação.'
        return
      }
      await api.mfaConfirm(user, pass, code)
      const res = await api.login(user, pass, code)
      await completeLogin(res)
      return
    }

    const res = await api.login(user, pass, mfaRequired.value ? code : undefined)
    if (res?.mfa_required) {
      mfaRequired.value = true
      return
    }
    if (res?.mfa_setup_required) {
      const setup = await api.mfaSetup(user, pass)
      mfaSetupMode.value = true
      mfaSecret.value = setup.secret || ''
      mfaUri.value = setup.otpauth_uri || ''
      totpCode.value = ''
      return
    }
    await completeLogin(res)
  } catch (e) {
    error.value = e?.status === 401
      ? 'Utilizador ou palavra-passe incorrectos.'
      : e?.message || 'Não foi possível entrar.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <main class="login-panel" aria-labelledby="login-title">
      <header class="login-head">
        <img class="mark" src="/mark.svg" alt="" width="34" height="41" />
        <div>
          <h1 id="login-title">Backoffice Diomika</h1>
          <p class="lead">Gestão do catálogo, orçamentos e encomendas.</p>
        </div>
      </header>

      <div v-if="checking" class="checking" role="status">
        <span class="spinner" aria-hidden="true" />
        A verificar a sessão…
      </div>

      <form v-else class="form" novalidate @submit.prevent="submit">
        <div class="field">
          <label class="field-label" for="login-user">Utilizador</label>
          <input
            id="login-user"
            v-model="username"
            class="input"
            type="text"
            autocomplete="username"
            autocapitalize="none"
            spellcheck="false"
            required
            autofocus
            :disabled="credentialsLocked"
          />
        </div>

        <div class="field">
          <label class="field-label" for="login-pass">Palavra-passe</label>
          <input
            id="login-pass"
            v-model="password"
            class="input"
            type="password"
            autocomplete="current-password"
            required
            :disabled="credentialsLocked"
          />
        </div>

        <section v-if="mfaSetupMode" class="mfa-setup" aria-label="Configurar verificação em dois passos">
          <p class="mfa-title">Active a verificação em dois passos</p>
          <p class="hint">
            Na Google Authenticator, Microsoft Authenticator ou Authy, adicione uma conta com esta chave e
            introduza o código de 6 dígitos que aparece.
          </p>
          <p v-if="mfaSecret" class="secret"><code>{{ mfaSecret }}</code></p>
          <details v-if="mfaUri" class="uri">
            <summary>Ligação otpauth</summary>
            <code>{{ mfaUri }}</code>
          </details>
        </section>

        <div v-if="mfaRequired || mfaSetupMode" class="field">
          <label class="field-label" for="login-totp">Código de verificação</label>
          <input
            id="login-totp"
            v-model="totpCode"
            class="input code-input"
            type="text"
            inputmode="numeric"
            autocomplete="one-time-code"
            maxlength="8"
            placeholder="000000"
            required
          />
        </div>

        <label v-if="!credentialsLocked" class="remember">
          <input v-model="remember" type="checkbox" />
          Manter sessão iniciada neste computador
        </label>

        <p v-if="error" class="err" role="alert">{{ error }}</p>

        <button type="submit" class="btn btn-primary btn-lg submit" :disabled="loading">
          {{ submitLabel }}
        </button>
        <button v-if="credentialsLocked" type="button" class="btn btn-ghost" @click="resetMfa">
          Usar outra conta
        </button>
      </form>
    </main>
    <p class="foot">Sessões terminam ao fim de 30 dias ou ao sair.</p>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 18px;
  padding: 32px 16px;
  background:
    linear-gradient(160deg, transparent 0 62%, var(--accent-soft) 62% 63%, transparent 63%),
    var(--bg);
}

.login-panel {
  width: min(400px, 100%);
  padding: 32px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

.login-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 26px;
}

.mark {
  flex: none;
}

h1 {
  font-size: 19px;
  font-stretch: 112%;
  font-weight: 680;
}

.lead {
  margin-top: 3px;
  font-size: 13.5px;
  color: var(--text-secondary);
}

.checking {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary);
}

.form {
  display: grid;
  gap: 16px;
}

.code-input {
  font-family: var(--font-mono);
  font-size: 18px;
  letter-spacing: 0.3em;
}

.remember {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
  color: var(--text-secondary);
  cursor: pointer;
}

.submit {
  width: 100%;
  margin-top: 4px;
}

.mfa-setup {
  display: grid;
  gap: 8px;
  padding: 14px;
  border-radius: var(--radius);
  background: var(--accent-soft);
}

.mfa-title {
  font-weight: 600;
  color: var(--accent);
}

.secret code {
  display: inline-block;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text-primary);
  font-size: 13px;
  letter-spacing: 0.08em;
  word-break: break-all;
  user-select: all;
}

.uri {
  font-size: 12px;
  color: var(--text-secondary);
}

.uri code {
  display: block;
  margin-top: 6px;
  word-break: break-all;
  user-select: all;
}

.foot {
  font-size: 12.5px;
  color: var(--text-muted);
}
</style>
