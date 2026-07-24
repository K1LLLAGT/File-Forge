# Deploying FileForge Services

One Docker image (`deploy/Dockerfile`) runs **either** service; pick with the
`SERVICE` env var:

| SERVICE (env) | Service         | Code            |
|---------------|-----------------|-----------------|
| `cloud-api`   | Cloud Conversion API | `cloud-api/`  |
| `license`     | License Server  | `license-server/` |

Both listen on `$PORT` (default `8080`) and expose `GET /healthz`.

## Local / VPS (Docker Compose)

Runs both at once — Cloud API on `:8080`, License Server on `:8081`:

```bash
docker compose -f deploy/docker-compose.yml up --build
```

## Fly.io

```bash
fly launch --no-deploy --copy-config     # first time; uses deploy/fly.toml
fly deploy
# license server variant:
fly secrets set SERVICE=license
fly volumes create ffdata --size 1       # for the SQLite DB
fly secrets set FF_LICENSE_DB=/data/licenses.db
```

The `fly.toml` includes a `/healthz` check and scale-to-zero
(`min_machines_running = 0`) so an idle deployment costs nothing.

## Railway

```bash
railway init
railway up                               # uses deploy/railway.json + Dockerfile
railway variables set SERVICE=cloud-api  # or license
```

## Single container (any host)

```bash
docker build -f deploy/Dockerfile -t fileforge .
docker run -p 8080:8080 -e SERVICE=cloud-api fileforge
```

## Environment variables

**Cloud API** — demo API keys are seeded at startup; replace the key store in
`cloud-api/app/main.py` with a real one for production.

**License Server** — see `license-server/README.md`. At minimum set
`FF_PRODUCT_MAP`, `FILEFORGE_SALT`, a provider verification secret
(`GUMROAD_ACCESS_TOKEN`/`GUMROAD_SELLER_ID` or `PAYHIP_SECRET`), and
`FF_ADMIN_TOKEN`. Use a persistent volume for `FF_LICENSE_DB`.

## Cloudflare Workers

The plan lists Cloudflare Workers as a hosting target. The current services are
Python/ASGI, which don't run natively on Workers; options are (a) front the
Fly/Railway deployment with a Worker for caching/routing, or (b) port the
conversion endpoints to a Python Worker (Pyodide) for the lightweight routes.
The Docker image above is the supported path today.

## Notes

- ffmpeg is installed in the image for the Pro video presets. Remove that line
  from the `Dockerfile` to shrink the image if you don't need server-side video.
- The image runs as a non-root user.
