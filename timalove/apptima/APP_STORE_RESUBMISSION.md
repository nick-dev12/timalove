# Soumission App Store — textes finaux (Lots A + B)

> **Document maître (toutes les modifications) :** [`ACCEPTATION_STORES_MODIFICATIONS.md`](ACCEPTATION_STORES_MODIFICATIONS.md)

Copier-coller dans **App Store Connect** avant resoumission.  
Compte démo créé via :

```bash
cd timalove
python manage.py create_apple_review_account --reset-partners
```

Sur le VPS :

```bash
python scripts/_vps_create_apple_review.py
```

Puis ajouter dans `.env` production :

```
QUOTA_EXEMPT_EMAILS=apple.review@timalove.local,gooteste@gmail.com
```

---

## 1. App Review Information (identifiants démo)

| Champ | Valeur |
|-------|--------|
| **Username** | `apple.review@timalove.local` |
| **Password** | `AppleReview2026!` |

**Notes for Review** (coller dans le champ Notes) :

```
Demo account (pre-approved — not subject to pending validation):
Email: apple.review@timalove.local
Password: AppleReview2026!

Recommended 3-minute review path:
1. Fresh install → native onboarding (marriage mission + mandatory charter).
2. Sign in → Parcours tab: curated daily list (8 profiles), not infinite swipe.
3. Messages → Awa: active thread with guided intro already sent.
4. Messages → Fatou: empty thread — must pick one of 3 guided questions before free text.
5. Coaching tab in bottom navigation.

This is a marriage-oriented community app (human validation, compatibility scores, coaching), not a casual dating clone. iPhone-only build.
```

---

## 2. Réponse à l'équipe de review (Resolution Center — anglais)

Coller dans **Répondre à l'équipe de vérification des apps** :

```
Hello App Review Team,

Thank you for your feedback on Guideline 4.3(b). We have substantially revised TimaLove to clarify that it is a marriage-oriented guided community — not a generic casual dating app.

WHAT CHANGED SINCE THE PREVIOUS SUBMISSION

1. Native first-launch onboarding (mission + matrimonial charter acceptance) before any web content.
2. Human registration validation — new members are pending until our team approves their dossier (demo account is pre-approved for your review).
3. Parcours (Discovery) is now a curated daily list of compatible profiles (8/day), not an infinite swipe deck.
4. Guided conversations — the first message in a new thread must use one of our suggested respectful marriage-oriented prompts.
5. Coaching is a primary tab in bottom navigation (individual relationship coaching).
6. UI vocabulary changed throughout: Parcours, Intérêts, Mise en relation, Priorité, % Compatible (no “dating/swipe/match” framing).
7. iPhone-only build for a focused matrimonial experience.

WHAT TIMA LOVE IS

TimaLove is a French-language matrimonial guidance platform for adults seeking serious union toward marriage. It serves a Francophone community (including West Africa and diaspora) with explicit relationship intent, life values, religion, life project fields, human moderation, and optional coaching.

NATIVE iOS VALUE

• Native onboarding + charter
• Push notifications (APNs)
• Sign in with Apple / Google (native bridges)
• Camera / mic / location with in-app explanation dialogs
• Universal Links to mytimalove.com
• App version gate

DEMO ACCOUNT

Email: apple.review@timalove.local
Password: AppleReview2026!

Steps:
1. Complete native onboarding + charter.
2. Sign in → Parcours: curated list with compatibility scores and “Mariage” intent labels.
3. Messages → Awa (active conversation).
4. Messages → Fatou (guided question picker before first message).
5. Coaching tab.

We respectfully ask you to re-evaluate under 4.3 as a niche matrimonial community product.

Thank you,
[Your name]
[Company name]
[Phone]
```

---

## 3. Fiche App Store (métadonnées)

### Nom affiché
`TimaLove`

### Sous-titre (30 car. max)
```
Parcours vers le mariage
```

### Texte promotionnel (optionnel)
```
Parcours matrimonial guidé : validation humaine, compatibilité, coaching et échanges respectueux — pas une app de rencontre casual.
```

### Description (début — FR)

```
TimaLove accompagne les adultes sincères vers une union stable et le mariage — pas le dating casual.

• Validation humaine de chaque inscription
• Parcours avec sélection compatible du jour (liste curated)
• Score de compatibilité basé sur valeurs, projet de vie et intention mariage
• Premier message guidé par des questions respectueuses
• Coaching individuel pour préparer l’union
• Charte matrimoniale et modération active
• Connexion sécurisée (Sign in with Apple)

Communauté francophone orientée famille et long terme.
```

### Mots-clés (éviter : dating, tinder, hookup)
```
matrimonial,mariage,relation sérieuse,union,famille,coaching,compatibilité
```

### Catégorie suggérée
**Style de vie** ou **Réseaux sociaux**

### Captures (ordre recommandé)
1. Onboarding natif « Parcours vers le mariage »
2. Charte matrimoniale (case cochée)
3. Parcours — liste « Sélection du jour » + % Compatible
4. Messages — questions guidées
5. Coaching (onglet + page)
6. Profil avec intention **Mariage**

---

## 4. Checklist avant « Soumettre à nouveau »

- [ ] `python manage.py create_apple_review_account --reset-partners` sur **production**
- [ ] `QUOTA_EXEMPT_EMAILS` inclut `apple.review@timalove.local` en prod
- [ ] Build iOS **5+** (iPhone only) uploadé
- [ ] Notes for Review + identifiants remplis
- [ ] Réponse Resolution Center collée
- [ ] Sous-titre + description + captures mises à jour
- [ ] Test manuel : connexion démo → Parcours → Messages (Awa + Fatou) → Coaching

---

*Généré le 20 sept. 2026 — submission ID initial : c4213e77-8bb7-4cee-b885-57ddd9f3f88f*
