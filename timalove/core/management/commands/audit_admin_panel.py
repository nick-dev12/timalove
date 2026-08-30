"""Audit intégral du panneau admin TimaLove."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.test import Client

User = get_user_model()

ADMIN_PAGES = [
    ("/espace-prive/dashboard/", "dashboard"),
    ("/espace-prive/membres/", "membres"),
    ("/espace-prive/signalements/", "signalements"),
    ("/espace-prive/paiements/", "paiements"),
    ("/espace-prive/monetisation/", "monetisation"),
    ("/espace-prive/communications/", "communications"),
    ("/espace-prive/configuration/", "configuration"),
    ("/espace-prive/equipe/", "roles_audit"),
]


class Command(BaseCommand):
    help = "Audit des pages et fonctionnalités admin"

    def handle(self, *args, **options):
        from core.controllers import (
            admin_controller,
            app_config_controller,
            audit_controller,
            crm_controller,
            finance_controller,
            moderation_controller,
            monetization_controller,
            profile_controller,
            rbac_controller,
            site_settings_controller,
        )
        from core.models import Profile
        from core.models.choices import UserRole

        results: list[tuple[str, str, str, str]] = []
        ok = warn = fail = 0

        def record(area: str, check: str, status: str, detail: str = ""):
            nonlocal ok, warn, fail
            results.append((area, check, status, detail))
            if status == "OK":
                ok += 1
            elif status == "WARN":
                warn += 1
            else:
                fail += 1

        # --- Controllers smoke ---
        try:
            kpis = admin_controller.dashboard_kpis()
            record("Dashboard", "dashboard_kpis()", "OK" if kpis else "FAIL", f"{len(kpis)} KPIs")
        except Exception as exc:
            record("Dashboard", "dashboard_kpis()", "FAIL", str(exc))

        try:
            charts = admin_controller.dashboard_analytics()
            record("Dashboard", "dashboard_analytics()", "OK" if charts.get("labels") else "FAIL")
        except Exception as exc:
            record("Dashboard", "dashboard_analytics()", "FAIL", str(exc))

        try:
            recent = admin_controller.dashboard_recent_activity()
            record("Dashboard", "dashboard_recent_activity()", "OK", f"{len(recent)} entrées")
        except Exception as exc:
            record("Dashboard", "dashboard_recent_activity()", "FAIL", str(exc))

        try:
            page = admin_controller.list_members(page=1, per_page=5)
            record("Membres", "list_members()", "OK", f"{page.paginator.count} membres")
        except Exception as exc:
            record("Membres", "list_members()", "FAIL", str(exc))

        try:
            summary = admin_controller.members_summary()
            record("Membres", "members_summary()", "OK", str(summary))
        except Exception as exc:
            record("Membres", "members_summary()", "FAIL", str(exc))

        try:
            reports = moderation_controller.list_reports(page=1)
            record("Modération", "list_reports()", "OK", f"{reports.paginator.count} signalements")
        except Exception as exc:
            record("Modération", "list_reports()", "FAIL", str(exc))

        try:
            txs = finance_controller.list_transactions(page=1)
            record("Finances", "list_transactions()", "OK", f"{txs.paginator.count} transactions")
        except Exception as exc:
            record("Finances", "list_transactions()", "FAIL", str(exc))

        try:
            fin = finance_controller.finance_summary()
            record("Finances", "finance_summary()", "OK", str(fin))
        except Exception as exc:
            record("Finances", "finance_summary()", "FAIL", str(exc))

        try:
            plans = site_settings_controller.get_subscription_plans()
            record("Monétisation", "get_subscription_plans()", "OK", f"{len(plans)} plans")
        except Exception as exc:
            record("Monétisation", "get_subscription_plans()", "FAIL", str(exc))

        try:
            promos = monetization_controller.list_promo_codes()
            record("Monétisation", "list_promo_codes()", "OK", f"{len(promos)} codes")
        except Exception as exc:
            record("Monétisation", "list_promo_codes()", "FAIL", str(exc))

        try:
            camps = crm_controller.list_campaigns()
            record("Communications", "list_campaigns()", "OK", f"{len(camps)} campagnes")
        except Exception as exc:
            record("Communications", "list_campaigns()", "FAIL", str(exc))

        try:
            cfg = app_config_controller.get_app_config()
            record("Configuration", "get_app_config()", "OK", f"keys={list(cfg.keys())[:5]}")
        except Exception as exc:
            record("Configuration", "get_app_config()", "FAIL", str(exc))

        try:
            staff = rbac_controller.list_staff_members()
            record("Rôles & Audit", "list_staff_members()", "OK", f"{len(staff)} staff")
        except Exception as exc:
            record("Rôles & Audit", "list_staff_members()", "FAIL", str(exc))

        try:
            logs = audit_controller.list_audit_logs(page=1)
            record("Rôles & Audit", "list_audit_logs()", "OK", f"{logs.paginator.count} logs")
        except Exception as exc:
            record("Rôles & Audit", "list_audit_logs()", "FAIL", str(exc))

        # --- Pricing propagation ---
        test_profile = Profile.objects.filter(role=UserRole.MEMBER).first()
        if test_profile:
            from core.controllers import subscription_controller

            original_plans = site_settings_controller.get_subscription_plans()
            catalog = subscription_controller.plans_catalog_for(test_profile)
            test_plan_id = catalog[0] if catalog else next(iter(original_plans))
            original_price = int(original_plans[test_plan_id].get("price", 0))
            new_price = original_price + 777
            updated = dict(original_plans)
            updated[test_plan_id] = {**updated[test_plan_id], "price": new_price, "label": "Test Audit Label"}
            site_settings_controller.save_subscription_plans(updated)

            user_plans = profile_controller.subscription_plans_for(test_profile)
            user_plan = next((p for p in user_plans if p["id"] == test_plan_id), None)
            if user_plan and user_plan["price"] == new_price:
                record("Sync utilisateurs", "Prix plan profil", "OK", f"{test_plan_id}={new_price}")
            else:
                record("Sync utilisateurs", "Prix plan profil", "FAIL", str(user_plan))

            public = site_settings_controller.public_config()
            api_prices = public.get("subscriptionPrices") or {}
            if int(api_prices.get(test_plan_id, 0)) == new_price:
                record("Sync utilisateurs", "Prix API site-config", "OK")
            else:
                record("Sync utilisateurs", "Prix API site-config", "FAIL", str(api_prices.get(test_plan_id)))

            if user_plan and user_plan.get("label") == "Test Audit Label":
                record("Sync utilisateurs", "Titre plan profil", "OK")
            else:
                record("Sync utilisateurs", "Titre plan profil", "FAIL", str(user_plan))

            # Restore
            site_settings_controller.save_subscription_plans(original_plans)
        else:
            record("Sync utilisateurs", "Propagation prix", "WARN", "Aucun membre test")

        # --- Configuration sync (quotas + features) ---
        if test_profile:
            original_msg_limit = site_settings_controller.get("free_messages_limit")
            site_settings_controller.set_value("free_messages_limit", 3)
            from core.controllers import quota_controller

            snap = quota_controller.messages_limit()
            if snap == 3:
                record("Sync utilisateurs", "Quota messages config", "OK")
            else:
                record("Sync utilisateurs", "Quota messages config", "FAIL", str(snap))
            site_settings_controller.set_value("free_messages_limit", original_msg_limit)

            original_cfg = app_config_controller.get_app_config()
            updated_cfg = {**original_cfg, "video_chat_enabled": False}
            app_config_controller.save_app_config(updated_cfg)
            flags = app_config_controller.feature_flags()
            if flags.get("video_chat_enabled") is False:
                record("Sync utilisateurs", "Feature flags config", "OK")
            else:
                record("Sync utilisateurs", "Feature flags config", "FAIL", str(flags))
            app_config_controller.save_app_config(original_cfg)

        # --- Boost price sync ---
        packs = site_settings_controller.get_in_app_packs()
        boost_id = next((pid for pid, m in packs.items() if m.get("pack_type") == "boost"), None)
        if boost_id:
            ctx = profile_controller.settings_context(test_profile) if test_profile else {}
            boost_label = ctx.get("boost_price_label", "")
            expected = site_settings_controller.default_boost_pack_price()
            formatted = f"{expected:,}".replace(",", "\u202f") + " FCFA"
            if boost_label == formatted:
                record("Sync utilisateurs", "Prix boost profil", "OK", boost_label)
            else:
                record("Sync utilisateurs", "Prix boost profil", "WARN", f"hardcodé? got={boost_label} expected={formatted}")

        # --- HTTP pages super admin ---
        admin_user = User.objects.filter(email="admin@timalove.local").first()
        if not admin_user:
            record("HTTP", "Super admin existe", "FAIL", "admin@timalove.local manquant")
        else:
            client = Client()
            client.force_login(admin_user)
            for url, name in ADMIN_PAGES:
                try:
                    r = client.get(url)
                    body = r.content.decode("utf-8", errors="replace")
                    has_shell = "adm__main" in body or "adm-login" in body
                    if r.status_code == 200 and has_shell:
                        record("HTTP", name, "OK", f"{len(body)} octets")
                    else:
                        record("HTTP", name, "FAIL", f"status={r.status_code}")
                except Exception as exc:
                    record("HTTP", name, "FAIL", str(exc))

            # Partials HTMX
            for url, name in [
                ("/espace-prive/membres/?format=partial", "membres partial"),
                ("/espace-prive/signalements/?format=partial", "signalements partial"),
                ("/espace-prive/paiements/?format=partial", "paiements partial"),
            ]:
                r = client.get(url)
                body = r.content.decode("utf-8", errors="replace")
                if r.status_code == 200 and ("<tr>" in body or "adm-empty" in body):
                    record("HTTP", name, "OK")
                else:
                    record("HTTP", name, "FAIL", f"status={r.status_code}")

            # Export CSV
            r = client.get("/espace-prive/paiements/?export=csv")
            if r.status_code == 200 and "text/csv" in r.get("Content-Type", ""):
                record("HTTP", "export CSV paiements", "OK")
            else:
                record("HTTP", "export CSV paiements", "WARN", f"status={r.status_code}")

        # --- RBAC moderator POST ---
        mod = Profile.objects.filter(role=UserRole.MODERATOR).first()
        member = Profile.objects.filter(role=UserRole.MEMBER).exclude(banned_at__isnull=False).first()
        if mod and member and admin_user:
            mod_client = Client()
            mod_client.force_login(mod.user)
            r = mod_client.post(
                "/espace-prive/membres/",
                {"action": "ban", "profile_id": str(member.id), "reason_key": "spam"},
            )
            member.refresh_from_db()
            if r.status_code in (302, 403) and member.banned_at is None:
                record("Sécurité", "Modérateur POST ban liste", "OK", "ban non appliqué")
            elif member.banned_at:
                record("Sécurité", "Modérateur POST ban liste", "FAIL", "ban appliqué sans permission!")
            else:
                record("Sécurité", "Modérateur POST ban liste", "WARN", f"status={r.status_code}")

            r2 = mod_client.get("/espace-prive/equipe/")
            if r2.status_code == 302 or "equipe" not in r2.url:
                record("Sécurité", "Modérateur accès equipe", "OK")
            else:
                record("Sécurité", "Modérateur accès equipe", "FAIL")

        # --- Promo checkout gap ---
        from core.controllers import payment_controller
        import inspect

        src = inspect.getsource(payment_controller.create_checkout)
        if "validate_promo" in src or "promo" in src.lower():
            record("Monétisation", "Promos au checkout", "OK")
        else:
            record("Monétisation", "Promos au checkout", "WARN", "Codes promo non branchés au paiement")

        # --- CRM popups gap ---
        from core.views.api import views as api_views
        api_src = inspect.getsource(api_views)
        if "pending_popups" in api_src:
            record("Communications", "API popups CRM", "OK")
        else:
            record("Communications", "API popups CRM", "WARN", "Popups CRM non exposés côté utilisateur")

        # --- Report ---
        self.stdout.write("\n=== AUDIT PANEL ADMIN TIMA LOVE ===\n")
        current_area = ""
        for area, check, status, detail in results:
            if area != current_area:
                self.stdout.write(f"\n[{area}]")
                current_area = area
            icon = {"OK": "+", "WARN": "!", "FAIL": "X"}[status]
            line = f"  [{icon}] {check}: {status}"
            if detail:
                safe = detail.encode("ascii", errors="replace").decode("ascii")
                line += f" — {safe}"
            self.stdout.write(line)

        self.stdout.write(f"\n--- Résumé: {ok} OK, {warn} avertissements, {fail} échecs ---\n")
