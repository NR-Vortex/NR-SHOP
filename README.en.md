# NR SHOP · Telegram Store & Reseller Platform

[راهنمای فارسی](README.md)

A self-hosted Telegram shop for VPN subscriptions and digital products, with a central 3x-ui server, a reseller quota dashboard and a Persian RTL Mini App.

- VPN and AI catalog, discounts, wallet and manual bank receipt review
- Wholesale traffic balances and per-reseller configurations provisioned on your central 3x-ui
- Optional reseller storefront bots with their own customers, offers and payment destination
- Telegram admin console and Mini App with configurable button colors
- Sales reports, support tickets, required channel membership and database backups

## Install on Linux

Install Docker Engine with Compose v2, curl, and OpenSSL. Keep your BotFather token and numeric Telegram admin ID ready.

```bash
curl -fLo nr-shop-install.sh https://raw.githubusercontent.com/NR-Vortex/NR-SHOP/main/install.sh
bash nr-shop-install.sh
```

The installer generates secrets locally, runs database migrations and launches the services. Enter a DNS name pointing to the server to enable the public Mini App. Leave it blank for a bot-only setup.

| Port | Purpose |
| --- | --- |
| TCP 80 and 443 | Public Caddy ingress for HTTPS and certificate issuance |
| TCP 8080 | Mini App API on the internal Docker network |
| TCP 5432 | PostgreSQL on the internal Docker network |
| Outbound TCP 443 | Telegram Bot API. Allow outbound access to your configured 3x-ui endpoint as well. |

Send `/admin` in the bot. Add the central 3x-ui panel and inbound under VPN, then set the subscription URL and wholesale rate under reseller settings. For bank transfer checkout in the main shop, set `PAYMENT_BANK_NAME`, `PAYMENT_CARD_NUMBER`, and `PAYMENT_CARDHOLDER` in the local `.env` and recreate the services.

```bash
cd nr-shop
docker compose -f compose.production.yaml logs -f bot miniapp
docker compose -f compose.production.yaml --profile https up -d
```

Keep your `.env` and database backups private. Restoring encrypted credentials requires the original encryption keys.
