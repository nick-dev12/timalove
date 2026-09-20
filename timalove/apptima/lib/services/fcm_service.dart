import 'dart:io';

import 'dart:convert';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/webview_site_config.dart';
import '../firebase_options.dart';

/// Canal Android haute priorité — bannière heads-up (popup native).
/// Nouvel ID obligatoire : Android ne met pas à jour l'importance d'un canal existant.
const String kTimaLoveNotifyChannelId = 'timalove_alerts';
const String kTimaLoveNotifyChannelName = 'Alertes TimaLove';
const String kTimaLoveNotifyChannelDesc =
    'Likes, matchs et nouveaux messages TimaLove';

/// Service pour gérer Firebase Cloud Messaging
class FCMService {
  static final FirebaseMessaging _messaging = FirebaseMessaging.instance;
  static final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();
  static String? _fcmToken;
  static String? _serverUrl;
  static Function(String)? _onNotificationTap;
  static Function(String)? _onTokenReady;
  static bool _handlersReady = false;

  /// Extrait l'URL de navigation depuis le payload FCM (web: link, legacy: redirect_url/url)
  static String? notificationUrlFromData(Map<String, dynamic> data) {
    for (final key in ['redirect_url', 'url', 'link']) {
      final value = data[key];
      if (value is String && value.trim().isNotEmpty) {
        return value.trim();
      }
    }
    return null;
  }

  /// Titre / corps depuis notification FCM ou data payload
  static ({String title, String body}) _messageText(RemoteMessage message) {
    final title = message.notification?.title?.trim().isNotEmpty == true
        ? message.notification!.title!.trim()
        : (message.data['title']?.toString().trim().isNotEmpty == true
            ? message.data['title'].toString().trim()
            : 'TimaLove');
    final body = message.notification?.body?.trim().isNotEmpty == true
        ? message.notification!.body!.trim()
        : (message.data['body']?.toString().trim().isNotEmpty == true
            ? message.data['body'].toString().trim()
            : (message.data['message']?.toString().trim() ?? ''));
    return (title: title, body: body);
  }

  static AndroidNotificationDetails _androidHeadsUpDetails() {
    return const AndroidNotificationDetails(
      kTimaLoveNotifyChannelId,
      kTimaLoveNotifyChannelName,
      channelDescription: kTimaLoveNotifyChannelDesc,
      importance: Importance.max,
      priority: Priority.max,
      playSound: true,
      enableVibration: true,
      enableLights: true,
      visibility: NotificationVisibility.public,
      category: AndroidNotificationCategory.message,
      icon: '@mipmap/ic_launcher',
      ticker: 'Nouvelle alerte TimaLove',
      channelShowBadge: true,
      autoCancel: true,
      // Favorise la bannière heads-up au-dessus des autres apps
      fullScreenIntent: false,
      styleInformation: BigTextStyleInformation(''),
    );
  }

  static DarwinNotificationDetails _iosHeadsUpDetails() {
    return const DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
      presentBanner: true,
      presentList: true,
      interruptionLevel: InterruptionLevel.timeSensitive,
      sound: 'default',
    );
  }

  /// Initialiser les notifications locales (Android + iOS)
  static Future<void> initializeLocalNotifications() async {
    const androidSettings = AndroidInitializationSettings(
      '@mipmap/ic_launcher',
    );
    const darwinSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
      defaultPresentAlert: true,
      defaultPresentBadge: true,
      defaultPresentSound: true,
      defaultPresentBanner: true,
      defaultPresentList: true,
    );
    const initializationSettings = InitializationSettings(
      android: androidSettings,
      iOS: darwinSettings,
      macOS: darwinSettings,
    );

    await _localNotifications.initialize(
      initializationSettings,
      onDidReceiveNotificationResponse: (NotificationResponse response) {
        final url = response.payload;
        if (url != null && url.isNotEmpty && _onNotificationTap != null) {
          _onNotificationTap!(url);
        }
      },
    );

    if (!kIsWeb && Platform.isAndroid) {
      const androidChannel = AndroidNotificationChannel(
        kTimaLoveNotifyChannelId,
        kTimaLoveNotifyChannelName,
        description: kTimaLoveNotifyChannelDesc,
        importance: Importance.max,
        playSound: true,
        enableVibration: true,
        showBadge: true,
      );

      await _localNotifications
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.createNotificationChannel(androidChannel);

      // Ancien canal (au cas où un appareil l’aurait déjà créé)
      const legacyChannel = AndroidNotificationChannel(
        'timalove_alerts',
        'Alertes TimaLove (ancien)',
        description: 'Canal historique — préférer timalove_alerts',
        importance: Importance.max,
        playSound: true,
        enableVibration: true,
        showBadge: true,
      );
      await _localNotifications
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.createNotificationChannel(legacyChannel);
    }
  }

  /// Demande l'autorisation d'afficher des notifications (iOS + Android 13+)
  static Future<bool> requestNotificationPermission() async {
    if (!kIsWeb && Platform.isAndroid) {
      final status = await Permission.notification.request();
      if (!status.isGranted) {
        print('❌ Permission de notification Android refusée');
        return false;
      }
    }

    final settings = await _messaging.requestPermission(
      alert: true,
      announcement: false,
      badge: true,
      carPlay: false,
      criticalAlert: false,
      provisional: false,
      sound: true,
    );

    final authorized =
        settings.authorizationStatus == AuthorizationStatus.authorized ||
            settings.authorizationStatus == AuthorizationStatus.provisional;

    if (authorized) {
      print('✅ Permission de notification accordée');
    } else {
      print('❌ Permission de notification refusée');
    }

    return authorized;
  }

  /// Définir le callback pour la navigation depuis une notification
  static void setNotificationTapCallback(Function(String url) callback) {
    _onNotificationTap = callback;
  }

  /// Appelé quand un token FCM est disponible (init ou refresh) — pour ré-injecter dans la WebView
  static void setTokenReadyCallback(Function(String token)? callback) {
    _onTokenReady = callback;
  }

  /// Initialiser FCM et obtenir le token
  static Future<String?> initialize(String serverUrl) async {
    print('🔥 FCMService.initialize() appelé avec URL: $serverUrl');
    _serverUrl = serverUrl;

    try {
      print('🔥 Initialisation des notifications locales...');
      await initializeLocalNotifications();
      print('✅ Notifications locales initialisées');

      final permissionGranted = await requestNotificationPermission();
      if (!permissionGranted) {
        return null;
      }

      // iOS + Android : toujours afficher bannière / son / badge même app au premier plan
      await _messaging.setForegroundNotificationPresentationOptions(
        alert: true,
        badge: true,
        sound: true,
      );

      if (!kIsWeb && Platform.isIOS) {
        final apnsOk = await _waitForApnsToken();
        if (!apnsOk) {
          print('⚠️ Token APNs indisponible — FCM iOS peut échouer');
          print('   Vérifier : Push Notifications dans Xcode + clé APNs (.p8) dans Firebase → Cloud Messaging');
        }
      }

      _fcmToken = await _messaging.getToken();

      // iOS : parfois le token FCM n’arrive qu’après APNs (retry court)
      if (_fcmToken == null && !kIsWeb && Platform.isIOS) {
        for (var i = 0; i < 6; i++) {
          await Future<void>.delayed(const Duration(milliseconds: 800));
          _fcmToken = await _messaging.getToken();
          if (_fcmToken != null) {
            break;
          }
        }
      }

      if (_fcmToken != null) {
        print('📱 Token FCM obtenu: ${_fcmToken!.substring(0, 20)}...');
        await _saveTokenLocally(_fcmToken!);
        await _sendTokenToServer(_fcmToken!);
        _setupMessageHandlers();
        _onTokenReady?.call(_fcmToken!);
        return _fcmToken;
      }

      print('❌ Impossible d\'obtenir le token FCM');
      return null;
    } catch (e) {
      print('❌ Erreur lors de l\'initialisation FCM: $e');
      return null;
    }
  }

  static Future<void> _saveTokenLocally(String token) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('fcm_token', token);
    } catch (e) {
      print('Erreur lors de la sauvegarde locale du token: $e');
    }
  }

  static Future<bool> _waitForApnsToken() async {
    if (kIsWeb || !Platform.isIOS) {
      return true;
    }
    for (var i = 0; i < 40; i++) {
      final apnsToken = await _messaging.getAPNSToken();
      if (apnsToken != null && apnsToken.isNotEmpty) {
        print('🍎 Token APNs obtenu (${apnsToken.length} car.)');
        return true;
      }
      await Future<void>.delayed(const Duration(milliseconds: 500));
    }
    return false;
  }

  /// Enregistre le token FCM sur l’API Django (session WebView).
  static Future<bool> registerTokenWithSession({
    required String cookieHeader,
    required String pageContext,
  }) async {
    final token = _fcmToken ?? await _messaging.getToken();
    if (token == null || token.isEmpty) {
      print('❌ registerTokenWithSession : pas de token FCM');
      return false;
    }
    _fcmToken = token;

    final serverUrl =
        (_serverUrl ?? kMarketplaceBaseUrl).replaceAll(RegExp(r'/+$'), '');
    final platform = (!kIsWeb && Platform.isIOS) ? 'ios' : 'android';
    final csrf = _csrfTokenFromCookieHeader(cookieHeader);

    try {
      final response = await http.post(
        Uri.parse('$serverUrl/api/push/register/'),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Origin': serverUrl,
          'Referer': '$serverUrl/',
          if (cookieHeader.isNotEmpty) 'Cookie': cookieHeader,
          if (csrf != null && csrf.isNotEmpty) 'X-CSRFToken': csrf,
        },
        body: jsonEncode({
          'token': token,
          'platform': platform,
        }),
      );
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final contentType = response.headers['content-type'] ?? '';
        if (!contentType.contains('json')) {
          print('⚠️ push/register : réponse non JSON (${response.statusCode})');
          return false;
        }
        final data = jsonDecode(response.body);
        if (data is Map && data['ok'] == true) {
          print('✅ Token FCM enregistré (natif, platform=$platform)');
          return true;
        }
        print('⚠️ push/register : ${data is Map ? data['message'] : response.body}');
      } else {
        print('⚠️ push/register HTTP ${response.statusCode}');
      }
    } catch (e) {
      print('❌ registerTokenWithSession : $e');
    }
    return false;
  }

  static String? _csrfTokenFromCookieHeader(String cookieHeader) {
    for (final part in cookieHeader.split(';')) {
      final kv = part.trim();
      if (kv.startsWith('csrftoken=')) {
        return Uri.decodeComponent(kv.substring('csrftoken='.length));
      }
    }
    return null;
  }

  static Future<bool> _sendTokenToServer(String token) async {
    if (_serverUrl == null) {
      print('❌ URL du serveur non configurée');
      return false;
    }
    print('📤 Token FCM prêt à être envoyé via WebView');
    return true;
  }

  /// Code JavaScript à injecter dans la WebView pour enregistrer le token
  static String getTokenRegistrationScript(String token) {
    final deviceType = (!kIsWeb && Platform.isIOS) ? 'ios' : 'android';
    return '''
      (function() {
        if (!window.__TIMALOVE_NATIVE_APP) return;
        const token = ${jsonEncode(token)};
        const platform = ${jsonEncode(deviceType)};
        function csrf() {
          var m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
          return m ? decodeURIComponent(m[1]) : '';
        }
        if (!csrf() || document.cookie.indexOf('sessionid=') === -1) return;
        fetch('/api/push/register/', {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-CSRFToken': csrf()
          },
          body: JSON.stringify({ token: token, platform: platform })
        })
        .then(function(r) {
          var ct = (r.headers.get('content-type') || '');
          if (!r.ok || ct.indexOf('json') === -1) {
            return null;
          }
          return r.json();
        })
        .then(function(data) {
          if (data && data.ok) console.log('✅ Token FCM enregistré', data);
        })
        .catch(function(err) { console.warn('Token FCM (js)', err); });
      })();
    ''';
  }

  /// Affiche toujours une bannière native (popup) — premier plan et secours arrière-plan
  static Future<void> showHeadsUpNotification(RemoteMessage message) async {
    final text = _messageText(message);
    final url = notificationUrlFromData(message.data) ?? _serverUrl ?? '';

    print('🔔 Bannière native: ${text.title} — ${text.body}');

    // BigText avec le vrai corps pour Android
    final androidDetails = AndroidNotificationDetails(
      kTimaLoveNotifyChannelId,
      kTimaLoveNotifyChannelName,
      channelDescription: kTimaLoveNotifyChannelDesc,
      importance: Importance.max,
      priority: Priority.max,
      playSound: true,
      enableVibration: true,
      enableLights: true,
      visibility: NotificationVisibility.public,
      category: AndroidNotificationCategory.message,
      icon: '@mipmap/ic_launcher',
      ticker: text.title,
      channelShowBadge: true,
      autoCancel: true,
      styleInformation: BigTextStyleInformation(
        text.body.isNotEmpty ? text.body : text.title,
        contentTitle: text.title,
        summaryText: 'TimaLove',
      ),
    );

    final notificationDetails = NotificationDetails(
      android: androidDetails,
      iOS: _iosHeadsUpDetails(),
    );

    await _localNotifications.show(
      DateTime.now().millisecondsSinceEpoch.remainder(100000),
      text.title,
      text.body,
      notificationDetails,
      payload: url,
    );
  }

  /// @deprecated utiliser [showHeadsUpNotification]
  static Future<void> _showLocalNotification(RemoteMessage message) =>
      showHeadsUpNotification(message);

  static void _setupMessageHandlers() {
    if (_handlersReady) {
      return;
    }
    _handlersReady = true;
    print('🔔 Configuration des handlers (bannière native toujours on)...');

    // App au premier plan
    FirebaseMessaging.onMessage.listen((RemoteMessage message) async {
      print('📬 Notification premier plan');
      print('   Titre: ${message.notification?.title}');
      print('   Corps: ${message.notification?.body}');
      // iOS : bannière système déjà via setForegroundNotificationPresentationOptions + AppDelegate
      if (!kIsWeb && Platform.isIOS && message.notification != null) {
        return;
      }
      try {
        await showHeadsUpNotification(message);
      } catch (e) {
        print('❌ Affichage bannière: $e');
      }
    });

    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      print('📬 Notification ouverte depuis l\'arrière-plan');
      _handleNotificationNavigation(message.data);
    });

    _checkInitialMessage();
  }

  static Future<void> _checkInitialMessage() async {
    final initialMessage = await _messaging.getInitialMessage();
    if (initialMessage != null) {
      _handleNotificationNavigation(initialMessage.data);
    }
  }

  static void _handleNotificationNavigation(Map<String, dynamic> data) {
    final url = notificationUrlFromData(data);
    if (url != null && url.isNotEmpty && _onNotificationTap != null) {
      _onNotificationTap!(url);
    }
  }

  static String? getToken() => _fcmToken;

  static void setupTokenRefresh() {
    _messaging.onTokenRefresh.listen((newToken) {
      print('🔄 Token FCM rafraîchi');
      _fcmToken = newToken;
      _saveTokenLocally(newToken);
      _sendTokenToServer(newToken);
      _onTokenReady?.call(newToken);
    });
  }
}

/// Handler arrière-plan / app tuée (fonction top-level obligatoire)
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
  } catch (_) {
    // Déjà initialisé dans ce isolate
  }

  print('📬 Notification arrière-plan / terminée');
  print('   Titre: ${message.notification?.title}');
  print('   Corps: ${message.notification?.body}');

  // Si FCM a déjà une "notification", le système affiche via le canal.
  // On crée quand même le canal MAX et, pour data-only, une locale heads-up.
  final localNotifications = FlutterLocalNotificationsPlugin();
  const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
  const darwinSettings = DarwinInitializationSettings();
  await localNotifications.initialize(
    const InitializationSettings(android: androidSettings, iOS: darwinSettings),
  );

  if (!kIsWeb && Platform.isAndroid) {
    const channel = AndroidNotificationChannel(
      kTimaLoveNotifyChannelId,
      kTimaLoveNotifyChannelName,
      description: kTimaLoveNotifyChannelDesc,
      importance: Importance.max,
      playSound: true,
      enableVibration: true,
      showBadge: true,
    );
    await localNotifications
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channel);
  }

  if (message.notification != null) {
    return;
  }

  final title = message.data['title']?.toString().trim().isNotEmpty == true
      ? message.data['title'].toString().trim()
      : 'TimaLove';
  final body = message.data['body']?.toString().trim().isNotEmpty == true
      ? message.data['body'].toString().trim()
      : (message.data['message']?.toString() ?? '');
  final url = FCMService.notificationUrlFromData(message.data) ?? '';

  final androidDetails = AndroidNotificationDetails(
    kTimaLoveNotifyChannelId,
    kTimaLoveNotifyChannelName,
    channelDescription: kTimaLoveNotifyChannelDesc,
    importance: Importance.max,
    priority: Priority.max,
    playSound: true,
    enableVibration: true,
    enableLights: true,
    visibility: NotificationVisibility.public,
    category: AndroidNotificationCategory.message,
    icon: '@mipmap/ic_launcher',
    ticker: title,
    channelShowBadge: true,
    autoCancel: true,
    styleInformation: BigTextStyleInformation(
      body.isNotEmpty ? body : title,
      contentTitle: title,
      summaryText: 'TimaLove',
    ),
  );

  const darwinDetails = DarwinNotificationDetails(
    presentAlert: true,
    presentBadge: true,
    presentSound: true,
    presentBanner: true,
    presentList: true,
    interruptionLevel: InterruptionLevel.timeSensitive,
  );

  await localNotifications.show(
    DateTime.now().millisecondsSinceEpoch.remainder(100000),
    title,
    body,
    NotificationDetails(android: androidDetails, iOS: darwinDetails),
    payload: url,
  );
}
