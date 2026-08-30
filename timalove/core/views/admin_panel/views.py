from django.contrib import messages
from django.http import Http404, HttpResponse, JsonResponse
from django.middleware.csrf import rotate_token
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST, require_GET
import json

from core.controllers import (
    admin_controller,
    app_config_controller,
    audit_controller,
    auth_controller,
    crm_controller,
    finance_controller,
    moderation_controller,
    monetization_controller,
    rbac_controller,
    site_settings_controller,
    two_factor_controller,
)
from core.models.choices import RegistrationStatus, ReportStatus, SubscriptionTier, TransactionStatus, TransactionType

def _admin_profile(request):
    return getattr(request.user, "profile", None)


def _page_param(request, default: int = 1) -> int:
    raw = request.GET.get("page") or default
    try:
        page = int(raw)
    except (TypeError, ValueError):
        page = default
    return max(1, page)

def _audit(request, action: str, message: str, **kwargs):
    audit_controller.log_admin(request, action, message, **kwargs)

def _member_label(member) -> str:
    return member.display_name or member.first_name or audit_controller.profile_ref(member)

def _audit_report(request, audit_action: str, report_id, message: str):
    _audit(request, audit_action, message, target_type="report", target_id=str(report_id))

def _admin_post_login_redirect(request, profile):
    request.session.pop("admin_2fa_verified", None)
    if two_factor_controller.must_setup_2fa(profile, request.session):
        return redirect("admin_panel:admin_2fa_setup")
    if two_factor_controller.must_verify_2fa(profile, request.session):
        return redirect("admin_panel:admin_2fa_verify")
    return redirect("admin_panel:dashboard")

@never_cache
@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def connexion(request):
    if request.user.is_authenticated and getattr(getattr(request.user, "profile", None), "is_admin", False):
        return _admin_post_login_redirect(request, request.user.profile)
    if request.method == "GET":
        rotate_token(request)
    if request.method == "POST":
        ok, msg = auth_controller.login_user(
            request, request.POST.get("email", ""), request.POST.get("password", "")
        )
        profile = getattr(request.user, "profile", None) if ok else None
        if ok and profile and profile.is_admin:
            return _admin_post_login_redirect(request, profile)
        if ok:
            auth_controller.logout_user(request)
            messages.error(request, "Accès réservé aux administrateurs.")
        else:
            messages.error(request, msg)
    return render(request, "admin_panel/connexion.html", {"title": "Espace administrateur"})

def dashboard(request):
    return render(
        request,
        "admin_panel/dashboard.html",
        {
            "title": "Vue d’ensemble",
            "kpis": admin_controller.dashboard_kpis(),
            "charts": admin_controller.dashboard_analytics(),
            "recent": admin_controller.dashboard_recent_activity(),
        },
    )

def _handle_member_action(request, member, *, redirect_name: str, redirect_kwargs: dict):
    actor = _admin_profile(request)
    if not rbac_controller.has_permission(actor, "membres.edit"):
        messages.error(request, "Vous n'avez pas la permission de modifier les membres.")
        return redirect(redirect_name, **redirect_kwargs)
    action = request.POST.get("action")
    reason = admin_controller.resolve_moderation_reason(
        request.POST.get("reason_key", ""),
        request.POST.get("reason", ""),
    )
    ref = audit_controller.profile_ref(member)
    label = _member_label(member)
    try:
        if action == "ban":
            moderation_controller.ban_profile(member, reason=reason, admin=_admin_profile(request))
            _audit(request, "user.ban", f"a banni l'utilisateur {label} ({ref})", target_type="profile", target_id=str(member.id), target_label=member.email or "")
            messages.success(request, "Compte banni.")
        elif action == "unban":
            admin_controller.unban_member(member.id)
            _audit(request, "user.unban", f"a levé le ban de l'utilisateur {label} ({ref})", target_type="profile", target_id=str(member.id))
            messages.success(request, "Ban levé.")
        elif action in {"suspend", "block"}:
            admin_controller.suspend_member(member.id, reason)
            _audit(request, "user.suspend", f"a suspendu l'utilisateur {label} ({ref})", target_type="profile", target_id=str(member.id))
            messages.success(request, "Compte suspendu.")
        elif action == "unsuspend":
            admin_controller.unsuspend_member(member.id)
            _audit(request, "user.unsuspend", f"a levé la suspension de {label} ({ref})", target_type="profile", target_id=str(member.id))
            messages.success(request, "Suspension levée.")
        elif action == "shadowban":
            admin_controller.shadowban_member(member.id, True)
            _audit(request, "user.shadowban", f"a activé le shadowban sur {label} ({ref})", target_type="profile", target_id=str(member.id))
            messages.success(request, "Shadowban activé — le profil n’est plus proposé aux autres.")
        elif action == "unshadowban":
            admin_controller.shadowban_member(member.id, False)
            _audit(request, "user.unshadowban", f"a levé le shadowban de {label} ({ref})", target_type="profile", target_id=str(member.id))
            messages.success(request, "Shadowban levé.")
        elif action == "reset_password":
            admin_controller.reset_member_password(member.id, request.POST.get("new_password") or None)
            _audit(request, "user.password_reset", f"a réinitialisé le mot de passe de {label} ({ref})", target_type="profile", target_id=str(member.id))
            messages.success(request, "Mot de passe réinitialisé.")
        elif action == "logout_sessions":
            count = admin_controller.logout_member_sessions(member.id)
            _audit(request, "user.sessions_logout", f"a déconnecté {count} session(s) de {label} ({ref})", target_type="profile", target_id=str(member.id))
            messages.success(request, f"{count} session(s) déconnectée(s).")
        elif action == "force_verify":
            admin_controller.force_verify_member(member.id)
            _audit(request, "user.verify", f"a certifié le profil de {label} ({ref})", target_type="profile", target_id=str(member.id))
            messages.success(request, "Profil certifié / vérifié.")
        elif action == "revoke_verify":
            admin_controller.revoke_verification(member.id)
            _audit(request, "user.unverify", f"a retiré la certification de {label} ({ref})", target_type="profile", target_id=str(member.id))
            messages.success(request, "Certification retirée.")
        elif action == "delete_account":
            admin_controller.delete_member_account(member.id)
            _audit(request, "user.delete", f"a supprimé le compte de {label} ({ref})", target_type="profile", target_id=str(member.id))
            messages.success(request, "Compte supprimé (RGPD).")
            return redirect("admin_panel:membres")
        elif action == "approve":
            admin_controller.set_registration_status(member.id, RegistrationStatus.APPROVED)
            _audit(request, "user.approve", f"a approuvé l'inscription de {label} ({ref})", target_type="profile", target_id=str(member.id))
            messages.success(request, "Profil approuvé.")
        elif action == "reject":
            admin_controller.set_registration_status(member.id, RegistrationStatus.REJECTED, request.POST.get("rejection_reason"))
            _audit(request, "user.reject", f"a rejeté l'inscription de {label} ({ref})", target_type="profile", target_id=str(member.id))
            messages.success(request, "Profil rejeté.")
        elif action == "subscription":
            tier = request.POST.get("tier", SubscriptionTier.FREE)
            days = int(request.POST.get("days") or 30)
            admin_controller.grant_subscription(member.id, tier, days)
            _audit(request, "user.subscription_grant", f"a accordé l'abonnement {tier} ({days} j.) à {label} ({ref})", target_type="profile", target_id=str(member.id), metadata={"tier": tier, "days": days})
            messages.success(request, "Abonnement mis à jour.")
        elif action == "revoke_subscription":
            admin_controller.revoke_subscription(member.id)
            _audit(request, "user.subscription_revoke", f"a révoqué l'abonnement de {label} ({ref})", target_type="profile", target_id=str(member.id))
            messages.success(request, "Abonnement révoqué.")
        elif action == "hide":
            admin_controller.set_member_hidden(member.id, True)
            _audit(request, "user.hide", f"a masqué le profil de {label} ({ref})", target_type="profile", target_id=str(member.id))
            messages.success(request, "Profil masqué.")
        elif action == "show":
            admin_controller.set_member_hidden(member.id, False)
            _audit(request, "user.show", f"a rendu visible le profil de {label} ({ref})", target_type="profile", target_id=str(member.id))
            messages.success(request, "Profil visible.")
        else:
            messages.error(request, "Action inconnue.")
    except Exception as exc:
        messages.error(request, str(exc) or "Action impossible.")
    return redirect(redirect_name, **redirect_kwargs)

@require_http_methods(["GET", "POST"])
def membres(request):
    if request.method == "POST":
        member = admin_controller.get_member(request.POST.get("profile_id"))
        if member is None:
            messages.error(request, "Membre introuvable.")
            return redirect("admin_panel:membres")
        return _handle_member_action(
            request,
            member,
            redirect_name="admin_panel:membres",
            redirect_kwargs={},
        )

    q = request.GET.get("q", "")
    account_status = request.GET.get("account_status") or None
    subscription_kind = request.GET.get("subscription_kind") or None
    page_obj = admin_controller.list_members(
        search=q,
        account_status=account_status,
        subscription_kind=subscription_kind,
        page=_page_param(request),
        per_page=30,
    )
    ctx = {
        "page_obj": page_obj,
        "q": q,
        "account_status": account_status,
        "subscription_kind": subscription_kind,
        "summary": admin_controller.members_summary(),
        "account_statuses": [
            ("active", "Actif"),
            ("pending", "En attente"),
            ("banned", "Banni"),
            ("suspended", "Suspendu"),
            ("shadowbanned", "Shadowban"),
        ],
        "subscription_kinds": [
            ("free", "Gratuit"),
            ("premium", "Premium"),
            ("vip", "VIP"),
        ],
    }
    if request.GET.get("format") == "partial":
        html = render(request, "admin_panel/partials/membres_rows.html", ctx)
        response = HttpResponse(html.content, content_type="text/html; charset=utf-8")
        response["X-Members-Total"] = str(page_obj.paginator.count)
        response["X-Members-Has-Next"] = "1" if page_obj.has_next else "0"
        response["X-Members-Next-Page"] = (
            str(page_obj.next_page_number()) if page_obj.has_next else ""
        )
        return response
    return render(
        request,
        "admin_panel/membres.html",
        {
            "title": "Gestion des utilisateurs",
            **ctx,
        },
    )

@require_http_methods(["GET", "POST"])
def membre_detail(request, profile_id):
    member = admin_controller.get_member(profile_id)
    if member is None:
        raise Http404("Membre introuvable")
    if request.method == "POST":
        if request.POST.get("action") == "delete_account":
            confirm = request.POST.get("confirm_delete", "")
            if confirm != "SUPPRIMER":
                messages.error(request, "Saisissez SUPPRIMER pour confirmer la suppression.")
                return redirect("admin_panel:membre_detail", profile_id=member.id)
        return _handle_member_action(
            request,
            member,
            redirect_name="admin_panel:membre_detail",
            redirect_kwargs={"profile_id": member.id},
        )

    detail = admin_controller.member_detail_context(member)
    return render(
        request,
        "admin_panel/membre_detail.html",
        {
            "title": detail["pseudonym"],
            "member": member,
            "detail": detail,
            "activity": admin_controller.member_activity(member),
            "subscription_tiers": SubscriptionTier.choices,
            "moderation_reasons": admin_controller.ADMIN_MODERATION_REASONS,
        },
    )

@require_http_methods(["GET", "POST"])
def paiements(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "refund":
            tx_id = request.POST.get("id")
            try:
                tx = finance_controller.refund_transaction(tx_id, _admin_profile(request), request.POST.get("notes", ""))
                amount = getattr(tx, "amount", "") or ""
                _audit(
                    request,
                    "finance.refund",
                    f"a remboursé la transaction {tx_id} ({amount})",
                    target_type="transaction",
                    target_id=str(tx_id),
                )
                messages.success(request, "Remboursement enregistré.")
            except Exception as exc:
                messages.error(request, str(exc) or "Remboursement impossible.")
        return redirect("admin_panel:paiements")

    export = request.GET.get("export")
    if export in ("csv", "xlsx", "excel"):
        return finance_controller.export_transactions_csv_response(
            request.GET.dict(),
            excel=export in ("xlsx", "excel"),
        )

    status = request.GET.get("status") or None
    product_type = request.GET.get("product_type") or None
    period = request.GET.get("period") or "30d"
    date_from = request.GET.get("date_from") or None
    date_to = request.GET.get("date_to") or None
    q = request.GET.get("q", "")
    page_obj = finance_controller.list_transactions(
        status=status,
        product_type=product_type,
        period=period,
        date_from=date_from,
        date_to=date_to,
        search=q,
        page=_page_param(request),
        per_page=30,
    )
    summary = finance_controller.finance_summary(
        status=status,
        product_type=product_type,
        period=period,
        date_from=date_from,
        date_to=date_to,
        search=q,
    )
    ctx = {
        "page_obj": page_obj,
        "summary": summary,
        "statuses": [
            (TransactionStatus.PAID, "Réussi"),
            (TransactionStatus.FAILED, "Échoué"),
            (TransactionStatus.PENDING, "En attente"),
            (TransactionStatus.REFUNDED, "Remboursé"),
            (TransactionStatus.DISPUTE, "Litige / Chargeback"),
        ],
        "product_types": finance_controller.PRODUCT_TYPE_FILTERS,
        "period_presets": finance_controller.PERIOD_PRESETS,
        "current_status": status,
        "current_product_type": product_type,
        "current_period": period,
        "date_from": date_from or "",
        "date_to": date_to or "",
        "q": q,
        "chart_channels_json": json.dumps(summary["channels"]),
    }
    if request.GET.get("format") == "partial":
        html = render(request, "admin_panel/partials/paiements_rows.html", ctx)
        response = HttpResponse(html.content, content_type="text/html; charset=utf-8")
        response["X-Payments-Total"] = str(page_obj.paginator.count)
        response["X-Payments-Has-Next"] = "1" if page_obj.has_next else "0"
        response["X-Payments-Next-Page"] = (
            str(page_obj.next_page_number()) if page_obj.has_next else ""
        )
        return response
    return render(
        request,
        "admin_panel/paiements.html",
        {
            "title": "Finances & Transactions",
            **ctx,
        },
    )

@require_http_methods(["GET", "POST"])
def signalements(request):
    if request.method == "POST":
        action = request.POST.get("action", "resolve")
        report_id = request.POST.get("id")
        admin = _admin_profile(request)
        notes = request.POST.get("notes", "")
        try:
            if action == "dismiss":
                moderation_controller.dismiss_report(report_id, admin, notes)
                _audit_report(request, "report.dismiss", report_id, f"a ignoré le signalement {report_id}")
                messages.success(request, "Signalement ignoré.")
            elif action == "warn":
                moderation_controller.warn_reported_user(report_id, admin, notes)
                _audit_report(request, "report.warn", report_id, f"a envoyé un avertissement via le signalement {report_id}")
                messages.success(request, "Avertissement officiel envoyé.")
            elif action == "ban":
                moderation_controller.ban_from_report(report_id, admin, notes)
                _audit_report(request, "report.ban", report_id, f"a banni un utilisateur via le signalement {report_id}")
                messages.success(request, "Utilisateur banni.")
            elif action == "blacklist":
                moderation_controller.blacklist_from_report(report_id, admin, notes)
                _audit_report(request, "report.blacklist", report_id, f"a blacklisté des photos via le signalement {report_id}")
                messages.success(request, "Photos ajoutées à la liste noire.")
            else:
                moderation_controller.resolve_report(
                    report_id,
                    admin,
                    request.POST.get("status"),
                    resolution=request.POST.get("resolution"),
                    notes=notes,
                )
                _audit_report(request, "report.resolve", report_id, f"a traité le signalement {report_id}")
                messages.success(request, "Signalement traité.")
        except Exception as exc:
            messages.error(request, str(exc) or "Action impossible.")
        return redirect("admin_panel:signalements")

    status = request.GET.get("status") or None
    priority = request.GET.get("priority") or None
    q = request.GET.get("q", "")
    page_obj = moderation_controller.list_reports(
        status=status,
        search=q,
        priority=priority,
        page=_page_param(request),
        per_page=30,
    )
    ctx = {
        "page_obj": page_obj,
        "statuses": ReportStatus.choices,
        "status_filters": [
            ("pending", "En attente"),
            ("resolved", "Traité"),
            ("dismissed", "Ignoré"),
            ("action_taken", "Action prise"),
        ],
        "current_status": status,
        "current_priority": priority,
        "q": q,
        "summary": moderation_controller.reports_summary(),
    }
    if request.GET.get("format") == "partial":
        html = render(request, "admin_panel/partials/signalements_rows.html", ctx)
        response = HttpResponse(html.content, content_type="text/html; charset=utf-8")
        response["X-Reports-Total"] = str(page_obj.paginator.count)
        response["X-Reports-Has-Next"] = "1" if page_obj.has_next else "0"
        response["X-Reports-Next-Page"] = (
            str(page_obj.next_page_number()) if page_obj.has_next else ""
        )
        return response
    return render(
        request,
        "admin_panel/signalements.html",
        {
            "title": "Modération & Signalements",
            **ctx,
        },
    )

@require_http_methods(["GET", "POST"])
def signalement_detail(request, report_id):
    report = moderation_controller.get_report(report_id)
    if report is None:
        raise Http404("Signalement introuvable")
    admin = _admin_profile(request)

    if request.method == "POST":
        action = request.POST.get("action")
        notes = request.POST.get("notes", "")
        try:
            if action == "dismiss":
                moderation_controller.dismiss_report(report.id, admin, notes)
                _audit_report(request, "report.dismiss", report.id, f"a ignoré le signalement {report.id}")
                messages.success(request, "Signalement ignoré.")
            elif action == "warn":
                moderation_controller.warn_reported_user(report.id, admin, notes)
                _audit_report(request, "report.warn", report.id, f"a envoyé un avertissement via le signalement {report.id}")
                messages.success(request, "Avertissement officiel envoyé.")
            elif action == "ban":
                moderation_controller.ban_from_report(report.id, admin, notes)
                reported = report.reported_profile
                ref = audit_controller.profile_ref(reported) if reported else "?"
                _audit_report(request, "report.ban", report.id, f"a banni l'utilisateur {ref} suite au signalement")
                messages.success(request, "Utilisateur banni définitivement.")
            elif action == "blacklist":
                moderation_controller.blacklist_from_report(report.id, admin, notes)
                _audit_report(request, "report.blacklist", report.id, f"a blacklisté des photos via le signalement {report.id}")
                messages.success(request, "Empreintes photo ajoutées à la liste noire.")
            else:
                messages.error(request, "Action inconnue.")
        except Exception as exc:
            messages.error(request, str(exc) or "Action impossible.")
        return redirect("admin_panel:signalement_detail", report_id=report.id)

    context = moderation_controller.report_context(report)
    return render(
        request,
        "admin_panel/signalement_detail.html",
        {
            "title": f"Signalement #{str(report.id)[:8]}",
            "report": report,
            "priority": moderation_controller.report_priority_label(report),
            "context": context,
            "statuses": ReportStatus.choices,
        },
    )

@require_http_methods(["GET", "POST"])
def monetisation(request):
    tab = request.GET.get("tab") or "plans"
    if tab not in {"plans", "promos"}:
        tab = "plans"
    if request.method == "POST":
        action = request.POST.get("action", "save_plans")
        try:
            if action == "add_plan":
                plan_id = site_settings_controller.validate_plan_id(request.POST.get("new_plan_id"))
                site_settings_controller.add_subscription_plan(
                    plan_id,
                    {
                        "label": request.POST.get("new_label", "").strip(),
                        "price": request.POST.get("new_price"),
                        "duration_label": request.POST.get("new_duration_label", "").strip(),
                        "duration_days": request.POST.get("new_duration_days"),
                        "tier_kind": request.POST.get("new_tier_kind", ""),
                        "audience": request.POST.get("new_audience", "all"),
                        "active": request.POST.get("new_active") == "on",
                        "is_featured": request.POST.get("new_featured") == "on",
                        "badge": request.POST.get("new_badge", "").strip(),
                        "features": request.POST.get("new_features", ""),
                    },
                )
                _audit(request, "monetisation.plan_add", f"a ajouté la formule d'abonnement {plan_id}", target_type="plan", target_id=plan_id)
                messages.success(request, "Formule d'abonnement ajoutée.")
                tab = "plans"
            elif action == "delete_plan":
                plan_id = request.POST.get("plan_id", "")
                site_settings_controller.remove_subscription_plan(plan_id)
                _audit(request, "monetisation.plan_delete", f"a supprimé la formule d'abonnement {plan_id}", target_type="plan", target_id=plan_id)
                messages.success(request, "Formule supprimée.")
            elif action == "save_plans":
                site_settings_controller.save_subscription_plans(
                    site_settings_controller.parse_plans_from_post(request.POST)
                )
                _audit(request, "monetisation.plans_save", "a enregistré les formules d'abonnement")
                messages.success(request, "Formules d'abonnement enregistrées.")
            elif action == "save_packs":
                site_settings_controller.save_in_app_packs(
                    site_settings_controller.parse_packs_from_post(request.POST)
                )
                _audit(request, "monetisation.packs_save", "a enregistré les packs in-app")
                messages.success(request, "Packs in-app enregistrés.")
                tab = "packs"
            elif action == "add_pack":
                pack_id = site_settings_controller.add_in_app_pack(
                    request.POST.get("new_pack_id", ""),
                    {
                        "label": request.POST.get("new_pack_label", "").strip(),
                        "description": request.POST.get("new_pack_desc", "").strip(),
                        "price": request.POST.get("new_pack_price"),
                        "pack_type": request.POST.get("new_pack_type", ""),
                        "quantity": request.POST.get("new_pack_qty"),
                        "duration_days": request.POST.get("new_pack_days"),
                        "active": request.POST.get("new_pack_active") == "on",
                    },
                )
                added_id = request.POST.get("new_pack_id", "").strip().lower()
                _audit(request, "monetisation.pack_add", f"a ajouté le pack {added_id}", target_type="pack", target_id=added_id)
                messages.success(request, "Pack in-app ajouté.")
                tab = "packs"
            elif action == "delete_pack":
                pack_id = request.POST.get("pack_id", "")
                site_settings_controller.remove_in_app_pack(pack_id)
                _audit(request, "monetisation.pack_delete", f"a supprimé le pack {pack_id}", target_type="pack", target_id=pack_id)
                messages.success(request, "Pack supprimé.")
                tab = "packs"
            elif action == "create_promo":
                promo = monetization_controller.create_promo_code(
                    {
                        "code": request.POST.get("promo_code", ""),
                        "plan_tier": request.POST.get("promo_plan_tier", ""),
                        "discount_percent": request.POST.get("promo_discount"),
                        "expires_at": request.POST.get("promo_expires"),
                        "max_uses": request.POST.get("promo_max_uses"),
                        "unlimited": request.POST.get("promo_unlimited") == "on",
                        "active": request.POST.get("promo_active") == "on",
                        "note": request.POST.get("promo_note", ""),
                    }
                )
                _audit(request, "monetisation.promo_create", f"a créé le code promo {getattr(promo, 'code', request.POST.get('promo_code', ''))}", target_type="promo", target_id=str(getattr(promo, 'id', '')))
                messages.success(request, "Code promo créé.")
                tab = "promos"
            elif action == "update_promo":
                promo_id = request.POST.get("promo_id")
                monetization_controller.update_promo_code(
                    promo_id,
                    {
                        "plan_tier": request.POST.get("promo_plan_tier", ""),
                        "discount_percent": request.POST.get("promo_discount"),
                        "expires_at": request.POST.get("promo_expires"),
                        "max_uses": request.POST.get("promo_max_uses"),
                        "unlimited": request.POST.get("promo_unlimited") == "on",
                        "active": request.POST.get("promo_active") == "on",
                        "note": request.POST.get("promo_note", ""),
                    },
                )
                _audit(request, "monetisation.promo_update", f"a mis à jour le code promo {promo_id}", target_type="promo", target_id=str(promo_id))
                messages.success(request, "Code promo mis à jour.")
                tab = "promos"
            elif action == "toggle_promo":
                promo_id = request.POST.get("promo_id")
                active = request.POST.get("promo_active") == "1"
                monetization_controller.toggle_promo_code(promo_id, active=active)
                state = "activé" if active else "désactivé"
                _audit(request, "monetisation.promo_toggle", f"a {state} le code promo {promo_id}", target_type="promo", target_id=str(promo_id))
                messages.success(request, "Statut du code promo mis à jour.")
                tab = "promos"
            elif action == "delete_promo":
                promo_id = request.POST.get("promo_id")
                monetization_controller.delete_promo_code(promo_id)
                _audit(request, "monetisation.promo_delete", f"a supprimé le code promo {promo_id}", target_type="promo", target_id=str(promo_id))
                messages.success(request, "Code promo supprimé.")
                tab = "promos"
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, str(exc) or "Action impossible.")
        return redirect(f"{reverse('admin_panel:monetisation')}?tab={tab}")

    plans = site_settings_controller.get_subscription_plans()
    configured_ids = set(plans.keys())
    plan_rows = sorted(
        [{"id": plan_id, **meta} for plan_id, meta in plans.items()],
        key=lambda row: (row.get("tier_kind", ""), row.get("price", 0)),
    )
    packs = site_settings_controller.get_in_app_packs()
    pack_rows = sorted(
        [{"id": pack_id, **meta} for pack_id, meta in packs.items()],
        key=lambda row: (row.get("pack_type", ""), row.get("price", 0)),
    )
    promo_codes = monetization_controller.list_promo_codes()
    promo_stats = monetization_controller.promo_summary()
    active_plans = sum(1 for row in plan_rows if row.get("active"))
    active_packs = sum(1 for row in pack_rows if row.get("active"))
    return render(
        request,
        "admin_panel/monetisation.html",
        {
            "title": "Gestion des Offres & Monétisation",
            "tab": tab,
            "plan_rows": plan_rows,
            "pack_rows": pack_rows,
            "promo_codes": promo_codes,
            "promo_stats": promo_stats,
            "active_plans": active_plans,
            "total_plans": len(plan_rows),
            "active_packs": active_packs,
            "total_packs": len(pack_rows),
            "available_tiers": [
                (tier_id, label)
                for tier_id, label in site_settings_controller.subscription_tier_choices_for_admin()
                if tier_id not in configured_ids
            ],
            "tier_kinds": [
                ("premium", "Premium"),
                ("vip", "VIP"),
                ("pass_femme", "Pass Femme"),
            ],
            "catalog_pack_ids": list(site_settings_controller.DEFAULT_IN_APP_PACKS.keys()),
            "pack_types": [
                ("boost", "Boost"),
                ("super_like", "Super-Like"),
                ("rewind", "Rewind"),
            ],
        },
    )

@require_http_methods(["GET", "POST"])
def communications(request):
    tab = request.GET.get("tab", "campaigns")
    if request.method == "POST":
        action = request.POST.get("action", "")
        try:
            if action == "create_campaign":
                image_url = (request.POST.get("image_url") or "").strip()
                upload = request.FILES.get("image_file")
                if upload:
                    image_url = crm_controller.store_campaign_image(upload)
                campaign = crm_controller.create_campaign(
                    _admin_profile(request),
                    {
                        "name": request.POST.get("name", ""),
                        "channel": request.POST.get("channel", ""),
                        "title": request.POST.get("title", ""),
                        "body": request.POST.get("body", ""),
                        "send_mode": request.POST.get("send_mode", ""),
                        "scheduled_at": request.POST.get("scheduled_at", ""),
                        "image_url": image_url,
                        "segment": crm_controller.parse_segment_from_post(request.POST),
                    },
                )
                _audit(
                    request,
                    "crm.campaign_create",
                    f"a créé la campagne {campaign.name}",
                    target_type="campaign",
                    target_id=str(campaign.id),
                )
                if campaign.status == "sending":
                    messages.success(request, "Campagne lancée. L’envoi se poursuit en arrière-plan.")
                elif campaign.status == "sent":
                    messages.success(request, "Campagne envoyée aux destinataires.")
                elif campaign.status == "scheduled":
                    messages.success(request, "Campagne programmée. Elle partira à l’heure prévue.")
                else:
                    messages.success(request, "Campagne enregistrée en brouillon.")
                tab = "campaigns"
            elif action == "launch_campaign":
                campaign_id = request.POST.get("campaign_id")
                crm_controller.launch_campaign(campaign_id)
                _audit(
                    request,
                    "crm.campaign_launch",
                    f"a lancé la campagne {campaign_id}",
                    target_type="campaign",
                    target_id=str(campaign_id),
                )
                messages.success(request, "Envoi lancé en arrière-plan.")
            elif action == "republish_campaign":
                campaign_id = request.POST.get("campaign_id")
                clone = crm_controller.republish_campaign(campaign_id, _admin_profile(request))
                _audit(
                    request,
                    "crm.campaign_republish",
                    f"a republicé la campagne {campaign_id}",
                    target_type="campaign",
                    target_id=str(clone.id),
                )
                messages.success(request, "Republication lancée en arrière-plan.")
            elif action == "cancel_campaign":
                campaign_id = request.POST.get("campaign_id")
                crm_controller.cancel_campaign(campaign_id)
                _audit(
                    request,
                    "crm.campaign_cancel",
                    f"a annulé la campagne {campaign_id}",
                    target_type="campaign",
                    target_id=str(campaign_id),
                )
                messages.success(request, "Campagne annulée.")
            elif action == "save_settings":
                crm_controller.save_crm_settings(
                    {
                        "popups_enabled": request.POST.get("popups_enabled") == "on",
                        "marketing_push_enabled": request.POST.get("marketing_push_enabled") == "on",
                        "show_on_login": request.POST.get("show_on_login") == "on",
                        "show_on_every_page": request.POST.get("show_on_every_page") == "on",
                        "popup_poll_seconds": int(request.POST.get("popup_poll_seconds") or 45),
                        "email_from_name": request.POST.get("email_from_name", ""),
                    }
                )
                _audit(request, "crm.settings", "a mis à jour les paramètres CRM")
                messages.success(request, "Paramètres CRM enregistrés.")
                tab = "settings"
        except (PermissionError, ValueError) as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, str(exc) or "Action impossible.")
        return redirect(f"{reverse('admin_panel:communications')}?tab={tab}")

    from core.models.crm import CampaignChannel, CampaignSendMode

    return render(
        request,
        "admin_panel/communications.html",
        {
            "title": "Notification & Communication",
            "tab": tab,
            "campaigns": crm_controller.list_campaigns(),
            "summary": crm_controller.campaigns_summary(),
            "crm_settings": crm_controller.get_crm_settings(),
            "channels": [c for c in CampaignChannel.choices if c[0] != CampaignChannel.EMAIL],
            "send_modes": CampaignSendMode.choices,
            "platform_cities": crm_controller.list_platform_cities(limit=20),
        },
    )


@require_GET
def communications_cities(request):
    q = (request.GET.get("q") or "").strip()
    cities = crm_controller.list_platform_cities(q)
    return JsonResponse({"ok": True, "cities": cities})


@require_http_methods(["GET", "POST"])
def configuration(request):
    tab = request.GET.get("tab") or "algorithm"
    if request.method == "POST":
        action = request.POST.get("action", "save")
        try:
            if action == "save_algorithm":
                from core.controllers import quota_controller

                quota_controller.save_limits_from_post(request.POST)
                _audit(request, "config.algorithm", "a mis à jour les quotas freemium")
                messages.success(request, "Restrictions enregistrées. Elles s’appliquent immédiatement aux membres.")
                tab = "algorithm"
            elif action == "save_features":
                cfg = app_config_controller.save_features_from_post(request.POST)
                _audit(
                    request,
                    "config.features",
                    "a mis à jour les fonctionnalités app (texte, vocal, image, selfie)",
                    metadata={
                        "text": cfg["text_messages_enabled"],
                        "voice": cfg["voice_messages_enabled"],
                        "image": cfg["image_messages_enabled"],
                        "selfie": cfg["selfie_verification_enabled"],
                    },
                )
                tab = "features"
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"ok": True, "features": app_config_controller.feature_flags()})
                messages.success(request, "Fonctionnalités appliquées immédiatement sur le site.")
            elif action == "save_maintenance":
                saved = site_settings_controller.save_maintenance_from_post(request.POST)
                _audit(
                    request,
                    "config.maintenance",
                    f"a mis à jour le mode maintenance ({'on' if saved['maintenance_mode'] else 'off'})",
                    metadata=saved,
                )
                messages.success(request, "Mode maintenance enregistré.")
                tab = "system"
            elif action == "save_registrations":
                enabled = site_settings_controller.save_registrations_from_post(request.POST)
                _audit(
                    request,
                    "config.registrations",
                    f"a {'ouvert' if enabled else 'fermé'} les inscriptions",
                    metadata={"registrations_enabled": enabled},
                )
                messages.success(request, "Inscriptions enregistrées.")
                tab = "system"
            elif action == "save_force_update":
                cfg = app_config_controller.save_force_update_from_post(request.POST)
                _audit(
                    request,
                    "config.force_update",
                    f"a mis à jour la version minimale iOS/Android ({'on' if cfg['force_update_enabled'] else 'off'})",
                    metadata={
                        "enabled": cfg["force_update_enabled"],
                        "ios": cfg["force_update_ios"],
                        "android": cfg["force_update_android"],
                    },
                )
                messages.success(request, "Version minimale iOS / Android enregistrée.")
                tab = "system"
            elif action == "save_system":
                saved = site_settings_controller.save_maintenance_from_post(request.POST)
                enabled = site_settings_controller.save_registrations_from_post(request.POST)
                cfg = app_config_controller.save_force_update_from_post(request.POST)
                _audit(
                    request,
                    "config.system",
                    f"a mis à jour les paramètres système (maintenance={'on' if saved['maintenance_mode'] else 'off'}, inscriptions={'on' if enabled else 'off'})",
                    metadata={
                        "maintenance_mode": saved["maintenance_mode"],
                        "registrations_enabled": enabled,
                        "force_update_enabled": cfg["force_update_enabled"],
                    },
                )
                messages.success(request, "Paramètres système enregistrés.")
                tab = "system"
        except ValueError as exc:
            messages.error(request, str(exc))
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"ok": False, "error": str(exc)}, status=400)
        except Exception as exc:
            messages.error(request, str(exc) or "Enregistrement impossible.")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"ok": False, "error": str(exc) or "Enregistrement impossible."}, status=400)
        return redirect(f"{reverse('admin_panel:configuration')}?tab={tab}")

    from core.controllers import quota_controller

    settings = site_settings_controller.get_all()
    app_config = app_config_controller.get_app_config()
    return render(
        request,
        "admin_panel/configuration.html",
        {
            "title": "Configuration Globale de l'App",
            "tab": tab,
            "settings": settings,
            "app_config": app_config,
            "quotas": quota_controller.quota_settings(),
        },
    )

@require_http_methods(["GET", "POST"])
def roles_audit(request):
    actor = _admin_profile(request)
    tab = request.GET.get("tab", "equipe")
    if tab == "securite":
        return redirect(f"{reverse('admin_panel:roles_audit')}?tab=equipe")

    if request.method == "POST":
        action = request.POST.get("action", "")
        try:
            if action == "create_staff":
                profile = rbac_controller.create_staff_user(
                    actor,
                    email=request.POST.get("email", ""),
                    password=request.POST.get("password", ""),
                    first_name=request.POST.get("first_name", ""),
                    last_name=request.POST.get("last_name", ""),
                    role=request.POST.get("role", ""),
                )
                audit_controller.log_action(
                    actor,
                    "staff.create",
                    f"a créé le compte staff {profile.display_name} ({rbac_controller.role_label(profile.role)})",
                    target_type="profile",
                    target_id=str(profile.id),
                    request=request,
                )
                messages.success(request, "Compte staff créé avec succès.")
            elif action == "update_role":
                target = rbac_controller.update_staff_role(
                    actor, request.POST.get("profile_id"), request.POST.get("role", "")
                )
                audit_controller.log_action(
                    actor,
                    "staff.role_update",
                    f"a modifié le rôle de {target.display_name} → {rbac_controller.role_label(target.role)}",
                    target_type="profile",
                    target_id=str(target.id),
                    request=request,
                )
                messages.success(request, "Rôle mis à jour.")
            elif action == "deactivate_staff":
                target = rbac_controller.deactivate_staff(actor, request.POST.get("profile_id"))
                audit_controller.log_action(
                    actor,
                    "staff.deactivate",
                    f"a désactivé le compte staff {target.display_name}",
                    target_type="profile",
                    target_id=str(target.id),
                    request=request,
                )
                messages.success(request, "Compte staff désactivé.")
            elif action == "save_2fa_policy":
                if not actor.is_super_admin:
                    raise PermissionError("Seul un super administrateur peut modifier la politique 2FA.")
                two_factor_controller.save_admin_security_settings(
                    {"require_2fa": request.POST.get("require_2fa") == "on"}
                )
                audit_controller.log_action(
                    actor,
                    "security.2fa_policy",
                    "a mis à jour la politique 2FA obligatoire pour l'équipe admin",
                    request=request,
                )
                messages.success(request, "Politique 2FA enregistrée.")
        except (PermissionError, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect(f"{reverse('admin_panel:roles_audit')}?tab={tab}")

    staff = rbac_controller.list_staff_members()
    for member in staff:
        member.tfa_status = two_factor_controller.two_factor_status(member)
    audit_page = audit_controller.list_audit_logs(
        search=request.GET.get("q", ""),
        action=request.GET.get("action") or None,
        page=_page_param(request),
    )
    return render(
        request,
        "admin_panel/roles_audit.html",
        {
            "title": "Gestion des Rôles & Audit",
            "tab": tab,
            "staff_members": staff,
            "staff_summary": rbac_controller.staff_summary(),
            "staff_roles": rbac_controller.STAFF_ROLE_CHOICES,
            "audit_page": audit_page,
            "audit_summary": audit_controller.audit_summary(),
            "audit_action_filters": audit_controller.ACTION_FILTERS,
            "current_audit_action": request.GET.get("action") or "",
            "admin_security": two_factor_controller.get_admin_security_settings(),
            "can_manage_staff": actor.is_super_admin or rbac_controller.has_permission(actor, "roles.manage"),
        },
    )

@require_http_methods(["GET", "POST"])
def admin_2fa_setup(request):
    profile = _admin_profile(request)
    if not profile or not profile.is_staff_member:
        return redirect("admin_panel:connexion")

    record = two_factor_controller.get_or_create_two_factor(profile)
    if request.method == "POST":
        try:
            two_factor_controller.enable_two_factor(profile, request.POST.get("code", ""))
            request.session["admin_2fa_verified"] = True
            audit_controller.log_action(
                profile,
                "security.2fa_enable",
                "a activé l'authentification à deux facteurs",
                request=request,
            )
            messages.success(request, "2FA activée. Conservez vos codes de secours.")
            return redirect("admin_panel:dashboard")
        except ValueError as exc:
            messages.error(request, str(exc))

    backup_codes = record.backup_codes if record.is_enabled else []
    return render(
        request,
        "admin_panel/admin_2fa_setup.html",
        {
            "title": "Configuration 2FA",
            "secret": record.secret,
            "provisioning_uri": two_factor_controller.provisioning_uri(profile, record.secret),
            "backup_codes": backup_codes,
            "require_2fa": two_factor_controller.get_admin_security_settings().get("require_2fa", True),
        },
    )

@require_http_methods(["GET", "POST"])
def admin_2fa_verify(request):
    profile = _admin_profile(request)
    if not profile or not profile.is_staff_member:
        return redirect("admin_panel:connexion")

    status = two_factor_controller.two_factor_status(profile)
    if not status["enabled"]:
        return redirect("admin_panel:admin_2fa_setup")

    if request.method == "POST":
        code = request.POST.get("code", "")
        if two_factor_controller.verify_login_code(profile, code):
            request.session["admin_2fa_verified"] = True
            audit_controller.log_action(
                profile,
                "security.2fa_verify",
                "s'est authentifié via 2FA",
                request=request,
            )
            return redirect(request.GET.get("next") or "admin_panel:dashboard")
        messages.error(request, "Code invalide. Réessayez.")

    return render(
        request,
        "admin_panel/admin_2fa_verify.html",
        {"title": "Vérification 2FA"},
    )
