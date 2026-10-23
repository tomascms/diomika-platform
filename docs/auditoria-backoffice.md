# Auditoria do backoffice — 2026-10-23

Âmbito: app Electron (`backoffice-desktop/`, versão 1.2.1 → 1.3.0) e as rotas de admin da API.
Medições a partir de Portugal, contra produção (só leituras).

## Porque é lento: o chão de latência
Cada pedido faz PC → Cloudflare → VM nos EUA (~250 ms) e, se tocar na BD, VM → Supabase na
Irlanda (~150 ms **por consulta**). Medido: pedidos com cache ~260 ms; com BD 450–650 ms.
Com este chão (imposto pelo custo 0 €: VM gratuita só nos EUA), o que pesa são **pedidos em série**
e **consultas em série no servidor**. Foi aí que se cortou.

## Erros funcionais corrigidos
| # | Problema | Efeito para o cliente | Correcção |
|---|---|---|---|
| 1 | «Guardar rascunho» num modelo publicado forçava `visibilidade: false` no modelo, cores e EAN | Corrigir uma gralha tirava o produto da loja | Registo publicado mostra «Guardar alterações» e mantém-se visível |
| 2 | «Publicar» num modelo publicado escondia-o primeiro e só voltava a publicar no fim | O produto desaparecia da loja durante a gravação (5–10 s) | Fica visível durante a gravação |
| 3 | Mensagens, Pedidos e Encomendas carregavam uma vez por arranque (KeepAlive) | Contactos e pedidos novos só apareciam ao reiniciar a app | Recarregam ao voltar à vista e a cada 60 s (janela visível) |
| 4 | Listas mantidas em memória não sabiam de escritas | Depois de editar, a lista mostrava o nome/estado antigo | Contador de escritas: a lista recarrega em fundo se algo mudou |
| 5 | A lista em fundo lia a tabela da rota | Ao abrir um registo, a lista recarregava contra a tabela errada (+1 pedido) e ao voltar perdia os filtros | Tabela fixa por instância de lista |
| 6 | Redis sem persistência | Cada deploy da API terminava as sessões (voltar a entrar) | AOF num volume; a API limpa a cache do catálogo no arranque |

## Desempenho
| Acção | Antes | Depois | Como |
|---|---|---|---|
| Abrir um modelo | 2 vagas: bundle (~0,7–1 s) + cores, EAN, schema e 2 listas do aviso (~0,6 s) | 1 pedido (bundle com cores e EAN, consultas em paralelo no servidor) | `/admin/form` devolve `children`; aviso calculado dos painéis |
| Gravar um modelo com 10 cores + 10 EAN | ~22 escritas + 4 listas | Só as linhas novas/alteradas + 2 listas | Estado gravado por linha |
| Cada escrita no servidor | + inserção de auditoria síncrona (~150 ms) | Auditoria numa thread | `core/audit.py` |
| Dropdowns de categorias/modelos | 470 ms (BD) | Cache Redis, limpa a cada escrita | `relation_options` |
| Pré-visualização de imagens | Original (centenas de KB por cor) | Miniatura 480 px, recua para o original | `ImageField.vue` |
| Respostas do proxy | Sem compressão (19 KB na lista de produtos) | gzip/br (~2–3 KB) | `electron/main.cjs` |
| Voltar de um registo à lista | Recarregava (e perdia filtros) | 0 pedidos, filtros mantidos | Verificado no browser |

Medido no browser com a API actual: abrir modelo 1,4–1,6 s (sem o pedido extra em fundo);
voltar à lista 0 pedidos. Com a API nova publicada, abrir um modelo passa a 1 pedido.

## Segurança
- Links externos só `http(s)`/`mailto` (a app mostra conteúdo de clientes); a janela já não
  pode ser levada para outro site.
- CSP do renderer: `connect-src` limitado ao proxy local (antes aceitava qualquer `https:`);
  `img-src` sem `http:`.
- Já estava bem: `contextIsolation`, `sandbox`, sem `nodeIntegration`, proxy só com cabeçalhos
  permitidos, uma instância, sessões com expiração.

## Por fazer (recomendado)
- **Gravar o modelo de forma atómica**: hoje são vários pedidos (modelo → cores → EAN → publicar);
  uma falha a meio deixa parte gravada (a app avisa). Um endpoint único com transacção na BD
  resolve e reduz a gravação a 1 pedido.
- **Testes do backoffice**: o CI só faz o build; falta configuração de lint e testes de componentes.
- **Instalador assinado** (tira o aviso do Windows) — custo anual.
- **Dados**: o modelo «Protetor de Mesa» está visível mas a cor nº 1 não tem imagem (não aparece
  na loja até ter).
