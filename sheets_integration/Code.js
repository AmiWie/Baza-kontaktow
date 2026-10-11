// --- STAŁE SYSTEMOWE ---
const ZAKLADKA_DANYCH = 'do wysłania';
const ZAKLADKA_WYSLANE = 'wysłane maile';
const ZAKLADKA_CONFIG = 'Ustawienia';
const ZAKLADKA_WSPOLPRACE = 'dane współprac';
const TRIGGER_FUNCTION_NAME = 'wyslijWiadomosciAutomatycznie';

/**
 * Menu w arkuszu oraz ciche odświeżenie odpowiedzi w tle przy otwarciu.
 */
function onOpen() {
    SpreadsheetApp.getUi()
        .createMenu('📩 Mailing & Baza')
        .addItem('Wyślij wiadomość testową (do siebie)', 'wyslijTestowaWiadomosc')
        .addSeparator()
        .addItem('Wyślij TERAZ do wszystkich odbiorców', 'wyslijWiadomosci')
        .addItem('Zaplanuj wysyłanie', 'otworzOknoPlanowania')
        .addItem('Sprawdź / Anuluj zaplanowaną wysyłkę', 'anulujZaplanowanaWysylke')
        .addSeparator()
        .addItem('💾 Eksportuj wszystko do CSV (do bazy)', 'eksportujWszystkoDoCsv')
        .addToUi();

    // Ciche sprawdzanie odpowiedzi w tle 
    try {
        cicheSprawdzenieOdpowiedzi();
    } catch (e) {
        Logger.log("Pominięto auto-sprawdzanie przy onOpen (brak uprawnień w prostym triggerze): " + e.message);
    }
}

/**
 * Odczytuje konfigurację z zakładki Ustawienia
 */
function pobierzKonfiguracje() {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheetConfig = ss.getSheetByName(ZAKLADKA_CONFIG);

    if (!sheetConfig) {
        throw new Error(`Brak zakładki konfiguracji '${ZAKLADKA_CONFIG}'.`);
    }

    const dane = sheetConfig.getDataRange().getValues();
    const rawConfig = {};

    dane.forEach(wiersz => {
        if (wiersz[0]) {
            rawConfig[String(wiersz[0]).trim().toLowerCase()] = String(wiersz[1] || '').trim();
        }
    });

    return {
        linkDocs: rawConfig['link do docx z treścią maila'] || rawConfig['link lub id dokumentu z treścią (docs)'] || '',
        temat: rawConfig['temat maila'] || rawConfig['temat'] || '',
        zalacznik: rawConfig['oferta - link do załącznika pdf'] || rawConfig['id lub link do załącznika'] || '',
        projekt: rawConfig['nazwa projektu'] || '',
        dw: rawConfig['dw'] || rawConfig['email koordynatora (dw)'] || ''
    };
}

function wyodrebnijIdPliku(linkLubId) {
    if (!linkLubId) return null;
    const match = linkLubId.match(/[-\w]{25,}/);
    return match ? match[0] : linkLubId;
}

function pobierzTrescZDocs(docIdLubLink) {
    const docId = wyodrebnijIdPliku(docIdLubLink);
    if (!docId) {
        throw new Error("Nie podano linku do dokumentu Google Docs z treścią w zakładce Ustawienia.");
    }

    const url = `https://docs.google.com/feeds/download/documents/export/Export?id=${docId}&exportFormat=html`;
    const parametry = {
        headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
        muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch(url, parametry);
    if (response.getResponseCode() !== 200) {
        throw new Error(`Nie udało się pobrać dokumentu Docs (Kod: ${response.getResponseCode()}). Sprawdź uprawnienia do pliku.`);
    }

    return response.getContentText();
}

function pobierzZalaczniki(idLubLink) {
    const fileId = wyodrebnijIdPliku(idLubLink);
    if (!fileId) return [];

    try {
        return [DriveApp.getFileById(fileId).getAs(MimeType.PDF)];
    } catch (e) {
        Logger.log("Błąd załącznika: " + e.message);
        return [];
    }
}

function pobierzPodpisGmail() {
    try {
        const aliasy = Gmail.Users.Settings.SendAs.list('me').sendAs;
        const podstawowyAlias = aliasy.find(alias => alias.isDefault) || aliasy[0];
        return podstawowyAlias.signature || "";
    } catch (e) {
        Logger.log("Błąd podpisu: " + e.message);
        return "";
    }
}

function pobierzLubStworzArkuszWyslane(ss, arkuszZrodlowy) {
    let arkuszWyslane = ss.getSheetByName(ZAKLADKA_WYSLANE);

    if (!arkuszWyslane) {
        arkuszWyslane = ss.insertSheet(ZAKLADKA_WYSLANE);
        const naglowki = arkuszZrodlowy.getRange(1, 1, 1, arkuszZrodlowy.getLastColumn()).getValues()[0];
        naglowki.push('Data wysyłki', 'Status maila', 'Odpowiedź');
        arkuszWyslane.appendRow(naglowki);
    }

    return arkuszWyslane;
}

function przygotujFinalnyHtml(htmlDocs, mapaZmiennych, podpis) {
    let tresc = htmlDocs;

    for (const [klucz, wartosc] of Object.entries(mapaZmiennych)) {
        tresc = tresc.split(`{${klucz}}`).join(wartosc);
    }

    const resetStyles = `
    <style>
      body { 
        font-family: Arial, Helvetica, sans-serif !important; 
        font-size: 14px !important; 
        line-height: 1.5 !important; 
        color: #222222 !important; 
        padding: 0 !important; 
        margin: 0 !important; 
      }
      p { margin: 0 0 14px 0 !important; }
    </style>
  `;

    if (tresc.includes('<head>')) {
        tresc = tresc.replace('<head>', `<head>${resetStyles}`);
    } else {
        tresc = resetStyles + tresc;
    }

    if (podpis) {
        const sekcjaPodpisu = `<br><div style="margin-top: 15px;">${podpis}</div>`;
        if (tresc.includes('</body>')) {
            tresc = tresc.replace('</body>', `${sekcjaPodpisu}</body>`);
        } else {
            tresc += sekcjaPodpisu;
        }
    }

    return tresc;
}

/**
 * WYSYŁKA TESTOWA (do siebie)
 */
function wyslijTestowaWiadomosc() {
    const ui = SpreadsheetApp.getUi();
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const config = pobierzKonfiguracje();
    const mojEmail = Session.getActiveUser().getEmail();

    let szablonHtml = "";
    try {
        szablonHtml = pobierzTrescZDocs(config.linkDocs);
    } catch (err) {
        ui.alert('BŁĄD SZABLONU', err.message, ui.ButtonSet.OK);
        return;
    }

    const arkuszDoWyslania = ss.getSheetByName(ZAKLADKA_DANYCH);
    let testowaNazwaFirmy = 'Firma Testowa';

    if (arkuszDoWyslania && arkuszDoWyslania.getLastRow() > 1) {
        const pierwszyWiersz = arkuszDoWyslania.getRange(2, 1, 1, arkuszDoWyslania.getLastColumn()).getValues()[0];
        testowaNazwaFirmy = String(pierwszyWiersz[1] || 'Firma Testowa').trim();
    }

    const zalaczniki = pobierzZalaczniki(config.zalacznik);
    const podpis = pobierzPodpisGmail();
    const emailDw = config.dw;

    const mapaZmiennych = {
        'FIRMA': testowaNazwaFirmy,
        'PROJEKT': config.projekt,
        'NAZWA_PROJEKTU': config.projekt
    };

    const temat = '[TEST] ' + config.temat
        .replace('{NAZWA_PROJEKTU}', config.projekt)
        .replace('{PROJEKT}', config.projekt);

    const html = przygotujFinalnyHtml(szablonHtml, mapaZmiennych, podpis);

    const opcjeWysylki = {
        htmlBody: html,
        attachments: zalaczniki
    };

    if (emailDw) {
        opcjeWysylki.cc = emailDw;
    }

    GmailApp.sendEmail(mojEmail, temat, '', opcjeWysylki);

    ui.alert('Test wysłany!',
        `Wiadomość testowa została wysłana na: ${mojEmail}\nFirma: "${testowaNazwaFirmy}"\nDW: ${emailDw || 'Brak'}`,
        ui.ButtonSet.OK
    );
}

/**
 * WYSYŁKA MAILI
 */
function wykonajMasowaWysylke() {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const config = pobierzKonfiguracje();
    const szablonHtml = pobierzTrescZDocs(config.linkDocs);

    const arkuszDoWyslania = ss.getSheetByName(ZAKLADKA_DANYCH);
    if (!arkuszDoWyslania) {
        throw new Error(`Nie znaleziono zakładki '${ZAKLADKA_DANYCH}'.`);
    }

    const daneZakresu = arkuszDoWyslania.getDataRange();
    if (daneZakresu.getNumRows() <= 1) {
        return { wyslano: 0, pominieto: 0, bledy: ['Brak danych w arkuszu.'] };
    }

    const emailDw = config.dw;
    const zalaczniki = pobierzZalaczniki(config.zalacznik);
    const arkuszWyslane = pobierzLubStworzArkuszWyslane(ss, arkuszDoWyslania);
    const podpis = pobierzPodpisGmail();
    const wiersze = daneZakresu.getValues();

    const naglowki = wiersze[0].map(h => String(h).trim().toLowerCase());
    let colFirma = naglowki.findIndex(h => h.includes('firma') || h.includes('odbiorca') || h.includes('nazwa'));
    let colEmail = naglowki.findIndex(h => h.includes('mail') || h.includes('adres'));

    if (colFirma === -1) colFirma = 1;
    if (colEmail === -1) colEmail = 2;

    let wyslano = 0;
    let pominieto = 0;
    let bledy = [];

    for (let i = wiersze.length - 1; i >= 1; i--) {
        const wiersz = wiersze[i];
        const nazwaOdbiorcy = String(wiersz[colFirma] || '').trim();
        const emailRaw = String(wiersz[colEmail] || '').trim();

        const listaAdresatow = emailRaw
            .replace(/[\n\r; ]+/g, ',')
            .split(',')
            .map(e => e.trim())
            .filter(e => e.includes('@'))
            .join(',');

        if (nazwaOdbiorcy && listaAdresatow) {
            const mapaZmiennych = {
                'FIRMA': nazwaOdbiorcy,
                'PROJEKT': config.projekt,
                'NAZWA_PROJEKTU': config.projekt
            };

            const temat = config.temat
                .replace('{NAZWA_PROJEKTU}', config.projekt)
                .replace('{PROJEKT}', config.projekt);

            const html = przygotujFinalnyHtml(szablonHtml, mapaZmiennych, podpis);

            const opcjeWysylki = {
                htmlBody: html,
                attachments: zalaczniki
            };

            if (emailDw) {
                opcjeWysylki.cc = emailDw;
            }

            try {
                GmailApp.sendEmail(listaAdresatow, temat, '', opcjeWysylki);

                const wierszDoArchiwum = [...wiersz];
                const dataWysylki = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss');
                wierszDoArchiwum.push(dataWysylki, 'Wysłano', 'Oczekiwanie');
                arkuszWyslane.appendRow(wierszDoArchiwum);

                arkuszDoWyslania.deleteRow(i + 1);

                wyslano++;
                Utilities.sleep(500);
            } catch (e) {
                bledy.push(`Wiersz ${i + 1}: ${e.message}`);
                Logger.log(`Błąd wysyłki do ${listaAdresatow}: ${e.message}`);
            }
        } else {
            pominieto++;
            bledy.push(`Wiersz ${i + 1}: brak nazwy firmy ("${nazwaOdbiorcy}") lub brak '@' w emailu ("${emailRaw}").`);
        }
    }

    return { wyslano, pominieto, bledy };
}

function wyslijWiadomosci() {
    const ui = SpreadsheetApp.getUi();
    const config = pobierzKonfiguracje();

    const potwierdzenie = ui.alert(
        'Potwierdzenie wysyłki',
        `Rozpocząć natychmiastową wysyłkę z projektu: "${config.projekt || 'Domyślny'}"?\nDW koordynatora: ${config.dw || 'BRAK'}`,
        ui.ButtonSet.YES_NO
    );

    if (potwierdzenie !== ui.Button.YES) return;

    try {
        const wynik = wykonajMasowaWysylke();
        let komunikatKoncowy = `Wysłano i przeniesiono: ${wynik.wyslano}\nPominięto: ${wynik.pominieto}`;
        if (wynik.bledy.length > 0) {
            komunikatKoncowy += `\n\nSzczegóły:\n` + wynik.bledy.slice(0, 4).join('\n');
        }
        ui.alert('Podsumowanie', komunikatKoncowy, ui.ButtonSet.OK);
    } catch (err) {
        ui.alert('Błąd wysyłki', err.message, ui.ButtonSet.OK);
    }
}

// PLANOWANE WYSYŁANIE
function otworzOknoPlanowania() {
    const ui = SpreadsheetApp.getUi();
    const html = HtmlService.createHtmlOutput(
        `<!DOCTYPE html>
    <html>
      <head>
        <base target="_top">
        <style>
          body { font-family: Arial, sans-serif; font-size: 13px; padding: 15px; color: #333; }
          label { font-weight: bold; display: block; margin-top: 10px; margin-bottom: 4px; }
          input[type="datetime-local"] { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
          .btn-container { margin-top: 20px; text-align: right; }
          button { padding: 9px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
          .btn-primary { background-color: #1a73e8; color: white; margin-left: 8px; }
          .btn-secondary { background-color: #f1f3f4; color: #3c4043; }
          .info { color: #5f6368; font-size: 12px; margin-top: 8px; line-height: 1.4; }
        </style>
      </head>
      <body>
        <label for="termin">Wybierz datę i godzinę wysyłki:</label>
        <input type="datetime-local" id="termin" required>
        <div class="info">Google uruchomi wysyłkę automatycznie w chmurze – arkusz może być zamknięty.</div>
        <div class="btn-container">
          <button class="btn-secondary" onclick="google.script.host.close()">Anuluj</button>
          <button class="btn-primary" onclick="zapiszTermin()">Zaplanuj</button>
        </div>
        <script>
          const jutro = new Date();
          jutro.setDate(jutro.getDate() + 1);
          jutro.setHours(9, 0, 0, 0);
          const pad = n => String(n).padStart(2, '0');
          document.getElementById('termin').value = jutro.getFullYear() + '-' + pad(jutro.getMonth() + 1) + '-' + pad(jutro.getDate()) + 'T' + pad(jutro.getHours()) + ':' + pad(jutro.getMinutes());

          function zapiszTermin() {
            const wartosc = document.getElementById('termin').value;
            if (!wartosc) return;
            this.disabled = true;
            google.script.run
              .withSuccessHandler(() => google.script.host.close())
              .withFailureHandler(err => { alert('Błąd: ' + err.message); this.disabled = false; })
              .utworzWyzwalaczCzasowy(wartosc);
          }
        </script>
      </body>
    </html>`
    ).setWidth(400).setHeight(250);

    ui.showModalDialog(html, 'Zaplanuj wysyłkę mailingową');
}

function utworzWyzwalaczCzasowy(isoString) {
    const dataZaplanowana = new Date(isoString);
    const teraz = new Date();
    if (dataZaplanowana.getTime() <= teraz.getTime() + 60000) {
        throw new Error('Wybrana data musi być przynajmniej za 2 minuty.');
    }

    usunWszystkieWyzwalaczePlanowania();
    ScriptApp.newTrigger(TRIGGER_FUNCTION_NAME).timeBased().at(dataZaplanowana).create();
    const sformatowanaData = Utilities.formatDate(dataZaplanowana, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm');
    PropertiesService.getDocumentProperties().setProperty('PLANOWANA_DATA', sformatowanaData);
    SpreadsheetApp.getActiveSpreadsheet().toast(`Wysyłka zaplanowana na: ${sformatowanaData}`, '⏰ Sukces', 8);
}

function wyslijWiadomosciAutomatycznie() {
    const mojEmail = Session.getActiveUser().getEmail();
    try {
        const wynik = wykonajMasowaWysylke();
        usunWszystkieWyzwalaczePlanowania();
        PropertiesService.getDocumentProperties().deleteProperty('PLANOWANA_DATA');
        if (mojEmail) {
            GmailApp.sendEmail(mojEmail, '[RAPORT] Zakończono zaplanowany mailing',
                `Zaplanowany mailing został zrealizowany.\n\nWysłano: ${wynik.wyslano}\nPominięto: ${wynik.pominieto}`);
        }
    } catch (err) {
        if (mojEmail) {
            GmailApp.sendEmail(mojEmail, '[BŁĄD] Zaplanowany mailing nie powiódł się', err.message);
        }
    }
}

function anulujZaplanowanaWysylke() {
    const ui = SpreadsheetApp.getUi();
    const zapisanaData = PropertiesService.getDocumentProperties().getProperty('PLANOWANA_DATA');
    const wyzwalacze = ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === TRIGGER_FUNCTION_NAME);

    if (wyzwalacze.length === 0) {
        ui.alert('Status', 'Aktualnie nie ma żadnej zaplanowanej wysyłki.', ui.ButtonSet.OK);
        return;
    }

    if (ui.alert('Anulowanie', `Zaplanowano na: ${zapisanaData}. Anulować?`, ui.ButtonSet.YES_NO) === ui.Button.YES) {
        usunWszystkieWyzwalaczePlanowania();
        PropertiesService.getDocumentProperties().deleteProperty('PLANOWANA_DATA');
        ui.alert('Anulowano', 'Wysyłka została anulowana.', ui.ButtonSet.OK);
    }
}

function usunWszystkieWyzwalaczePlanowania() {
    ScriptApp.getProjectTriggers().forEach(t => {
        if (t.getHandlerFunction() === TRIGGER_FUNCTION_NAME) ScriptApp.deleteTrigger(t);
    });
}

// AUTOMATYCZNE ODŚWIEŻANIE ODPOWIEDZI I METRYKI 

/**
 * Ciche sprawdzanie odpowiedzi w tle (uruchamiane automatycznie przy otwarciu arkusza)
 */
function cicheSprawdzenieOdpowiedzi() {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const arkuszWyslane = ss.getSheetByName(ZAKLADKA_WYSLANE);

    if (!arkuszWyslane || arkuszWyslane.getLastRow() <= 1) return;

    const dane = arkuszWyslane.getDataRange().getValues();
    const naglowki = dane[0].map(h => String(h).trim().toLowerCase());

    let colEmail = naglowki.findIndex(h => h.includes('mail'));
    if (colEmail === -1) colEmail = 2;

    let colOdpowiedz = naglowki.findIndex(h => h.includes('odpowiedź') || h.includes('odpowiedz'));
    if (colOdpowiedz === -1) {
        colOdpowiedz = dane[0].length;
        arkuszWyslane.getRange(1, colOdpowiedz + 1).setValue('Odpowiedź');
    }

    let noweOdpowiedzi = 0;
    const mojEmail = Session.getActiveUser().getEmail().toLowerCase();

    for (let r = 1; r < dane.length; r++) {
        const email = String(dane[r][colEmail] || '').trim();
        if (!email || !email.includes('@')) continue;

        // Jeśli już wcześniej odnotowano odpowiedź, pomijamy szukanie
        const aktualnyStatus = String(dane[r][colOdpowiedz] || '');
        if (aktualnyStatus.includes('TAK')) {
            noweOdpowiedzi++;
            continue;
        }

        const watki = GmailApp.search(`to:${email}`);
        let czyOdpowiedziano = false;

        for (let w = 0; w < watki.length; w++) {
            if (watki[w].getMessageCount() > 1) {
                const wiadomosci = watki[w].getMessages();
                const czyJestOdpowiedzOsoby = wiadomosci.some(msg => !msg.getFrom().toLowerCase().includes(mojEmail));
                if (czyJestOdpowiedzOsoby) {
                    czyOdpowiedziano = true;
                    break;
                }
            }
        }

        if (czyOdpowiedziano) {
            arkuszWyslane.getRange(r + 1, colOdpowiedz + 1).setValue('TAK (Odpisał)');
            noweOdpowiedzi++;
        } else {
            arkuszWyslane.getRange(r + 1, colOdpowiedz + 1).setValue('Brak odpowiedzi');
        }
    }

    ss.toast(`Zaktualizowano odpowiedzi w tle: ${noweOdpowiedzi} firm odpisało.`, '📬 Poczta sprawdzona', 5);
}

/**
 * Obliczanie metryk projektu
 */
function obliczMetrykiProjektu() {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const config = pobierzKonfiguracje();
    const projekt = config.projekt || 'Brak nazwy';

    const arkuszWyslane = ss.getSheetByName(ZAKLADKA_WYSLANE);
    let wyslaneRazem = 0;
    let odpowiedziRazem = 0;

    if (arkuszWyslane && arkuszWyslane.getLastRow() > 1) {
        const dane = arkuszWyslane.getDataRange().getValues();
        const naglowki = dane[0].map(h => String(h).trim().toLowerCase());
        let colOdp = naglowki.findIndex(h => h.includes('odpowiedź') || h.includes('odpowiedz'));

        wyslaneRazem = dane.length - 1;
        if (colOdp !== -1) {
            for (let i = 1; i < dane.length; i++) {
                if (String(dane[i][colOdp] || '').includes('TAK')) {
                    odpowiedziRazem++;
                }
            }
        }
    }

    const arkuszWspolprace = ss.getSheetByName(ZAKLADKA_WSPOLPRACE);
    let kanaly = { 'Mail': 0, 'Telefon': 0, 'Osobisty kontakt': 0, 'Inny': 0 };
    let potwierdzoneRazem = 0;

    if (arkuszWspolprace && arkuszWspolprace.getLastRow() > 1) {
        const dane = arkuszWspolprace.getDataRange().getValues();
        const naglowki = dane[0].map(h => String(h).trim().toLowerCase());
        let colKanal = naglowki.findIndex(h => h.includes('kanał') || h.includes('sposób') || h.includes('kontakt'));

        for (let i = 1; i < dane.length; i++) {
            const nazwaFirmy = String(dane[i][0] || '').trim();
            if (!nazwaFirmy) continue;
            potwierdzoneRazem++;

            let kanalWartosc = colKanal !== -1 ? String(dane[i][colKanal] || '').trim() : 'Mail';
            if (!kanalWartosc) kanalWartosc = 'Mail';

            const klucz = Object.keys(kanaly).find(k => k.toLowerCase() === kanalWartosc.toLowerCase()) || 'Inny';
            kanaly[klucz] = (kanaly[klucz] || 0) + 1;
        }
    }

    const responseRate = wyslaneRazem > 0 ? ((odpowiedziRazem / wyslaneRazem) * 100).toFixed(1) + '%' : '0%';

    return {
        projekt,
        wyslaneRazem,
        odpowiedziRazem,
        responseRate,
        potwierdzoneRazem,
        kanaly
    };
}

/**
 * Eksport bazy współprac z metrykami w jednym pliku CSV
 * Pobieranie plik bezpośrednio na komputer przez przeglądarkę oraz zapisuje na dysku.
 */
function eksportujWszystkoDoCsv() {
    const ui = SpreadsheetApp.getUi();
    const ss = SpreadsheetApp.getActiveSpreadsheet();

    // Zawsze odświeżamy odpowiedzi przed samym eksportem
    try {
        cicheSprawdzenieOdpowiedzi();
    } catch (e) {
        Logger.log(e.message);
    }

    const stats = obliczMetrykiProjektu();
    const arkusz = ss.getSheetByName(ZAKLADKA_WSPOLPRACE);

    if (!arkusz) {
        ui.alert('Błąd', `Nie znaleziono zakładki '${ZAKLADKA_WSPOLPRACE}'.`, ui.ButtonSet.OK);
        return;
    }

    const dane = arkusz.getDataRange().getValues();
    if (dane.length <= 1) {
        ui.alert('Informacja', 'Brak wpisanych firm w zakładce potwierdzonych współprac.', ui.ButtonSet.OK);
        return;
    }

    // Kolumny: Współprace + kolumny podsumowujące statystyki projektu
    const naglowki = [
        'Nazwa firmy',
        'Kategoria',
        'Projekt',
        'Imię',
        'Nazwisko',
        'Email',
        'Telefon',
        'Status',
        'Komentarz',
        'Sposób nawiązania kontaktu',
        'Statystyka: Wysłane maile',
        'Statystyka: Odpowiedzi mailowe',
        'Statystyka: Response Rate',
        'Statystyka: Współprace z maila',
        'Statystyka: Współprace z telefonu',
        'Statystyka: Współprace osobiście'
    ];

    let csvRows = [];
    csvRows.push(naglowki.map(escapeCsvValue).join(','));

    for (let r = 1; r < dane.length; r++) {
        const row = dane[r];
        const nazwaFirmy = String(row[0] || '').trim();
        let kategoria = String(row[1] || '').trim();
        const projekt = String(row[2] || stats.projekt || '').trim();
        const imie = String(row[3] || '').trim();
        const nazwisko = String(row[4] || '').trim();
        const email = String(row[5] || '').trim();
        const telefon = String(row[6] || '').trim();
        let status = String(row[7] || '').trim();
        const komentarz = String(row[8] || '').trim();
        let kanal = String(row[9] || '').trim();

        if (!nazwaFirmy && !email) continue;
        if (!nazwaFirmy) continue;

        if (!kategoria) kategoria = 'Inna';
        if (!status) status = 'Sukces';
        if (!kanal) kanal = 'Mail';

        const cleanRow = [
            nazwaFirmy,
            kategoria,
            projekt,
            imie,
            nazwisko,
            email,
            telefon,
            status,
            komentarz,
            kanal,
            stats.wyslaneRazem,
            stats.odpowiedziRazem,
            stats.responseRate,
            stats.kanaly['Mail'] || 0,
            stats.kanaly['Telefon'] || 0,
            stats.kanaly['Osobisty kontakt'] || 0
        ];

        csvRows.push(cleanRow.map(escapeCsvValue).join(','));
    }

    // Dodajemy BOM (\uFEFF), aby Excel i programy w Windowsie poprawnie czytały polskie znaki w UTF-8
    const csvContent = '\uFEFF' + csvRows.join('\r\n');
    const timestamp = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyyMMdd_HHmmss');
    const czystaNazwaProjektu = stats.projekt.replace(/[\s\W]+/g, '_');
    const nazwaPliku = `eksport_baza_${czystaNazwaProjektu}_${timestamp}.csv`;

    // Zapisujemy kopię na Dysku Google (jako backup)
    const arkuszPlik = DriveApp.getFileById(ss.getId());
    const foldery = arkuszPlik.getParents();
    let folderDocelowy = foldery.hasNext() ? foldery.next() : DriveApp.getRootFolder();
    const plikDrive = folderDocelowy.createFile(nazwaPliku, csvContent, MimeType.CSV);

    // Zakodowanie treści do Base64, aby przeglądarka mogła pobrać plik bezpośrednio z okna modalnego
    const base64Csv = Utilities.base64Encode(csvContent, Utilities.Charset.UTF_8);

    const htmlOutput = HtmlService.createHtmlOutput(
        `<!DOCTYPE html>
    <html>
      <head>
        <base target="_top">
        <style>
          body { font-family: Arial, sans-serif; padding: 15px; font-size: 13px; color: #333; }
          .btn {
            display: inline-block;
            padding: 10px 16px;
            font-size: 13px;
            font-weight: bold;
            text-decoration: none;
            border-radius: 4px;
            cursor: pointer;
            border: none;
            margin-right: 8px;
            margin-top: 10px;
          }
          .btn-download { background-color: #1a73e8; color: white; }
          .btn-drive { background-color: #f1f3f4; color: #1a73e8; border: 1px solid #dadce0; }
        </style>
      </head>
      <body>
        <p style="color: #2e7d32; font-weight: bold; margin: 0 0 8px 0; font-size: 14px;">
          ✅ Plik CSV został pomyślnie przygotowany!
        </p>
        <p style="margin: 0 0 14px 0; color: #555;">
          Projekt: <b>${stats.projekt}</b><br>
          Zawiera: <b>${csvRows.length - 1}</b> rekordów firm.
        </p>

        <div>
          <!-- Bezpośrednie pobieranie na komputer -->
          <a id="downloadBtn" class="btn btn-download" download="${nazwaPliku}" href="data:text/csv;charset=utf-8;base64,${base64Csv}">
            ⬇️ Pobierz na komputer (.csv)
          </a>

          <!-- Otwarcie kopii zapisanej na Dysku Google -->
          <a class="btn btn-drive" href="${plikDrive.getUrl()}" target="_blank">
            📁 Zobacz na Dysku
          </a>
        </div>

        <script>
          // Automatyczne wywołanie pobierania zaraz po otwarciu okienka
          window.onload = function() {
            setTimeout(function() {
              var btn = document.getElementById('downloadBtn');
              if (btn) btn.click();
            }, 300);
          };
        </script>
      </body>
    </html>`
    ).setWidth(430).setHeight(210);

    ui.showModalDialog(htmlOutput, 'Eksport do Bazy Danych');
}

function escapeCsvValue(val) {
    if (val === null || val === undefined) return '""';
    let str = String(val);
    if (str.includes('"') || str.includes(',') || str.includes('\n') || str.includes('\r')) {
        str = '"' + str.replace(/"/g, '""') + '"';
    }
    return str;
}