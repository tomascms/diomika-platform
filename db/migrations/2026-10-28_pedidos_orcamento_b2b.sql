-- ============================================================================
-- Pedido de orçamento B2B: NIF, localidade e tipo de cliente
-- (auditoria BR-06, RP-05, FE-14, LEGAL-10)
-- ============================================================================
-- Três colunas novas, todas anuláveis e sem valor por omissão: os pedidos que já
-- existem ficam com NULL e a API continua a gravar pedidos sem estes campos
-- (só envia as colunas que têm valor). `empresa` já existe desde o início.
--
-- Ordem de publicação: aplicar isto, publicar a API e só depois a loja (a loja
-- passa a enviar `tipo_cliente`). A API nova aceita a BD sem isto enquanto o
-- pedido não trouxer nenhum dos três campos.
--
-- Idempotente. Não apaga nem reescreve dados.
-- ============================================================================

ALTER TABLE pedidos_orcamento ADD COLUMN IF NOT EXISTS nif text;
ALTER TABLE pedidos_orcamento ADD COLUMN IF NOT EXISTS localidade text;
ALTER TABLE pedidos_orcamento ADD COLUMN IF NOT EXISTS tipo_cliente text;

-- «empresa» (compra para a sua actividade: parte B2B das condições de venda) ou
-- «particular» (consumidor: DL 24/2014 e DL 84/2021). NULL = não indicou.
ALTER TABLE pedidos_orcamento DROP CONSTRAINT IF EXISTS ck_pedidos_orcamento_tipo_cliente;
ALTER TABLE pedidos_orcamento ADD CONSTRAINT ck_pedidos_orcamento_tipo_cliente
  CHECK (tipo_cliente IN ('empresa', 'particular'));
