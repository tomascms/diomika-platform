-- Advisor 0011 (function_search_path_mutable): fixa o search_path do trigger que
-- copia tipo_catalogo do modelo para a variante. Aplicado a 2026-10-21.
ALTER FUNCTION public.diomika_variant_inherit_tipo() SET search_path = public, pg_temp;
