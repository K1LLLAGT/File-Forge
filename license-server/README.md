# FileForge License Server

Turns purchases into license keys automatically. Receives **Gumroad** /
**Payhip** webhooks, verifies them, mints a signed FileForge key for the mapped
tier (using the same signing logic as the CLI, so keys validate everywhere),
stores it, and emails it to the buyer.

## Endpoints

| Method | Path                 | Purpose                                    |
|--------|----------------------|--------------------------------------------|
| POST   | `/webhook/gumroad`   | Gumroad Ping/webhook (form-encoded)        |
| POST   | `/webhook/payhip`    | Payhip webhook (form-encoded)              |
| GET    | `/license/{key}`     | verify a key (valid / tier / revoked)      |
| POST   | `/admin/revoke`      | revoke a key (`X-Admin-Token`)             |
| POST   | `/admin/issue`       | manually mint a key (`X-Admin-Token`)      |
| GET    | `/healthz`           | liveness                                   |

## Configure (env)

```bash
# Which product maps to which tier (Gumroad permalink / Payhip product id -> tier)
export FF_PRODUCT_MAP="pro-desktop=pro,cloud-lifetime=cloud,enterprise=enterprise"

# Signing salt — MUST match the CLI/engine (fileforge.licensing) in production
export FILEFORGE_SALT="your-long-random-secret"

# Gumroad verification: prefer an API token; seller-id is the fallback
export GUMROAD_ACCESS_TOKEN="..."      # or:
export GUMROAD_SELLER_ID="..."

# Payhip verification
export PAYHIP_SECRET="..."

# Admin + storage + email
export FF_ADMIN_TOKEN="..."
export FF_LICENSE_DB="/data/licenses.db"
export FF_SMTP_HOST="smtp.example.com"   # optional; logs to stdout if unset
export FF_SMTP_USER="..." FF_SMTP_PASS="..." FF_SMTP_FROM="sales@yourdomain"
```

> **Important:** set the same `FILEFORGE_SALT` here and wherever keys are
> validated. A server-issued key only verifies if both sides sign with the same
> salt. Keep it secret and stable — changing it invalidates every issued key.

## Run

```bash
pip install -e '.[server]'          # from the repo root
cd license-server
uvicorn app.main:app --port 8080
```

## Wire up the store

- **Gumroad:** Product → *Settings* → **Ping** → set the URL to
  `https://your-host/webhook/gumroad`. (Or use *Advanced → Webhooks*.)
- **Payhip:** *Account → Settings → Developers/Webhooks* → point at
  `https://your-host/webhook/payhip` and copy the secret into `PAYHIP_SECRET`.

## Notes

- **Idempotent:** duplicate webhook deliveries for the same sale return the
  original key instead of issuing a second one.
- **Verification-first:** a webhook with no configured way to verify it is
  rejected (403) rather than trusted.
- Deploys the same way as the Cloud API (see `../deploy/`): Docker, Fly.io,
  Railway, or a VPS.
