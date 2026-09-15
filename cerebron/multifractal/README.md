# CÉRÉBRON Ω — Ferme d’agents multifractale

## But

Construire une couche d’orchestration où une mission est décomposée en sous-essaims, puis en agents feuilles indépendants, avant fusion locale et arbitrage racine.

Topologie générale :

`MISSION -> META-COORDINATEUR -> N SOUS-ESSAIMS -> AGENTS FEUILLES -> FUSIONS LOCALES -> FUSION RACINE`

Le moteur accepte de 1 à 120 agents feuilles. Par défaut : 20 agents, sous-essaims de 10.

## Règles de preuve

- REALITY > COHERENCE
- EVIDENCE > CONFIDENCE
- CLAIM <= EVIDENCE
- SIMULATION != TEST
- UNKNOWN REMAINS UNKNOWN
- consensus entre agents utilisant le même modèle != preuve indépendante
- aucune source, donnée, simulation ou expérience ne doit être inventée

## Multifractalité

Chaque agent reçoit :

1. un rôle métier (recherche, benchmark, calcul, architecture, simulation, invention, IP, industrialisation, Red Team, audit) ;
2. une lentille indépendante (voie directe, falsification, formalisation, sensibilité, transfert, ablation, vérification numérique, causalité, mécanisme nouveau, preuve minimale, etc.) ;
3. un sous-essaim ;
4. un identifiant stable.

Les sorties sont fusionnées à deux niveaux : coordinateur de sous-essaim puis Méta-Coordinateur racine.

## Exécution réelle

Le fichier `provider-openai-compatible.mjs` branche le moteur sur un fournisseur d’inférence compatible OpenAI.

Variables serveur :

- `CEREBRON_BASE_URL`
- `CEREBRON_API_KEY`
- `CEREBRON_MODEL`
- `CEREBRON_MAX_TOKENS` (optionnel)

L’API Next.js est :

`POST /api/cerebron/multifractal`

Exemple de corps :

```json
{
  "mission": "Auditer un lemme Collatz et chercher des contre-exemples",
  "agentCount": 20,
  "swarmSize": 10,
  "concurrency": 4
}
```

## GitHub

GitHub est la source du code, de l’historique, des tests et des versions. Les GitHub Actions de ce dépôt servent uniquement à tester le logiciel CÉRÉBRON. Elles ne constituent pas une ferme de calcul IA de production.

Cette séparation est volontaire : les GitHub-hosted runners ne doivent pas être détournés en service de calcul général. L’inférence réelle doit être exécutée par un runtime prévu pour cela (Cloudflare Workers AI, Groq, Render, Vercel avec fournisseur IA, serveur autorisé, etc.).

## États

Un résultat complet contient :

- plan/topologie ;
- sorties feuilles ;
- synthèses par essaim ;
- fusion finale ;
- métriques réelles : agents demandés, réussis, échoués, essaims réussis et nombre d’appels modèle prévus.

## Prochaine étape

Brancher un fournisseur gratuit ou à quota gratuit côté serveur, déployer l’API, puis exposer cette API à ChatGPT sous forme d’outil/plugin/MCP afin que le Méta-Coordinateur puisse lancer les essaims et lire leurs résultats directement depuis la conversation.
