"""RBAC — rôles staff et permissions back-office."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from core.controllers.auth_controller import normalize_email, unique_username
from core.models import AdminTwoFactor, Profile
from core.models.choices import STAFF_ROLES, UserRole

User = get_user_model()

ROLE_LABELS: dict[str, str] = dict(UserRole.choices)

STAFF_ROLE_CHOICES: list[tuple[str, str]] = [
    (UserRole.SUPER_ADMIN, "Super administrateur"),
    (UserRole.ADMIN, "Administrateur"),
    (UserRole.MODERATOR, "Modérateur"),
    (UserRole.SUPPORT, "Support client"),
]

# Permissions par rôle (super_admin = toutes)
ROLE_PERMISSIONS: dict[str, frozenset[str] | None] = {
    UserRole.SUPER_ADMIN: None,
    UserRole.ADMIN: frozenset(
        {
            "dashboard",
            "membres",
            "membres.edit",
            "paiements",
            "monetisation",
            "signalements",
            "signalements.action",
            "configuration",
            "communications",
        }
    ),
    UserRole.MODERATOR: frozenset(
        {
            "dashboard",
            "membres.view",
            "signalements",
            "signalements.action",
        }
    ),
    UserRole.SUPPORT: frozenset(
        {
            "dashboard",
            "membres.view",
            "communications",
        }
    ),
}

VIEW_PERMISSION_MAP: dict[str, str] = {
    "dashboard": "dashboard",
    "membres": "membres.view",
    "membre_detail": "membres.edit",
    "paiements": "paiements",
    "monetisation": "monetisation",
    "communications": "communications",
    "communications_cities": "communications",
    "signalements": "signalements",
    "signalement_detail": "signalements.action",
    "configuration": "configuration",
    "roles_audit": "roles.manage",
    "admin_2fa_setup": "dashboard",
    "admin_2fa_verify": "dashboard",
    "connexion": "dashboard",
}


def role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role)


def has_permission(profile: Profile | None, permission: str) -> bool:
    if not profile or not profile.is_staff_member:
        return False
    allowed = ROLE_PERMISSIONS.get(profile.role)
    if allowed is None:
        return True
    if permission in allowed:
        return True
    if permission.endswith(".view"):
        base = permission.rsplit(".", 1)[0]
        if base in allowed:
            return True
    view_only = f"{permission}.view"
    if view_only in allowed:
        return True
    return False


def can_access_view(profile: Profile | None, view_name: str) -> bool:
    perm = VIEW_PERMISSION_MAP.get(view_name, "dashboard")
    return has_permission(profile, perm)


def list_staff_members():
    return list(
        Profile.objects.filter(role__in=STAFF_ROLES)
        .select_related("user", "admin_two_factor")
        .order_by("role", "first_name")
    )


def staff_summary() -> dict:
    qs = Profile.objects.filter(role__in=STAFF_ROLES)
    return {
        "total": qs.count(),
        "super_admins": qs.filter(role=UserRole.SUPER_ADMIN).count(),
        "admins": qs.filter(role=UserRole.ADMIN).count(),
        "moderators": qs.filter(role=UserRole.MODERATOR).count(),
        "support": qs.filter(role=UserRole.SUPPORT).count(),
    }


def _actor_can_manage_staff(actor: Profile) -> bool:
    return actor.is_super_admin or has_permission(actor, "roles.manage")


@transaction.atomic
def create_staff_user(
    actor: Profile,
    *,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: str,
) -> Profile:
    if not _actor_can_manage_staff(actor):
        raise PermissionError("Seul un super administrateur peut créer des comptes staff.")
    if role not in STAFF_ROLES:
        raise ValueError("Rôle staff invalide.")
    if role == UserRole.SUPER_ADMIN and not actor.is_super_admin:
        raise PermissionError("Seul un super administrateur peut créer un super administrateur.")
    email_n = normalize_email(email)
    if not email_n or not password or len(password) < 10:
        raise ValueError("Email valide et mot de passe (10 caractères min.) requis.")
    if User.objects.filter(email__iexact=email_n).exists():
        raise ValueError("Un compte existe déjà avec cet email.")

    user = User.objects.create_user(
        username=unique_username(email_n.split("@")[0]),
        email=email_n,
        password=password,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        is_staff=True,
        is_superuser=role == UserRole.SUPER_ADMIN,
    )
    profile = Profile.objects.create(
        user=user,
        first_name=first_name.strip() or "Staff",
        last_name=last_name.strip() or "TimaLove",
        email=email_n,
        role=role,
        registration_status="approved",
        is_verified=True,
        onboarding_completed=True,
    )
    return profile


@transaction.atomic
def update_staff_role(actor: Profile, profile_id, new_role: str) -> Profile:
    if not _actor_can_manage_staff(actor):
        raise PermissionError("Permission refusée.")
    if new_role not in STAFF_ROLES:
        raise ValueError("Rôle invalide.")
    target = Profile.objects.select_related("user").get(pk=profile_id)
    if not target.is_staff_member:
        raise ValueError("Ce membre n'est pas un compte staff.")
    if target.is_super_admin and not actor.is_super_admin:
        raise PermissionError("Impossible de modifier un super administrateur.")
    if new_role == UserRole.SUPER_ADMIN and not actor.is_super_admin:
        raise PermissionError("Seul un super administrateur peut promouvoir en super admin.")
    if target.id == actor.id and new_role != actor.role:
        raise ValueError("Vous ne pouvez pas modifier votre propre rôle.")
    target.role = new_role
    target.save(update_fields=["role", "updated_at"])
    user = target.user
    user.is_staff = True
    user.is_superuser = new_role == UserRole.SUPER_ADMIN
    user.save(update_fields=["is_staff", "is_superuser"])
    return target


def deactivate_staff(actor: Profile, profile_id) -> Profile:
    if not _actor_can_manage_staff(actor):
        raise PermissionError("Permission refusée.")
    target = Profile.objects.select_related("user").get(pk=profile_id)
    if target.id == actor.id:
        raise ValueError("Vous ne pouvez pas désactiver votre propre compte.")
    if target.is_super_admin and not actor.is_super_admin:
        raise PermissionError("Impossible de désactiver un super administrateur.")
    target.role = UserRole.MEMBER
    target.save(update_fields=["role", "updated_at"])
    user = target.user
    user.is_staff = False
    user.is_superuser = False
    user.is_active = False
    user.save(update_fields=["is_staff", "is_superuser", "is_active"])
    AdminTwoFactor.objects.filter(profile=target).delete()
    return target


def nav_links_for(profile: Profile | None) -> list[dict]:
    sections = [
        (
            "Dashboard",
            [
                ("dashboard", "Vue d'ensemble", "admin_panel:dashboard", "▣"),
            ],
        ),
        (
            "Plateforme",
            [
                ("membres", "Gestion des utilisateurs", "admin_panel:membres", "M"),
                ("signalements", "Modération & Signalements", "admin_panel:signalements", "!"),
            ],
        ),
        (
            "Business",
            [
                ("paiements", "Finances & Transactions", "admin_panel:paiements", "₣"),
                ("monetisation", "Plan et abonnement", "admin_panel:monetisation", "◆"),
                ("communications", "Notification & Communication", "admin_panel:communications", "✉"),
            ],
        ),
        (
            "Système",
            [
                ("configuration", "Configuration Globale de l'App", "admin_panel:configuration", "⚙"),
                ("roles_audit", "Rôles & Audit", "admin_panel:roles_audit", "🔐"),
            ],
        ),
    ]
    result = []
    for label, links in sections:
        visible = []
        for key, link_label, url_name, icon in links:
            if can_access_view(profile, key):
                visible.append({"key": key, "label": link_label, "url_name": url_name, "icon": icon})
        if visible:
            result.append({"label": label, "links": visible})
    return result
