"""Import depuis export SQL TimaLove (format INSERT VALUES)."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.controllers import site_settings_controller
from core.models import Profile, SiteSetting, Testimonial
from core.models.choices import Gender, RegistrationStatus, UserRole

User = get_user_model()

ROW_RE = re.compile(
    r"^\s*\('([0-9a-f-]{36})'::uuid,'((?:\\'|[^'])*)','((?:\\'|[^'])*)',(?:'((?:\\'|[^'])*)'|NULL),",
    re.I,
)


class Command(BaseCommand):
    help = "Importe profiles / testimonials / site_settings depuis le dump INSERT SQL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dump",
            default=str(Path(__file__).resolve().parents[4] / "tinalove" / "export_202608111550.sql"),
        )
        parser.add_argument("--limit-profiles", type=int, default=300)

    def handle(self, *args, **options):
        dump = Path(options["dump"])
        if not dump.exists():
            raise CommandError(f"Dump introuvable: {dump}")

        site_settings_controller.seed_defaults()
        self.stdout.write("Scan du dump…")

        section = None
        profiles = 0
        testimonials = 0
        settings_n = 0
        limit = options["limit_profiles"]

        with dump.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if line.startswith("INSERT INTO public.profiles"):
                    section = "profiles"
                    continue
                if line.startswith("INSERT INTO public.testimonials"):
                    section = "testimonials"
                    continue
                if line.startswith("INSERT INTO public.site_settings"):
                    section = "settings"
                    continue
                if line.startswith("INSERT INTO public."):
                    section = None
                    continue

                if section == "profiles" and profiles < limit:
                    if self._import_profile_line(line):
                        profiles += 1
                elif section == "testimonials":
                    if self._import_testimonial_line(line):
                        testimonials += 1
                elif section == "settings":
                    if self._import_setting_line(line):
                        settings_n += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import OK — profiles:{profiles} testimonials:{testimonials} settings:{settings_n}"
            )
        )
        self.stdout.write(
            self.style.WARNING("Mots de passe importés = ChangeMe123! (non portables depuis Supabase)")
        )

    @transaction.atomic
    def _import_profile_line(self, line: str) -> bool:
        # Extraction pragmatique des champs principaux via split SQL naïf
        if "'::uuid" not in line or not line.strip().startswith("("):
            return False
        try:
            # id
            m = re.search(r"'([0-9a-f-]{36})'::uuid", line, re.I)
            if not m:
                return False
            pid = m.group(1)
            # strings quoted in order after uuid: first_name, last_name, email, phone, date, ...
            strings = re.findall(r"'(?:\\'|[^'])*'", line)
            # strings[0] is uuid already captured differently; first quoted after cast varies
            # Better: remove casts then parse
            cleaned = re.sub(r"::[a-zA-Z0-9_.\"]+", "", line)
            vals = self._split_sql_values(cleaned)
            if len(vals) < 10:
                return False
            pid = vals[0].strip("'")
            first_name = vals[1].strip("'")
            last_name = vals[2].strip("'")
            email = None if vals[3] == "NULL" else vals[3].strip("'")
            phone = None if vals[4] == "NULL" else vals[4].strip("'")
            dob = vals[5].strip("'")[:10]
            gender = vals[6].strip("'")
            city = vals[7].strip("'")
            country = vals[8].strip("'") if vals[8] != "NULL" else "Sénégal"
            photo_url = None
            # photo_url is around index 14
            if len(vals) > 14 and vals[14] != "NULL":
                photo_url = vals[14].strip("'")
            role = UserRole.MEMBER
            if len(vals) > 18 and "admin" in vals[18]:
                role = UserRole.ADMIN
            reg = RegistrationStatus.APPROVED
            if len(vals) > 17 and "pending" in vals[17]:
                reg = RegistrationStatus.PENDING
            elif len(vals) > 17 and "rejected" in vals[17]:
                reg = RegistrationStatus.REJECTED

            if not email:
                email = f"user_{pid[:8]}@import.timalove.local"
            user, created = User.objects.get_or_create(
                username=email[:150],
                defaults={"email": email},
            )
            if created:
                user.set_password("ChangeMe123!")
                user.first_name = first_name
                user.last_name = last_name
                user.save()

            Profile.objects.update_or_create(
                id=pid,
                defaults={
                    "user": user,
                    "first_name": first_name or "Membre",
                    "last_name": last_name or "",
                    "email": email,
                    "phone": phone,
                    "date_of_birth": date.fromisoformat(dob) if dob else date(1995, 1, 1),
                    "gender": gender if gender in Gender.values else Gender.FEMALE,
                    "city": city or "Dakar",
                    "country": country or "Sénégal",
                    "photo_url": photo_url,
                    "registration_status": reg,
                    "role": role,
                },
            )
            return True
        except Exception as exc:
            self.stderr.write(f"skip profile: {exc}")
            return False

    def _import_testimonial_line(self, line: str) -> bool:
        if "'::uuid" not in line or not line.strip().startswith("("):
            return False
        try:
            cleaned = re.sub(r"::[a-zA-Z0-9_.\"]+", "", line)
            vals = self._split_sql_values(cleaned)
            if len(vals) < 5:
                return False
            tid = vals[0].strip("'")
            # flexible field order — search dump columns if needed
            author = vals[1].strip("'") if vals[1] != "NULL" else "Anonyme"
            content = vals[2].strip("'") if len(vals) > 2 and vals[2] != "NULL" else ""
            # Sometimes content is later — keep best effort
            Testimonial.objects.update_or_create(
                id=tid,
                defaults={
                    "author_name": author[:120],
                    "content": content or author,
                    "rating": 5,
                    "is_published": "true" in line.lower() or "t," in line.lower(),
                },
            )
            return True
        except Exception:
            return False

    def _import_setting_line(self, line: str) -> bool:
        m = re.search(r"\('([^']+)'\s*,\s*('.*?'|NULL|true|false|\d+|\{.*?\})", line)
        if not m:
            # tab-like: ('key', 'value'::jsonb)
            m2 = re.search(r"\('([^']+)',\s*(.+?)(?:::jsonb)?\)", line)
            if not m2:
                return False
            key, raw = m2.group(1), m2.group(2)
        else:
            key, raw = m.group(1), m.group(2)
        raw = raw.strip()
        value = _parse_jsonish(raw.strip("'") if raw.startswith("'") else raw)
        SiteSetting.objects.update_or_create(key=key, defaults={"value": value})
        return True

    def _split_sql_values(self, line: str) -> list[str]:
        # strip leading ( and trailing ),
        s = line.strip().rstrip(",").rstrip(";")
        if s.startswith("("):
            s = s[1:]
        if s.endswith(")"):
            s = s[:-1]
        vals: list[str] = []
        cur = ""
        in_str = False
        i = 0
        while i < len(s):
            ch = s[i]
            if ch == "'" and not in_str:
                in_str = True
                cur += ch
            elif ch == "'" and in_str:
                if i + 1 < len(s) and s[i + 1] == "'":
                    cur += "''"
                    i += 1
                else:
                    in_str = False
                    cur += ch
            elif ch == "," and not in_str:
                vals.append(cur.strip())
                cur = ""
            else:
                cur += ch
            i += 1
        if cur.strip():
            vals.append(cur.strip())
        return vals


def _parse_jsonish(v: str):
    import json

    if v in ("NULL", None):
        return {}
    if v in ("true", "t", "True"):
        return True
    if v in ("false", "f", "False"):
        return False
    try:
        return json.loads(v)
    except Exception:
        try:
            return int(v)
        except Exception:
            return v
