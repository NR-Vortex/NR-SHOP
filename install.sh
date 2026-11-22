#!/usr/bin/env bash
set -euo pipefail
umask 077

for command in curl tar docker openssl python3; do
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
telegram() {
    printf 'url = "https://api.telegram.org/bot%s/%s"\n' "$token" "$1" |
        curl --silent --fail --max-time 15 --config -
}

read -rsp "BotFather token: " token </dev/tty; echo
[[ "$token" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]] || { echo "Invalid token format." >&2; exit 1; }
if ! bot_name=$(telegram getMe | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["username"])' 2>/dev/null); then
    echo "Could not verify the token. Check the token and the server connection to Telegram." >&2
    exit 1
fi
if ! webhook=$(telegram getWebhookInfo | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["url"])' 2>/dev/null); then
    echo "Could not verify the bot polling settings." >&2
    exit 1
fi
if [[ -n "$webhook" ]]; then
    echo "This bot already has a webhook. Disconnect it from its current hosting before installing." >&2
    exit 1
fi

echo "Open https://t.me/$bot_name and press Start before entering your personal chat ID."
read -rp "Your numeric private Telegram chat ID: " chat_id </dev/tty
[[ "$chat_id" =~ ^[1-9][0-9]{0,15}$ ]] || { echo "Invalid private chat ID." >&2; exit 1; }
if ! telegram "getChat?chat_id=$chat_id" | python3 -c 'import json,sys; data=json.load(sys.stdin)["result"]; sys.exit(not (data["type"]=="private" and data["id"]==int(sys.argv[1])))' "$chat_id" 2>/dev/null; then
    echo "Chat not verified. Start the bot in private and check your numeric chat ID." >&2
    exit 1
fi
read -rp "Public DNS name for Mini App (blank for bot only): " domain </dev/tty
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
ADMIN_IDS=$chat_id
COMPOSE_PROJECT_NAME=nr-shop-${token%%:*}
POSTGRES_PASSWORD=$(openssl rand -hex 32)
VPN_PANEL_ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')
AGENCY_TOKEN_KEY=$(openssl rand -base64 32 | tr '+/' '-_')
MINIAPP_DOMAIN=$domain
MINIAPP_URL=$url
ENV
unset token
docker compose -f compose.production.yaml "${profile[@]}" up -d --build
echo "Installed in $destination"
echo "Open https://t.me/$bot_name and send /admin."
