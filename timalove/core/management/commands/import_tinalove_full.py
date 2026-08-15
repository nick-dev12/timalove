"""
Import COMPLET du dump SQL TimaLove vers Django (3 passes).
Le dump place matches/messages AVANT profiles → il faut multi-pass.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.controllers import site_settings_controller
from core.models import (
    BannedIdentity,
    BlockedUser,
    ConversationHide,
    Match,
    Message,
    Notification,
    Profile,
    ProfileGalleryPhoto,
    Report,
    SiteSetting,
    Swipe,
    Testimonial,
    Transaction,
)
from core.models.choices import (
    Gender,
    MatchStatus,
    MessageType,
    NotificationType,
    RegistrationStatus,
    ReportReason,
    ReportStatus,
    SubscriptionStatus,
    SubscriptionTier,
    SwipeAction,
    TransactionStatus,
    TransactionType,
    UserRole,
)

User = get_user_model()

TABLE_MAP = {
    "site_settings": "settings",
    "profiles": "profiles",
    "profile_gallery_photos": "gallery",
    "banned_identities": "bans",
    "blocked_users": "blocks",
    "swipes": "swipes",
    "matches": "matches",
    "messages": "messages",
    "conversation_hides": "hides",
    "notifications": "notifications",
    "transactions": "transactions",
    "reports": "reports",
    "testimonials": "testimonials",
}


class Command(BaseCommand):
    help = "Import complet dump SQL → Django (toutes tables métier)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dump",
            default=str(Path(__file__).resolve().parents[4] / "tinalove" / "export_202608111550.sql"),
        )
        parser.add_argument("--only", default="", help="Limiter: profiles,messages,...")

    def handle(self, *args, **options):
        dump = Path(options["dump"])
        if not dump.exists():
            raise CommandError(f"Dump introuvable: {dump}")

        only = {x.strip() for x in options["only"].split(",") if x.strip()}
        site_settings_controller.seed_defaults()
        counts: dict[str, int] = {}

        self.stdout.write(self.style.WARNING(
            f"Import complet {dump.name} ({dump.stat().st_size // 1_000_000} Mo)"
        ))

        self.stdout.write("Pass 1/3 - profiles & settings...")
        target1 = only & {"profiles", "settings"} if only else {"profiles", "settings"}
        self.profile_ids = set()
        self.match_ids = set()
        self._scan(dump, target1, counts)
        self.profile_ids = {str(x) for x in Profile.objects.values_list("id", flat=True)}
        self.stdout.write(f"  -> {len(self.profile_ids)} profils")
        self.stdout.write("Pass 2/3 - gallery, swipes, matches, blocks, bans, transactions...")
        target2 = {
            "gallery", "bans", "blocks", "swipes", "matches",
            "transactions", "reports", "testimonials",
        }
        if only:
            target2 &= only
        self._scan(dump, target2, counts)
        self.match_ids = {str(x) for x in Match.objects.values_list("id", flat=True)}
        self.stdout.write(f"  -> {len(self.match_ids)} matchs, swipes={counts.get('swipes', 0)}")

        self.stdout.write("Pass 3/3 - messages, notifications, conversation_hides...")
        target3 = {"messages", "notifications", "hides"}
        if only:
            target3 &= only
        self._scan(dump, target3, counts)

        self.stdout.write(self.style.SUCCESS(f"Import terminé: {counts}"))
        self.stdout.write(self.style.WARNING("Mots de passe importés = ChangeMe123!"))

    def _scan(self, dump: Path, allowed: set[str], counts: dict) -> None:
        if not allowed:
            return
        section = None
        batch: list = []
        batch_table = None

        def flush():
            nonlocal batch, batch_table
            if not batch or not batch_table:
                batch = []
                return
            n = self._flush(batch_table, batch)
            counts[batch_table] = counts.get(batch_table, 0) + n
            batch = []

        with dump.open("r", encoding="utf-8", errors="ignore") as fh:
            for line_no, line in enumerate(fh, 1):
                if line.startswith("INSERT INTO public."):
                    flush()
                    table = line.split("INSERT INTO public.")[1].split(" ")[0].split("(")[0]
                    section = TABLE_MAP.get(table)
                    batch_table = section
                    continue
                if not section or section not in allowed:
                    continue
                if not line.strip().startswith("("):
                    continue
                row = self._parse_row(line)
                if row:
                    batch.append(row)
                if len(batch) >= 500:
                    flush()
                    if line_no % 80000 == 0:
                        self.stdout.write(f"  … ligne {line_no}")
        flush()

    def _flush(self, table: str, rows: list) -> int:
        try:
            return {
                "settings": self._import_settings,
                "profiles": self._import_profiles,
                "gallery": self._import_gallery,
                "bans": self._import_bans,
                "blocks": self._import_blocks,
                "swipes": self._import_swipes,
                "matches": self._import_matches,
                "messages": self._import_messages,
                "hides": self._import_hides,
                "notifications": self._import_notifications,
                "transactions": self._import_transactions,
                "reports": self._import_reports,
                "testimonials": self._import_testimonials,
            }[table](rows)
        except Exception as exc:
            self.stderr.write(f"Erreur {table}: {exc}")
            return 0

    def _parse_row(self, line: str) -> list[str] | None:
        cleaned = re.sub(r"::[a-zA-Z0-9_.\"]+", "", line)
        s = cleaned.strip().rstrip(",").rstrip(";")
        if not s.startswith("("):
            return None
        if s.endswith("),"):
            s = s[1:-2]
        elif s.endswith(")"):
            s = s[1:-1]
        else:
            s = s[1:]
        return self._split(s)

    def _split(self, s: str) -> list[str]:
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

    def _v(self, raw):
        if raw is None or raw == "NULL":
            return None
        if raw in ("true", "t"):
            return True
        if raw in ("false", "f"):
            return False
        if len(raw) >= 2 and raw[0] == "'" and raw[-1] == "'":
            return raw[1:-1].replace("''", "'")
        return raw

    def _dt(self, raw):
        v = self._v(raw)
        if not v:
            return None
        dt = parse_datetime(str(v).replace(" ", "T", 1) if "T" not in str(v) else str(v))
        if dt and timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.utc)
        return dt

    def _date(self, raw):
        v = self._v(raw)
        if not v:
            return date(1995, 1, 1)
        try:
            return date.fromisoformat(str(v)[:10])
        except Exception:
            return date(1995, 1, 1)

    def _import_settings(self, rows) -> int:
        n = 0
        for r in rows:
            if len(r) < 2:
                continue
            key = self._v(r[0])
            val = self._v(r[1])
            if isinstance(val, str) and val[:1] in "{[\"":
                try:
                    val = json.loads(val)
                except Exception:
                    pass
            if key:
                SiteSetting.objects.update_or_create(key=key, defaults={"value": val})
                n += 1
        return n

    def _import_profiles(self, rows) -> int:
        n = 0
        for r in rows:
            if len(r) < 9:
                continue
            pid = self._v(r[0])
            email = self._v(r[3]) or f"user_{str(pid)[:8]}@import.timalove.local"
            user, created = User.objects.get_or_create(username=email[:150], defaults={"email": email})
            if created:
                user.set_password("ChangeMe123!")
                user.first_name = self._v(r[1]) or ""
                user.last_name = self._v(r[2]) or ""
                user.save()
            role = self._v(r[18]) if len(r) > 18 else "member"
            reg = self._v(r[17]) if len(r) > 17 else "approved"
            Profile.objects.update_or_create(
                id=pid,
                defaults={
                    "user": user,
                    "first_name": self._v(r[1]) or "Membre",
                    "last_name": self._v(r[2]) or "",
                    "email": email,
                    "phone": self._v(r[4]),
                    "date_of_birth": self._date(r[5]),
                    "gender": self._v(r[6]) if self._v(r[6]) in Gender.values else Gender.FEMALE,
                    "city": self._v(r[7]) or "Dakar",
                    "country": self._v(r[8]) or "Sénégal",
                    "residence_country": self._v(r[9]) if len(r) > 9 else None,
                    "religion": self._v(r[10]) if len(r) > 10 else None,
                    "profession": self._v(r[11]) if len(r) > 11 else None,
                    "bio": self._v(r[12]) if len(r) > 12 else None,
                    "looking_for": self._v(r[13]) if len(r) > 13 else None,
                    "photo_url": self._v(r[14]) if len(r) > 14 else None,
                    "photo_url_2": self._v(r[15]) if len(r) > 15 else None,
                    "photo_url_3": self._v(r[16]) if len(r) > 16 else None,
                    "registration_status": reg if reg in RegistrationStatus.values else RegistrationStatus.APPROVED,
                    "role": UserRole.ADMIN if role == "admin" else UserRole.MEMBER,
                    "is_verified": bool(self._v(r[19])) if len(r) > 19 else False,
                    "subscription_tier": self._v(r[21]) if len(r) > 21 and self._v(r[21]) in SubscriptionTier.values else SubscriptionTier.FREE,
                    "subscription_status": self._v(r[22]) if len(r) > 22 and self._v(r[22]) in SubscriptionStatus.values else SubscriptionStatus.INACTIVE,
                    "subscription_end_date": self._dt(r[23]) if len(r) > 23 else None,
                    "likes_received_count": int(self._v(r[24]) or 0) if len(r) > 24 else 0,
                    "likes_given_count": int(self._v(r[25]) or 0) if len(r) > 25 else 0,
                    "matches_count": int(self._v(r[26]) or 0) if len(r) > 26 else 0,
                    "is_boosted": bool(self._v(r[27])) if len(r) > 27 else False,
                    "boost_end_date": self._dt(r[28]) if len(r) > 28 else None,
                    "last_active_at": self._dt(r[29]) if len(r) > 29 else timezone.now(),
                    "is_online": bool(self._v(r[30])) if len(r) > 30 else False,
                    "is_hidden": bool(self._v(r[33])) if len(r) > 33 else False,
                    "hide_age": bool(self._v(r[35])) if len(r) > 35 else False,
                },
            )
            self.profile_ids.add(str(pid))
            n += 1
        return n

    def _import_gallery(self, rows) -> int:
        objs = []
        for r in rows:
            if len(r) < 4:
                continue
            pid = self._v(r[1])
            if str(pid) not in self.profile_ids:
                continue
            objs.append(ProfileGalleryPhoto(
                id=self._v(r[0]), profile_id=pid, position=int(self._v(r[2]) or 1),
                photo_url=self._v(r[3]) or "",
                created_at=self._dt(r[4]) if len(r) > 4 else timezone.now(),
            ))
        ProfileGalleryPhoto.objects.bulk_create(objs, ignore_conflicts=True, batch_size=200)
        return len(objs)

    def _import_bans(self, rows) -> int:
        n = 0
        for r in rows:
            if len(r) < 5:
                continue
            email_n = self._v(r[2])
            phone_n = self._v(r[3])
            if not email_n and not phone_n:
                continue
            BannedIdentity.objects.update_or_create(
                id=self._v(r[0]),
                defaults={
                    "profile_id": self._v(r[1]) if str(self._v(r[1]) or "") in self.profile_ids else None,
                    "email_normalized": email_n,
                    "phone_normalized": phone_n,
                    "reason": self._v(r[4]),
                },
            )
            n += 1
        return n

    def _import_blocks(self, rows) -> int:
        objs = []
        for r in rows:
            if len(r) < 3:
                continue
            a, b = self._v(r[1]), self._v(r[2])
            if str(a) not in self.profile_ids or str(b) not in self.profile_ids:
                continue
            objs.append(BlockedUser(
                id=self._v(r[0]), blocker_id=a, blocked_id=b,
                created_at=self._dt(r[3]) if len(r) > 3 else timezone.now(),
            ))
        BlockedUser.objects.bulk_create(objs, ignore_conflicts=True, batch_size=200)
        return len(objs)

    def _import_swipes(self, rows) -> int:
        objs = []
        for r in rows:
            if len(r) < 6:
                continue
            a, b = self._v(r[1]), self._v(r[2])
            if str(a) not in self.profile_ids or str(b) not in self.profile_ids:
                continue
            action = self._v(r[6]) if len(r) > 6 else ("like" if self._v(r[3]) else "pass")
            if action not in SwipeAction.values:
                action = SwipeAction.LIKE if self._v(r[3]) else SwipeAction.PASS
            objs.append(Swipe(
                id=self._v(r[0]), swiper_id=a, swiped_id=b,
                is_like=bool(self._v(r[3])), is_super_like=bool(self._v(r[4])),
                created_at=self._dt(r[5]) or timezone.now(), action=action,
            ))
        Swipe.objects.bulk_create(objs, ignore_conflicts=True, batch_size=800)
        return len(objs)

    def _import_matches(self, rows) -> int:
        objs = []
        for r in rows:
            if len(r) < 4:
                continue
            a, b = self._v(r[1]), self._v(r[2])
            if str(a) not in self.profile_ids or str(b) not in self.profile_ids:
                continue
            mid = self._v(r[0])
            status = self._v(r[3]) if self._v(r[3]) in MatchStatus.values else MatchStatus.ACTIVE
            objs.append(Match(
                id=mid, user_1_id=a, user_2_id=b, status=status,
                user_1_message_count=int(self._v(r[4]) or 0) if len(r) > 4 else 0,
                user_2_message_count=int(self._v(r[5]) or 0) if len(r) > 5 else 0,
                created_at=self._dt(r[6]) if len(r) > 6 else timezone.now(),
                updated_at=self._dt(r[7]) if len(r) > 7 else timezone.now(),
                scheduled_date=self._dt(r[8]) if len(r) > 8 else None,
                meet_link=self._v(r[9]) if len(r) > 9 else None,
            ))
            self.match_ids.add(str(mid))
        Match.objects.bulk_create(objs, ignore_conflicts=True, batch_size=400)
        return len(objs)

    def _import_messages(self, rows) -> int:
        objs = []
        for r in rows:
            if len(r) < 5:
                continue
            mid, sid = self._v(r[1]), self._v(r[2])
            if str(mid) not in self.match_ids or str(sid) not in self.profile_ids:
                continue
            mtype = self._v(r[4]) if self._v(r[4]) in MessageType.values else MessageType.TEXT
            voice_duration = None
            if len(r) > 6 and self._v(r[6]) not in (None, False, ""):
                try:
                    voice_duration = int(self._v(r[6]))
                except Exception:
                    voice_duration = None
            objs.append(Message(
                id=self._v(r[0]), match_id=mid, sender_id=sid,
                content=self._v(r[3]) or "", message_type=mtype,
                voice_url=self._v(r[5]) if len(r) > 5 else None,
                voice_duration_seconds=voice_duration,
                is_read=bool(self._v(r[7])) if len(r) > 7 else False,
                read_at=self._dt(r[8]) if len(r) > 8 else None,
                is_flagged=bool(self._v(r[9])) if len(r) > 9 else False,
                original_content=self._v(r[10]) if len(r) > 10 else None,
                created_at=self._dt(r[11]) if len(r) > 11 else timezone.now(),
            ))
        Message.objects.bulk_create(objs, ignore_conflicts=True, batch_size=800)
        return len(objs)

    def _import_hides(self, rows) -> int:
        objs = []
        for r in rows:
            if len(r) < 2:
                continue
            a, b = self._v(r[0]), self._v(r[1])
            if str(a) not in self.profile_ids or str(b) not in self.profile_ids:
                continue
            objs.append(ConversationHide(
                user_id=a, partner_id=b,
                hidden_at=self._dt(r[2]) if len(r) > 2 else timezone.now(),
            ))
        ConversationHide.objects.bulk_create(objs, ignore_conflicts=True, batch_size=200)
        return len(objs)

    def _import_notifications(self, rows) -> int:
        objs = []
        for r in rows:
            if len(r) < 5:
                continue
            uid = self._v(r[1])
            if str(uid) not in self.profile_ids:
                continue
            ntype = self._v(r[2])
            if ntype not in NotificationType.values:
                ntype = NotificationType.NEW_LIKE
            related = self._v(r[5]) if len(r) > 5 else None
            match_id = self._v(r[6]) if len(r) > 6 else None
            objs.append(Notification(
                id=self._v(r[0]), user_id=uid, type=ntype,
                title=self._v(r[3]) or "", message=self._v(r[4]) or "",
                related_user_id=related if related and str(related) in self.profile_ids else None,
                related_match_id=match_id if match_id and str(match_id) in self.match_ids else None,
                is_read=bool(self._v(r[7])) if len(r) > 7 else False,
                read_at=self._dt(r[8]) if len(r) > 8 else None,
                created_at=self._dt(r[9]) if len(r) > 9 else timezone.now(),
            ))
        Notification.objects.bulk_create(objs, ignore_conflicts=True, batch_size=800)
        return len(objs)

    def _import_transactions(self, rows) -> int:
        n = 0
        for r in rows:
            if len(r) < 7:
                continue
            uid = self._v(r[1])
            ttype = self._v(r[5])
            status = self._v(r[6])
            order_id = self._v(r[2]) or str(self._v(r[0]))
            Transaction.objects.update_or_create(
                id=self._v(r[0]),
                defaults={
                    "user_id": uid if uid and str(uid) in self.profile_ids else None,
                    "order_id": order_id,
                    "amount": int(self._v(r[3]) or 0),
                    "payment_method": self._v(r[4]),
                    "type": ttype if ttype in TransactionType.values else TransactionType.SUBSCRIPTION,
                    "status": status if status in TransactionStatus.values else TransactionStatus.PENDING,
                    "naboo_transaction_id": self._v(r[9]) if len(r) > 9 else None,
                    "paid_at": self._dt(r[11]) if len(r) > 11 else None,
                    "plan_tier": self._v(r[14]) if len(r) > 14 and self._v(r[14]) in SubscriptionTier.values else None,
                    "subscription_end_date": self._dt(r[15]) if len(r) > 15 else None,
                },
            )
            n += 1
        return n

    def _import_reports(self, rows) -> int:
        n = 0
        for r in rows:
            if len(r) < 4:
                continue
            rid = self._v(r[1])
            if str(rid) not in self.profile_ids:
                continue
            reason = self._v(r[3])
            Report.objects.update_or_create(
                id=self._v(r[0]),
                defaults={
                    "reporter_id": rid,
                    "reported_profile_id": self._v(r[2]) if self._v(r[2]) and str(self._v(r[2])) in self.profile_ids else None,
                    "reason": reason if reason in ReportReason.values else ReportReason.OTHER,
                    "message": self._v(r[4]) if len(r) > 4 else None,
                    "status": ReportStatus.PENDING,
                },
            )
            n += 1
        return n

    def _import_testimonials(self, rows) -> int:
        n = 0
        for r in rows:
            if len(r) < 3:
                continue
            Testimonial.objects.update_or_create(
                id=self._v(r[0]),
                defaults={
                    "author_name": (self._v(r[1]) or "Anonyme")[:120],
                    "content": self._v(r[2]) or "",
                    "rating": 5,
                    "is_published": True,
                },
            )
            n += 1
        return n
