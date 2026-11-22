#!/usr/bin/env bash
set -euo pipefail
umask 077

for command in curl tar docker openssl; do
    command -v "$command" >/dev/null || { echo "Missing dependency: $command" >&2; exit 1; }
done
docker compose version >/dev/null
docker info >/dev/null

destination="${1:-$PWD/nr-shop}"
ref="${NR_SHOP_REF:-main}"
[[ "$ref" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "Invalid release ref." >&2; exit 1; }
if [[ -e "$destination" || -L "$destination" ]]; then
    echo "Destination already exists: $destination" >&2
    exit 1
fi
read -rsp "BotFather token: " token </dev/tty; echo
read -rp "Telegram admin IDs (comma-separated): " admins </dev/tty
read -rp "Public DNS name for Mini App (blank for bot only): " domain </dev/tty
[[ "$token" =~ ^[0-9]+:[A-Za-z0-9_-]+$ && "$admins" =~ ^[0-9]+(,[0-9]+)*$ ]] || { echo "Invalid token format or admin IDs." >&2; exit 1; }
[[ -z "$domain" || "$domain" =~ ^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$ ]] || { echo "Invalid DNS name." >&2; exit 1; }

temp=$(mktemp -d)
trap 'rm -f -- "$temp/source.tar.gz"; rmdir -- "$temp"' EXIT
curl --fail --silent --show-error --location "https://github.com/NR-Vortex/NR-SHOP/archive/$ref.tar.gz" -o "$temp/source.tar.gz"
mkdir -- "$destination"
tar --extract --gzip --file "$temp/source.tar.gz" --directory "$destination" --strip-components=1
cd -- "$destination"
cp .env.example .env
url=""
profile=()
if [[ -n "$domain" ]]; then
    url="https://$domain/"
    profile=(--profile https)
fi
cat > .env <<ENV
BOT_TOKEN=$token
ADMIN_IDS=$admins
POSTGRES_PASSWORD=$(openssl rand -hex 32)
VPN_PANEL_ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')
AGENCY_TOKEN_KEY=$(openssl rand -base64 32 | tr '+/' '-_')
MINIAPP_DOMAIN=$domain
MINIAPP_URL=$url
ENV
unset token
docker compose -f compose.production.yaml "${profile[@]}" up -d --build
echo "Installed in $destination"
echo "Open your bot and send /admin."
