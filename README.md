# 🏢 CRM dla Organizacji Studenckiej - BAZA FR BEST Łódź

Aplikacja wspomagająca zarządzanie relacjami biznesowymi (Fundraising) w organizacji studenckiej. Projekt rozwiązuje realny problem chaosu w kontaktach, dublowania firm i braku ciągłości historii interakcji.

## 🚀 Technologie
* **Python** (Backend & Logika aplikacji)
* **SQLite** (Lokalna, relacyjna baza danych)
* **Streamlit** (Interfejs użytkownika / Web App)
* **Pandas** (Przetwarzanie danych)
* **Faker** (Generowanie danych testowych zgodnych z RODO)

## 📊 Architektura Bazy Danych
Projekt opiera się na znormalizowanej relacyjnej strukturze SQL (3NF), która obejmuje tabele: `Firma`, `OsobaKontaktowa`, `Uzytkownik` (Członkowie), `Interakcja` (Historia kontaktów) oraz tabelę łączącą dla relacji wiele-do-wielu (`FirmaOsobaKontaktowa`).

## 🔐 Zgodność z RODO
Zgodnie z zasadami ochrony danych osobowych, repozytorium **nie zawiera** prawdziwych danych kontaktowych ani plików produkcyjnej bazy danych (zabezpieczenie przez `.gitignore`). Projekt zawiera dedykowany skrypt generujący w pełni fikcyjne, polskojęzyczne dane testowe.

## 🛠️ Jak uruchomić projekt lokalnie?

1. Sklonuj repozytorium i wejdź do folderu projektu.
2. Stwórz i aktywuj środowisko wirtualne:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Na Windows: .venv\Scripts\Activate.ps1