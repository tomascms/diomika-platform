-- ============================================================================
-- 0004: garantias de integridade do catálogo unificado
-- ============================================================================
-- O esquema unificado trocou 40 tabelas por 3. Isso trouxe uma fraqueza nova:
-- no esquema antigo o *nome da tabela* era o tipo de produto, por isso um tipo
-- inválido era fisicamente impossível. Agora `tipo_catalogo` é uma coluna de
-- texto livre, e um valor errado cria uma linha que nenhum caminho de código
-- encontra — dados invisíveis, sem erro nenhum.
--
-- Estas garantias fecham isso SEM contrariar a decisão de design de que os
-- tipos de produto vivem em Python (models/catalog_attributes.py) e não na BD:
-- nenhuma restrição aqui lista os tipos válidos, por isso acrescentar uma
-- categoria nova continua a não precisar de migração SQL.
--
-- Idempotente. Todos os dados em produção já satisfaziam estas restrições
-- quando isto foi aplicado (verificado: 0 violações em 29 modelos, 68
-- variantes, 33 cores).
-- ============================================================================

-- === 1. A variante herda sempre o tipo do seu modelo ===
-- Antes: `product_variants.tipo_catalogo` era passado pelo chamador e nada
-- garantia que batesse com o do modelo-pai. Uma divergência fazia a variante
-- desaparecer da loja e do backoffice (ambos filtram por tipo) enquanto
-- continuava a ocupar o seu EAN no índice único — um EAN "gasto" por uma
-- linha que ninguém consegue ver. Agora é derivado, não confiado.

CREATE OR REPLACE FUNCTION diomika_variant_inherit_tipo() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  SELECT tipo_catalogo INTO NEW.tipo_catalogo
  FROM product_models WHERE id = NEW.id_modelo;
  RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS trg_product_variants_inherit_tipo ON product_variants;
CREATE TRIGGER trg_product_variants_inherit_tipo
  BEFORE INSERT OR UPDATE OF id_modelo, tipo_catalogo ON product_variants
  FOR EACH ROW EXECUTE FUNCTION diomika_variant_inherit_tipo();

-- === 2. Forma dos dados ===
-- `attributes` tem de ser um objeto JSON: o código faz sempre acesso por
-- chave (attributes->>'dimensoes'), por isso um array ou um escalar aqui
-- quebraria silenciosamente a leitura em vez de dar erro na escrita.

ALTER TABLE product_models DROP CONSTRAINT IF EXISTS ck_product_models_attributes_object;
ALTER TABLE product_models ADD CONSTRAINT ck_product_models_attributes_object
  CHECK (jsonb_typeof(attributes) = 'object');

ALTER TABLE product_variants DROP CONSTRAINT IF EXISTS ck_product_variants_attributes_object;
ALTER TABLE product_variants ADD CONSTRAINT ck_product_variants_attributes_object
  CHECK (jsonb_typeof(attributes) = 'object');

-- `tipo_catalogo` tem de ter forma de slug — apanha strings vazias, espaços,
-- maiúsculas e acentos (todos os erros que produzem dados invisíveis) sem
-- fixar a lista de tipos válidos, que continua a viver em Python.

ALTER TABLE product_models DROP CONSTRAINT IF EXISTS ck_product_models_tipo_slug;
ALTER TABLE product_models ADD CONSTRAINT ck_product_models_tipo_slug
  CHECK (tipo_catalogo ~ '^[a-z][a-z0-9_]*$');

ALTER TABLE product_variants DROP CONSTRAINT IF EXISTS ck_product_variants_tipo_slug;
ALTER TABLE product_variants ADD CONSTRAINT ck_product_variants_tipo_slug
  CHECK (tipo_catalogo ~ '^[a-z][a-z0-9_]*$');

-- EAN-13 ao nível da BD, igual ao que o modelo Pydantic já exige
-- (ProductVariant.ean, pattern ^\d{13}$). Sem isto, `ean` só era NOT NULL —
-- a string vazia passava, e o índice único exclui-a explicitamente, por isso
-- várias variantes sem EAN podiam coexistir e nenhuma aparecia na loja.

ALTER TABLE product_variants DROP CONSTRAINT IF EXISTS ck_product_variants_ean13;
ALTER TABLE product_variants ADD CONSTRAINT ck_product_variants_ean13
  CHECK (ean ~ '^[0-9]{13}$');

-- === 3. Índices redundantes (limpeza do 0001) ===
-- Cada um destes é um prefixo exacto de outro índice que já existe, por isso
-- não serve nenhuma query que o outro não sirva — só custa escritas e espaço:
--   idx_product_models_categoria (id_categoria)
--     <- idx_product_models_cat_vis_created (id_categoria, visibilidade, created_at DESC)
--   idx_product_variants_modelo (id_modelo)
--     <- idx_product_variants_modelo_vis (id_modelo, visibilidade)
--   idx_product_model_colors_modelo (id_modelo)
--     <- product_model_colors_id_modelo_numero_key UNIQUE (id_modelo, numero)

DROP INDEX IF EXISTS idx_product_models_categoria;
DROP INDEX IF EXISTS idx_product_variants_modelo;
DROP INDEX IF EXISTS idx_product_model_colors_modelo;
