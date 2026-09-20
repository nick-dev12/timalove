# Refus Apple — Guideline 4.3(b) (Design: Spam)

> **Document maître (toutes les modifications) :** [`ACCEPTATION_STORES_MODIFICATIONS.md`](ACCEPTATION_STORES_MODIFICATIONS.md)

Document de travail pour **Mytimalove / TimaLove** (`com.mytimalove.app`).  
À utiliser dans App Store Connect → **Répondre à l’équipe de vérification** + champs **Notes for Review** et **App Review Information**.

---

## 1. Texte de réponse (copier-coller en anglais)

> Apple préfère l’anglais pour la review. Adaptez les noms d’écrans si votre UI est 100 % en français.

```
Hello App Review Team,

Thank you for your message regarding Guideline 4.3(b). We understand that the App Store has many dating apps, and we would like to clarify how TimaLove (Mytimalove) is designed as a distinct, marriage-oriented community product—not a generic swipe/hookup experience.

WHAT TIMA LOVE IS
TimaLove is a French-language service for adults seeking serious relationships with marriage as the stated goal (“mise en relation sérieuse vers le mariage”). It serves a specific community (including Francophone West Africa and diaspora) with profile fields and flows that reflect cultural and family-oriented criteria (e.g. relationship intent: marriage vs. serious relationship, religion, life project, residence country/city).

HOW WE DIFFER FROM GENERIC DATING APPS
1. Intent-first onboarding: members declare relationship intent (marriage / serious relationship) during signup; profiles and discovery emphasize long-term compatibility, not casual browsing.
2. Human moderation & safety: in-app reporting, moderator workflows, automatic actions after repeated reports, photo blacklist, block between users, and staff roles (moderator/admin). Legal pages include child safety and account deletion (https://mytimalove.com/securite-des-enfants/, https://mytimalove.com/suppression-de-compte/).
3. Conversation controls for member safety: VIP recipients can require explicit acceptance before a conversation proceeds (reduces unsolicited messaging).
4. Coaching & guidance: optional paid coaching requests (relationship preparation), exposed in the product—not only matching/chat.
5. Strict discovery rules: only approved registrations appear in Explorer; matching excludes non-approved profiles; opposite-gender discovery rules apply consistently.
6. Premium tiers tied to serious use (media in chat for premium, VIP acceptance flows)—not unlimited anonymous swiping.

NATIVE iOS VALUE (NOT A SIMPLE WEBSITE WRAPPER)
The iOS app (Flutter) loads our web experience but adds native integrations required for a trustworthy matrimonial service:
• Native first-launch onboarding: marriage mission + how the guided path works + mandatory matrimonial charter acceptance
• Push notifications (APNs/FCM) for interests, mutual connections, and messages
• Sign in with Apple and Google via native SDK bridges (avoiding broken OAuth inside WebView)
• Camera / photo library / microphone with in-app explanation dialogs before system prompts (profile photos, verification selfie, voice messages in chat)
• Location when-in-use only (nearby profiles and city on profile—no background tracking)
• Universal Links / deep links to mytimalove.com
• App version gate via /api/app-config/
• iPhone-optimized build (iPhone only target)

REVIEW ACCESS
We prepared a dedicated sandbox account with a complete approved profile and sample matches/conversations:

  Email: apple.review@timalove.local
  Password: AppleReview2026!

Steps to see differentiation in under 3 minutes:
1. Fresh install → complete native onboarding (mission + charter checkbox) before the main experience.
2. Sign in → open Parcours (/explorer/) — note compatibility labels and detailed profiles (not anonymous cards only).
3. Open Messages — show mutual connection / conversation flow (and VIP acceptance if applicable on demo account).
4. Profile → relationship intent “Mariage” and completed life project fields.
5. Optional: tap Coaching from Parcours atmosphere / coaching page.
6. Settings / legal: privacy policy, account deletion, child safety URLs load from mytimalove.com.

We respectfully ask you to re-evaluate TimaLove under 4.3 as a niche matrimonial community app with moderation, intent-based profiles, and native iOS integrations—not as a duplicate of casual dating templates.

Thank you for your time,
[Your name]
[Company / Goo-Bridge or legal entity name]
[Phone number]
```

---

## 2. Notes for Review (version courte, ≤ ~500 mots)

Champ **App Review Information → Notes** (complète le compte démo) :

```
TimaLove = marriage-oriented French community (not casual dating).

Demo: apple.review@timalove.local / AppleReview2026!

After login: Explorer shows intent-based profiles (Mariage). Messages = match chat. Reporting available on profiles. No background location.

Native: push, Sign in with Apple, camera/mic for profile & voice messages, permission dialogs before iOS prompts.

Legal: https://mytimalove.com/politique-de-confidentialite/ | deletion: https://mytimalove.com/suppression-de-compte/ | child safety: https://mytimalove.com/securite-des-enfants/
```

---

## 3. Compte démo Apple

Commande Django (local ou prod) :

```bash
cd timalove
python manage.py create_apple_review_account --reset-partners
```

Sur le VPS : `python scripts/_vps_create_apple_review.py`

| Champ | Valeur |
|-------|--------|
| Email | `apple.review@timalove.local` |
| Mot de passe | `AppleReview2026!` |
| Statut | `approved` (pre-approuve pour la review) |
| Partenaires | Awa (conversation active) + Fatou (questions guidees) |

Production : ajouter dans `.env` :

```
QUOTA_EXEMPT_EMAILS=apple.review@timalove.local,gooteste@gmail.com
```

Textes copy-paste App Store Connect : voir **`APP_STORE_RESUBMISSION.md`**.

Comptes dev existants (local uniquement) :

- `teste1@gmail.com` / `teste2@gmail.com` — réservés dev local `127.0.0.1`.

---

## 4. Checklist App Store Connect (avant resoumission)

### Fiche produit

- [ ] **Nom affiché** : TimaLove (cohérent avec `CFBundleDisplayName`)
- [ ] **Sous-titre** : « Parcours matrimonial vers le mariage » (éviter Dating / Rencontres hot)
- [ ] **Description** : 1er paragraphe = niche + modération + intention mariage + charte ; mentionner coaching
- [ ] **Mots-clés** : matrimonial, mariage, relation sérieuse, communauté — éviter `dating`, `hookup`, `tinder`
- [ ] **Catégorie** : Style de vie ou Réseaux sociaux (pas « dating game »)
- [ ] **Captures** : onboarding natif (mission + charte), intention Mariage, dossier / % Compatible, coaching, messages — **pas** une carte swipe plein écran en 1re image
- [ ] **URL support** + **politique de confidentialité** : liens `mytimalove.com` qui répondent en 200

### Review

- [ ] Compte démo prod créé et testé sur **iPhone** (cible iPhone only)
- [ ] **Notes for Review** + réponse 4.3 collées
- [ ] **Sign in with Apple** fonctionnel dans le build soumis
- [ ] Aucune mention « Sugar Paper » / livreur / GPS arrière-plan
- [ ] `JUSTIFICATIONS_PERMISSIONS.md` : App Privacy = pas de localisation arrière-plan

### Binaire / Xcode

- [x] `TARGETED_DEVICE_FAMILY = 1` (iPhone only) — Lot A
- [ ] Build number incrémenté (ex. 5)
- [ ] Vérifier onboarding natif au 1er lancement (charte obligatoire)

### Risque compte (Extended Review)

- [ ] **Ne pas** resoumettre le même binaire sans texte + compte démo + ajustements fiche
- [ ] Vérifier pages **sécurité des enfants**, **suppression de compte**, modération active
- [ ] Pas de contenu placeholder / profils vides / pages « coming soon » visibles après login

---

## 5. Plan B si second refus 4.3

1. **PWA** : guider les utilisateurs iOS vers Safari → « Sur l’écran d’accueil » (Apple le suggère explicitement).
2. **Lot B** : liste curated, validation pending, coaching onglet principal, messages guidés.
3. **Appel Resolution Center** : demander un **app review appointment** (téléphone) avec démo live.
4. **Conseil juridique / ASO** : parfois utile après 2× 4.3 sur le même compte développeur.

---

## 6. Où cliquer dans App Store Connect

1. **My Apps** → **Mytimalove** → **Distribution** → message du refus  
2. **Répondre à l’équipe de vérification des apps** → coller la section 1  
3. **App Information** / version **1.x** → **App Review Information** → notes section 2 + identifiants démo  
4. Corriger métadonnées + nouveau build → **Soumettre à nouveau**

---

## 7. Lot A — livré (code)

Implémenté dans le dépôt (avant Lot B) :

| Élément | Statut |
|--------|--------|
| Onboarding natif Flutter (mission + parcours + **charte**) | ✅ `lib/widgets/matrimonial_onboarding.dart` |
| Splash sans double cœur dating | ✅ `timalove_launch_loader.dart` |
| iPhone only (`TARGETED_DEVICE_FAMILY = 1`) | ✅ |
| Vocabulaire UI : Explorer→Parcours, Likes→Intérêts, Match→Mise en relation, Super like→Priorité, % Match→% Compatible | ✅ templates + JS |
| Fiche store à remplir manuellement | ⬜ checklist §4 |

### Texte fiche — suggestions (copier dans App Store Connect)

**Sous-titre (30 car. max) :**
```
Parcours vers le mariage
```

**Promotional text (optionnel) :**
```
TimaLove accompagne les adultes sincères vers une union sérieuse — intention claire, compatibilité et coaching humain.
```

**Description (début) :**
```
TimaLove est un parcours matrimonial pour adultes qui cherchent le mariage — pas une app de rencontre casual.

• Intention déclarée (mariage / relation sérieuse)
• Charte de respect et modération active
• Compatibilité basée sur valeurs, projet de vie et critères culturels
• Coaching individuel pour préparer l’union
• Notifications et connexion sécurisée (Sign in with Apple)

Rejoignez une communauté francophone orientée famille et long terme.
```

**Captures à préparer (ordre) :**
1. Onboarding natif « Parcours vers le mariage »
2. Charte matrimoniale (case à cocher)
3. Parcours / profil avec % Compatible + intention Mariage
4. Coaching
5. Messages guidés + mise en relation

## 8. Lot B — livré (code)

| Élément | Statut |
|--------|--------|
| Inscriptions `pending` par défaut | ✅ signup / onboarding / auth |
| Écran `/validation-en-attente/` + garde middleware | ✅ |
| Parcours **liste curated** (8 profils/jour, pas swipe infini) | ✅ |
| **Coaching** en onglet principal (dock) | ✅ |
| **Messages guidés** avant 1er message | ✅ |

Flags `app_config` : `explorer_curated_mode`, `curated_daily_limit` (8), `guided_messages_enabled`.

*Dernière mise à jour : Lots A + B livrés — 20 sept. 2026.*
