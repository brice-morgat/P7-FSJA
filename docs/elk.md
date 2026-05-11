# ELK (local)

Demarrage:

```bash
docker compose -f docker-compose-elk.yml up -d
docker compose up -d
```

Kibana: `http://localhost:5601`

Data View: `microcrm-logs-*` (time field `@timestamp`).

Les logs applicatifs sont ecrits dans `logs/backend/backend.log` et `logs/frontend/frontend.log`, puis lus par Logstash.

## Kibana: erreur Elastic Package Registry (EPR)

Si Kibana affiche `Kibana cannot connect to the Elastic Package Registry`, ce n'est pas un probleme Elasticsearch/Logstash: c'est Kibana (Fleet/Integrations) qui n'a pas de sortie reseau vers l'EPR.

Dans ce repo, Kibana est configure via `elk/kibana/kibana.yml`. En environnement avec proxy ou registry interne, configure:

- `xpack.fleet.registryProxyUrl` via la variable `FLEET_REGISTRY_PROXY_URL`
- `xpack.fleet.registryUrl` via la variable `FLEET_REGISTRY_URL`

Puis relance:

```bash
docker compose -f docker-compose-elk.yml up -d --force-recreate
```
