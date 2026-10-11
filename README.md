# CRM dla Organizacji Studenckiej

Centralna platforma webowa wspomagająca zarządzanie relacjami partnerskimi, historią kontaktu z firmami, harmonogramem wniosków grantowych oraz analityką kampanii mailingowych w organizacji studenckiej.

Projekt rozwiązuje problem rozproszonej wiedzy, dublowania firm między projektami i utraty historii ustaleń, łącząc automatyzację outreachu w Google Workspace z centralną bazą relacyjną w chmurze.

---
## Główne moduły aplikacji

1. **Baza Firm**:
   * Centralny rejestr partnerów biznesowych z relacją wiele-do-wielu (`Firma` ↔ `OsobaKontaktowa`).
   * Błyskawiczne filtrowanie według nazwy, kategorii (*Sponsor*, *Barter*, *Inna*) oraz projektów.
   * Moduł powiadomień: **Pilne follow-upy na dziś** z możliwością szybkiego oznaczenia sukcesu lub odmowy.
   * Obsługa załączników (umowy, prezentacje, ustalenia w PDF/DOCX) przypisanych bezpośrednio do notatek.
   * Eksport przefiltrowanych danych do pliku CSV.

2. **Dynamiczny Dashboard & Analityka**:
   * Kluczowe metryki KPI: całkowita liczba partnerów, sfinalizowane współprace, zrealizowane interakcje.
   * Wykres struktury partnerów według kategorii (z adaptacyjną legendą do motywu jasnego/ciemnego).
   * **Analityka mailingu i konwersji**: łączny *Response Rate*, wolumen wysłanych maili vs uzyskanych odpowiedzi.
   * Podział pozyskanych współprac według kanału dotarcia (*E-mail*, *Telefon*, *Osobisty kontakt*).

3. **Granty & Dofinansowania**:
   * Interaktywny kalendarz deadline'ów (`streamlit-calendar`) z oznaczeniem statusów wniosków kolorami.
   * Śledzenie kwot wnioskowanych, instytucji dotujących oraz linków do dokumentacji.

4. **Import & Deduplikacja (CSV)**:
   * Bezpieczny import danych wyeksportowanych z arkuszy kampanii cold mailingowych.
   * Wbudowana logika deduplikacji – rozpoznawanie istniejących firm i osób, zapobieganie duplikatom oraz automatyczne dopisywanie nowych interakcji i metryk projektowych.

5. **Outreach (`sheets_template/`)**:
   * Gotowy arkusz Google Sheets zintegrowany z Gmail API, Google Docs i Dyskiem Google przez Apps Script.
   * Automatyczna wysyłka spersonalizowanych ofert z oficjalnym podpisem Gmaila, śledzenie odpowiedzi odbiorców oraz generator pliku `.csv` zgodnego ze standardem RFC 4180.

---

## Technologie
* **Frontend**: [Streamlit](https://streamlit.io/) (Python 3.12+) z reaktywnym interfejsem użytkownika.
* **Baza danych**: 
  * **Produkcja**: [Supabase](https://supabase.com/) (PostgreSQL w chmurze) z szyfrowaniem SSL i poolingiem połączeń w trybie transakcyjnym.
  * **Development lokalny**: Automatyczny fallback do relacyjnej bazy SQLite (`database.db`).
* **Wydajność & Pula połączeń**:
  * `psycopg2.pool.SimpleConnectionPool` cachowany przez `@st.cache_resource`.
  * Wielopoziomowy cache odczytów (`@st.cache_data`) z natychmiastową inwalidacją (`st.cache_data.clear()`) przy operacjach zapisu.
* **Bezpieczeństwo & Autoryzacja**:
  * Integracja z Google Cloud Platform przez protokół **OAuth 2.0 / OpenID Connect** (`Authlib`, `httpx`).
  * Dostęp ograniczony wyłącznie do zweryfikowanych kont organizacji w Google Workspace.
  * Automatyczne mapowanie zalogowanego konta Google z profilem członka w tabeli `Uzytkownik`.

---

## Architektura Bazy Danych
Projekt opiera się na znormalizowanej relacyjnej strukturze SQL (3NF), która obejmuje tabele: `Firma`, `OsobaKontaktowa`, `Uzytkownik` (Członkowie), `Interakcja` (Historia kontaktów) oraz tabelę łączącą dla relacji wiele-do-wielu (`FirmaOsobaKontaktowa`).
Tabele pomocnicze:
* `Granty`: rejestr wniosków o dofinansowania, terminów i statusów.
* `ProjektStatystyki`: zagregowane metryki kampanii mailingowych (wysłane, odpowiedzi, Response Rate, konwersje per kanał).

---

## Środowiska i Git Workflow

W repozytorium obowiązuje podział na dwie odseparowane gałęzie podpięte pod osobne instancje w Streamlit Cloud:

* **`main` (Środowisko stabilne / produkcyjne)**:
  * Wersja dla całego zespołu BEST. Wdrażane są na nią wyłącznie przetestowane i zatwierdzone funkcjonalności.
* **`dev` (Środowisko testowe / poligon deweloperski)**:
  * Niezależna aplikacja testowa z własnym wpisem `redirect_uri` w Google Cloud Console. Służy do prac rozwojowych bez ryzyka zakłócenia pracy organizacji.

---

## 🔐 Zgodność z RODO
Zgodnie z zasadami ochrony danych osobowych, repozytorium **nie zawiera** prawdziwych danych kontaktowych ani plików produkcyjnej bazy danych (zabezpieczenie przez `.gitignore`). Projekt zawiera dedykowany skrypt generujący w pełni fikcyjne, polskojęzyczne dane testowe.

---
## Uruchomienie lokalne (Development)
### 1. Klonowanie i środowisko wirtualne
```bash
git clone [https://github.com/](https://github.com/)<twoja-organizacja>/baza-kontaktow.git
cd baza-kontaktow

python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\Activate.ps1

pip install -r requirements.txt