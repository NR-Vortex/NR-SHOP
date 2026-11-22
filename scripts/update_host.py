"""Host-side runner. Install as a systemd user timer with enable-updates.sh."""
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.releases import API, github_json, installed, latest_release, version_tuple, write_json

QUEUE = ROOT / ".updates"
SOURCE_ROOTS = {"api","core","database","migrations","miniapp","modules","scripts","utils"}
SOURCE_FILES = {"main.py","config.py","alembic.ini","requirements.txt","Dockerfile",".dockerignore",
                ".gitignore",".env.example","compose.production.yaml","Caddyfile","install.sh","README.md","README.en.md","VERSION"}


def compose(*args,output=None):
    subprocess.run(["docker","compose","-f","compose.production.yaml",*args],cwd=ROOT,check=True,stdout=output)


def download(target, tag):
    # Resolve the release to an immutable Git commit before fetching files.
    ref=github_json(f"/commits/{tag}")["sha"]
    if len(ref)!=40 or any(c not in "0123456789abcdef" for c in ref):
        raise ValueError("Invalid commit ID")
    request=Request(API+f"/tarball/{ref}",headers={"User-Agent":"NR-SHOP-updater"})
    with urlopen(request,timeout=30) as response, target.open("wb") as stream:
        shutil.copyfileobj(response,stream)


def unpack(archive, destination):
    files=[]
    with tarfile.open(archive,"r:gz") as source:
        for member in source:
            parts=PurePosixPath(member.name).parts[1:]
            if not parts or not member.isfile() or ".." in parts or any("\\" in part for part in parts):
                continue
            first=parts[0]
            if len(parts)==1 and first not in SOURCE_FILES or len(parts)>1 and first not in SOURCE_ROOTS:
                continue
            if any(part.startswith(".") for part in parts) and len(parts)>1:
                continue
            relative=Path(*parts)
            target=destination/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            with source.extractfile(member) as contents,target.open("wb") as output:
                shutil.copyfileobj(contents,output)
            files.append(relative)
    return files


def backup(directory):
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    with (directory/"postgres.dump").open("xb") as output:
        compose("exec","-T","postgres","sh","-c",'exec pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"',output=output)
    code="""import os,sqlite3,sys,tempfile
source='/data/admin_settings.sqlite3'
with tempfile.TemporaryDirectory() as directory:
    path=directory+'/settings'
    with sqlite3.connect(path) as target:
        if os.path.exists(source):
            with sqlite3.connect(source) as database: database.backup(target)
        else: target.execute('VACUUM')
    with open(path,'rb') as data: sys.stdout.buffer.write(data.read())
"""
    with (directory/"admin_settings.sqlite3").open("xb") as output:
        compose("exec","-T","bot","python","-c",code,output=output)


def update(tag):
    if tag!=latest_release() or version_tuple(tag)<=version_tuple(installed(ROOT)):
        raise ValueError("Requested version is no longer the current stable upgrade")
    with tempfile.TemporaryDirectory(dir=ROOT) as staging:
        staging=Path(staging)
        archive=staging/"source.tar.gz"
        candidate=staging/"candidate"
        previous=ROOT/".update-backups"/f"{tag}-{time.time_ns()}"
        download(archive,tag)
        files=unpack(archive,candidate)
        if installed(candidate)!=tag:
            raise ValueError("Source version does not match release")
        backup(previous)
        for relative in files:
            path=ROOT/relative
            if path.is_file():
                snapshot=previous/"source"/relative
                snapshot.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(path,snapshot)
        replaced=[]
        try:
            for relative in files:
                (ROOT/relative).parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(candidate/relative,ROOT/relative)
                replaced.append(relative)
            compose("build","bot")
        except (OSError,subprocess.CalledProcessError):
            for relative in reversed(replaced):
                snapshot=previous/"source"/relative
                if snapshot.is_file():
                    shutil.copyfile(snapshot,ROOT/relative)
                else:
                    (ROOT/relative).unlink(missing_ok=True)
            raise
        # Keep the backup after migration. Do not automatically revert a changed schema.
        try:
            compose("run","--rm","--no-deps","migrate")
            compose("up","-d","--no-deps","--force-recreate","--wait","--wait-timeout","120","bot","miniapp")
        except subprocess.CalledProcessError:
            shutil.copyfile(previous/"source"/"VERSION",ROOT/"VERSION")
            raise
        return previous.name


def main():
    os.umask(0o077)
    QUEUE.mkdir(exist_ok=True)
    with (ROOT/".update.lock").open("a") as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            return
        request=QUEUE/"request.json"
        try:
            fd=os.open(request,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        except FileNotFoundError:
            return
        with os.fdopen(fd,"rb") as data:
            raw=data.read(1024)
        request.unlink(missing_ok=True)
        tag=json.loads(raw)["tag"]
        version_tuple(tag)
        write_json(QUEUE/"status.json",{"state":"running","tag":tag})
        try:
            snapshot=update(tag)
        except Exception:
            write_json(QUEUE/"status.json",{"state":"failed","tag":tag})
            raise
        write_json(QUEUE/"status.json",{"state":"done","tag":tag,"backup":snapshot})


if __name__=="__main__":
    main()
