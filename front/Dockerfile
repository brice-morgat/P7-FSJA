FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 AS build

WORKDIR /workspace/front
COPY front/package*.json ./
RUN npm ci
COPY front/ ./
RUN npm run build

FROM caddy:2.8-alpine@sha256:af32e97399febea808609119bb21544d0265c58a02836576e32a2d082c262c17

COPY --from=build /workspace/front/dist/microcrm/browser/ /usr/share/caddy/
COPY misc/docker/Caddyfile /etc/caddy/Caddyfile

USER caddy

EXPOSE 8080

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile"]
