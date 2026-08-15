"""Sync parallèle des photos distantes restantes."""
from __future__ import annotations

import hashlib
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings

from core.models import Message, Profile, ProfileGalleryPhoto


def download(url: str, dest_dir: Path) -> str | None:
    if not url or not url.startswith("http"):
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = urlparse(url).path.rstrip("/").split("/")[-1].split("?")[0]
    if not name or "." not in name:
        name = hashlib.sha1(url.encode()).hexdigest()[:16] + ".bin"
    local = dest_dir / name
    if not local.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "TimaLove-Sync/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp, open(local, "wb") as out:
            out.write(resp.read())
    return f"{settings.MEDIA_URL}{dest_dir.name}/{name}"


def main():
    photos_dir = Path(settings.MEDIA_ROOT) / "profile-photos"
    voice_dir = Path(settings.MEDIA_ROOT) / "voice-messages"
    jobs = []

    for p in Profile.objects.filter(photo_url__startswith="http").iterator():
        jobs.append(("profile", p.id, "photo_url", p.photo_url, photos_dir))
        for f in ("photo_url_2", "photo_url_3"):
            u = getattr(p, f)
            if u and str(u).startswith("http"):
                jobs.append(("profile", p.id, f, u, photos_dir))

    for g in ProfileGalleryPhoto.objects.filter(photo_url__startswith="http").iterator():
        jobs.append(("gallery", g.id, "photo_url", g.photo_url, photos_dir))

    for m in Message.objects.filter(message_type="voice", voice_url__startswith="http").iterator():
        jobs.append(("message", m.id, "voice_url", m.voice_url, voice_dir))

    print(f"Jobs: {len(jobs)}")
    ok = fail = 0

    def work(job):
        kind, pk, field, url, dest = job
        try:
            rel = download(url, dest)
            return kind, pk, field, rel, None
        except Exception as exc:
            return kind, pk, field, None, str(exc)

    with ThreadPoolExecutor(max_workers=12) as ex:
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
            if i % 200 == 0:
                print(f"… {i}/{len(jobs)} ok={ok} fail={fail}")

    print(f"DONE ok={ok} fail={fail}")
    print("local profiles", Profile.objects.filter(photo_url__startswith="/media/").count())
    print("remote profiles", Profile.objects.filter(photo_url__startswith="http").count())


if __name__ == "__main__":
    main()
