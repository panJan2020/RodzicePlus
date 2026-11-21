import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';

import 'app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Dostępność: włącza drzewo semantyki w przeglądarce (czytniki ekranu).
  SemanticsBinding.instance.ensureSemantics();
  runApp(const App());
}
