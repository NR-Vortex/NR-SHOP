"""Release discovery and the local handoff from the bot to the host updater."""
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen

REPOSITORY = "NR-Vortex/NR-SHOP"
API = "https://api.github.com/repos/" + REPOSITORY
VERSION_PATTERN = re.compile(r"v([0-9]{1,6})\.([0-9]{1,6})\.([0-9]{1,6})")


def version_tuple(tag):
    match = VERSION_PATTERN.fullmatch(tag)
    if not match:
        raise ValueError("Unsupported release tag")
    return tuple(map(int, match.groups()))


def github_json(path):
    request = Request(API + path, headers={"Accept":"application/vnd.github+json","User-Agent":"NR-SHOP-updater"})
    with urlopen(request, timeout=12) as response:
        return json.load(response)


def latest_release():
    release = github_json("/releases/latest")
    version_tuple(release["tag_name"])
    if release["draft"] or release["prerelease"]:
        raise ValueError("Not a stable release")
    return release["tag_name"]


def installed(directory):
    return (directory / "VERSION").read_text(encoding="ascii").strip()


def write_json(path, payload):
    import tempfile
    with tempfile.NamedTemporaryFile(dir=path.parent, mode="w", encoding="utf8", delete=False) as tmp:
        try:
            json.dump(payload,tmp)
        except BaseException:
            Path(tmp.name).unlink(missing_ok=True)
            raise
    os.chmod(tmp.name,0o644)
    os.replace(tmp.name,path)
