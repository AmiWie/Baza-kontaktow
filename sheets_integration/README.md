# Szablon Google Sheets: Automatyzacja Cold Maili i eksport współprac do CRM

Dedykowany arkusz Google Sheets zintegrowany ze środowiskiem **Google Workspace (Gmail, Drive, Docs)** za pomocą skryptów **Google Apps Script**. Narzędzie służy do automatyzacji procesu outreachu (cold mailingu do firm i partnerów) oraz gromadzenia danych o współpracach przed ich eksportem do centralnej aplikacji webowej.

---

## 🎯 Główne możliwości

* **Dynamiczne szablony z Google Docs**: Treść wiadomości pobierana jest bezpośrednio ze sformatowanego pliku Docs z automatycznym uzupełnianiem zmiennych (`{FIRMA}`, `{PROJEKT}`).
* **Personalizacja i załączniki**: Automatyczne dołączanie ofert barterowych/sponsorskich w formacie PDF z Dysku Google oraz dołączanie domyślnego podpisu nadawcy z Gmaila.
* **Globalne DW**: Każdy wysyłany mail automatycznie dodaje osobę w DW.
* **Kolejkowanie i archiwizacja**: Po udanej wysyłce wiersze natychmiast znikają z arkusza roboczego i trafiają do zakładki archiwalnej z sygnaturą czasową.
* **Planowanie wysyłki**: Możliwość zaplanowania wysyłki na konkretną datę i godzinę bez konieczności trzymania otwartego arkusza czy włączonego komputera.
* **Śledzenie odpowiedzi w tle**: Sprawdzanie skrzynki Gmail i oznaczanie, którzy odbiorcy odesłali odpowiedź na ofertę.
* **Eksport do bazy**: Generowanie pliku `.csv` ze strukturą gotową do wgrania do bazy danych aplikacji webowej (wraz z metrykami konwersji mailingu).

---

## 📑 Struktura zakładek w arkuszu

### 1. `Ustawienia`
Główny panel konfiguracyjny projektu. Skrypt odczytuje parametry wpisane w kolumnach:

| Pole (Kolumna A) | Wartość (Kolumna B) | Opis |
| :--- | :--- | :--- |
| **Link do docx z treścią maila** | `https://docs.google.com/document/d/...` | Link lub ID dokumentu Google Docs z szablonem maila |
| **Temat maila** | `Współpraca przy organizacji {PROJEKT}` | Tytuł wiadomości (obsługuje tag `{PROJEKT}`) |
| **Oferta - link do załącznika PDF**| `https://drive.google.com/file/d/...` | Link do pliku PDF z ofertą na Dysku Google |
| **Nazwa projektu** | `Międzynarodowy Kurs Naukowy AI...` | Nazwa podstawiana pod zmienną projektu |
| **DW** | `koordynator@best.p.lodz.pl` | Adres e-mail koordynatora projektu dodawany w DW |

---

### 2. `do wysłania`
Lista odbiorców oczekujących na wysłanie. Skrypt automatycznie wykrywa kolumny na podstawie nagłówków w 1. wierszu:

* **Kolumna A**: `Lp.`
* **Kolumna B**: `Firma` – nazwa wstawiana w miejsce `{FIRMA}`
* **Kolumna C**: `Email` – adresy e-mail (skrypt czyści spacje, średniki i akceptuje listy po przecinku)

---

### 3. `wysłane maile`
Automatycznie zarządzane archiwum. Wiersz po udanej wysyłce jest przenoszony tutaj z dopiskiem:
* `Data wysyłki`
* `Status maila` (`Wysłano`)
* `Odpowiedź` (`TAK (Odpisał)` / `Brak odpowiedzi`)

---

### 4. `dane współprace`
Miejsce, w którym zbierane są sfinalizowane ustalenia. Kolumny są przygotowane pod schemat bazy danych:

| Kolumna | Nazwa nagłówka | Wymagane? | Wartości dopuszczalne / Domyślne |
| :--- | :--- | :---: | :--- |
| **A** | `Nazwa firmy` | **TAK** | Pełna nazwa partnera |
| **B** | `Kategoria` | NIE | `Sponsor`, `Barter`, `Inna` (domyślnie: *Inna*) |
| **C** | `Projekt` | **TAK** | Nazwa powiązanego projektu |
| **D** | `Imię` | NIE | Imię osoby kontaktowej |
| **E** | `Nazwisko` | NIE | Nazwisko osoby kontaktowej |
| **F** | `Email` | NIE | Adres e-mail kontaktu |
| **G** | `Telefon` | NIE | Numer telefonu |
| **H** | `Status` | NIE | `Sukces`, `W trakcie`, `Odrzucone` (domyślnie: *Sukces*) |
| **I** | `Komentarz` | NIE | Notatki, ustalenia barterowe itp. |
| **J** | `Sposób nawiązania kontaktu` | NIE | `Mail`, `Telefon`, `Osobisty Kontakt` (domyślnie: *Mail*) |

---

## Instrukcja wdrożenia i użycia

### Krok 1: Utworzenie własnej kopii
1. Dodaj plik Szablon Współprac do swojego Dysku.
2. Przygotuj tekst maila w Google Docs, zachowując znaczniki `{FIRMA}` i `{PROJEKT}`.

### Krok 2: Konfiguracja i uprawnienia
1. Uzupełnij zakładkę `Ustawienia` linkami do dokumentu Docs, załącznika PDF oraz adresem mail do DW.
2. Odśwież stronę w przeglądarce (**F5**) – po chwili obok menu *Pomoc* pojawi się dedykowane menu:  
    **`Mailing & Baza`**.
3. Kliknij **`Wyślij wiadomość testową (do siebie)`**:
   * Google wyświetli jednorazowe okno autoryzacji uprawnień (zezwól skryptowi na dostęp do poczty i dysku).
   * Sprawdź swoją skrzynkę i upewnij się, że tekst, formatowanie i załącznik wyglądają poprawnie.

### Krok 3: Nadanie wysyłki
1. Wklej firmy i adresy e-mail do zakładki `do wysłania`.
2. Z poziomu menu wybierz:
   * **Wyślij TERAZ do wszystkich odbiorców** – natychmiastowe nadanie mailingu,
   * **Zaplanuj wysłanie** – wybór daty i godziny.

### Krok 4: Eksport do aplikacji webowej
1. Po zakończeniu projektu uzupełnij zakładkę `dane współprac`.
2. Kliknij **`Eksportuj wszystko do CSV (do bazy)`**.
3. Plik `.csv` pobierze się automatycznie na dysk lokalny komputera (oraz zapisze kopię bezpieczeństwa w folderze na Dysku Google).
4. Otwórz aplikację webową, przejdź do modułu **Import danych** i załaduj wygenerowany plik.

---

## Wymagania techniczne i konfiguracja kodu Apps Script

Jeśli tworzysz arkusz od zera lub migrujesz kod do nowej instancji:
1. W arkuszu wejdź w **Rozszerzenia ➔ Apps Script**.
2. Wklej zawartość pliku `Code.js`.
3. W sekcji **Usługi (Services)** po lewej stronie kliknij **`+`** i włącz usługę **`Gmail API`** (wymaganą do pobierania oficjalnego podpisu użytkownika).
4. Zapisz projekt (**Ctrl + S**).