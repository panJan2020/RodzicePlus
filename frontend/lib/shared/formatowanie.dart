/// Formatowanie do wyświetlania (bez logiki biznesowej).
library;

String _dwa(int n) => n.toString().padLeft(2, '0');

/// `10.07.2026`
String formatujDate(DateTime d) => '${_dwa(d.day)}.${_dwa(d.month)}.${d.year}';
