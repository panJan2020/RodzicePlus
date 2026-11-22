import 'package:go_router/go_router.dart';

import '../features/dane/dane_view.dart';
import '../features/kalkulator/kalkulator_view.dart';
import '../features/konto/konto_view.dart';
import '../features/logowanie/logowanie_view.dart';
import '../features/moje_swiadczenia/moje_swiadczenia_view.dart';
import '../features/start/start_view.dart';
import '../features/ubezpieczenie/ubezpieczenie_view.dart';
import '../shared/widgets/szkielet_strony.dart';
import 'session.dart';

/// Ekrany dostępne tylko po zalogowaniu.
const _chronione = {'/konto', '/ubezpieczenie'}; // „Dane”, „Świadczenia” i „Kalkulator” działają też bez logowania

/// Trasy aplikacji. Router nasłuchuje sesji:
/// * niezalogowany na chronionym ekranie → `/logowanie?z=<skąd przyszedł>`,
/// * po zalogowaniu na /logowanie → wraca tam, skąd przyszedł (albo na start).
GoRouter utworzRouter(SesjaAplikacji sesja) => GoRouter(
      refreshListenable: sesja,
      redirect: (context, stan) {
        final sciezka = stan.matchedLocation;
        if (!sesja.zalogowany && _chronione.contains(sciezka)) {
          return Uri(path: '/logowanie', queryParameters: {'z': stan.uri.toString()}).toString();
        }
        if (sesja.zalogowany && sciezka == '/logowanie') {
          final z = stan.uri.queryParameters['z'];
          return (z != null && z.startsWith('/') && !z.startsWith('//')) ? z : '/';
        }
        return null;
      },
      routes: [
        ShellRoute(
          builder: (context, stan, child) => SzkieletStrony(sciezka: stan.matchedLocation, child: child),
          routes: [
            GoRoute(path: '/', builder: (_, _) => const StartView()),
            GoRoute(path: '/logowanie', builder: (_, _) => const LogowanieView()),
            GoRoute(path: '/konto', builder: (_, _) => const KontoView()),
            GoRoute(path: '/ubezpieczenie', builder: (_, _) => const UbezpieczenieView()),
            // /dane?pytanie=B5 – rozwija sekcję i przewija do pytania
            GoRoute(path: '/dane', builder: (_, s) => DaneView(pytanie: s.uri.queryParameters['pytanie'])),
            GoRoute(path: '/swiadczenia', builder: (_, _) => const MojeSwiadczeniaView()),
            GoRoute(path: '/kalkulator', builder: (_, _) => const KalkulatorView()),
          ],
        ),
      ],
    );
