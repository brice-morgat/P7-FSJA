# Metriques DORA & KPI operationnels

Ce document sert de **tableau provisoire** (a integrer ensuite dans la documentation finale) pour analyser la performance du pipeline CI/CD et la fiabilite observable via ELK.

## Prerequis

- Avoir execute plusieurs pipelines CI/CD (3 minimum).
- Avoir une stack ELK (ou equivalent) et un premier dashboard (meme simple).

## Methode (source des donnees)

- **CI/CD**: historique GitHub Actions (`.github/workflows/ci.yml`, `.github/workflows/cd.yml`).
- **Application**: logs applicatifs dans ELK (erreurs, warnings, pics, tendances).

## Generation automatique du tableau (recommande)

Le script ci-dessous collecte les donnees via l'API GitHub et produit un tableau Markdown:

```bash
export GITHUB_TOKEN=ghp_xxx   # token avec droits lecture Actions
python3 misc/metrics/collect_github_actions_metrics.py > docs/metrics-dora-kpi.generated.md
```

Ensuite, copie/colle les valeurs pertinentes dans ce document (ou reference directement le fichier genere).

## Tableau provisoire (a remplir / verifier)

### Valeurs observees (extraction GitHub Actions)

Une extraction a ete generee automatiquement dans `docs/metrics-dora-kpi.generated.md` sur la periode **2026-04-11 -> 2026-05-11 (UTC)**.

### 4 metriques DORA

| Metrie DORA | Valeur | Methode de calcul (a documenter) |
| --- | --- | --- |
| Deployment frequency | 7 deploy(s) / 30j | Nb de runs `cd.yml` en succes / periode. |
| Lead time for changes | 2.2min (mediane) | Mediane (timestamp commit -> fin du run `cd.yml` en succes). |
| Change failure rate | 22.2% (proxy) | Proxy: runs `cd.yml` en echec / total runs `cd.yml`. Ideal: incidents/rollback en prod. |
| MTTR | n/a (proxy) | Proxy: fin run `cd.yml` en echec -> fin run `cd.yml` suivant en succes. Ideal: temps de retablissement en prod. |

### 3 a 5 KPI supplementaires

| KPI operationnel | Valeur | Methode de calcul (a documenter) |
| --- | --- | --- |
| Temps CI (p50/p95) | 57s / 1.3min | Duree du workflow `ci.yml` (run_started_at -> updated_at), p50/p95. |
| Taux de succes CI | 20.0% | Runs `ci.yml` en succes / total. |
| Temps CD (p50) | 2.0min | Duree du workflow `cd.yml`. |
| Qualite SonarQube | (manuel/auto) | Quality Gate + indicateurs (bugs, vuln., code smells, coverage). |
| Frequence des erreurs (ELK) | (manuel) | Ex: nb `ERROR`/min ou % requetes 5xx sur une fenetre glissante. |

## Analyse commentee (guide)

1. **Pipeline (CI/CD)**:
   - Les temps de CI/CD sont faibles (ordre de la minute), ce qui est positif pour le feedback developpeur.
   - En revanche, le **taux de succes CI (20%)** est un signal fort d'instabilite (tests intermittents, dependances externes, ou configuration).
2. **Qualite**:
   - La qualite SonarQube doit etre suivie separement (quality gate, couverture, dette) et corrigee avant de viser une cadence de deploiement plus elevee.
3. **Fiabilite (ELK)**:
   - Le **change failure rate** et le **MTTR** doivent idealement etre corrigees avec des signaux prod (incidents/rollback + pics d'erreurs dans Kibana apres deploiement).
   - Exemple de methode: definir un seuil (ex: `ERROR`/min ou % 5xx) sur 30-60 minutes post-deploiement, et marquer le deploiement comme "failed change" si depasse.
