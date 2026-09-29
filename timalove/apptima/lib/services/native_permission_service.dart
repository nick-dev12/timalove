import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';
import '../theme/app_colors.dart';

/// Textes alignés sur Info.plist / Play Console — TimaLove.
class NativePermissionCopy {
  static const locationTitle = 'Autoriser la localisation';
  static const locationBody =
      'TimaLove utilise votre position uniquement lorsque vous l’autorisez, pour :\n\n'
      '• proposer des profils près de vous dans l’explorer ;\n'
      '• renseigner ou confirmer votre ville sur votre profil.\n\n'
      'La position n’est jamais suivie en continu ni en arrière-plan. '
      'Vous pouvez refuser et indiquer votre ville manuellement.';

  static const locationDeniedForeverTitle = 'Localisation désactivée';
  static const locationDeniedForeverBody =
      'L’accès à la localisation est refusé pour TimaLove. '
      'Pour afficher les profils près de vous, activez-la dans les paramètres '
      '(Paramètres > TimaLove > Localisation).';

  static const cameraTitle = 'Autoriser l’appareil photo';
  static const cameraBody =
      'TimaLove utilise l’appareil photo lorsque vous prenez une photo de profil, '
      'un selfie de vérification, ou une image à envoyer dans une discussion.\n\n'
      'Exemple : photographier votre portrait pour votre fiche membre.';

  static const cameraDeniedForeverTitle = 'Caméra désactivée';
  static const cameraDeniedForeverBody =
      'L’accès à la caméra est refusé pour TimaLove. '
      'Activez-la dans les paramètres de l’appareil si vous souhaitez prendre une photo.';

  static const microphoneTitle = 'Autoriser le microphone';
  static const microphoneBody =
      'TimaLove utilise le microphone uniquement lorsque vous enregistrez '
      'un message vocal dans une conversation.\n\n'
      'L’écoute n’est jamais activée en arrière-plan. Vous pouvez refuser '
      'et continuer à écrire des messages texte.';

  static const microphoneDeniedForeverTitle = 'Microphone désactivé';
  static const microphoneDeniedForeverBody =
      'L’accès au microphone est refusé pour TimaLove. '
      'Activez-le dans les paramètres (TimaLove > Microphone) pour envoyer un vocal.';

  static const photosTitle = 'Autoriser l’accès aux photos';
  static const photosBody =
      'TimaLove accède à vos photos uniquement si vous choisissez d’importer '
      'une image depuis la galerie pour votre profil ou une discussion.\n\n'
      'Aucune photo n’est lue automatiquement.';

  static const photosDeniedForeverTitle = 'Photos désactivées';
  static const photosDeniedForeverBody =
      'L’accès à la galerie est refusé pour TimaLove. '
      'Activez-le dans les paramètres si vous souhaitez importer une photo.';

  static const notificationsTitle = 'Autoriser les notifications';
  static const notificationsBody =
      'TimaLove peut vous prévenir d’une nouvelle connexion, d’une demande reçue ou d’un message. '
      'Vous pourrez désactiver les alertes à tout moment dans les réglages.';

  static const notificationsDeniedForeverTitle = 'Notifications désactivées';
  static const notificationsDeniedForeverBody =
      'Les notifications sont refusées pour TimaLove. '
      'Activez-les dans les paramètres de l’appareil (TimaLove > Notifications) '
      'pour être prévenu d’une connexion ou d’un message.';
}

/// Boîtes de dialogue explicatives avant les autorisations système (Apple 5.1.1 / Google Play).
class NativePermissionService {
  static Future<bool> _showRationaleDialog(
    BuildContext context, {
    required String title,
    required String body,
    required IconData icon,
  }) async {
    final result = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        backgroundColor: kCream,
        icon: Icon(icon, color: kRosePrincipal, size: 32),
        title: Text(title, style: const TextStyle(color: kBordeauxDark)),
        content: SingleChildScrollView(
          child: Text(body, style: const TextStyle(color: kTexteSecondaire)),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Plus tard', style: TextStyle(color: kTexteSecondaire)),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: FilledButton.styleFrom(backgroundColor: kRosePrincipal),
            child: const Text('Continuer'),
          ),
        ],
      ),
    );
    return result == true;
  }

  static Future<void> _showOpenSettingsDialog(
    BuildContext context, {
    required String title,
    required String body,
  }) async {
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: kCream,
        title: Text(title, style: const TextStyle(color: kBordeauxDark)),
        content: Text(body, style: const TextStyle(color: kTexteSecondaire)),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Fermer'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              openAppSettings();
            },
            style: FilledButton.styleFrom(backgroundColor: kRosePrincipal),
            child: const Text('Ouvrir les paramètres'),
          ),
        ],
      ),
    );
  }

  static Future<LocationPermission> requestLocationWithRationale(
    BuildContext context,
  ) async {
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.always ||
        permission == LocationPermission.whileInUse) {
      return permission;
    }

    if (permission == LocationPermission.deniedForever) {
      if (context.mounted) {
        await _showOpenSettingsDialog(
          context,
          title: NativePermissionCopy.locationDeniedForeverTitle,
          body: NativePermissionCopy.locationDeniedForeverBody,
        );
      }
      return permission;
    }

    if (!context.mounted) return permission;
    final accepted = await _showRationaleDialog(
      context,
      title: NativePermissionCopy.locationTitle,
      body: NativePermissionCopy.locationBody,
      icon: Icons.location_on_outlined,
    );
    if (!accepted) return LocationPermission.denied;

    permission = await Geolocator.requestPermission();
    if (permission == LocationPermission.deniedForever && context.mounted) {
      await _showOpenSettingsDialog(
        context,
        title: NativePermissionCopy.locationDeniedForeverTitle,
        body: NativePermissionCopy.locationDeniedForeverBody,
      );
    }
    return permission;
  }

  static Future<bool> requestCameraWithRationale(BuildContext context) async {
    return _requestPermissionWithRationale(
      context,
      permission: Permission.camera,
      title: NativePermissionCopy.cameraTitle,
      body: NativePermissionCopy.cameraBody,
      deniedTitle: NativePermissionCopy.cameraDeniedForeverTitle,
      deniedBody: NativePermissionCopy.cameraDeniedForeverBody,
      icon: Icons.photo_camera_outlined,
    );
  }

  static Future<bool> requestMicrophoneWithRationale(BuildContext context) async {
    return _requestPermissionWithRationale(
      context,
      permission: Permission.microphone,
      title: NativePermissionCopy.microphoneTitle,
      body: NativePermissionCopy.microphoneBody,
      deniedTitle: NativePermissionCopy.microphoneDeniedForeverTitle,
      deniedBody: NativePermissionCopy.microphoneDeniedForeverBody,
      icon: Icons.mic_none_outlined,
    );
  }

  static Future<bool> requestPhotosWithRationale(BuildContext context) async {
    final permission = Platform.isIOS ? Permission.photos : Permission.photos;
    return _requestPermissionWithRationale(
      context,
      permission: permission,
      title: NativePermissionCopy.photosTitle,
      body: NativePermissionCopy.photosBody,
      deniedTitle: NativePermissionCopy.photosDeniedForeverTitle,
      deniedBody: NativePermissionCopy.photosDeniedForeverBody,
      icon: Icons.photo_library_outlined,
    );
  }

  static Future<bool> requestNotificationsWithRationale(BuildContext context) async {
    return _requestPermissionWithRationale(
      context,
      permission: Permission.notification,
      title: NativePermissionCopy.notificationsTitle,
      body: NativePermissionCopy.notificationsBody,
      deniedTitle: NativePermissionCopy.notificationsDeniedForeverTitle,
      deniedBody: NativePermissionCopy.notificationsDeniedForeverBody,
      icon: Icons.notifications_none_outlined,
    );
  }

  static Future<bool> _requestPermissionWithRationale(
    BuildContext context, {
    required Permission permission,
    required String title,
    required String body,
    required String deniedTitle,
    required String deniedBody,
    required IconData icon,
  }) async {
    var status = await permission.status;
    if (status.isGranted || status.isLimited) return true;

    if (status.isPermanentlyDenied) {
      if (context.mounted) {
        await _showOpenSettingsDialog(
          context,
          title: deniedTitle,
          body: deniedBody,
        );
      }
      return false;
    }

    if (!context.mounted) return false;
    final accepted = await _showRationaleDialog(
      context,
      title: title,
      body: body,
      icon: icon,
    );
    if (!accepted) return false;

    status = await permission.request();
    if (status.isPermanentlyDenied && context.mounted) {
      await _showOpenSettingsDialog(
        context,
        title: deniedTitle,
        body: deniedBody,
      );
      return false;
    }
    return status.isGranted || status.isLimited;
  }

  /// Conservé pour compatibilité du pont JS (non utilisé par TimaLove).
  static Future<bool> requestDeliveryTrackingPermissions(BuildContext context) async {
    final permission = await requestLocationWithRationale(context);
    return permission == LocationPermission.always ||
        permission == LocationPermission.whileInUse;
  }

  /// Conservé pour compatibilité du pont JS (non utilisé par TimaLove).
  static Future<bool> requestContactsWithRationale(BuildContext context) async {
    return false;
  }
}
