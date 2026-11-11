-- Estado pequeno da API que vivia em ficheiros no disco da VM (contas do backoffice, emails já registados).
-- No Render grátis o disco apaga-se a cada arranque, por isso fica aqui. Só a service_role lhe chega (RLS sem políticas).
create table if not exists public.app_state (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz not null default now()
);
alter table public.app_state enable row level security;
revoke all on public.app_state from anon, authenticated;
