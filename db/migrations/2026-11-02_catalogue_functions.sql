-- ============================================================================
-- Gravações atómicas do catálogo (auditoria API-08)
-- ============================================================================
-- Antes: guardar um modelo eram 1 pedido do modelo + 1 por cor + 1 por EAN + apagar órfãos + publicar, cada
-- um com a sua invalidação de cache; uma falha a meio deixava modelo/cores/EAN com visibilidades diferentes.
-- Agora cada operação é uma só chamada rpc(...) = uma só transacção:
--   * save_model_bundle(p jsonb)                  modelo + cores + variantes (+ apagar as retiradas)
--   * set_catalog_visibility(kind, id, visible)   categoria->modelos->cores/variantes, ou modelo->cores/variantes
--
-- Só a service_role as pode chamar (a API). O PostgREST expõe as funções de `public` como RPC, por isso o
-- EXECUTE é retirado a todos e dado só à service_role.
-- Idempotente (CREATE OR REPLACE). Aplicar ANTES da API nova.
-- ============================================================================

-- Upsert em lote por `id`: só as colunas que aparecem em alguma linha do JSON; as que faltam nas linhas ficam NULL
-- nos inserts (jsonb_populate_recordset não aplica o DEFAULT: a API envia sempre todas as chaves) e intactas nos
-- updates. Nas tabelas filhas (com `id_modelo`) o UPDATE só acontece se o id já for do mesmo modelo: um id de outro
-- modelo não se reatribui, nem numa corrida entre a verificação da API e esta função. Falha em qualquer linha = nada fica gravado.
CREATE OR REPLACE FUNCTION public._bundle_upsert(p_table regclass, p_rows jsonb)
RETURNS integer
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $fn$
DECLARE
  v_cols text;
  v_sets text;
  v_guard text := '';
  v_n integer;
BEGIN
  IF p_rows IS NULL OR jsonb_typeof(p_rows) <> 'array' OR jsonb_array_length(p_rows) = 0 THEN
    RETURN 0;
  END IF;

  SELECT string_agg(quote_ident(a.attname), ', ' ORDER BY a.attnum),
         string_agg(quote_ident(a.attname) || ' = excluded.' || quote_ident(a.attname), ', ' ORDER BY a.attnum)
           FILTER (WHERE a.attname NOT IN ('id', 'created_at'))
    INTO v_cols, v_sets
    FROM pg_attribute a
   WHERE a.attrelid = p_table
     AND a.attnum > 0
     AND NOT a.attisdropped
     AND a.attgenerated = ''
     AND EXISTS (SELECT 1 FROM jsonb_array_elements(p_rows) r WHERE r ? a.attname);

  IF v_cols IS NULL OR v_sets IS NULL THEN
    RAISE EXCEPTION 'bundle: sem colunas reconhecidas para %', p_table;
  END IF;

  IF EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid = p_table AND a.attname = 'id_modelo' AND NOT a.attisdropped) THEN
    v_guard := format(' WHERE %s.id_modelo = excluded.id_modelo', p_table);
  END IF;

  EXECUTE format(
    'INSERT INTO %s (%s) SELECT %s FROM jsonb_populate_recordset(NULL::%s, $1) ON CONFLICT (id) DO UPDATE SET %s%s',
    p_table, v_cols, v_cols, p_table, v_sets, v_guard
  ) USING p_rows;
  GET DIAGNOSTICS v_n = ROW_COUNT;
  RETURN v_n;
END
$fn$;

-- p = {
--   "model":   {...linha de product_models, com "id"...},
--   "colors":  [{...linha de product_model_colors...}],      (id_modelo é forçado ao id do modelo)
--   "variants":[{...linha de product_variants...}],          (idem)
--   "delete_colors":   ["uuid", ...],                        (só apaga filhos DESTE modelo)
--   "delete_variants": ["uuid", ...]
-- }
CREATE OR REPLACE FUNCTION public.save_model_bundle(p jsonb)
RETURNS jsonb
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $fn$
DECLARE
  v_id uuid;
  v_colors integer;
  v_variants integer;
BEGIN
  v_id := NULLIF(p->'model'->>'id', '')::uuid;
  IF v_id IS NULL THEN
    RAISE EXCEPTION 'save_model_bundle: model.id em falta';
  END IF;

  -- Primeiro o modelo (os filhos referenciam-no), depois as retiradas (libertam EAN/cor), depois os filhos.
  PERFORM public._bundle_upsert('public.product_models', jsonb_build_array(p->'model'));

  DELETE FROM public.product_model_colors
   WHERE id_modelo = v_id
     AND id IN (SELECT x::uuid FROM jsonb_array_elements_text(COALESCE(p->'delete_colors', '[]'::jsonb)) AS x);
  DELETE FROM public.product_variants
   WHERE id_modelo = v_id
     AND id IN (SELECT x::uuid FROM jsonb_array_elements_text(COALESCE(p->'delete_variants', '[]'::jsonb)) AS x);

  v_colors := public._bundle_upsert(
    'public.product_model_colors',
    (SELECT COALESCE(jsonb_agg(c || jsonb_build_object('id_modelo', v_id)), '[]'::jsonb)
       FROM jsonb_array_elements(COALESCE(p->'colors', '[]'::jsonb)) AS c)
  );
  v_variants := public._bundle_upsert(
    'public.product_variants',
    (SELECT COALESCE(jsonb_agg(v || jsonb_build_object('id_modelo', v_id)), '[]'::jsonb)
       FROM jsonb_array_elements(COALESCE(p->'variants', '[]'::jsonb)) AS v)
  );

  RETURN jsonb_build_object('id', v_id, 'colors', v_colors, 'variants', v_variants);
END
$fn$;

-- kind = 'category' | 'model'. Devolve o nº de linhas da própria categoria/modelo alteradas (0 = não existe).
CREATE OR REPLACE FUNCTION public.set_catalog_visibility(p_kind text, p_id uuid, p_visible boolean)
RETURNS integer
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $fn$
DECLARE
  v_n integer;
BEGIN
  IF p_kind = 'category' THEN
    UPDATE public.categories SET visibilidade = p_visible WHERE id = p_id;
    GET DIAGNOSTICS v_n = ROW_COUNT;
    UPDATE public.product_models SET visibilidade = p_visible WHERE id_categoria = p_id;
    UPDATE public.product_variants SET visibilidade = p_visible
     WHERE id_modelo IN (SELECT id FROM public.product_models WHERE id_categoria = p_id);
    UPDATE public.product_model_colors SET visibilidade = p_visible
     WHERE id_modelo IN (SELECT id FROM public.product_models WHERE id_categoria = p_id);
  ELSIF p_kind = 'model' THEN
    UPDATE public.product_models SET visibilidade = p_visible WHERE id = p_id;
    GET DIAGNOSTICS v_n = ROW_COUNT;
    UPDATE public.product_variants SET visibilidade = p_visible WHERE id_modelo = p_id;
    UPDATE public.product_model_colors SET visibilidade = p_visible WHERE id_modelo = p_id;
  ELSE
    RAISE EXCEPTION 'set_catalog_visibility: tipo desconhecido %', p_kind;
  END IF;
  RETURN v_n;
END
$fn$;

REVOKE ALL ON FUNCTION public._bundle_upsert(regclass, jsonb) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.save_model_bundle(jsonb) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.set_catalog_visibility(text, uuid, boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public._bundle_upsert(regclass, jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.save_model_bundle(jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.set_catalog_visibility(text, uuid, boolean) TO service_role;
