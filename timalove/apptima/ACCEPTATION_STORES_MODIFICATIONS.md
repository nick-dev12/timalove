# TimaLove — Modifications pour l’acceptation App Store & Play Store

Document de référence **unique** listant tout ce qui a été apporté au projet pour répondre au refus Apple **Guideline 4.3(b) Design: Spam** (app perçue comme dating générique) et renforcer la conformité **Google Play**.

**Date de synthèse :** 20 septembre 2026  
**Bundle iOS :** `com.mytimalove.app`  
**Bundle Android :** `com.timalove.app`  
**Site production :** https://mytimalove.com/

---

## Sommaire

1. [Contexte et objectif](#1-contexte-et-objectif)
2. [Vue d’ensemble — Lots A et B](#2-vue-densemble--lots-a-et-b)
3. [Lot A — Positionnement matrimonial natif](#3-lot-a--positionnement-matrimonial-natif)
4. [Lot B — Communauté guidée (anti-dating)](#4-lot-b--communauté-guidée-anti-dating)
5. [Renommage du vocabulaire UI](#5-renommage-du-vocabulaire-ui)
6. [Compte démo Apple Review + production](#6-compte-démo-apple-review--production)
7. [Permissions et conformité 5.1.1](#7-permissions-et-conformité-511)
8. [Fichiers modifiés (inventaire)](#8-fichiers-modifiés-inventaire)
9. [Déploiement](#9-déploiement)
10. [App Store Connect & Play Console](#10-app-store-connect--play-console)
11. [Parcours reviewer (3 minutes)](#11-parcours-reviewer-3-minutes)
12. [Points restants et risques](#12-points-restants-et-risques)
13. [Documents connexes](#13-documents-connexes)

---

## 1. Contexte et objectif

### Problème initial

Apple a refusé **Mytimalove** avec :

- **Guideline 4.3(b) — Design: Spam** : l’app ressemble à une app de rencontre générique (swipe, cœurs, vocabulaire « dating »).
- **Extended Review** : examen prolongé.

Signaux négatifs identifiés côté reviewer :

| Signal « dating générique » | État avant refus |
|----------------------------|------------------|
| Swipe infini + cœurs animés | Explorer type Tinder |
| Vocabulaire Explorer / Likes / Match | Termes dating US |
| App = simple WebView du site | Peu de valeur native visible |
| Inscription ouverte immédiate | Profils approuvés par défaut |
| Catégorie & mots-clés store | Risque « dating » |

### Stratégie retenue

Ne pas réécrire l’app, mais **rendre visible** ce qui existe déjà (intention mariage, modération, coaching, compatibilité) et ajouter des **flux distinctifs** qu’Apple ne retrouve pas dans un clone Tinder :

1. **Lot A** — différenciation native + vocabulaire matrimonial + iPhone only.
2. **Lot B** — validation humaine, parcours curated, messages guidés, coaching en navigation principale.

---

## 2. Vue d’ensemble — Lots A et B

| Lot | Thème | Statut code | Statut prod (20/09/2026) |
|-----|-------|-------------|--------------------------|
| **A** | Onboarding natif, charte, splash, iPhone only, vocabulaire UI, permissions | ✅ Livré | ⚠️ Flutter à rebuild + deploy web complet |
| **B** | Pending, validation, liste curated, messages guidés, coaching dock | ✅ Livré | ⚠️ Partiel sur VPS (compte review + migration 0021 seulement) |
| **Manuel** | Métadonnées store, captures, réponse Resolution Center | ⬜ À faire | — |

---

## 3. Lot A — Positionnement matrimonial natif

### 3.1 Onboarding natif Flutter (avant WebView)

**Fichier :** `lib/widgets/matrimonial_onboarding.dart`  
**Branchement :** `lib/main.dart` → `MatrimonialOnboardingGate` → `WebViewScreen`

3 écrans natifs au **premier lancement** :

1. **Mission** — parcours vers le mariage, pas le dating casual.
2. **Parcours guidé** — comment fonctionne la mise en relation sérieuse.
3. **Charte matrimoniale** — case obligatoire à cocher avant d’accéder au site.

Persistance : `SharedPreferences` clé `timalove_matrimonial_onboarding_v1`.

### 3.2 Splash / écran de chargement

**Fichier :** `lib/widgets/timalove_launch_loader.dart`

- Logo TimaLove + texte **« Parcours guidé vers le mariage »**.
- Suppression de l’esthétique double-cœur « dating app ».

**Assets :** `assets/images/timalove_logo_splash.png`, palette crème `#FDF5F0` (`pubspec.yaml` → `flutter_native_splash`).

### 3.3 iPhone only (App Store)

**Fichier :** `ios/Runner.xcodeproj/project.pbxproj`

```
TARGETED_DEVICE_FAMILY = 1
SUPPORTED_PLATFORMS = iphoneos
```

Build ciblé **iPhone uniquement** — expérience matrimoniale focalisée, pas iPad générique.

### 3.4 Valeur native iOS (au-delà de la WebView)

| Fonctionnalité | Fichier(s) |
|----------------|------------|
| Sign in with Apple / Google | `lib/services/social_auth_service.dart` |
| Push APNs / FCM | `lib/services/fcm_service.dart` |
| Dialogues permissions avant prompt système | `lib/services/native_permission_service.dart` |
| Universal Links `mytimalove.com` | `ios/Runner/Runner.entitlements`, `lib/config/webview_site_config.dart` |
| Gate version forcée | `lib/widgets/app_version_gate.dart`, `lib/services/app_version_service.dart` |
| Palette TimaLove native | `lib/theme/app_colors.dart` |

### 3.5 Configuration iOS review-safe

**Fichier :** `ios/Runner/Info.plist`

- `CFBundleDisplayName` : **TimaLove**
- Usage strings camera / micro / photos / localisation (**when-in-use only**)
- `UIBackgroundModes` : **`remote-notification` uniquement** — pas de localisation arrière-plan

---

## 4. Lot B — Communauté guidée (anti-dating)

### 4.1 Validation humaine des inscriptions

**Migration :** `core/migrations/0021_lot_b_pending_guided.py`

- Nouvelles inscriptions → `registration_status = pending` (plus `approved` automatique).
- Seuls les profils **approuvés** apparaissent dans le Parcours.

**Contrôleurs modifiés :**

| Fichier | Changement |
|---------|------------|
| `controllers/signup_controller.py` | Fin inscription → `pending` |
| `controllers/onboarding_controller.py` | Fin onboarding → `pending` + message 24–48 h |
| `controllers/auth_controller.py` | OAuth / complétion profil → `pending` |
| `controllers/registration_controller.py` | **Nouveau** — garde d’accès, chemins autorisés |
| `middleware/auth_guards.py` | Redirection vers validation si non approuvé |

**Écran dédié :** `/validation-en-attente/`  
**Template :** `templates/app/validation_pending.html`

Accès limité en attente : profil, coaching, pages légales.  
Parcours / likes / messages **bloqués** jusqu’à approbation admin.

### 4.2 Parcours en liste curated (plus de swipe infini)

**Contrôleur :** `controllers/explore_controller.py` → `curated_daily_feed()`

- **8 profils/jour** sélectionnés selon compatibilité.
- Affichage en **grille** (photo, intention, % Compatible, actions).
- Session Django mémorise la sélection du jour.
- Mode swipe infini désactivé quand le flag est actif.

**Template :** `templates/partials/explorer_curated_list.html`  
**CSS :** `static/css/timalove.css` (sections `.curated-list*`, `.curated-card*`)

**Flags admin** (`app_config_controller.py`) :

| Flag | Défaut | Rôle |
|------|--------|------|
| `explorer_curated_mode` | `true` | Liste curated vs swipe |
| `curated_daily_limit` | `8` | Profils max / jour |
| `guided_messages_enabled` | `true` | Messages guidés actifs |

### 4.3 Coaching en navigation principale

**Fichier :** `templates/partials/explorer_dock.html`

Nouvel onglet **Coaching** dans la barre du bas (dock) :

```
Intérêts | Parcours | Coaching | Messages | Profil
```

**Page :** `templates/landing/coaching.html` (dock actif sur coaching).

### 4.4 Messages guidés (premier message)

**Modèle :** `core/models/matching.py` → `Match.guided_intro_completed`

**Contrôleur :** `controllers/message_controller.py`

- 3 questions suggérées orientées mariage (`GUIDED_INTRO_PROMPTS`).
- Le **1er message** doit choisir une des suggestions — pas de texte libre immédiat.
- Ensuite messagerie normale.

**UI :** `templates/app/message_thread.html` + CSS `.msg__guided*` dans `timalove.css`.

---

## 5. Renommage du vocabulaire UI

Objectif : supprimer le framing « dating US » visible par le reviewer.

| Ancien terme | Nouveau terme |
|--------------|---------------|
| Explorer | **Parcours** |
| Likes | **Intérêts** |
| Match | **Mise en relation** |
| Super like | **Priorité** |
| % Match | **% Compatible** |

### Templates principaux touchés

- `partials/explorer_dock.html`, `layouts/app.html`
- `app/likes.html`, `landing/explorer.html`
- `partials/explorer_curated_list.html`, `partials/likes_feed.html`
- `partials/visit_profil.html`, `partials/discover_card.html`
- `app/messages.html`, `app/profil.html`, `layouts/public.html`

### JavaScript

- `static/js/explorer-match.js` — « Compatible ? », « X% Compatible »
- `static/js/message-invite.js` — « Priorité — mise en relation ! »
- `static/js/realtime.js` — notifications « Mise en relation », « Priorité reçue »

### Tagline marque

`context_processors.py` + `home_controller.py` :

> **Mise en relation sérieuse vers le mariage**

### Termes encore présents (nettoyage optionnel)

- `partials/likes_match_badge.html` — libellé visible « Match » (aria-label déjà « Mise en relation »)
- `landing/explorer.html` — lien invité « Explorer » (ligne menu)
- `home_controller.py` — étape onboarding mentionne encore « swipez pour trouver votre match »

---

## 6. Compte démo Apple Review + production

### Commande Django

```bash
cd timalove
python manage.py create_apple_review_account --reset-partners
```

**Fichier :** `core/management/commands/create_apple_review_account.py`

### Identifiants App Store Connect

| Champ | Valeur |
|-------|--------|
| Email | `apple.review@timalove.local` |
| Mot de passe | `AppleReview2026!` |
| Statut | **`approved`** (pré-approuvé — ne passe pas par `/validation-en-attente/`) |

### Profils démo créés

| Profil | Rôle review |
|--------|-------------|
| **Amadou Review** | Compte reviewer (homme, intention Mariage, profil complet) |
| **Awa Demo** | Match + conversation active (message guidé déjà envoyé) |
| **Fatou Demo** | Match + fil vide → **questions guidées obligatoires** |

### Quota exempt (freemium)

Dans `.env` production :

```
QUOTA_EXEMPT_EMAILS=apple.review@timalove.local,gooteste@gmail.com
```

**Fichiers :** `config/settings.py`, `deploy/env.mytimalove.example`, `timalove/.env.example`

### Script VPS

```bash
python scripts/_vps_create_apple_review.py
```

**Vérification :** `python scripts/_vps_verify_quota_exempt.py apple.review@timalove.local`

### État production (20/09/2026)

| Action | Statut |
|--------|--------|
| Migration `0021` appliquée sur VPS | ✅ |
| Compte review créé | ✅ |
| `QUOTA_EXEMPT_EMAILS` mis à jour | ✅ |
| Services redémarrés (daphne, celery) | ✅ |
| **Deploy complet Lot B** (templates, guards, curated UI…) | ⚠️ **Non déployé via git** — hotfix partiel par SCP |

> **Important :** le reviewer Apple **doit** utiliser le compte pré-approuvé. Toute nouvelle inscription reste bloquée sur l’écran de validation.

---

## 7. Permissions et conformité 5.1.1

Résumé — détail complet dans **`JUSTIFICATIONS_PERMISSIONS.md`**.

| Permission | Usage TimaLove | iOS | Android |
|------------|----------------|-----|---------|
| Caméra | Photo profil, selfie vérification | ✅ When-in-use | ✅ |
| Micro | Messages vocaux | ✅ | ✅ |
| Photos | Galerie profil | ✅ | ✅ |
| Localisation | Ville / proximité profils | ✅ **When-in-use only** | ✅ |
| Notifications | Intérêts, messages, mises en relation | ✅ APNs | ✅ FCM |
| Localisation arrière-plan | **Non utilisé** | ❌ Absent | ❌ Absent |

**Flutter :** dialogues explicatifs in-app avant chaque prompt système (`native_permission_service.dart`).

---

## 8. Fichiers modifiés (inventaire)

### Flutter — `timalove/apptima/`

| Fichier | Lot | Modification |
|---------|-----|--------------|
| `lib/widgets/matrimonial_onboarding.dart` | A | Onboarding 3 écrans + charte |
| `lib/widgets/timalove_launch_loader.dart` | A | Splash matrimonial |
| `lib/main.dart` | A | Gate onboarding |
| `lib/widgets/app_version_gate.dart` | A | Force update |
| `lib/services/native_permission_service.dart` | A | Rationale permissions |
| `lib/services/social_auth_service.dart` | A | Apple / Google natif |
| `lib/services/fcm_service.dart` | A | Push |
| `lib/config/webview_site_config.dart` | A | URL mytimalove.com |
| `lib/theme/app_colors.dart` | A | Palette TimaLove |
| `ios/Runner.xcodeproj/project.pbxproj` | A | iPhone only |
| `ios/Runner/Info.plist` | A | Usage strings, pas bg location |
| `ios/Runner/Runner.entitlements` | A | Universal Links, Sign in with Apple |

### Backend — `timalove/core/`

| Fichier | Lot | Modification |
|---------|-----|--------------|
| `migrations/0021_lot_b_pending_guided.py` | B | pending + guided_intro |
| `models/profile.py` | B | default pending |
| `models/matching.py` | B | guided_intro_completed |
| `controllers/signup_controller.py` | B | pending |
| `controllers/onboarding_controller.py` | B | pending |
| `controllers/auth_controller.py` | B | pending |
| `controllers/registration_controller.py` | B | **Nouveau** guards |
| `controllers/explore_controller.py` | B | curated_daily_feed |
| `controllers/message_controller.py` | B | messages guidés |
| `controllers/app_config_controller.py` | B | flags curated / guided |
| `middleware/auth_guards.py` | B | redirect validation |
| `views/public/views.py` | B | validation_pending, curated |
| `views/public/urls.py` | B | `/validation-en-attente/` |
| `views/app/views.py` | B | guided prompts thread |
| `context_processors.py` | A+B | flags + tagline |
| `management/commands/create_apple_review_account.py` | A+B | Compte démo |

### Templates — `timalove/templates/`

| Fichier | Lot | Modification |
|---------|-----|--------------|
| `app/validation_pending.html` | B | Écran attente validation |
| `partials/explorer_curated_list.html` | B | Grille curated |
| `partials/explorer_dock.html` | A+B | Vocabulaire + Coaching |
| `app/message_thread.html` | B | Composer guidé |
| `landing/coaching.html` | B | Page + dock |
| `landing/explorer.html` | A+B | Parcours, mode curated |
| `app/likes.html` | A | Intérêts reçus |
| + ~15 partials / pages | A | Vocabulaire matrimonial |

### Static — `timalove/static/`

| Fichier | Lot | Modification |
|---------|-----|--------------|
| `css/timalove.css` | B | Styles curated + guided |
| `js/explorer-match.js` | A | % Compatible |
| `js/message-invite.js` | A | Mise en relation |
| `js/realtime.js` | A | Notifications renommées |

### Scripts & deploy

| Fichier | Modification |
|---------|--------------|
| `scripts/_vps_create_apple_review.py` | Wrapper VPS compte review |
| `scripts/_vps_verify_quota_exempt.py` | Vérif quota exempt |
| `deploy/env.mytimalove.example` | QUOTA_EXEMPT_EMAILS |

---

## 9. Déploiement

### Local (dev + test Flutter)

Terminal 1 — **Daphne** (WebSocket) :

```powershell
cd C:\wamp64\www\projet_timalove\timalove
..\venv\Scripts\daphne.exe -b 127.0.0.1 -p 8000 config.asgi:application
```

Terminal 2 — **Celery worker** (optionnel si `CELERY_TASK_ALWAYS_EAGER=False`) :

```powershell
..\venv\Scripts\celery.exe -A config worker --loglevel=info --pool=solo
```

Terminal 3 — **Flutter** :

```powershell
cd timalove\apptima
flutter run
```

> En `DEBUG=True`, Celery exécute les tâches **en synchrone** par défaut — pas besoin de worker pour l’UI.

### Production — deploy complet Lot B

```bash
# Sur le VPS
sudo bash /home/jomas/timalove/timalove/deploy.sh
```

Avant deploy : **commit + push** de tous les fichiers Lot A/B (actuellement partiellement non versionnés sur Git).

### Migration

```bash
python manage.py migrate core 0021
```

---

## 10. App Store Connect & Play Console

Textes **copy-paste** prêts : **`APP_STORE_RESUBMISSION.md`**

### Checklist App Store (avant « Soumettre à nouveau »)

- [ ] Build iOS **5+** uploadé (iPhone only)
- [ ] Identifiants démo dans **App Review Information**
- [ ] **Notes for Review** collées (EN)
- [ ] Réponse **Resolution Center** collée (EN)
- [ ] Sous-titre : **« Parcours vers le mariage »**
- [ ] Description + mots-clés matrimoniaux (pas `dating`, `tinder`, `hookup`)
- [ ] Catégorie : **Style de vie** ou **Réseaux sociaux**
- [ ] Captures refaites (ordre recommandé ci-dessous)
- [ ] Compte review testé sur iPhone réel
- [ ] Deploy complet Lot B sur production
- [ ] URLs légales en 200 : privacy, suppression compte, sécurité enfants

### Captures recommandées (ordre)

1. Onboarding natif « Parcours vers le mariage »
2. Charte matrimoniale (case cochée)
3. Parcours — « Sélection du jour » + % Compatible + intention Mariage
4. Messages — questions guidées
5. Coaching (onglet + page)
6. Profil avec intention **Mariage**

### Google Play

- Même positionnement matrimonial dans la fiche store.
- Permissions alignées sur `JUSTIFICATIONS_PERMISSIONS.md`.
- Pas de localisation arrière-plan déclarée.

---

## 11. Parcours reviewer (3 minutes)

Script à suivre avec le compte `apple.review@timalove.local` :

| Étape | Action | Ce que le reviewer doit voir |
|-------|--------|------------------------------|
| 1 | Installation fraîche | Onboarding natif 3 écrans + charte obligatoire |
| 2 | Connexion démo | Accès direct (pas d’écran validation) |
| 3 | Onglet **Parcours** | Liste curated 8 profils, % Compatible, intention Mariage |
| 4 | **Messages → Awa** | Conversation active, intro guidée déjà envoyée |
| 5 | **Messages → Fatou** | Fil vide → choix obligatoire parmi 3 questions |
| 6 | Onglet **Coaching** | Page coaching accessible depuis le dock |

---

## 12. Points restants et risques

### À faire avant resoumission

| Item | Priorité |
|------|----------|
| Commit + push + `deploy.sh` complet sur VPS | 🔴 Haute |
| Rebuild iOS avec onboarding natif + build number 5+ | 🔴 Haute |
| Nouvelles captures App Store | 🔴 Haute |
| Nettoyer termes « Match » / « Explorer » restants | 🟡 Moyenne |
| `pubspec.yaml` description encore « Rencontres sérieuses » | 🟡 Moyenne |
| `test/widget_test.dart` références Sugar Paper legacy | 🟡 Moyenne |
| Vérifier absence Sugar Paper / GPS livreur dans le build review | 🔴 Haute |

### Plan B si second refus 4.3

Voir **`APP_STORE_GUIDELINE_4_3.md` §5** :

- PWA matrimoniale en parallèle.
- Demande de rendez-vous téléphonique App Review Resolution Center.

### Risque prod actuel

La migration `0021` est appliquée en prod : **nouvelles inscriptions passent en `pending`**, mais l’UI Lot B complète (écran validation, curated, dock coaching) n’est pas encore déployée via git. **Deploy complet urgent** avant ouverture aux nouveaux inscrits.

---

## 13. Documents connexes

| Document | Contenu |
|----------|---------|
| **`APP_STORE_RESUBMISSION.md`** | Textes finaux App Store Connect (Notes, Resolution Center, fiche FR) |
| **`APP_STORE_GUIDELINE_4_3.md`** | Analyse refus 4.3, réponse EN initiale, checklists, plan B |
| **`JUSTIFICATIONS_PERMISSIONS.md`** | Matrice permissions iOS / Android / App Privacy |
| **`AUTHENTIFICATION_SOCIALE.md`** | Sign in with Apple / Google |
| **`CONFIGURATION_FCM_FINALE.md`** | Push notifications |
| **`GESTION_VERSIONS_APK.md`** | Versions Android / force update |

---

*Document généré le 20 septembre 2026 — submission ID initial Apple : `c4213e77-8bb7-4cee-b885-57ddd9f3f88f`*
