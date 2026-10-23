# Adicionar uma família de produto

**Categoria nova numa família que já existe** (ex.: «Almofadas de Natal»): faz-se no backoffice,
em Categorias → + Nova. Não precisa de código.

**Família nova** (ex.: «Mantas», com campos próprios): uma entrada num dicionário + deploy da API.
Não há tabelas novas nem SQL: todas as famílias partilham `product_models`,
`product_variants` e `product_model_colors`, separadas por `tipo_catalogo`.

## Passos
1. Em `backend-api/models/catalog_attributes.py`, acrescentar a `CATEGORY_ATTRIBUTE_SCHEMAS`:

   ```python
   "manta": {
       "label": "Mantas",
       "model_discriminator_field": "dimensoes",   # campo que distingue os produtos do modelo, ou None
       "product_readonly_on_edit": True,
       "apply_barcode_on_save": True,
       "storefront_mode": "variantes",             # "variantes" | "unico" | "assento"
       "storefront_picker": {"source": "products", "field": "dimensoes",
                             "label": "Dimensão", "format": "dimensions", "suffix": " cm"},
       "model_attributes": {
           "composicao": _COMPOSICAO_FIELD,
           "dimensoes": _DIMENSOES_MODEL_FIELD,
       },
       "variant_attributes": {
           "dimensoes": _DIMENSOES_VARIANT_FIELD,
       },
   },
   ```

   Tipos de campo: `enum` (com `options`/`labels`), `composition`, `dimension_list`,
   `dimension_single`, `string_list`, `string_single`, `string`. Copiar de uma família parecida
   é o caminho mais rápido (`guarda_chuva` é a mais simples; `almofada` tem filtros).
2. `cd backend-api && python -m pytest tests -q`
3. PR → CI verde → merge → Actions → *Deploy API* (ver [runbook](runbook.md)).
4. No backoffice: Categorias → + Nova → escolher a família nova. A loja e o backoffice leem os
   campos de `/catalogo/meta` e ajustam-se sozinhos.

## Opcional
- `frontend-web/src/lib/catalogMeta.js` tem uma cópia estática da metadata, usada só se a API
  não responder. Actualizá-la evita que a família nova desapareça da loja nesse caso.
- Se a família precisar de um seletor de encomenda diferente de medidas, o formulário de encomenda
  interna (`backoffice-desktop/src/views/OrderCreateView.vue`) só tem o modo especial `assento`.
