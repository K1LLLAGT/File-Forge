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

# Ed25519 signing key (the SECRET private key). Generate with:
#   python scripts/keygen.py
export FILEFORGE_PRIVATE_KEY="<private key from keygen>"
# The matching PUBLIC key is embedded in the client (or set FILEFORGE_PUBLIC_KEY
# here too if this server also verifies keys via /license/{key}).
export FILEFORGE_PUBLIC_KEY="<public key from keygen>"

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

> **Important:** the **private** key (`FILEFORGE_PRIVATE_KEY`) is your signing
> secret — keep it only on the server, never commit it, never ship it to
> clients. Clients need only the **public** key. Rotating the keypair
> invalidates every previously issued key, so keep it stable.

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
