import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'core/config.dart';
import 'core/router.dart';
import 'core/session.dart';
import 'core/theme.dart';
import 'data/api_client.dart';
import 'data/repositories/auth_repository.dart';
import 'data/repositories/sprawa_repository.dart';
import 'data/repositories/zus_repository.dart';

/// Korzeń aplikacji: tworzy sesję, klienta API, repozytoria i router (raz, na całe życie aplikacji)
/// i udostępnia je widokom przez `provider`.
class App extends StatefulWidget {
  const App({super.key, this.api});

  /// Do testów: własny klient API (np. z fałszywym HTTP).
  final ApiClient Function(SesjaAplikacji sesja)? api;

  @override
  State<App> createState() => _AppState();
}

class _AppState extends State<App> {
  late final SesjaAplikacji _sesja = SesjaAplikacji();
  late final ApiClient _api = widget.api?.call(_sesja) ?? ApiClient(_sesja);
  late final AuthRepository _auth = AuthRepository(_api, _sesja);
  late final ZusRepository _zus = ZusRepository(_api);
  late final SprawaRepository _sprawy = SprawaRepository(_api, _sesja);
  late final GoRouter _router = utworzRouter(_sesja);

  @override
  void dispose() {
    _router.dispose();
    _sesja.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<SesjaAplikacji>.value(value: _sesja),
        Provider<ApiClient>.value(value: _api),
        Provider<AuthRepository>.value(value: _auth),
        Provider<ZusRepository>.value(value: _zus),
        Provider<SprawaRepository>.value(value: _sprawy),
      ],
      child: MaterialApp.router(
        title: Config.nazwaAplikacji,
        debugShowCheckedModeBanner: false,
        theme: zbudujMotyw(),
        routerConfig: _router,
      ),
    );
  }
}
