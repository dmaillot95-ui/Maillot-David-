# CÉRÉBRON Ω — Architecture d'auto-amélioration contrôlée

## Objectif

Construire une couche persistante autour des modèles IA qui puisse :

- distribuer des missions à des essaims spécialisés ;
- mémoriser résultats, erreurs, inconnues et décisions ;
- comparer plusieurs configurations sur les mêmes benchmarks ;
- ajuster les **poids de routage** entre rôles, modèles et stratégies ;
- promouvoir uniquement une configuration qui améliore les scores sans régression critique ;
- préparer l'usage futur de modèles open-weight pouvant être adaptés séparément.

## Limite fondamentale

CÉRÉBRON Ω ne modifie pas les poids internes de GPT-5.6 Sol. Les poids modifiables ici sont des poids d'orchestration : routage, priorités, allocation de budget, choix de rôle, sélection de stratégie, nombre d'agents et ordre des étapes.

## Boucle d'amélioration

```text
CONFIG_N
  ↓
BENCHMARKS FIXES
  ↓
MESURES
  ↓
MUTATIONS CONTRÔLÉES
  ↓
CONFIG_N+1 CANDIDATE
  ↓
A/B + ABLATION + RED TEAM
  ↓
PROMOTE / REJECT / HOLD
```

## Règles racines

- REALITY > COHERENCE
- EVIDENCE > CONFIDENCE
- CLAIM <= EVIDENCE
- SIMULATION != TEST
- MEMORY != LEARNING
- BENCHMARK BEFORE PROMOTION
- ABLATION BEFORE ADDITION
- NO REGRESSION WITHOUT EXPLICIT ACCEPTANCE
- UNKNOWN REMAINS UNKNOWN

## Composants

1. **Router** — alloue les rôles et budgets selon des poids explicites.
2. **Memory** — conserve configurations, scores, campagnes, erreurs et décisions.
3. **Benchmark Engine** — exécute les mêmes tâches de référence sur chaque variante.
4. **Mutation Engine** — génère de petites variations bornées des poids d'orchestration.
5. **Evaluator** — calcule score global + sous-scores et détecte les régressions.
6. **Promotion Gate** — n'accepte une nouvelle configuration que si les critères sont satisfaits.
7. **Red Team** — cherche les gains artificiels, fuites de benchmark et effets de bord.
8. **Audit Trail** — conserve pourquoi une version a été acceptée ou rejetée.

## Critère de promotion par défaut

Une configuration candidate peut être promue si :

- score global > baseline + marge minimale ;
- aucune régression critique au-delà du seuil ;
- au moins un test d'ablation confirme que le gain dépend réellement du changement ;
- les résultats sont reproductibles sur plusieurs exécutions ;
- aucune violation des règles de preuve n'est détectée.

## Poids ajustables

Exemples :

- recherche
- benchmark
- physique/calculs
- architecture
- simulation
- invention
- IP
- industrialisation
- red-team
- audit-evidence

Les poids contrôlent la part de budget logique attribuée à chaque rôle. Ils ne représentent pas les poids neuronaux du modèle.

## États de décision

- PROMOTE
- KEEP
- NARROW
- HOLD
- REJECT
- ROLLBACK

## Principe de sécurité scientifique

Une amélioration n'est jamais déclarée parce que la sortie semble meilleure. Elle doit être soutenue par une mesure définie avant le test, exécutée sur un benchmark fixe, comparée à une baseline et auditée contre les régressions.
