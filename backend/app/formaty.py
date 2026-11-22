"""Formatowanie liczb dla tekstów użytkownika – bez zależności od reguł i kalkulatora."""
from decimal import Decimal


def kwota_tekst(k: Decimal | str) -> str:
    """1234.5 → „1 234,50 zł”."""
    calosc, grosze = f"{Decimal(str(k)):.2f}".split(".")
    znak = "-" if calosc.startswith("-") else ""
    calosc = calosc.lstrip("-")
    grupy = []
    while calosc:
        grupy.insert(0, calosc[-3:])
        calosc = calosc[:-3]
    return f"{znak}{' '.join(grupy)},{grosze} zł"
