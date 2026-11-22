// ViewModel ekranu „Dokumenty” na fałszywym repozytorium (bez sieci i bez widżetów).
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:rodziceplus/core/session.dart';
import 'package:rodziceplus/data/api_client.dart';
import 'package:rodziceplus/data/models/modele.dart';
import 'package:rodziceplus/data/models/plik_do_wgrania.dart';
import 'package:rodziceplus/data/repositories/sprawa_repository.dart';
import 'package:rodziceplus/features/dokumenty/dokumenty_viewmodel.dart';

const _liczniki = Liczniki();

Zadanie _zadanie(String status, {String etap = 'odczyt', double postep = 0.5, String? blad}) => Zadanie(
      id: 'z1',
      status: status,
      etap: etap,
      postep: postep,
      komunikat: status == 'w_toku' ? 'Odczytujemy zaświadczenie Z-3 (1 z 2)…' : null,
      dokumenty: const [],
      blad: blad,
    );

const _z3 = Dokument(
  id: 'd1', plik: 'sprawa.pdf', typ: 'Z-3', typOpis: 'Zaświadczenie płatnika składek', strony: [5, 6],
  wystawca: 'pracodawca', archiwalny: false, rola: 'dane', liczbaPol: 3, doSprawdzenia: 1, informacja: [],
);

class _FakeRepo extends SprawaRepository {
  _FakeRepo() : super(ApiClient(SesjaAplikacji()), SesjaAplikacji());

  /// Kolejne odpowiedzi odpytywania zadania.
  final List<Zadanie> odpowiedziZadania = [];
  Object? bladWgrania;
  List<Dokument> zapisane = [];
  int wgrano = 0;
  int odpytan = 0;
  int zaladowanDokumentow = 0;

  @override
  Future<String> wgrajDokumenty(List<PlikDoWgrania> pliki) async {
    if (bladWgrania != null) throw bladWgrania!;
    wgrano++;
    return 'z1';
  }

  @override
  Future<Zadanie> zadanie(String zadanieId) async {
    odpytan++;
    final z = odpowiedziZadania.removeAt(0);
    if (!z.wToku) zapisane = [_z3];
    return z;
  }

  @override
  Future<List<Dokument>> dokumenty() async {
    zaladowanDokumentow++;
    return zapisane;
  }

  @override
  Future<List<OdczytanePole>> odczytanePola() async => [];

  @override
  Future<Porownanie?> porownanie() async => null;

  @override
  Future<ZmianaDanych> usunDokument(String dokumentId) async {
    zapisane = [];
    return const ZmianaDanych(
        dodano: 0, zmienionoAktywne: [], noweKonflikty: 0, liczniki: _liczniki, wynikiNieaktualne: true);
  }
}

PlikDoWgrania _plik(String nazwa, [int rozmiar = 10]) => PlikDoWgrania(nazwa: nazwa, bajty: Uint8List(rozmiar));

DokumentyViewModel _vm(_FakeRepo repo) => DokumentyViewModel(repo, odstepOdpytywania: Duration.zero);

void main() {
  test('upload → odpytywanie → gotowe: lista dokumentów, wybrane pliki wyczyszczone', () async {
    final repo = _FakeRepo()
      ..odpowiedziZadania.addAll([_zadanie('w_toku'), _zadanie('w_toku', postep: 0.8), _zadanie('gotowe', postep: 1)]);
    final vm = _vm(repo);
    await Future<void>.delayed(Duration.zero); // pierwsze ładowanie (pusta sprawa)
    expect(vm.maWynik, isFalse);

    final etapy = <String>[];
    vm.addListener(() {
      if (vm.wgrywa) etapy.add(vm.komunikatEtapu);
    });
    vm.dodajPliki([_plik('sprawa.pdf')]);
    expect(vm.mozeWgrac, isTrue);
    await vm.wgraj();

    expect(repo.wgrano, 1);
    expect(repo.odpytan, 3);
    expect(etapy, contains('Odczytujemy zaświadczenie Z-3 (1 z 2)…'));
    expect(vm.wgrywa, isFalse);
    expect(vm.bladWgrania, isNull);
    expect(vm.wybrane, isEmpty);
    expect(vm.dokumenty.single.typOpis, 'Zaświadczenie płatnika składek');
  });

  test('błąd 415 z serwera: komunikat po polsku, pliki zostają, brak odpytywania', () async {
    final repo = _FakeRepo()..bladWgrania = const NieobslugiwanyFormat();
    final vm = _vm(repo);
    vm.dodajPliki([_plik('skan.pdf')]);
    await vm.wgraj();

    expect(vm.bladWgrania, 'Na razie przyjmujemy tylko pliki PDF.');
    expect(vm.wgrywa, isFalse);
    expect(vm.wybrane, hasLength(1));
    expect(repo.odpytan, 0);
  });

  test('błąd odczytu w tle: komunikat, a rozpoznane dokumenty i tak się pokazują', () async {
    final repo = _FakeRepo()..odpowiedziZadania.add(_zadanie('blad', blad: 'Nie udało się odczytać pliku.'));
    final vm = _vm(repo);
    vm.dodajPliki([_plik('sprawa.pdf')]);
    await vm.wgraj();

    expect(vm.bladWgrania, 'Nie udało się odczytać pliku.');
    expect(vm.dokumenty, hasLength(1));
  });

  test('nie-PDF i za duży plik są odrzucane po stronie klienta', () {
    final vm = _vm(_FakeRepo());
    vm.dodajPliki([
      _plik('notatka.docx'),
      _plik('dobry.PDF'),
      _plik('dobry.PDF'), // duplikat
      _plik('ogromny.pdf', DokumentyViewModel.maxRozmiarPliku + 1),
    ]);

    expect([for (final p in vm.wybrane) p.nazwa], ['dobry.PDF']);
    expect(vm.uwagaOPlikach, allOf(contains('notatka.docx'), contains('ogromny.pdf')));
  });

  test('usunięcie dokumentu odświeża listę', () async {
    final repo = _FakeRepo()..zapisane = [_z3];
    final vm = _vm(repo);
    await Future<void>.delayed(Duration.zero);
    expect(vm.dokumenty, hasLength(1));

    await vm.usun(_z3);
    expect(vm.dokumenty, isEmpty);
    expect(vm.usuwanyId, isNull);
  });

  group('ApiClient – własne wyjątki', () {
    ApiClient klient(http.Client c) => ApiClient(SesjaAplikacji(), klient: c, bazowyUrl: 'http://test');

    Future<Object?> blad(http.Client c) async {
      try {
        await klient(c).wgraj('/sprawy/s1/dokumenty', 'pliki', [_plik('a.pdf')]);
      } catch (e) {
        return e;
      }
      return null;
    }

    http.Response json(Object o, int kod) =>
        http.Response.bytes(utf8.encode(jsonEncode(o)), kod, headers: {'content-type': 'application/json'});

    test('413 → PlikZaDuzy, 415 → NieobslugiwanyFormat (bez surowego komunikatu serwera)', () async {
      expect(await blad(MockClient((_) async => json({'detail': 'surowe'}, 413))), isA<PlikZaDuzy>());
      final e415 = await blad(MockClient((_) async => json({'detail': 'surowe'}, 415)));
      expect(e415, isA<NieobslugiwanyFormat>());
      expect((e415! as ApiException).komunikat, isNot(contains('surowe')));
    });

    test('brak sieci → BladSieci; odpowiedź nie-JSON nie kończy się wyjątkiem parsera', () async {
      expect(await blad(MockClient((_) async => throw http.ClientException('offline'))), isA<BladSieci>());
      final e = await blad(MockClient((_) async => http.Response('<html>502</html>', 502)));
      expect(e, isA<ApiException>());
      expect((e! as ApiException).kod, 502);
    });

    test('plik trafia w polu „pliki” jako multipart', () async {
      late http.BaseRequest zapytanie;
      final c = MockClient((r) async {
        zapytanie = r;
        return json({'zadanie_id': 'z1'}, 202);
      });
      final odp = await klient(c).wgraj('/sprawy/s1/dokumenty', 'pliki', [_plik('a.pdf'), _plik('b.pdf')]);
      expect(odp, {'zadanie_id': 'z1'});
      expect(zapytanie.headers['content-type'], startsWith('multipart/form-data'));
    });
  });
}
