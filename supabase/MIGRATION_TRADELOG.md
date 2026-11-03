# Migration SQL — TradeLog (mouvements de fonds)

Migration additive à exécuter une seule fois dans Supabase > SQL Editor > New query. Aucune donnée existante n'est supprimée.

```sql
create table if not exists public.account_movements (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references public.trading_accounts(id) on delete cascade,
  movement_type text not null check (movement_type in ('deposit','withdrawal')),
  amount numeric(14,2) not null check (amount > 0),
  movement_date date not null default current_date,
  note text,
  created_at timestamptz not null default now()
);

alter table public.account_movements enable row level security;

drop policy if exists "Users manage own account movements" on public.account_movements;
create policy "Users manage own account movements"
on public.account_movements for all to authenticated
using (
  exists (select 1 from public.trading_accounts a
          where a.id = account_movements.account_id and a.user_id = auth.uid())
)
with check (
  exists (select 1 from public.trading_accounts a
          where a.id = account_movements.account_id and a.user_id = auth.uid())
);

create index if not exists account_movements_account_date_idx
on public.account_movements(account_id, movement_date desc);
```

Le solde calculé sera : capital initial + dépôts - retraits + PNL net réalisé. Les filtres de période ne modifient aucune donnée.

Avant exécution, vérifier que la table trading_accounts possède bien user_id et que cette colonne est celle utilisée par ses politiques RLS existantes.
