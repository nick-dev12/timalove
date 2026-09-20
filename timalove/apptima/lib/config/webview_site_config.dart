/// URL du site TimaLove chargée dans la WebView.
const String kMarketplaceBaseUrl = 'https://mytimalove.com/';

/// Suivi livreur natif (Sugar Paper) — désactivé pour TimaLove App Store.
const bool kNativeDeliveryTrackingEnabled = false;

/// API configuration / force update (Django).
String get kAppVersionApiUrl {
  return 'https://mytimalove.com/api/app-config/';
}

const Set<String> kTimaLoveHosts = {
  'mytimalove.com',
  'www.mytimalove.com',
  '127.0.0.1',
  'localhost',
  // Ancien domaine — deep links / sessions migrées
  'timalove.goo-bridge.com',
  'www.timalove.goo-bridge.com',
};

bool isMarketplaceHost(String host) {
  final h = host.toLowerCase();
  if (kTimaLoveHosts.contains(h)) {
    return true;
  }
  return h.endsWith('.goo-bridge.com') && h.contains('timalove');
}

String normalizeMarketplaceHost(String host) {
  var h = host.toLowerCase();
  if (h == 'www.mytimalove.com') {
    return 'mytimalove.com';
  }
  if (h == 'www.timalove.goo-bridge.com') {
    return 'timalove.goo-bridge.com';
  }
  return h;
}

bool isLegacyMarketplaceUrl(String url) {
  final lower = url.toLowerCase();
  return lower.contains('goo-bridge.com');
}
