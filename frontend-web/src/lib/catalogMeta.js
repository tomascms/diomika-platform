/**
 * Esquema unificado: 3 tabelas físicas partilhadas por todas as categorias
 * (discriminadas por `tipo_catalogo`). Os nomes `model_table`/`product_table`/
 * `colors_table` dentro de `catalog_types` abaixo (e os que vêm de
 * GET /catalogo/meta) são "virtuais" — servem o backoffice para encaminhar
 * pedidos a /admin/crud/{tabela} — nunca uses esses campos para consultar o
 * Supabase diretamente a partir da loja; usa estas constantes.
 */
export const PHYSICAL_CATALOG_TABLES = {
  models: 'product_models',
  variants: 'product_variants',
  colors: 'product_model_colors',
}

/** Metadados do catálogo — fallback estático; em runtime a loja prefere GET /catalogo/meta. */
export const CATALOG_META = {
  "catalog_types": [
    {
      "tipo": "almofada",
      "label": "Almofadas",
      "model_table": "modelos_almofadas",
      "product_table": "almofada",
      "colors_table": "modelo_almofada_cores",
      "storefront_mode": "variantes",
      "storefront_filters": [
        {
          "field": "tipo",
          "label": "Tipo de Almofada",
          "options": [
            "decorativa",
            "dormir"
          ],
          "labels": {
            "decorativa": "Decorativa",
            "dormir": "Dormir"
          }
        }
      ],
      "storefront_picker": {
        "source": "products",
        "field": "dimensoes",
        "label": "Tamanho",
        "format": "dimensions",
        "suffix": " cm"
      },
      "storefront_specs": [
        {
          "field": "composicao",
          "label": "Composição",
          "widget": "composition",
          "enum_labels": {}
        }
      ],
      "storefront_badge": {
        "field": "tipo",
        "labels": {
          "decorativa": "Decorativa",
          "dormir": "Dormir"
        }
      },
      "order_picker_mode": "variantes",
      "product_select": "id, ean, barcode_url, visibilidade, dimensoes"
    },
    {
      "tipo": "assento",
      "label": "Assentos",
      "model_table": "modelos_assentos",
      "product_table": "assento",
      "colors_table": "modelo_assento_cores",
      "storefront_mode": "assento",
      "storefront_filters": [],
      "storefront_picker": {
        "source": "products",
        "field": "altura",
        "label": "Altura",
        "format": "plain"
      },
      "storefront_specs": [
        {
          "field": "material_forro",
          "label": "Material Forro",
          "widget": "text",
          "enum_labels": {}
        },
        {
          "field": "material_enchimento",
          "label": "Material Enchimento",
          "widget": "text",
          "enum_labels": {}
        }
      ],
      "storefront_badge": null,
      "order_picker_mode": "assento",
      "product_select": "id, ean, barcode_url, visibilidade, altura"
    },
    {
      "tipo": "guarda_chuva",
      "label": "Guarda-chuvas",
      "model_table": "modelos_guarda_chuvas",
      "product_table": "guarda_chuva",
      "colors_table": "modelo_guarda_chuva_cores",
      "storefront_mode": "unico",
      "storefront_filters": [],
      "storefront_picker": null,
      "storefront_specs": [],
      "storefront_badge": null,
      "order_picker_mode": "unico",
      "product_select": "id, ean, barcode_url, visibilidade"
    },
    {
      "tipo": "oculo",
      "label": "Óculos",
      "model_table": "modelos_oculos",
      "product_table": "oculo",
      "colors_table": "modelo_oculo_cores",
      "storefront_mode": "unico",
      "storefront_filters": [
        {
          "field": "tipo_oculo",
          "label": "Tipo",
          "options": [
            "sol",
            "leitura"
          ],
          "labels": {
            "sol": "Óculos de sol",
            "leitura": "Óculos de leitura"
          }
        }
      ],
      "storefront_picker": null,
      "storefront_specs": [],
      "storefront_badge": {
        "field": "tipo_oculo",
        "labels": {
          "sol": "Óculos de sol",
          "leitura": "Óculos de leitura"
        }
      },
      "order_picker_mode": "unico",
      "product_select": "id, ean, barcode_url, visibilidade"
    },
    {
      "tipo": "toalha_mesa",
      "label": "Toalhas de mesa",
      "model_table": "modelos_toalhas_mesa",
      "product_table": "toalha_mesa",
      "colors_table": "modelo_toalha_mesa_cores",
      "storefront_mode": "variantes",
      "storefront_filters": [
        {
          "field": "tipo_produto",
          "label": "Tipo",
          "options": [
            "toalha",
            "protetor"
          ],
          "labels": {
            "toalha": "Toalha de mesa",
            "protetor": "Protetor de mesa"
          }
        }
      ],
      "storefront_picker": {
        "source": "products",
        "field": "dimensoes",
        "label": "Dimensão",
        "format": "dimensions",
        "suffix": " cm"
      },
      "storefront_specs": [
        {
          "field": "composicao",
          "label": "Composicao",
          "widget": "composition",
          "enum_labels": {}
        }
      ],
      "storefront_badge": {
        "field": "tipo_produto",
        "labels": {
          "toalha": "Toalha de mesa",
          "protetor": "Protetor de mesa"
        }
      },
      "order_picker_mode": "variantes",
      "product_select": "id, ean, barcode_url, visibilidade, dimensoes"
    },
    {
      "tipo": "avental",
      "label": "Aventais",
      "model_table": "modelos_aventais",
      "product_table": "avental",
      "colors_table": "modelo_avental_cores",
      "storefront_mode": "unico",
      "storefront_filters": [],
      "storefront_picker": null,
      "storefront_specs": [
        {
          "field": "composicao",
          "label": "Composicao",
          "widget": "composition",
          "enum_labels": {}
        }
      ],
      "storefront_badge": null,
      "order_picker_mode": "unico",
      "product_select": "id, ean, barcode_url, visibilidade"
    },
    {
      "tipo": "luva",
      "label": "Luvas",
      "model_table": "modelos_luvas",
      "product_table": "luva",
      "colors_table": "modelo_luva_cores",
      "storefront_mode": "unico",
      "storefront_filters": [],
      "storefront_picker": null,
      "storefront_specs": [
        {
          "field": "composicao",
          "label": "Composicao",
          "widget": "composition",
          "enum_labels": {}
        }
      ],
      "storefront_badge": null,
      "order_picker_mode": "unico",
      "product_select": "id, ean, barcode_url, visibilidade"
    },
    {
      "tipo": "pega",
      "label": "Pegas",
      "model_table": "modelos_pegas",
      "product_table": "pega",
      "colors_table": "modelo_pega_cores",
      "storefront_mode": "unico",
      "storefront_filters": [],
      "storefront_picker": null,
      "storefront_specs": [
        {
          "field": "composicao",
          "label": "Composicao",
          "widget": "composition",
          "enum_labels": {}
        }
      ],
      "storefront_badge": null,
      "order_picker_mode": "unico",
      "product_select": "id, ean, barcode_url, visibilidade"
    },
    {
      "tipo": "pano_cozinha",
      "label": "Panos de cozinha",
      "model_table": "modelos_panos_cozinha",
      "product_table": "pano_cozinha",
      "colors_table": "modelo_pano_cozinha_cores",
      "storefront_mode": "variantes",
      "storefront_filters": [],
      "storefront_picker": {
        "source": "products",
        "field": "dimensoes",
        "label": "Dimensão",
        "format": "dimensions",
        "suffix": " cm"
      },
      "storefront_specs": [
        {
          "field": "composicao",
          "label": "Composicao",
          "widget": "composition",
          "enum_labels": {}
        }
      ],
      "storefront_badge": null,
      "order_picker_mode": "variantes",
      "product_select": "id, ean, barcode_url, visibilidade, dimensoes"
    },
    {
      "tipo": "protetor_colchao",
      "label": "Protetor de colchão",
      "model_table": "modelos_protetores_colchao",
      "product_table": "protetor_colchao",
      "colors_table": "modelo_protetor_colchao_cores",
      "storefront_mode": "variantes",
      "storefront_filters": [],
      "storefront_picker": {
        "source": "products",
        "field": "dimensoes",
        "label": "Dimensão",
        "format": "dimensions",
        "suffix": " cm"
      },
      "storefront_specs": [
        {
          "field": "composicao",
          "label": "Composicao",
          "widget": "composition",
          "enum_labels": {}
        }
      ],
      "storefront_badge": null,
      "order_picker_mode": "variantes",
      "product_select": "id, ean, barcode_url, visibilidade, dimensoes"
    },
    {
      "tipo": "passadeira",
      "label": "Passadeira",
      "model_table": "modelos_passadeiras",
      "product_table": "passadeira",
      "colors_table": "modelo_passadeira_cores",
      "storefront_mode": "variantes",
      "storefront_filters": [],
      "storefront_picker": {
        "source": "products",
        "field": "dimensoes",
        "label": "Dimensão",
        "format": "dimensions",
        "suffix": " cm"
      },
      "storefront_specs": [
        {
          "field": "composicao",
          "label": "Composicao",
          "widget": "composition",
          "enum_labels": {}
        }
      ],
      "storefront_badge": null,
      "order_picker_mode": "variantes",
      "product_select": "id, ean, barcode_url, visibilidade, dimensoes"
    },
    {
      "tipo": "regional",
      "label": "Regional",
      "model_table": "modelos_regionais",
      "product_table": "regional",
      "colors_table": "modelo_regional_cores",
      "storefront_mode": "variantes",
      "storefront_filters": [
        {
          "field": "subtipo",
          "label": "Tipo",
          "options": [
            "avental",
            "luva",
            "pega",
            "pano_cozinha",
            "toalha",
            "protetor"
          ],
          "labels": {
            "avental": "Avental",
            "luva": "Luva",
            "pega": "Pega",
            "pano_cozinha": "Pano de cozinha",
            "toalha": "Toalha de mesa",
            "protetor": "Protetor de mesa"
          }
        }
      ],
      "storefront_picker": {
        "source": "products",
        "field": "dimensoes",
        "label": "Dimensão",
        "format": "dimensions",
        "suffix": " cm"
      },
      "storefront_specs": [
        {
          "field": "composicao",
          "label": "Composicao",
          "widget": "composition",
          "enum_labels": {}
        }
      ],
      "storefront_badge": {
        "field": "subtipo",
        "labels": {
          "avental": "Avental",
          "luva": "Luva",
          "pega": "Pega",
          "pano_cozinha": "Pano de cozinha",
          "toalha": "Toalha de mesa",
          "protetor": "Protetor de mesa"
        }
      },
      "order_picker_mode": "variantes",
      "product_select": "id, ean, barcode_url, visibilidade, dimensoes"
    },
    {
      "tipo": "material_cozinha",
      "label": "Material de cozinha",
      "aggregated_tipos": [
        "avental",
        "luva",
        "pega",
        "pano_cozinha"
      ],
      "storefront_mode": "aggregado",
      "storefront_filters": [
        {
          "field": "_tipo_catalogo",
      "label": "Subcategoria",
      "options": [
        "avental",
        "luva",
        "pega",
        "pano_cozinha"
      ],
      "labels": {
        "avental": "Aventais",
        "luva": "Luvas",
        "pega": "Pegas",
        "pano_cozinha": "Panos de cozinha"
      }
        }
      ],
      "storefront_picker": null,
      "storefront_specs": [],
      "storefront_badge": null,
      "order_picker_mode": "aggregado"
    }
  ],
  "category_definitions": {
    "almofadas": {
      "nome": "Almofadas",
      "tipo_catalogo": "almofada",
      "carrinho_step": 6,
      "carrinho_min": 6
    },
    "assentos": {
      "nome": "Assentos",
      "tipo_catalogo": "assento",
      "carrinho_step": 12,
      "carrinho_min": 12
    },
    "guarda-chuvas": {
      "nome": "Guarda-chuvas",
      "tipo_catalogo": "guarda_chuva"
    },
    "oculos": {
      "nome": "Óculos",
      "tipo_catalogo": "oculo"
    },
    "toalhas-mesa": {
      "nome": "Toalhas de mesa",
      "tipo_catalogo": "toalha_mesa"
    },
    "protetores-colchao": {
      "nome": "Protetor de colchão",
      "tipo_catalogo": "protetor_colchao",
      "carrinho_step": 6,
      "carrinho_min": 6
    },
    "passadeiras": {
      "nome": "Passadeira",
      "tipo_catalogo": "passadeira",
      "carrinho_step": 6,
      "carrinho_min": 6
    },
    "material-cozinha": {
      "nome": "Material de cozinha",
      "tipo_catalogo": "material_cozinha",
      "aggregated_tipos": [
        "avental",
        "luva",
        "pega",
        "pano_cozinha"
      ]
    },
    "regional": {
      "nome": "Regional",
      "tipo_catalogo": "regional"
    }
  }
}

let liveCatalogMeta = null

/** Injecção a partir de GET /catalogo/meta (fonte de verdade do backend). */
export function setLiveCatalogMeta(meta) {
  if (meta?.catalog_types?.length) liveCatalogMeta = meta
}

export function getCatalogMeta() {
  return liveCatalogMeta || CATALOG_META
}

export function getTipoConfig(tipo) {
  const meta = getCatalogMeta()
  const fromPhysical = (meta.catalog_types || []).find((t) => t.tipo === tipo)
  if (fromPhysical) return fromPhysical
  const fromAgg = (meta.aggregated_categories || []).find((t) => t.tipo === tipo)
  return fromAgg || null
}
