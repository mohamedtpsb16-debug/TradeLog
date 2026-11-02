# Migration SQL — TradeLog

À exécuter une seule fois dans Supabase > SQL Editor > New query. Cette migration est additive : elle ne supprime aucune ligne existante.

```sql
alter table public.trades
  add column if not exists risk_respected boolean not null default false,
  add column if not exists setup_valid boolean not null default false;

-- Le bucket doit rester privé.
update storage.buckets
set public = false,
    file_size_limit = 10485760,
    allowed_mime_types = array['image/jpeg','image/png','image/webp']
where id = 'trade-screenshots';
```

Après exécution, les nouveaux trades enregistrent séparément les trois contrôles :
- respect du plan ;
- respect du risque autorisé ;
- validité du setup.

Le champ `result` reste textuel : les quatre valeurs proposées par l'application sont TP, SL, CP (stocké sous `PARTIAL`) et BE. Les anciennes valeurs déjà enregistrées ne sont pas modifiées.
