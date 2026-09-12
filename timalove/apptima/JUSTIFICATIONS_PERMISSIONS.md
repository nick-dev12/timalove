# Justifications des permissions — TimaLove

Application de mise en relation sérieuse vers le mariage (WebView + pont natif).

- Android : `com.timalove.app`
- iOS : `com.mytimalove.app`
- Site : https://mytimalove.com/

Pages légales :
- Politique de confidentialité : https://mytimalove.com/politique-de-confidentialite/
- Suppression de compte : https://mytimalove.com/suppression-de-compte/
- Mentions légales : https://mytimalove.com/mentions-legales/
- Sécurité des enfants : https://mytimalove.com/securite-des-enfants/
- CGV : https://mytimalove.com/cgv/

Les notifications push (FCM / APNs) sont configurées (projet Firebase `timalove-ddaa5`). Les textes ci-dessous restent la source pour la review.

---

## Apple App Store — `Info.plist` (Guideline 5.1.1)

Chaque clé décrit **comment**, **pourquoi** et un **exemple concret**.

| Clé | Finalité |
|-----|----------|
| `NSCameraUsageDescription` | Photo de profil, selfie de vérification, image envoyée dans une discussion |
| `NSMicrophoneUsageDescription` | Message vocal dans une conversation uniquement |
| `NSPhotoLibraryUsageDescription` | Import galerie si l’utilisateur choisit une photo existante |
| `NSPhotoLibraryAddUsageDescription` | Enregistrement d’une image uniquement sur action explicite |
| `NSLocationWhenInUseUsageDescription` | Profils près de vous + ville du profil — jamais en arrière-plan |

**Non utilisé** : contacts, localisation « toujours », GPS arrière-plan.

**Dialogue in-app** (avant la boîte système) : `NativePermissionService`.

### App Store Connect — App Privacy

- **Localisation précise** : Oui — uniquement pendant l’utilisation, pour l’explorer et la ville
- **Photos** : Oui — contenu fourni par l’utilisateur
- **Microphone** : Oui — messages vocaux, action utilisateur
- **Caméra** : Oui — photos de profil / discussion
- **Identifiants** : jeton push (quand FCM sera activé)

---

## Google Play Console

**CAMERA**
```
TimaLove utilise l’appareil photo lorsque l’utilisateur prend une photo de profil, un selfie de vérification ou une image à envoyer dans une discussion. Exemple : photographier son portrait pour sa fiche membre.
```

**RECORD_AUDIO**
```
TimaLove utilise le microphone uniquement lorsque l’utilisateur enregistre un message vocal dans une conversation. L’écoute n’est jamais activée en arrière-plan.
```

**ACCESS_FINE_LOCATION / ACCESS_COARSE_LOCATION**
```
TimaLove utilise la position uniquement lorsque l’utilisateur l’autorise, pour afficher des profils près de lui et renseigner sa ville. La position n’est pas suivie en continu ni en arrière-plan. Il peut indiquer sa ville manuellement.
```

**READ_MEDIA_IMAGES / stockage (Android ≤ 12)**
```
TimaLove accède aux images uniquement lorsque l’utilisateur importe une photo depuis la galerie pour son profil ou une conversation.
```

**POST_NOTIFICATIONS (Android 13+)**
```
Alertes de like, de match et de nouveau message. Refusable dans les paramètres système. (Activation FCM prévue ultérieurement.)
```

Chaînes Android : `android/app/src/main/res/values/strings.xml`  
Dialogues in-app : `lib/services/native_permission_service.dart`

---

## Matrice technique

| Permission | Android | iOS | Dialogue in-app | Contexte |
|------------|---------|-----|-----------------|----------|
| Caméra | ✅ | ✅ | ✅ | Profil, selfie, discussion |
| Micro | ✅ | ✅ | ✅ | Message vocal |
| Galerie | ✅ | ✅ | ✅ | Import utilisateur |
| Localisation (usage) | ✅ | ✅ | ✅ | Explorer, ville |
| Localisation arrière-plan | ❌ | ❌ | — | Non utilisé |
| Contacts | ❌ | ❌ | — | Non utilisé |
| Notifications | ✅ | UIBackgroundModes | prêts | Like, match, message |

---

## Checklist avant soumission

- [ ] Politique, suppression de compte et mentions à jour sur mytimalove.com
- [ ] App Store Connect : pas de localisation arrière-plan
- [ ] Play Console : pas de background location
- [x] FCM / APNs : app configurée — uploader la clé APNs (.p8) dans Firebase + compte de service Django
- [ ] Universal Links / App Links : host `mytimalove.com`
