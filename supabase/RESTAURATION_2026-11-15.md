# Retour en arrière — mises à jour du 15/11/2026

## Code (appli)
L'état d'avant est conservé dans la branche `sauvegarde-2026-11-15`.
Pour revenir en arrière : remettre `main` sur cette branche (Claude peut le faire sur demande).

## Base Supabase
Copie complète des 4 tables au 15/11/2026, avant toute modification, dans le schéma privé
`sauvegarde_20261115` (non accessible depuis l'appli ni depuis Internet).

Restaurer les données des trades (SQL Editor) :

```sql
begin;
update public.trades t set
  result = b.result, setup = b.setup, gross_pnl = b.gross_pnl, risk_reference = b.risk_reference,
  plan_respected = b.plan_respected, risk_respected = b.risk_respected, setup_valid = b.setup_valid,
  notes = b.notes, trade_date = b.trade_date, account_id = b.account_id
from sauvegarde_20261115.trades b where b.id = t.id;
commit;
```

Supprimer la sauvegarde quand tout est validé : `drop schema sauvegarde_20261115 cascade;`
