# Documentation technique - Publication des images Docker

Cette documentation decrit les commandes importantes de la chaine CI/CD MicroCRM.

## Workflow CD

Le workflow est defini dans `.github/workflows/cd.yml`.

| Commande ou action | Objectif | Ou elle est definie | Moment d'execution |
| --- | --- | --- | --- |
| `actions/checkout@v4` | Recuperer le code source a publier. | `.github/workflows/cd.yml`, job `publish`. | Au debut du job CD. |
| `owner_repo="${GITHUB_REPOSITORY,,}"` | Convertir le chemin `owner/repo` en minuscules pour respecter les contraintes de nommage Docker/GHCR. | Job `publish`, etape `Compute image names and tags`. | Avant l'authentification au registre. |
| `sha_tag="sha-${GITHUB_SHA}"` | Generer un tag immuable base sur le SHA du commit. | Job `publish`, etape `Compute image names and tags`. | Avant les builds Docker. |
| `docker/login-action@v3` | Authentifier Docker aupres de `ghcr.io` avec le `GITHUB_TOKEN` fourni par GitHub Actions. | Job `publish`, etape `Log in to GitHub Container Registry`. | Juste avant les publications d'images. |
| `docker/build-push-action@v6` avec `file: ./back/Dockerfile` | Construire l'image back-end depuis le Dockerfile dedie et la publier. | Job `publish`, etape `Build and publish back-end image`. | Apres la connexion a GHCR. |
| `docker/build-push-action@v6` avec `file: ./front/Dockerfile` | Construire l'image front-end depuis le Dockerfile dedie et la publier. | Job `publish`, etape `Build and publish front-end image`. | Apres la publication de l'image back-end. |

## Matrice des commandes importantes (CI, CD, local)

| Commande ou action | Objectif | Ou elle est definie | Moment d'execution |
| --- | --- | --- | --- |
| `./gradlew test` | Lancer tous les tests back-end Spring Boot. | `.github/workflows/ci.yml` (job `backend`) et `back/gradlew`. | CI et local. |
| `./gradlew build` | Compiler le back-end et produire l'artefact JAR. | `.github/workflows/ci.yml` (job `backend`) et `back/build.gradle`. | CI et local. |
| `npm ci` | Installer les dependances front-end de maniere reproductible. | `.github/workflows/ci.yml` (job `frontend`), `front/Dockerfile`, et `front/package-lock.json`. | CI, CD (build image), local. |
| `npm run build` | Construire l'application Angular de production. | `.github/workflows/ci.yml` (job `frontend`), `front/package.json`, et `front/Dockerfile`. | CI, CD (build image), local. |
| `npm test -- --watch=false --browsers=ChromeHeadlessNoSandbox` | Lancer les tests front en mode non interactif pour CI. | `.github/workflows/ci.yml` (job `frontend`) et `front/package.json` (script `test`). | CI. |
| `SonarSource/sonarqube-scan-action` | Executer l'analyse de qualite SonarQube Cloud. | `.github/workflows/ci.yml` (job `sonarqube`). | CI apres succes des jobs `backend` et `frontend`. |
| `docker/login-action@v3` | Authentifier Docker vers `ghcr.io` avec token GitHub ephemere. | `.github/workflows/cd.yml` (job `publish`). | CD. |
| `docker/build-push-action@v6` (`file: ./back/Dockerfile`) | Construire et publier l'image GHCR du back-end. | `.github/workflows/cd.yml` (job `publish`) et `back/Dockerfile`. | CD sur `main`, tag `v*` ou declenchement manuel. |
| `docker/build-push-action@v6` (`file: ./front/Dockerfile`) | Construire et publier l'image GHCR du front-end. | `.github/workflows/cd.yml` (job `publish`) et `front/Dockerfile`. | CD apres publication back-end. |
| `docker compose up --build` | Construire et lancer l'application complete en local avec Docker. | `docker-compose.yml`. | Local. |

## Dockerfiles applicatifs

Les Dockerfiles applicatifs sont definis dans `back/Dockerfile` et `front/Dockerfile`.

| Commande | Objectif | Dockerfile concerne | Moment d'execution |
| --- | --- | --- | --- |
| `gradle --no-daemon clean build` | Compiler le back-end Spring Boot et executer la validation Gradle necessaire a la creation du JAR. | `back/Dockerfile` | Pendant le build de l'image back-end. |
| `java -jar /app/microcrm.jar` | Demarrer l'application Spring Boot dans l'image finale. | `back/Dockerfile` | Au lancement du conteneur back-end. |
| `npm ci` | Installer les dependances front-end de maniere reproductible depuis `package-lock.json`. | `front/Dockerfile` | Pendant le build de l'image front-end. |
| `npm run build` | Generer les fichiers statiques Angular de production. | `front/Dockerfile` | Pendant le build de l'image front-end. |
| `caddy run --config /etc/caddy/Caddyfile` | Servir les fichiers statiques Angular via Caddy. | `front/Dockerfile` | Au lancement du conteneur front-end. |

## Declenchement

Le CD est declenche automatiquement sur un `push` vers `main` ou lors de la creation d'un tag de release dont le nom commence par `v`. Il peut aussi etre lance manuellement avec `workflow_dispatch`.

Le workflow ne publie pas d'image sur une pull request.

La dependance "CI validee avant CD" est assuree par la protection de branche `main`: le depot doit exiger la reussite du workflow `CI` avant d'autoriser un merge vers `main`. Le CD publie ensuite le code arrive sur `main` ou un tag `v*` cree depuis un commit de release valide.

## Permissions et secrets

Le workflow utilise uniquement les permissions GitHub Actions suivantes:

- `contents: read` pour lire le depot.
- `packages: write` pour publier dans GitHub Container Registry.

Aucun secret applicatif, token Docker Hub ou mot de passe en clair n'est stocke dans le depot. L'authentification a GHCR utilise exclusivement `secrets.GITHUB_TOKEN`, genere automatiquement par GitHub Actions.

Le token SonarQube est lu uniquement depuis `secrets.SONAR_TOKEN` dans le workflow CI. Il n'est jamais committe dans le depot.
