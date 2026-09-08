"""Sync complete des medias distants restants (photos + vocaux) vers MEDIA_ROOT.

- Photos en http(s) : telechargement avec retries + miroirs media/supabase
- Vocaux en chemin relatif storage : download via SERVICE_ROLE Supabase
- Reecrit les chemins DB en /media/...

Usage :
  cd timalove
  python -u sync_media_parallel.py
"""
from __future__ import annotations

import hashlib
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse, unquote

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings

from core.models import Message, Profile, ProfileGalleryPhoto

SUPABASE_URL = "https://unuujqaicghkhtjvhbdw.supabase.co"
MEDIA_CDN = "https://media.mytimalove.com"
MAX_RETRIES = 4
WORKERS = 10


def load_service_key() -> str | None:
    candidates = [
        Path(__file__).resolve().parents[1] / "tinalove" / ".env.local",
        Path(r"c:\wamp64\www\projet_timalove\tinalove\.env.local"),
    ]
    for env_path in candidates:
        if not env_path.is_file():
            continue
        for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line.startswith("SUPABASE_SERVICE_ROLE_KEY="):
                continue
            val = line.split("=", 1)[1].strip().strip('"').strip("'")
            if val:
                return val
    return os.environ.get("SUPABASE_SERVICE_ROLE_KEY")


def mirrors_for(url: str) -> list[str]:
    urls = [url]
    if "media.mytimalove.com" in url:
        urls.append(url.replace(MEDIA_CDN, SUPABASE_URL))
    elif "supabase.co" in url:
        urls.append(url.replace(SUPABASE_URL, MEDIA_CDN))
    # dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def filename_from_url(url: str) -> str:
    name = unquote(urlparse(url).path.rstrip("/").split("/")[-1].split("?")[0])
    if not name or "." not in name:
        name = hashlib.sha1(url.encode()).hexdigest()[:16] + ".bin"
    return name


def download_http(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return
    last_err: Exception | None = None
    for candidate in mirrors_for(url):
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(
                    candidate,
                    headers={"User-Agent": "TimaLove-Sync/2.0", "Accept": "*/*"},
                )
                with urllib.request.urlopen(req, timeout=45) as resp, open(dest, "wb") as out:
                    while True:
                        chunk = resp.read(1024 * 256)
                        if not chunk:
                            break
                        out.write(chunk)
                if dest.exists() and dest.stat().st_size > 0:
                    return
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                if dest.exists():
                    try:
                        dest.unlink()
                    except OSError:
                        pass
                time.sleep(min(2 * attempt, 6))
    raise RuntimeError(f"http fail: {last_err}")


_supabase_client = None


def download_storage(bucket: str, object_path: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return
    # Essai public d'abord
    public_urls = [
        f"{MEDIA_CDN}/storage/v1/object/public/{bucket}/{object_path}",
        f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{object_path}",
    ]
    for u in public_urls:
        try:
            download_http(u, dest)
            return
        except Exception:
            continue
    # Authentifie (bucket prive)
    key = load_service_key()
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY manquante (.env.local)")
    auth_urls = [
        f"{SUPABASE_URL}/storage/v1/object/{bucket}/{object_path}",
        f"{SUPABASE_URL}/storage/v1/object/authenticated/{bucket}/{object_path}",
    ]
    last_err: Exception | None = None
    for auth_url in auth_urls:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(
                    auth_url,
                    headers={
                        "User-Agent": "TimaLove-Sync/2.0",
                        "Authorization": f"Bearer {key}",
                        "apikey": key,
                        "Accept": "*/*",
                    },
                )
                with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
                    while True:
                        chunk = resp.read(1024 * 256)
                        if not chunk:
                            break
                        out.write(chunk)
                if dest.exists() and dest.stat().st_size > 0:
                    return
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                if dest.exists():
                    try:
                        dest.unlink()
                    except OSError:
                        pass
                time.sleep(min(2 * attempt, 6))
    raise RuntimeError(f"storage fail {bucket}/{object_path}: {last_err}")


def media_url_for(rel_under_media: str) -> str:
    # settings.MEDIA_URL is typically /media/
    base = settings.MEDIA_URL.rstrip("/")
    return f"{base}/{rel_under_media.lstrip('/')}"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    photos_dir = Path(settings.MEDIA_ROOT) / "profile-photos"
    voice_dir = Path(settings.MEDIA_ROOT) / "voice-messages"
    jobs: list[tuple] = []

    for p in Profile.objects.filter(photo_url__startswith="http").iterator():
        jobs.append(("profile", p.id, "photo_url", p.photo_url, "http", photos_dir))
        for f in ("photo_url_2", "photo_url_3"):
            u = getattr(p, f)
            if u and str(u).startswith("http"):
                jobs.append(("profile", p.id, f, u, "http", photos_dir))

    for g in ProfileGalleryPhoto.objects.filter(photo_url__startswith="http").iterator():
        jobs.append(("gallery", g.id, "photo_url", g.photo_url, "http", photos_dir))

    for m in Message.objects.exclude(voice_url__isnull=True).exclude(voice_url="").iterator():
        u = str(m.voice_url)
        if u.startswith("http"):
            jobs.append(("message", m.id, "voice_url", u, "http", voice_dir))
        elif not u.startswith("/media"):
            # chemin relatif bucket voice-messages
            jobs.append(("message", m.id, "voice_url", u, "voice", voice_dir))

    print(f"Jobs: {len(jobs)}", flush=True)
    ok = fail = 0
    fail_samples: list[str] = []

    def work(job):
        kind, pk, field, url_or_path, mode, dest_dir = job
        try:
            if mode == "http":
                name = filename_from_url(url_or_path)
                local = dest_dir / name
                download_http(url_or_path, local)
                rel = media_url_for(f"{dest_dir.name}/{name}")
            else:
                # preserve nested path under voice-messages/
                object_path = url_or_path.lstrip("/")
                local = dest_dir / object_path
                download_storage("voice-messages", object_path, local)
                rel = media_url_for(f"voice-messages/{object_path}")
            return kind, pk, field, rel, None
        except Exception as exc:  # noqa: BLE001
            return kind, pk, field, None, str(exc)

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = [ex.submit(work, j) for j in jobs]
        for i, fut in enumerate(as_completed(futures), 1):
            kind, pk, field, rel, err = fut.result()
            if rel:
                if kind == "profile":
                    Profile.objects.filter(pk=pk).update(**{field: rel})
                elif kind == "gallery":
                    ProfileGalleryPhoto.objects.filter(pk=pk).update(**{field: rel})
                else:
                    Message.objects.filter(pk=pk).update(**{field: rel})
                ok += 1
            else:
                fail += 1
                if len(fail_samples) < 8:
                    fail_samples.append(err or "unknown")
            if i % 50 == 0 or i == len(jobs):
                print(f"… {i}/{len(jobs)} ok={ok} fail={fail}", flush=True)

    print(f"DONE ok={ok} fail={fail}", flush=True)
    if fail_samples:
        print("Exemples erreurs:", flush=True)
        for s in fail_samples:
            print(f"  - {s[:200]}", flush=True)
    print("local profiles", Profile.objects.filter(photo_url__startswith="/media/").count(), flush=True)
    print("remote profiles", Profile.objects.filter(photo_url__startswith="http").count(), flush=True)
    print(
        "gallery remote",
        ProfileGalleryPhoto.objects.filter(photo_url__startswith="http").count(),
        flush=True,
    )
    print(
        "voice local /media",
        Message.objects.filter(voice_url__startswith="/media/").count(),
        flush=True,
    )
    print(
        "voice relative restants",
        Message.objects.exclude(voice_url__isnull=True)
        .exclude(voice_url="")
        .exclude(voice_url__startswith="http")
        .exclude(voice_url__startswith="/media")
        .count(),
        flush=True,
    )


if __name__ == "__main__":
    main()
