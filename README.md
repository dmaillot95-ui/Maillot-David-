# CEREBRON OMEGA

Orchestrateur multi-agents experimental, prepare pour GitHub + Vercel.

## Etat

- Interface Next.js
- Endpoint `/api/orchestrate`
- Endpoint de controle `/api/health`
- Jusqu'a 100 agents logiques par mission
- Concurrence configurable par `CEREBRON_MAX_CONCURRENCY`
- Fournisseur IA compatible OpenAI configurable
- Aucun faux resultat : `EXECUTED`, `NOT_EXECUTED`, `ERROR`

## Variables d'environnement

Copier les valeurs de `.env.example` dans les variables d'environnement du deploiement :

- `CEREBRON_API_BASE`
- `CEREBRON_API_KEY`
- `CEREBRON_MODEL`
- `CEREBRON_MAX_CONCURRENCY`

Sans `CEREBRON_API_BASE`, l'interface reste utilisable mais les agents sont marques `NOT_EXECUTED`.

## Deploiement Vercel

1. Importer ce depot GitHub dans Vercel.
2. Vercel detecte automatiquement Next.js.
3. Deployer d'abord sans cle IA pour verifier l'interface.
4. Tester `/api/health`.
5. Ajouter ensuite un fournisseur IA dans les variables d'environnement.

## Regles racines

- REALITY > COHERENCE
- EVIDENCE > CONFIDENCE
- CLAIM <= EVIDENCE
- SIMULATION != TEST
- UNKNOWN REMAINS UNKNOWN
- VERIFY BEFORE COMMIT
