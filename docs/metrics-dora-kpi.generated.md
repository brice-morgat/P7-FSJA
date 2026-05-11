# Tableau provisoire - DORA & KPI (sur 30 jours)

- Repo: `brice-morgat/P7-FSJA`
- Periode: `2026-04-11` -> `2026-05-11` (UTC)

| Metrie DORA | Valeur | Methode de calcul |
| --- | --- | --- |
| Deployment frequency | 7 deploy(s) / 30j | Nb de runs `cd.yml` en succes sur 30 jours (proxy du nombre de deploiements). |
| Lead time for changes | 2.2min | Mediane (commit timestamp -> fin du run `cd.yml` en succes) (proxy). |
| Change failure rate | 22.2% | Runs `cd.yml` en echec / total runs `cd.yml` (proxy, ne capture pas tous les incidents prod). |
| MTTR | n/a | Mediane (fin run `cd.yml` en echec -> fin run `cd.yml` suivant en succes) (proxy). |

| KPI operationnel | Valeur | Methode de calcul |
| --- | --- | --- |
| Taux de succes CI | 20.0% | Runs `ci.yml` en succes / total runs `ci.yml` sur 30 jours. |
| Temps CI (p50) | 57s | Duree du workflow `ci.yml` (run_started_at -> updated_at). |
| Temps CI (p95) | 1.3min | 95e percentile duree workflow `ci.yml`. |
| Taux de succes CD | 77.8% | Runs `cd.yml` en succes / total runs `cd.yml` sur 30 jours. |
| Temps CD (p50) | 2.0min | Duree du workflow `cd.yml` (run_started_at -> updated_at). |

## Indicateurs applicatifs (extrait local de logs)

| KPI | Valeur | Note |
| --- | --- | --- |
| Nb logs INFO | 76 | Comptage simple sur `logs/*/*.log` (JSON lines). |
| Nb logs WARN | 3 | A relier a un seuil (ex: > X/h). |
| Nb logs ERROR | 0 | A relier a la fiabilite (ex: erreurs/req). |

## Commentaires / limites

- Les calculs DORA ci-dessus sont des *proxies* basees sur GitHub Actions; idealement, relier aux evenements prod (incidents, rollback, erreurs ELK post-deploy).
- Pour fiabilite, privilegier Kibana (taux d'erreurs, pics) plutot que les 2 fichiers `logs/*/*.log`.
- Assure-toi d'avoir au moins 3 executions (CI et CD) sur la periode pour que p50/p95 soient significatifs.
