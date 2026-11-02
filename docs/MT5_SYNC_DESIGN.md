# TradeLog — Préparation de la synchronisation MT5

> Statut : conception uniquement. Aucun EA n'est déployé, aucune connexion MT5 n'est active et aucun changement n'est apporté à l'application publiée.

## 1. Objectif

Importer dans TradeLog les positions MT5 entièrement clôturées, sur le compte GOAT Funded Trader du propriétaire, tout en conservant les trades saisis manuellement.

La connexion ne doit jamais ouvrir, modifier, gérer, copier ou fermer une position. Elle ne doit lire que l'historique clôturé.

**Condition préalable impérative :** ne pas installer, compiler pour utilisation réelle, attacher à MT5 ou exécuter un Expert Advisor sur le compte GOAT tant que GOAT Funded Trader n'a pas confirmé par écrit que cet outil de reporting auto-développé est autorisé.

## 2. Architecture envisagée

1. **Connecteur MT5 Windows (EA de reporting, sous réserve d'autorisation)** : lit les deals de l'historique et reconstitue uniquement les positions complètement clôturées.
2. **Endpoint Supabase Edge Function** : reçoit les données HTTPS, authentifie le connecteur et valide le format.
3. **Registre d'import MT5** : conserve l'identité externe de chaque position afin de rendre les synchronisations idempotentes.
4. **Table trades existante** : reçoit le trade importé avec `import_source = 'mt5'`. Les entrées manuelles restent `import_source = 'manual'`.
5. **TradeLog** : continue d'afficher les deux sources dans le même journal. Les champs de journal non fournis par MT5 (setup, émotions, biais, respect du plan, notes, captures) restent à compléter par l'utilisateur.

Aucune clé Supabase `service_role` ne doit être intégrée au connecteur MT5.

## 3. Règles anti-doublons

- Identité externe proposée : combinaison du compte TradeLog, du login MT5, du serveur MT5 et du `POSITION_IDENTIFIER` MT5.
- Une position clôturée ne peut créer qu'un seul trade TradeLog.
- Une contrainte unique en base doit protéger cette identité, même si le connecteur envoie deux fois le même message.
- Une synchronisation répétée doit retourner « déjà importé » sans créer une nouvelle ligne.
- Les trades manuels ne sont jamais rapprochés ou supprimés automatiquement.
- Ne pas utiliser le seul symbole, la date ou le montant du PNL comme clé d'identification.

## 4. Reconstitution d'une position

MT5 peut produire plusieurs deals pour une seule position (entrée, sortie partielle, sortie finale, commissions). Le connecteur doit agréger les deals par identifiant de position et n'envoyer la position qu'une fois sa clôture totale confirmée.

Le calcul doit tenir compte des profits, commissions, swaps et frais disponibles dans l'historique. Les montants bruts et frais doivent rester séparés pour être stockés dans les champs TradeLog correspondants. La devise du compte MT5 doit être transmise explicitement.

Si les données sont incomplètes ou incohérentes, l'enregistrement doit être rejeté ou placé en attente, jamais importé avec des valeurs inventées.

## 5. Correspondance des champs

| Donnée MT5 | Champ TradeLog / traitement |
|---|---|
| Date/heure de clôture | `trade_date` (conversion explicite du fuseau MT5 vers la date attendue par TradeLog) |
| Symbole | `symbol` |
| Type de position | `side` |
| Profit de trading | `gross_pnl` |
| Commission | `commission` |
| Swap | `swap` |
| Frais additionnels | `other_fees` |
| Source | `import_source = 'mt5'` |
| Identité externe | registre d'import MT5, avec référence unique |
| Setup, émotions, biais, notes | laissés vides pour annotation manuelle |
| Capture d'écran | aucune importation automatique prévue |

Le calcul net existant de TradeLog reste la référence : profit brut + commission + swap + autres frais. Le risque de référence et le R réalisé ne doivent pas être inventés. Leur calcul nécessite de définir comment le risque initial sera fourni ou associé à la position MT5.

## 6. Sécurité

- HTTPS uniquement.
- Jeton individuel révocable par connecteur, stocké de manière sécurisée et jamais affiché dans l'interface.
- Stocker uniquement une empreinte du jeton côté serveur.
- Vérifier que le compte TradeLog destinataire appartient à l'utilisateur authentifié.
- Valider les types, tailles, devise, identifiants et bornes des données reçues.
- Journaliser les imports et les erreurs sans enregistrer de secrets.
- Prévoir révocation et rotation du jeton.
- Ne jamais exposer de clé Supabase privilégiée dans le terminal MT5.

## 7. Tests avant toute utilisation réelle

1. Test unitaire de l'agrégation des deals, y compris sorties partielles et frais.
2. Test d'un même message envoyé deux fois : une seule ligne TradeLog.
3. Test de deux positions différentes sur le même symbole et la même journée : deux trades distincts.
4. Test de coexistence avec les trades manuels : aucune modification des entrées manuelles.
5. Test de rejet d'un payload incomplet ou d'un jeton invalide.
6. Test sur compte de démonstration uniquement, après validation de l'architecture.
7. Activation sur le compte GOAT uniquement après autorisation écrite explicite.

## 8. Points encore à confirmer

- Réponse écrite de GOAT Funded Trader sur l'EA de reporting auto-développé.
- Nom exact du serveur MT5 et devise du compte.
- Convention de date/fuseau à utiliser dans TradeLog.
- Règle de calcul du risque initial et du R réalisé pour les trades importés.
- Schéma réel des tables et politiques RLS Supabase avant de préparer la migration SQL.

## 9. Hors périmètre

Le connecteur ne doit pas être un robot de trading, un gestionnaire de risque actif, un trade copier, un outil d'exécution ou un service hébergé/VPS. Il ne doit exercer aucune action sur les ordres ou positions.
