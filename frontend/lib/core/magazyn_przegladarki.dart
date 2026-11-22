// Wybór implementacji magazynu: w przeglądarce sessionStorage, gdzie indziej (testy) – brak zapamiętywania.
export 'magazyn_stub.dart' if (dart.library.js_interop) 'magazyn_web.dart';
