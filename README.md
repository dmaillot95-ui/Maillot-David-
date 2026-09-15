# CÉRÉBRON Ω Local

CÉRÉBRON Ω est configuré ici en application **statique** pour GitHub + Vercel. Le modèle IA tourne directement dans le navigateur avec WebLLM/WebGPU : Vercel sert l’interface mais n’exécute pas les appels IA.

## Ce que cela change

- aucun appel Floot pour les agents locaux ;
- aucune clé API OpenAI nécessaire ;
- aucun crédit IA Vercel consommé par l’orchestrateur local ;
- chaque agent correspond à un appel d’inférence local distinct avec son propre rôle/contexte ;
- un seul modèle est chargé et partagé afin de ne pas saturer le portable ;
- les agents sont exécutés en file et regroupés par essaims ;
- 10, 50, 100 ou 120 agents de travail peuvent être demandés ;
- Stop/Reprise et sauvegarde locale des campagnes sont prévus.

## Limite réelle

120 agents ne signifie pas 120 modèles simultanés. La limite devient la puissance du portable, sa RAM/VRAM, WebGPU, la taille du modèle et le temps d’exécution. Les grands nombres d’agents peuvent prendre longtemps.

## Utilisation

1. Déployer/importer ce dépôt dans Vercel avec le preset `Other` (le `vercel.json` l’impose).
2. Ouvrir l’application depuis Chrome ou Edge récent sur le portable.
3. Vérifier que WebGPU est disponible.
4. Choisir un petit modèle 1B–3B pour commencer.
5. Charger le modèle ; le premier téléchargement peut être important.
6. Entrer la mission et lancer le nombre d’agents voulu.

Les résultats et checkpoints sont conservés dans `localStorage` du navigateur et peuvent être exportés en JSON.

## Règles racines

- `REALITY > COHERENCE`
- `EVIDENCE > CONFIDENCE`
- `CLAIM <= EVIDENCE`
- `SIMULATION != TEST`
- `UNKNOWN REMAINS UNKNOWN`
- `VERIFY BEFORE COMMIT`

## Moteur local

WebLLM / MLC exécute l’inférence dans le navigateur via WebGPU. Aucun résultat d’agent n’est annoncé avant qu’un appel local réel n’ait terminé.
