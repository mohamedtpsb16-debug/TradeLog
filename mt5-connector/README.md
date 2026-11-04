# TradeLog — connecteur MT5 local (lecture seule)

## Sécurité et périmètre

- Le serveur écoute exclusivement sur \`127.0.0.1:8765\` (ordinateur local).
- Utilise l'intégration Python officielle MetaTrader 5 pour communiquer avec le terminal MT5 local.
- Lit uniquement l'état du terminal et l'historique des deals.
- N'appelle aucune fonction d'envoi/modification/suppression d'ordre (\`order_send\`, etc.).
- N'installe aucun EA, ne crée aucun ordre et ne modifie aucun SL/TP.
- Ne stocke aucun mot de passe MT5. Le numéro de compte et le serveur associés à chaque compte TradeLog sont conservés localement dans le navigateur.
- Peut sélectionner temporairement un autre compte déjà enregistré dans MT5, sans transmettre de mot de passe, vérifier son identité, lire son historique puis rétablir le compte MT5 qui était actif au départ.
- Le jeton d'accès est généré à chaque lancement et affiché dans la console. Ne le partage jamais.

**Important :** MT5 reste connecté au serveur du courtier. Le connecteur ne communique pas directement avec le serveur du courtier, mais lit les informations accessibles au terminal. Lecture seule ne signifie donc pas absence de connexion au compte.

## Prérequis

- Windows 10/11
- MetaTrader 5 installé, ouvert et connecté au compte
- Python 3.10+ (64 bits recommandé)

## Installation

1. Décompresser le dossier.
2. Double-cliquer sur \`install.bat\`.
3. Ouvrir MT5 et vérifier que le compte est connecté. Les comptes supplémentaires pourront être ajoutés plus tard dans MT5, avec leurs identifiants enregistrés dans le terminal.
4. Double-cliquer sur \`start.bat\`.
5. Garder la fenêtre ouverte pendant la synchronisation.

Le connecteur affiche un jeton temporaire à chaque lancement. La future interface TradeLog l'utilisera pour demander les données depuis ce même PC.

## Endpoints locaux

Tous les appels nécessitent l'en-tête \`Authorization: Bearer <jeton>\`.

- \`GET http://127.0.0.1:8765/health\`
- \`GET http://127.0.0.1:8765/status\`
- \`GET http://127.0.0.1:8765/history?days=90\` (1 à 365 jours)

Le navigateur n'accepte les requêtes cross-origin que depuis les origines explicitement autorisées dans \`connector.py\`. Le serveur n'écoute pas sur le réseau local.

## Limites actuelles

Cette première brique est le pont local. Elle ne modifie pas TradeLog ni Supabase et ne réalise aucun import. L'étape suivante consiste à intégrer l'interface de prévisualisation et le rapprochement manuel des deals avec les trades saisis dans TradeLog. Aucun rapprochement ne doit reposer uniquement sur la date, puisque le journal ne conserve pas l'heure d'ouverture.
