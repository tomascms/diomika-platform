"""
Modelos de dados Diomika — FONTE DE VERDADE do catálogo.

Catálogo unificado (desde o refactor de esquema): 3 tabelas físicas para
TODAS as categorias — product_models, product_model_colors, product_variants.
Os campos que variam por categoria (tipo, composição, dimensões, altura, ...)
vivem em `attributes jsonb`, validados por models/catalog_attributes.py.

Para adicionar um tipo de produto novo (ex.: mantas):
  1. Acrescenta uma entrada a CATEGORY_ATTRIBUTE_SCHEMAS (models/catalog_attributes.py).
  2. Reinicia a API.
  3. Cria a categoria no backoffice (CRUD real).
Nenhum destes passos precisa de uma migração SQL — não há tabela nova.

TABLE_MAP, sidebar, loja e validações são gerados automaticamente a partir disto.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from models.catalog_attributes import (
    AGGREGATED_CATEGORY_GROUPS,
    CATEGORY_ATTRIBUTE_SCHEMAS,
    is_registered_tipo as _is_registered_tipo,
    validate_attributes as _validate_attributes,
)
from models.catalog_validators import generate_slug, validate_ean as _validate_ean

TIPO_CATALOGO = str  # valores válidos = chaves de CATALOG_TYPES (validado em Categoria)

PRODUCT_MODELS_TABLE = "product_models"
PRODUCT_MODEL_COLORS_TABLE = "product_model_colors"
PRODUCT_VARIANTS_TABLE = "product_variants"

CATEGORY_DEFINITIONS = {
    "almofadas": {"nome": "Almofadas", "tipo_catalogo": "almofada", "carrinho_step": 6, "carrinho_min": 6},
    "assentos": {"nome": "Assentos", "tipo_catalogo": "assento", "carrinho_step": 12, "carrinho_min": 12},
    "guarda-chuvas": {"nome": "Guarda-chuvas", "tipo_catalogo": "guarda_chuva", "carrinho_step": 6, "carrinho_min": 6},
    "oculos": {"nome": "Óculos", "tipo_catalogo": "oculo", "carrinho_step": 6, "carrinho_min": 6},
    "toalhas-mesa": {"nome": "Toalhas de mesa", "tipo_catalogo": "toalha_mesa", "carrinho_step": 6, "carrinho_min": 6},
    "protetores-colchao": {"nome": "Protetor de colchão", "tipo_catalogo": "protetor_colchao", "carrinho_step": 6, "carrinho_min": 6},
    "passadeiras": {"nome": "Passadeira", "tipo_catalogo": "passadeira", "carrinho_step": 6, "carrinho_min": 6},
    "material-cozinha": {
        "nome": "Material de cozinha",
        "tipo_catalogo": "material_cozinha",
        "aggregated_tipos": AGGREGATED_CATEGORY_GROUPS["material_cozinha"],
        "carrinho_step": 6,
        "carrinho_min": 6,
    },
    "regional": {"nome": "Regional", "tipo_catalogo": "regional", "carrinho_step": 6, "carrinho_min": 6},
}


def category_definition_for_slug(slug: str | None) -> dict | None:
    if not slug:
        return None
    return CATEGORY_DEFINITIONS.get(slug)


def aggregated_tipos_for_tipo(tipo: str | None) -> list[str] | None:
    if not tipo:
        return None
    for definition in CATEGORY_DEFINITIONS.values():
        if definition.get("tipo_catalogo") == tipo and definition.get("aggregated_tipos"):
            return list(definition["aggregated_tipos"])
    return None


def is_registered_tipo(tipo: str | None) -> bool:
    if not tipo:
        return False
    if tipo in CATALOG_TYPES:
        return True
    return aggregated_tipos_for_tipo(tipo) is not None


MIN_ORCAMENTO_TEXTO = "Mínimo de encomenda: 500€ + IVA (sem preços no site — orçamento sob consulta)."


class Categoria(BaseModel):
    id: UUID = Field(default_factory=uuid4, json_schema_extra={"ui_hidden": True})
    tipo_catalogo: Optional[TIPO_CATALOGO] = Field(
        default=None,
        description="Tipo de catálogo (obrigatório — define modelos e produtos)",
        json_schema_extra={"ui_widget": "enum", "ui_label": "Família de produto"},
    )
    nome: str = Field(..., min_length=2)
    slug: str = Field(default="", json_schema_extra={"ui_readonly": True})
    imagem: str = Field(..., description="URL da imagem")
    visibilidade: bool = Field(default=False)
    carrinho_step: Optional[int] = Field(default=None, description="Passo quantidade (ex: 6 ou 12). Predefinido pelo tipo.")
    carrinho_min: Optional[int] = Field(default=None, description="Quantidade mínima por linha no carrinho")

    @model_validator(mode="after")
    def set_slug_and_cart_rules(self) -> "Categoria":
        if not self.slug:
            self.slug = generate_slug(self.nome)

        # CRUD real de categorias: a família é escolhida por quem cria, e
        # CATEGORY_DEFINITIONS só serve de predefinição para os slugs
        # conhecidos — nunca para recusar a escolha. Antes, uma categoria
        # chamada "Assentos" com outra família era rejeitada com um erro
        # enganador, o que contrariava o próprio CRUD livre.
        definition = category_definition_for_slug(self.slug)
        if self.tipo_catalogo is None:
            self.tipo_catalogo = (definition or {}).get("tipo_catalogo") or next(
                iter(CATALOG_TYPES.keys()), "almofada"
            )
        elif not is_registered_tipo(self.tipo_catalogo):
            raise ValueError(f"tipo_catalogo «{self.tipo_catalogo}» não está registado.")

        if self.carrinho_step is None:
            self.carrinho_step = int((definition or {}).get("carrinho_step") or 6)
        if self.carrinho_min is None:
            self.carrinho_min = int((definition or {}).get("carrinho_min") or self.carrinho_step)
        return self


class ProductModelColor(BaseModel):
    """Cor de um modelo — tabela única product_model_colors, para todas as categorias."""
    id: UUID = Field(default_factory=uuid4, json_schema_extra={"ui_hidden": True})
    id_modelo: UUID = Field(..., json_schema_extra={"ui_hidden": True})
    numero: int = Field(..., ge=1, description="Número da cor")
    nome: str = Field(default="", description="Nome da cor (opcional)")
    imagem: str = Field(..., description="URL da imagem desta cor")
    visibilidade: bool = Field(default=False)


class ProductModel(BaseModel):
    """Modelo — tabela única product_models, para todas as categorias.
    Campos específicos da categoria (tipo, composição, dimensões, ...) em `attributes`."""
    id: UUID = Field(default_factory=uuid4, json_schema_extra={"ui_hidden": True})
    id_categoria: UUID = Field(..., description="Categoria", json_schema_extra={"ui_relation": "categories"})
    tipo_catalogo: str = Field(..., description="Família de produto", json_schema_extra={"ui_hidden": True})
    nome: str = Field(..., description="Nome do Modelo")
    slug: str = Field(default="", json_schema_extra={"ui_readonly": True})
    descricao: str = Field(default="", description="Descrição")
    attributes: Dict[str, Any] = Field(default_factory=dict, json_schema_extra={"ui_hidden": True})
    visibilidade: bool = Field(default=False)

    @model_validator(mode="after")
    def set_slug(self) -> "ProductModel":
        if not self.slug:
            self.slug = generate_slug(self.nome)
        return self

    @model_validator(mode="after")
    def validate_attrs(self) -> "ProductModel":
        self.attributes = _validate_attributes(self.tipo_catalogo, "model", self.attributes)
        return self


class ProductVariant(BaseModel):
    """Variante/EAN de um modelo — tabela única product_variants, para todas as categorias."""
    id: UUID = Field(default_factory=uuid4, json_schema_extra={"ui_hidden": True})
    # Sem `ui_relation` fixo: `product_models` é o nome físico e não é uma chave
    # do TABLE_MAP, por isso /admin/crud/product_models/options dava 404 e o
    # dropdown "Modelo" ficava sempre vazio. A relação é resolvida por família
    # (nome virtual, ex.: modelos_almofadas) em ui_schema.relation_table().
    id_modelo: UUID = Field(..., description="Modelo")
    tipo_catalogo: str = Field(..., description="Família de produto", json_schema_extra={"ui_hidden": True})
    ean: str = Field(..., pattern=r"^\d{13}$", description="EAN-13")
    barcode_url: Optional[str] = Field(None, json_schema_extra={"ui_readonly": True})
    attributes: Dict[str, Any] = Field(default_factory=dict, json_schema_extra={"ui_hidden": True})
    visibilidade: bool = Field(default=False)

    @field_validator("ean")
    @classmethod
    def validate_ean(cls, v: str) -> str:
        return _validate_ean(v)

    @model_validator(mode="after")
    def validate_attrs(self) -> "ProductVariant":
        self.attributes = _validate_attributes(self.tipo_catalogo, "variant", self.attributes)
        return self


class PedidoOrcamentoLinha(BaseModel):
    ean: str = Field(..., pattern=r"^\d{13}$")
    numero_cor: int = Field(..., ge=1)
    quantidade: int = Field(..., ge=1)
    altura: Optional[str] = Field(None, max_length=32, description="Altura (assentos, ex: 32mm)")


class PedidoOrcamento(BaseModel):
    id: UUID = Field(default_factory=uuid4, json_schema_extra={"ui_hidden": True})
    nome: str = Field(..., json_schema_extra={"ui_readonly": True})
    email: str = Field(..., json_schema_extra={"ui_readonly": True})
    contacto: Optional[str] = Field(None, json_schema_extra={"ui_readonly": True})
    empresa: Optional[str] = Field(None, json_schema_extra={"ui_readonly": True})
    observacoes: Optional[str] = Field(None, json_schema_extra={"ui_readonly": True})
    linhas: List[Dict] = Field(default_factory=list, json_schema_extra={"ui_hidden": True})
    lida: bool = Field(default=False)
    visibilidade: bool = Field(default=True)
    status: str = Field(default="Nova", json_schema_extra={"ui_readonly": True})


class EncomendaInternaLinha(BaseModel):
    ean: str = Field(..., pattern=r"^\d{13}$")
    numero_cor: int = Field(..., ge=1)
    quantidade: int = Field(..., ge=1)
    altura: Optional[str] = Field(None, max_length=32)


class EncomendaInterna(BaseModel):
    id: UUID = Field(default_factory=uuid4, json_schema_extra={"ui_hidden": True})
    referencia_cliente: str = Field(..., description="Cliente")
    observacoes: Optional[str] = Field(None, json_schema_extra={"ui_hidden": True})
    linhas: List[Dict] = Field(default_factory=list, json_schema_extra={"ui_hidden": True})
    visibilidade: bool = Field(default=True)


class ContactMessage(BaseModel):
    id: UUID = Field(default_factory=uuid4, json_schema_extra={"ui_hidden": True})
    nome: str = Field(..., json_schema_extra={"ui_readonly": True})
    email: str = Field(..., json_schema_extra={"ui_readonly": True})
    contacto: Optional[str] = Field(None, json_schema_extra={"ui_readonly": True})
    assunto: str = Field(..., json_schema_extra={"ui_readonly": True})
    mensagem: str = Field(..., json_schema_extra={"ui_readonly": True})
    lida: bool = Field(default=False)
    visibilidade: bool = Field(default=True)
    status: Optional[str] = Field(None, json_schema_extra={"ui_readonly": True})
    last_sender: Optional[str] = Field(None, json_schema_extra={"ui_hidden": True})


class IdempotencyKey(BaseModel):
    key: str = Field(..., json_schema_extra={"ui_hidden": True})
    operation: str = Field(...)
    response: Dict = Field(default_factory=dict)
    expires_at: Optional[str] = Field(None, json_schema_extra={"ui_hidden": True})


class OutboxEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4, json_schema_extra={"ui_hidden": True})
    event_type: str = Field(...)
    payload: Dict = Field(default_factory=dict)
    status: str = Field(default="pending")
    attempts: int = Field(default=0)
    max_attempts: int = Field(default=5)
    next_retry_at: Optional[str] = None
    last_error: Optional[str] = None


class SagaInstance(BaseModel):
    id: UUID = Field(default_factory=uuid4, json_schema_extra={"ui_hidden": True})
    saga_type: str = Field(...)
    status: str = Field(default="running")
    current_step: Optional[str] = None
    context: Dict = Field(default_factory=dict)


# --- Registo de tipos de catálogo (metadados de vitrine por família) ---
# Os campos (quais atributos existem, validação) vivem em catalog_attributes.py.
# Aqui só se junta a isso o apontador para as 3 tabelas físicas partilhadas.

CATALOG_TYPES: dict = {}


def _register_catalog_types() -> None:
    global CATALOG_TYPES
    CATALOG_TYPES.clear()
    for tipo, cfg in CATEGORY_ATTRIBUTE_SCHEMAS.items():
        CATALOG_TYPES[tipo] = {
            "label": cfg.get("label") or tipo.title(),
            "model_table": PRODUCT_MODELS_TABLE,
            "product_table": PRODUCT_VARIANTS_TABLE,
            "colors_table": PRODUCT_MODEL_COLORS_TABLE,
            "colors_schema": ProductModelColor,
            "model_schema": ProductModel,
            "product_schema": ProductVariant,
            "model_discriminator_field": cfg.get("model_discriminator_field"),
            "product_readonly_on_edit": bool(cfg.get("product_readonly_on_edit")),
            "apply_barcode_on_save": bool(cfg.get("apply_barcode_on_save")),
            "storefront_mode": cfg.get("storefront_mode") or "variantes",
            "storefront_filters": cfg.get("storefront_filters"),
            "storefront_picker": cfg.get("storefront_picker"),
        }


_register_catalog_types()

TIPO_CATALOGO_LABELS = {k: v["label"] for k, v in CATALOG_TYPES.items()}


def _rebuild_table_map() -> None:
    from models.table_map_builder import build_operations_table_map, build_unified_catalog_table_map

    global TABLE_MAP
    ops = build_operations_table_map(
        categoria_schema=Categoria,
        pedido_schema=PedidoOrcamento,
        encomenda_schema=EncomendaInterna,
        contact_schema=ContactMessage,
        infra_schemas={
            "idempotency_keys": IdempotencyKey,
            "outbox_events": OutboxEvent,
            "saga_instances": SagaInstance,
        },
    )
    TABLE_MAP.clear()
    TABLE_MAP.update(ops)
    TABLE_MAP.update(
        build_unified_catalog_table_map(
            model_schema=ProductModel,
            variant_schema=ProductVariant,
            colors_schema=ProductModelColor,
        )
    )


TABLE_MAP: dict = {}
_rebuild_table_map()


def sidebar_tables() -> dict:
    """Sidebar: Categorias, Modelos, Produtos + operações."""
    from models.catalog_views import sidebar_entries

    return sidebar_entries()
