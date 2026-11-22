"""Scalanie wartości pól z wielu źródeł (docs/architektura.md, rozdz. 6)."""
from app.merge.scalanie import (NiedozwolonaWartosc, aktywne_wartosci, dodaj, konflikt, konflikty, migawka,
                                przelicz, ustaw_recznie, usun, usun_dokument, wybor_aktywnej)

__all__ = ["NiedozwolonaWartosc", "aktywne_wartosci", "dodaj", "konflikt", "konflikty", "migawka", "przelicz",
           "ustaw_recznie", "usun", "usun_dokument", "wybor_aktywnej"]
