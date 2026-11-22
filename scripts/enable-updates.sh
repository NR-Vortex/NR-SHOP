#!/usr/bin/env bash
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if (( EUID == 0 )); then
    echo "Run this as the Docker-enabled user who installed NR SHOP, without sudo." >&2
    exit 1
fi
docker info >/dev/null
systemctl --user show-environment >/dev/null
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
id=$(printf '%s' "$root" | sha256sum | cut -c1-16)
unit="nr-shop-update-$id"
mkdir -p -- "$unit_dir" "$root/.updates"
# Bot and API containers run as root, but mailbox files must be readable by the installing user.
chmod 700 "$root/.updates"
python3 - "$unit_dir" "$unit" "$root" <<'PY'
import json,sys
from pathlib import Path
directory,unit,root=sys.argv[1:]
quoted=json.dumps(root.replace('%','%%')+'/scripts/update_host.py',ensure_ascii=False)
Path(directory,f"{unit}.service").write_text(f"[Unit]\nDescription=NR SHOP release updater\n[Service]\nType=oneshot\nExecStart=/usr/bin/env python3 {quoted}\n")
Path(directory,f"{unit}.timer").write_text(f"[Unit]\nDescription=Check NR SHOP update requests\n[Timer]\nOnCalendar=minutely\nPersistent=true\nUnit={unit}.service\n[Install]\nWantedBy=timers.target\n")
PY
systemctl --user daemon-reload
systemctl --user enable --now "$unit.timer"
touch "$root/.updates/enabled"
echo "Updater enabled. Logs: journalctl --user -u $unit.service"
