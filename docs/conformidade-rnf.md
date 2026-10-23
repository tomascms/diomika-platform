# Conformidade com os requisitos não funcionais

Medido a 2026-10-23, depois do deploy de `f314882` (loja) e `aa8a9b0` (API) (loja em `www.diomika.com`, API em `api.diomika.com`). Legenda:
✅ cumpre (medido) · 🟡 parcial · ❌ não cumpre · ⛔ impossível com orçamento 0 € · — não aplicável.

**Contexto que decide muita coisa:** a loja é B2B de pedidos de orçamento. Não há pagamentos,
cartões, cupões, frete, antifraude, checkout com dinheiro, ERP nem stock. A API corre numa única VM
e2-micro gratuita (1 GB de RAM, EUA) e a base de dados no Supabase Free (Irlanda).

## 1. Desempenho
| Requisito | Estado | Evidência |
|---|---|---|
| LCP ≤ 2,5 s (4G) | 🟡 | Em produção, ecrã de telemóvel, rede rápida: página inicial 0,64 s; produto nunca visitado 1,0–1,7 s (era 3,9 s — *preload* da imagem + 26 detalhes pré-aquecidos em Redis). **Não medido com 4G real.** |
| INP ≤ 200 ms | 🟡 | Interacções simples (menu, cores, quantidade), sem tarefas longas conhecidas; **não medido em campo**. |
| CLS ≤ 0,1 | ✅ | Era 0,9 (rodapé) e 0,151 (filtros da categoria). Agora 0,000 em início, categoria e produto no telemóvel; 0,044 na categoria em computador. |
| TTFB p95 < 200 ms | 🟡 | Via edge (o que o visitante usa): 153–196 ms (p95, a partir de Portugal). API directa na VM dos EUA: p50 ~300 ms ⛔ (geografia). |
| Timeout 2000 ms a terceiros | 🟡 | Sem frete/antifraude (—). Edge→API 2 s/8 s; Supabase 15 s (ligação 3 s); Turnstile 10 s; SMTP 30 s. |
| ≥ 500 RPS | ⛔ | Catálogo e páginas servidos pela Cloudflare (escala global). A origem (1 worker, 1 GB) não foi testada a 500 RPS e não os aguenta; limite de concorrência devolve 503 em vez de cair. |

## 2. Segurança e privacidade
| Requisito | Estado | Evidência |
|---|---|---|
| Só TLS 1.3 | ❌ | TLS 1.2 e 1.3 aceites. Mudança de 1 clique na Cloudflare (*Minimum TLS 1.3*); pode excluir browsers/proxies antigos — decisão do dono. |
| HSTS ≥ 31 536 000 s | ✅ | Loja 63 072 000 s + preload; API 31 536 000 s + preload. |
| AES-256 em repouso | ✅ | Supabase cifra disco em AES-256. Não há tokens de pagamento. |
| Cookies HttpOnly/Secure/SameSite | — | Não há cookies de sessão (loja sem login; backoffice com token bearer). |
| Sem dados pessoais em Local/SessionStorage | 🟡 | Loja ✅ desde `e8a9b85` (rascunho guarda só observações; limpa versões antigas). Backoffice ❌: token em `localStorage` com «manter sessão» — passar a `safeStorage` exige nova versão do backoffice. |
| PCI-DSS | — | Sem pagamentos. |
| RGPD | 🟡 | Consentimento opt-in/opt-out (PostHog só com aceitação) ✅; apagar dados por email (`POST /privacy/erase`, admin) ✅; logs com emails mascarados e segredos redigidos ✅; retenção automática ✅. Sem base de homologação (não existe staging). |
| Injecção / XSS | ✅ | Construtor PostgREST parametrizado; nomes de filtro validados; sem `v-html`; CSP sem `unsafe-*`. |
| Login 5 tentativas/min por IP (Redis) | ✅ | `3aabe6d`: 5/min por IP + 10/5 min por utilizador. Formulários: Turnstile + Redis + regra Cloudflare. |

## 3. Escalabilidade e disponibilidade
| Requisito | Estado | Evidência |
|---|---|---|
| 99,95 % de uptime | ⛔ | 1 VM. A loja e o catálogo continuam a abrir com a API em baixo (cache no edge até 7 dias); formulários não. |
| Multi-AZ com failover DNS | ⛔ | Exige 2.ª instância/serviço pago. |
| Auto-scaling (CPU 70 % / RAM 80 %) | ⛔ | Sem grupo de instâncias no plano gratuito. |
| 15 000 utilizadores / 2 000 pedidos/min | ⛔ | Navegação: Cloudflare aguenta. Pedidos: limitados pela VM gratuita. |

## 4. Usabilidade e acessibilidade
| Requisito | Estado | Evidência |
|---|---|---|
| WCAG 2.2 AA | 🟡 | Revisto: etiquetas, `alt`, nomes de botões, títulos, erros anunciados, `autocomplete`, link «Saltar para o conteúdo», foco visível global. **Sem auditoria formal completa** (contraste página a página, leitor de ecrã real). |
| ARIA + teclado no fluxo | 🟡 | Igual ao anterior; não foi feito teste completo só com teclado em todas as páginas. |
| 320 px a 3840 px | ✅ | Sem scroll horizontal a 320 px em início, catálogo, categoria, produto, pedido, contacto, pesquisa (produto corrigido em `e8a9b85`); a 3840 px conteúdo centrado (1320 px). |

## 5. Resiliência e recuperação
| Requisito | Estado | Evidência |
|---|---|---|
| Circuit breaker de frete | — | Sem frete. Equivalente: edge serve a última versão do catálogo se a API falhar. |
| Idempotency-Key | ✅ | Pedido de orçamento e contacto enviam `Idempotency-Key`; em produção o orçamento sem chave é rejeitado (teste `test_orcamento_requires_idempotency_in_production`). |
| RPO ≤ 5 min | ⛔ | Backup diário (RPO 24 h). Réplica/PITR exigem Supabase pago. Cópia fora da VM recusada pelo dono. |
| RTO < 30 min | 🟡 | Restauro testado (contagens iguais à produção). Recuo da API: imagem anterior em segundos; da loja: 1 clique. Rebuild completo da VM ~25–40 min. |

## 6. Manutenção e CI/CD
| Requisito | Estado | Evidência |
|---|---|---|
| Zero downtime | 🟡 | Loja ✅ (deploy atómico Pages). API ❌: ~10–20 s sem resposta ao trocar o contentor (catálogo segue servido pelo edge; formulários falham nesse intervalo). Blue-green numa e2-micro de 1 GB não cabe. |
| Cobertura ≥ 80 % | ❌ | 57 %. O CI passa a falhar abaixo de 56 % (`3aabe6d`); subir a 80 % exige ~2 000 linhas de testes. |
| Modularidade | 🟡 | Rotas / serviços / modelos separados; sem domínio de pagamentos. Não é Clean Architecture formal. |

## 7. Observabilidade
| Requisito | Estado | Evidência |
|---|---|---|
| Logs JSON estruturados | ✅ | `ts`, `level`, `service`, `env`, `logger`, `request_id` (`3aabe6d`). `print` só em erros fatais de arranque. |
| Correlation ID | 🟡 | `X-Request-Id` na API, nos logs e no Sentry. Não é propagado pelo edge nem para a BD/outbox. |
| `/metrics` Prometheus | ✅ | `3aabe6d`: pedidos por rota e classe de estado, tempo, memória, uptime; só localhost + chave ops/admin. |

## 8. Interoperabilidade
| Requisito | Estado | Evidência |
|---|---|---|
| OpenAPI 3 | ✅ | Gerado pelo FastAPI (3.1); desligado em produção por segurança (`docs_enabled`). |
| Pós-venda assíncrono por mensageria | 🟡 | Email enviado em fundo com *outbox* em caso de falha; sem RabbitMQ/Kafka (sem ERP/stock a integrar). |

## 9. SEO
| Requisito | Estado | Evidência |
|---|---|---|
| JSON-LD | 🟡 | `Product` (nome, descrição, marca, categoria, GTIN-13, imagem real), `BreadcrumbList`, `ItemList`, `Organization`. Sem `offers`/`price`/`AggregateRating`: a loja não tem preços públicos nem avaliações. |
| SSR / estático | 🟡 | 41 páginas pré-geradas no build (título, descrição, canonical, JSON-LD e conteúdo em `<noscript>`); o corpo visível é montado em JS. |

## O que falta e como
- **Decisão tua, 0 €:** TLS 1.3 obrigatório; token do backoffice em `safeStorage` (nova versão).
- **Trabalho, 0 €:** cobertura até 80 %; auditoria WCAG formal; propagar `X-Request-Id` pelo edge.
- **Só com custo:** multi-AZ, auto-scaling, 99,95 %, 500 RPS na origem, RPO 5 min, zero downtime na API.
