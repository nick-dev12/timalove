"""Télécharge photos profil + vocaux accessibles vers MEDIA_ROOT."""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Message, Profile, ProfileGalleryPhoto


class Command(BaseCommand):
    help = "Sync URLs distantes (photos / vocaux publics) vers media/"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="0 = toutes")
        parser.add_argument("--skip-voice", action="store_true")

    def handle(self, *args, **options):
        limit = options["limit"]
        photos_dir = Path(settings.MEDIA_ROOT) / "profile-photos"
        voice_dir = Path(settings.MEDIA_ROOT) / "voice-messages"
        photos_dir.mkdir(parents=True, exist_ok=True)
        voice_dir.mkdir(parents=True, exist_ok=True)

        synced = failed = 0

        # Profile photos
        qs = Profile.objects.exclude(photo_url__isnull=True).exclude(photo_url="")
        if limit:
            qs = qs[:limit]
        for p in qs.iterator():
            ok = self._download(p.photo_url, photos_dir, p, "photo_url")
            synced += int(ok)
            failed += int(not ok)
            for field in ("photo_url_2", "photo_url_3"):
                url = getattr(p, field)
                if url and str(url).startswith("http"):
                    ok = self._download(url, photos_dir, p, field)
                    synced += int(ok)
                    failed += int(not ok)

        gqs = ProfileGalleryPhoto.objects.all()
        if limit:
            gqs = gqs[:limit]
        for g in gqs.iterator():
            if g.photo_url and g.photo_url.startswith("http"):
                ok = self._download(g.photo_url, photos_dir, g, "photo_url")
                synced += int(ok)
                failed += int(not ok)

        if not options["skip_voice"]:
            vqs = Message.objects.filter(message_type="voice").exclude(voice_url__isnull=True).exclude(voice_url="")
            if limit:
                vqs = vqs[:limit]
            for m in vqs.iterator():
                ok = self._download(m.voice_url, voice_dir, m, "voice_url")
                synced += int(ok)
                failed += int(not ok)

        self.stdout.write(self.style.SUCCESS(f"Sync terminée — ok:{synced} échecs:{failed}"))
        self.stdout.write("Note: les vocaux bucket privé Supabase peuvent échouer sans token.")

    def _download(self, url: str, dest_dir: Path, obj, field: str) -> bool:
        if not url or not str(url).startswith("http"):
            return False
        # déjà local
        if "/media/" in url and not url.startswith("http"):
            return False
        try:
            path = urlparse(url).path
            name = path.rstrip("/").split("/")[-1] or "file"
            name = name.split("?")[0]
            if not name or "." not in name:
                name = hashlib.sha1(url.encode()).hexdigest()[:16] + ".bin"
            # préfixe profile id si possible
            local = dest_dir / name
            if not local.exists():
                req = urllib.request.Request(url, headers={"User-Agent": "TimaLove-Sync/1.0"})
                with urllib.request.urlopen(req, timeout=20) as resp, open(local, "wb") as out:
                    out.write(resp.read())
            rel = f"{settings.MEDIA_URL}{dest_dir.name}/{name}"
            if getattr(obj, field) != rel:
                setattr(obj, field, rel)
                obj.save(update_fields=[field])
            return True
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"skip {url[:80]}… ({exc.__class__.__name__})"))
            return False
