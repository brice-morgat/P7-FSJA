<p align="center">
   <img src="./front/src/favicon.png" width="192px" />
</p>

# MicroCRM (P7 - Développeur Full-Stack - Java et Angular - Mettez en œuvre l'intégration et le déploiement continu d'une application Full-Stack)

MicroCRM est une application de démonstration basique ayant pour être objectif de servir de socle pour le module "P7 - Développeur Full-Stack".

L'application MicroCRM est une implémentation simplifiée d'un ["CRM" (Customer Relationship Management)](https://fr.wikipedia.org/wiki/Gestion_de_la_relation_client). Les fonctionnalités sont limitées à la création, édition et la visualisations des individus liés à des organisations.

![Page d'accueil](./misc/screenshots/screenshot_1.png)
![Édition de la fiche d'un individu](./misc/screenshots/screenshot_2.png)

## Code source

### Organisation

Ce [monorepo](https://en.wikipedia.org/wiki/Monorepo) contient les 2 composantes du projet "MicroCRM":

- La partie serveur (ou "backend"), en Java SpringBoot 3;
- La partie cliente (ou "frontend"), en Angular 17.

### Démarrer avec les sources

#### Serveur

##### Dépendances

- [OpenJDK >= 17](https://openjdk.org/)

##### Procédure

1. Se positionner dans le répertoire `back` avec une invite de commande:

   ```shell
   cd back
   ```

2. Construire le JAR:

   ```shell
   # Sur Linux
   ./gradlew build

   # Sur Windows
   gradlew.bat build
   ```

3. Démarrer le service:

   ```shell
   java -jar build/libs/microcrm-0.0.1-SNAPSHOT.jar
   ```

Puis ouvrir l'URL http://localhost:8080 dans votre navigateur.

#### Client

##### Dépendances

- [NPM >= 10.2.4](https://www.npmjs.com/)

##### Procédure

1. Se positionner dans le répertoire `front` avec une invite de commande:

   ```shell
   cd front
   ```

2. (La première fois seulement) Installer les dépendances NodeJS:

   ```shell
   npm install
   ```

3. Démarrer le service de développement:

   ```shell
   npx @angular/cli serve
   ```

Puis ouvrir l'URL http://localhost:4200 dans votre navigateur.

### Exécution des tests

#### Client

**Dépendances**

- Google Chrome ou Chromium

Dans votre terminal:

```shell
cd front
CHROME_BIN=</path/to/google/chrome> npm test
```

#### Serveur

Dans votre terminal:

```shell
cd back
./gradlew test
```

## CI/CD

Le projet utilise GitHub Actions pour automatiser la validation du monorepo.
Le workflow CI se trouve dans `.github/workflows/ci.yml` et se compose de trois
jobs separes:

- `Back-end`: installe Java 17, utilise le cache Gradle, lance les tests puis
  le build Spring Boot depuis le dossier `back`.
- `Front-end`: installe Node.js 20, restaure le cache npm, installe les
  dependances avec `npm ci`, lance le build Angular puis les tests Karma en
  mode non interactif avec `ChromeHeadlessNoSandbox`.
- `SonarQube Cloud`: s'execute apres les jobs back-end et front-end, puis lance
  l'analyse SonarQube Cloud sur le code Java et TypeScript.

Le pipeline se declenche sur:

- chaque `push`;
- chaque `pull_request`;
- une execution manuelle via `workflow_dispatch`;
- une execution planifiee hebdomadaire.

L'analyse SonarQube Cloud necessite le secret GitHub `SONAR_TOKEN`, a declarer
dans les secrets du depot. La valeur du token ne doit jamais etre stockee dans
le code, affichee dans les logs ou ajoutee dans un fichier `.env`.
Dans un fork sans `SONAR_TOKEN`, le job SonarQube est automatiquement ignore
pour eviter un echec CI lie a l'absence de secret.

### Déploiement / Publication des images Docker

La publication des images Docker est geree par le workflow CD
`.github/workflows/cd.yml`.

Le CD est declenche automatiquement sur un `push` vers `main` ou lors de la
creation d'un tag de release commencant par `v`. Il peut aussi etre lance
manuellement avec `workflow_dispatch`. Une simple pull request ne publie aucune
image.

La garantie "CI validee avant CD" repose sur la protection de branche `main`:
la branche `main` doit exiger la reussite du workflow `CI` avant merge. Le CD
publie donc uniquement du code arrive sur `main` apres validation CI, ou un tag
`v*` cree depuis un commit de release valide.

Les images sont publiees dans GitHub Container Registry:

- `ghcr.io/<owner>/<repo>/microcrm-back`
- `ghcr.io/<owner>/<repo>/microcrm-front`

Les noms d'images sont convertis en minuscules dans le workflow avant la
publication.

Tags generes:

- `sha-<commit_sha>` pour chaque publication back-end et front-end.
- `latest` uniquement lorsque la publication concerne la branche `main`.

Le workflow utilise les permissions minimales `contents: read` et
`packages: write`. L'authentification a `ghcr.io` utilise le `GITHUB_TOKEN`
fourni automatiquement par GitHub Actions via `docker/login-action`; aucun
token Docker Hub, mot de passe ou secret de publication n'est stocke dans le
depot.

La documentation technique detaillee des commandes CD se trouve dans
[`docs/deploiement-images-docker.md`](docs/deploiement-images-docker.md).

## Docker

Le projet utilise deux Dockerfiles dedies:

- `front/Dockerfile` pour le front Angular (build Node 20 + runtime Caddy).
- `back/Dockerfile` pour le back Spring Boot (build Gradle JDK 17 + runtime JRE 17 non-root).

### Lancer l'application avec Docker Compose

```shell
docker compose up --build
```

Mode detache:

```shell
docker compose up --build -d
```

Arreter l'application:

```shell
docker compose down
```

### Ports utilises

- Front-end: http://localhost:4200
- Back-end: http://localhost:8080

### Centraliser les logs (ELK)

Voir `docs/elk.md`.

### Construire les images individuellement

```shell
docker build -f front/Dockerfile -t orion-microcrm-front:local .
docker build -f back/Dockerfile -t orion-microcrm-back:local .
```

### Justification technique

- Multi-stage build conserve pour separer build et runtime.
- Images officielles legeres (`node:20-alpine`, `gradle:8.7-jdk17-alpine`, `caddy:2.8-alpine`, `eclipse-temurin:17-jre-alpine`).
- Front statique servi par Caddy avec fallback SPA (`try_files ... /index.html`).
- Back expose en `8080`.
- Aucun secret embarque dans les images.
