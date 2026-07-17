import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt
from streamlit_calendar import calendar
import psycopg2



def pobierz_polaczenie():
    try:
        if st.secrets is not None and "SUPABASE_URL" in st.secrets:
            return psycopg2.connect(st.secrets["SUPABASE_URL"])
    except Exception:
        pass
    return sqlite3.connect('database.db')

def pobierz_firmy(nazwa_do_szukania=None, kategoria_do_szukania=None, projekt_do_szukania=None):
    conn = pobierz_polaczenie()

    query = "SELECT * FROM Firma WHERE 1=1"
    params = []

    if nazwa_do_szukania:
        query += " AND nazwa LIKE ?"
        params.append('%' + nazwa_do_szukania + '%')

    if kategoria_do_szukania and kategoria_do_szukania != "Wszyscy":
            query += " AND kategoria = ?"
            params.append(kategoria_do_szukania)

    if projekt_do_szukania and projekt_do_szukania != "Wszystkie":
        query += " AND id IN (SELECT DISTINCT id_firmy FROM Interakcja WHERE projekt = ?)"
        params.append(projekt_do_szukania)

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def dodaj_firme(nazwa, kategoria):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Firma (nazwa, kategoria) VALUES (?, ?)", (nazwa, kategoria))
    conn.commit()
    conn.close()

def pobierz_historie_interakcji(id_firmy):
    conn = pobierz_polaczenie()
    query = """
    SELECT 
        Interakcja.id,
        Interakcja.data_interakcji AS "Data", 
        Uzytkownik.imie || ' ' || Uzytkownik.nazwisko AS "Uzytkownik",
        Interakcja.status AS "Status", 
        Interakcja.komentarz AS "Komentarz", 
        Interakcja.projekt AS "Projekt",
        Interakcja.sciezka_pliku
    FROM Interakcja
    JOIN Uzytkownik ON Interakcja.id_uzytkownika = Uzytkownik.id
    WHERE Interakcja.id_firmy = ?
    ORDER BY Interakcja.data_interakcji DESC
    """
    df = pd.read_sql_query(query, conn, params=(id_firmy,))
    conn.close()
    return df

def pobierz_uzytkownikow():
    conn = pobierz_polaczenie()
    df = pd.read_sql_query("SELECT id, imie || ' ' || nazwisko AS nazwa FROM Uzytkownik", conn)
    conn.close()
    return df

def dodaj_interakcje(id_firmy, id_uzytkownika, data_int, status, komentarz, projekt, kolejny_kont, sciezka_pliku=None):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    query = """
    INSERT INTO Interakcja (id_firmy, id_uzytkownika, data_interakcji, status, komentarz, projekt, kolejny_kontakt, sciezka_pliku)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor.execute(query, (id_firmy, id_uzytkownika, data_int, status, komentarz, projekt, kolejny_kont, sciezka_pliku))
    conn.commit()
    conn.close()

def pobierz_unikalne_projekty():
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    df = pd.read_sql_query(
        "SELECT DISTINCT projekt FROM Interakcja WHERE projekt IS NOT NULL AND projekt != ''", 
        conn
    )
    conn.close()
    return df['projekt'].tolist()

def pobierz_osoby_kontaktowe(id_firmy):
    conn = pobierz_polaczenie()
    query = """
    SELECT 
        OsobaKontaktowa.imie || ' ' || OsobaKontaktowa.nazwisko AS "Osoba kontaktowa",
        OsobaKontaktowa.email AS "E-mail",
        OsobaKontaktowa.telefon AS "Telefon"
    FROM OsobaKontaktowa
    JOIN FirmaOsobaKontaktowa ON OsobaKontaktowa.id = FirmaOsobaKontaktowa.osoba_id
    WHERE FirmaOsobaKontaktowa.firma_id = ?
    """
    df = pd.read_sql_query(query, conn, params=(id_firmy,))
    conn.close()
    return df

def dodaj_osobe_kontaktowa(id_firmy, imie, nazwisko, email, telefon):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO OsobaKontaktowa (imie, nazwisko, email, telefon) VALUES (?, ?, ?, ?)",
        (imie, nazwisko, email, telefon)
    )
    
    osoba_id = cursor.lastrowid
    
    cursor.execute(
        "INSERT INTO FirmaOsobaKontaktowa (firma_id, osoba_id) VALUES (?, ?)",
        (id_firmy, osoba_id)
    )
    
    conn.commit()
    conn.close()

def znajdz_uzytkownika_po_nazwie(pelne_nazwisko):
    conn = pobierz_polaczenie()
    czysty_wpis = pelne_nazwisko.strip()
    
    # Szukanie w bazie dokładnego dopasowania (Imię + Spacja + Nazwisko)
    query = "SELECT id FROM Uzytkownik WHERE imie || ' ' || nazwisko = ?"
    df = pd.read_sql_query(query, conn, params=(czysty_wpis,))
    conn.close()
    
    if not df.empty:
        return int(df.iloc[0]['id']) 
    return None

def usun_interakcje(id_interakcji):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Interakcja WHERE id = ?", (id_interakcji,))
    conn.commit()
    conn.close()

def usun_firme_i_relacje(id_firmy):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    # Usuń firmę, powiązane osoby kontaktowe i interakcje
    cursor.execute("DELETE FROM Interakcja WHERE id_firmy = ?", (id_firmy,))
    cursor.execute("DELETE FROM FirmaOsobaKontaktowa WHERE firma_id = ?", (id_firmy,))
    cursor.execute("DELETE FROM Firma WHERE id = ?", (id_firmy,))
    conn.commit()
    conn.close()

def pobierz_pilne_follow_upy(id_uzytkownika):
    conn = pobierz_polaczenie()
    query = """
    SELECT 
        Interakcja.id AS "id", 
        Firma.nazwa AS "Firma", 
        Interakcja.kolejny_kontakt AS "Termin", 
        Interakcja.projekt AS "Projekt"
    FROM Interakcja
    JOIN Firma ON Interakcja.id_firmy = Firma.id
    WHERE Interakcja.id_uzytkownika = ? 
      AND Interakcja.kolejny_kontakt IS NOT NULL 
      AND Interakcja.kolejny_kontakt != ''
      AND Interakcja.status = 'W trakcie'
    ORDER BY Interakcja.kolejny_kontakt ASC
    """
    df = pd.read_sql_query(query, conn, params=(id_uzytkownika,))
    conn.close()
    return df

def pobierz_granty(sortowanie_projekt=None):
    conn = pobierz_polaczenie()
    query = 'SELECT id, nazwa AS "Nazwa Grantu", instytucja AS "Instytucja", kwota AS \'Kwota (PLN)\', deadline AS \'Deadline\', status AS \'Status\', projekt AS \'Projekt\', notatki, link FROM Granty'
    if sortowanie_projekt and sortowanie_projekt != "Wszystkie":
        query += " WHERE projekt = ?"
        df = pd.read_sql_query(query, conn, params=(sortowanie_projekt,))
    else:
        query += " ORDER BY deadline ASC"
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def dodaj_grant(nazwa, inst, kwota, ddl, status, proj, notatki, link=None):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Granty (nazwa, instytucja, kwota, deadline, status, projekt, notatki, link) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (nazwa, inst, kwota, ddl, status, proj, notatki, link)
    )
    conn.commit()
    conn.close()

def pobierz_unikalne_projekty_grantow():
    conn = pobierz_polaczenie()
    df = pd.read_sql_query(
        "SELECT DISTINCT projekt FROM Granty WHERE projekt IS NOT NULL AND projekt != ''", 
        conn
    )
    conn.close()
    return df['projekt'].tolist()

def usun_grant(id_grantu):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Granty WHERE id = ?", (id_grantu,))
    conn.commit()
    conn.close()

def aktualizuj_status_interakcji(id_interakcji, nowy_status):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    cursor.execute("UPDATE Interakcja SET status = ? WHERE id = ?", (nowy_status, id_interakcji))
    conn.commit()
    conn.close()

def aktualizuj_grant(id_grantu, nowy_status, nowy_link):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Granty SET status = %s, link = %s WHERE id = %s", 
        (nowy_status, nowy_link, id_grantu)
    )
    conn.commit()
    conn.close()    




# USER INTERFACE
st.title("Baza Kontaktów i Współpracy")


if 'wybrana_firma_id' not in st.session_state:
    st.session_state.wybrana_firma_id = None
if 'wybrana_firma_nazwa' not in st.session_state:
    st.session_state.wybrana_firma_nazwa = None
if 'zalogowany_uzytkownik_id' not in st.session_state:
    st.session_state.zalogowany_uzytkownik_id = None
if 'wybrany_grant_id' not in st.session_state:
    st.session_state.wybrany_grant_id = None
if 'wybrany_grant_nazwa' not in st.session_state:
    st.session_state.wybrany_grant_nazwa = None


# PANEL BOCZNY - LOGOWANIE TEKSTOWE
st.sidebar.title("👤 Twój profil")  
wpisany_user = st.sidebar.text_input(
    "Wpisz swoje Imię i Nazwisko:",
    placeholder="np. Anna Kowalska",
    value=""
)

if wpisany_user:
    # System szuka profilu w tle
    user_id = znajdz_uzytkownika_po_nazwie(wpisany_user)
    
    if user_id:
        st.session_state.zalogowany_uzytkownik_id = user_id
        st.sidebar.success(f"🔓 Zalogowano jako: **{wpisany_user}**")
    else:
        st.session_state.zalogowany_uzytkownik_id = None
        st.sidebar.error("❌ Nie znaleziono takiego użytkownika. Sprawdź pisownię!")
else:
    st.session_state.zalogowany_uzytkownik_id = None
    st.sidebar.info("Wpisz swoje dane, aby odblokować zapisywanie kontaktu.")


tab_firmy, tab_dashboard, tab_granty = st.tabs([
    "🏢 Baza Firm", 
    "📊 Dashboard", 
    "📜 Granty & Dofinansowania"
])



# SZCZEGÓŁY FIRMY (PROFIL)
with tab_firmy:
    # Sekcja Follow-up 
    if st.session_state.zalogowany_uzytkownik_id:
        df_follow = pobierz_pilne_follow_upy(st.session_state.zalogowany_uzytkownik_id)
        if not df_follow.empty:
            st.error("🚨 **Pilne follow-upy na dziś!** Skontaktuj się z firmami i odznacz status:")
            
            # Nagłówki
            f1, f2, f3, f4, f5 = st.columns([3, 2, 2, 1.5, 1.5])
            f1.markdown("**Firma**")
            f2.markdown("**Termin**")
            f3.markdown("**Projekt**")
            f4.markdown("**Sukces**")
            f5.markdown("**Odrzucone**")
            st.divider()
            
            for index, row in df_follow.iterrows():
                col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns([3, 2, 2, 1.5, 1.5])
                col_f1.write(row['Firma'])
                col_f2.write(row['Termin'])
                col_f3.write(row['Projekt'])
                
                # Przycisk: Oznacz jako Sukces
                if col_f4.button("✅", key=f"f_succ_{row['id']}", use_container_width=True):
                    aktualizuj_status_interakcji(int(row['id']), "Sukces")
                    st.toast("Status zaktualizowany na Sukces!")
                    st.rerun()
                    
                # Przycisk: Oznacz jako Odrzucone
                if col_f5.button("❌", key=f"f_fail_{row['id']}", use_container_width=True):
                    aktualizuj_status_interakcji(int(row['id']), "Odrzucone")
                    st.toast("Status zaktualizowany na Odrzucone.")
                    st.rerun()

    if st.session_state.wybrana_firma_id is not None:
        # Przycisk powrotu do listy
        if st.button("⬅️ Powrót do listy firm"):
            st.session_state.wybrana_firma_id = None
            st.session_state.wybrana_firma_nazwa = None
            st.rerun()
            
        st.title(f"Firma: {st.session_state.wybrana_firma_nazwa}")

        st.subheader("📞 Dane kontaktowe")
        df_kontakty = pobierz_osoby_kontaktowe(st.session_state.wybrana_firma_id)

        if not df_kontakty.empty:
            st.dataframe(df_kontakty, use_container_width=True, hide_index=True)
        else:
            st.info("Brak przypisanych osób kontaktowych dla tej firmy.")

        # Formularz dodawania nowego kontaktu do tej firmy
        with st.expander("➕ Dodaj nową osobę kontaktową do tej firmy"):
            with st.form("formularz_nowej_osoby", clear_on_submit=True):
                o_imie = st.text_input("Imię:")
                o_nazwisko = st.text_input("Nazwisko:")
                o_email = st.text_input("E-mail:")
                o_telefon = st.text_input("Telefon:")
                
                submitted_osoba = st.form_submit_button("Zapisz osobę kontaktową")
                
                if submitted_osoba:
                    if o_imie and o_nazwisko: 
                        dodaj_osobe_kontaktowa(
                            id_firmy=st.session_state.wybrana_firma_id,
                            imie=o_imie,
                            nazwisko=o_nazwisko,
                            email=o_email,
                            telefon=o_telefon
                        )
                        st.toast(f"Dodano kontakt: {o_imie} {o_nazwisko}")
                        st.rerun()
                    else:
                        st.error("Imię i nazwisko są wymagane!")
        

        st.subheader("Historia kontaktów")
        df_historia = pobierz_historie_interakcji(st.session_state.wybrana_firma_id)
        
        if not df_historia.empty:
            # Dodaliśmy kolumnę na Pobieranie pliku (h5)
            h1, h2, h3, h4, h5, h6 = st.columns([1.5, 1.5, 1.5, 3.5, 1.5, 1])
            h1.markdown("**Data**")
            h2.markdown("**Użytkownik**")
            h3.markdown("**Status**")
            h4.markdown("**Komentarz**")
            h5.markdown("**Załącznik**")
            h6.markdown("**Akcja**")
            st.divider()
            
            # Iterujemy i wyświetlamy wiersze
            for index, row in df_historia.iterrows():
                c1, c2, c3, c4, c5, c6 = st.columns([1.5, 1.5, 1.5, 3.5, 1.5, 1])
                c1.write(row['Data'])
                c2.write(row['Uzytkownik'])
                c3.write(row['Status'])
                c4.write(row['Komentarz'])
                
                # Przycisk pobierania pliku
                if 'sciezka_pliku' in row and row['sciezka_pliku'] and os.path.exists(row['sciezka_pliku']):
                    with open(row['sciezka_pliku'], "rb") as file:
                        c5.download_button(
                            "📥 Pobierz", 
                            data=file.read(), 
                            file_name=os.path.basename(row['sciezka_pliku']), 
                            key=f"dl_{row['id']}"
                        )
                else:
                    c5.write("_Brak pliku_")
                
                # Przycisk usuwania dla konkretnego wpisu
                if c6.button("🗑️", key=f"del_int_{row['id']}"):
                    # Jeśli plik istnieje fizycznie na dysku, usuwamy go
                    if 'sciezka_pliku' in row and row['sciezka_pliku'] and os.path.exists(row['sciezka_pliku']):
                        try:
                            os.remove(row['sciezka_pliku'])
                        except:
                            pass
                    conn_id = int(row['id'])
                    usun_interakcje(conn_id)
                    st.toast("Notatka usunięta.")
                    st.rerun()
        else:
            st.info("Brak zarejestrowanej historii.")
        
        # 2. Formularz dodawania interakcji
        st.subheader("➕ Dodaj nową interakcję")
        
        if st.session_state.zalogowany_uzytkownik_id is None:
            st.warning("👈 Aby dodać nową interakcję, musisz najpierw zalogować się w panelu bocznym (wpisz swoje Imię i Nazwisko)!")
        else:
            with st.form("formularz_interakcji", clear_on_submit=True):
                st.info(f"Zapisujesz kontakt jako: **{wpisany_user}**")
                
                data_int = st.date_input("Data kontaktu:", value=None)
                status_int = st.selectbox("Status:", ["W trakcie", "Sukces", "Odrzucone"])
                projekt_int = st.text_input("Projekt:")
                komentarz_int = st.text_area("Notatka z rozmowy:")
                kolejny_kont = st.date_input("Kiedy odezwać się kolejny raz? (Opcjonalnie):", value=None)
                wgrany_plik = st.file_uploader("Załącz plik (PDF, DOCX):", type=["pdf", "docx"])

                submitted_interakcja = st.form_submit_button("Zapisz kontakt")
                
                if submitted_interakcja:
                    if data_int and komentarz_int:
                        uzytkownik_id = st.session_state.zalogowany_uzytkownik_id

                        data_int_str = data_int.strftime("%Y-%m-%d") if data_int else None
                        kolejny_kont_str = kolejny_kont.strftime("%Y-%m-%d") if kolejny_kont else None
                        
                        # Obsługa fizycznego zapisu wgranego pliku na serwerze/dysku
                        sciezka_zapisu = None
                        if wgrany_plik is not None:
                            os.makedirs("uploads", exist_ok=True)
                            sciezka_zapisu = os.path.join("uploads", f"{int(datetime.now().timestamp())}_{wgrany_plik.name}")
                            with open(sciezka_zapisu, "wb") as f:
                                f.write(wgrany_plik.getbuffer())
                        
                        dodaj_interakcje(
                            id_firmy=st.session_state.wybrana_firma_id,
                            id_uzytkownika=uzytkownik_id,
                            data_int=data_int_str,
                            status=status_int,
                            komentarz=komentarz_int,
                            projekt=projekt_int,
                            kolejny_kont=kolejny_kont_str,
                            sciezka_pliku=sciezka_zapisu  # Przekazujemy ścieżkę pliku do bazy
                        )

                        st.toast("Interakcja dodana pomyślnie!")
                        st.rerun()
                    else:
                        st.error("Data kontaktu i notatka nie mogą być puste!")
                        

        potwierdzenie = st.checkbox("Zaznacz, aby odblokować usuwanie firmy")
        
        if st.button("🗑️ Całkowicie usuń tę firmę z bazy", type="primary", disabled=not potwierdzenie):
            usun_firme_i_relacje(st.session_state.wybrana_firma_id)
            st.toast(f"Firma {st.session_state.wybrana_firma_nazwa} została trwale usunięta.")
            
            st.session_state.wybrana_firma_id = None
            st.session_state.wybrana_firma_nazwa = None
            st.rerun()    

    # GŁÓWNA LISTA FIRM
    else:
        st.subheader("Wyszukiwarka i filtry firm")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            szukana_fraza = st.text_input("Szukaj po nazwie:")
        with col2:
            wybrana_kat = st.selectbox("Filtruj po kategorii:", ["Wszyscy", "Sponsor", "Barter"])
        with col3:
            lista_projektow = pobierz_unikalne_projekty()
            wybrany_proj = st.selectbox("Filtruj po projekcie:", ["Wszystkie"] + lista_projektow)
        
        df_firmy = pobierz_firmy(
            nazwa_do_szukania=szukana_fraza, 
            kategoria_do_szukania=wybrana_kat, 
            projekt_do_szukania=wybrany_proj
        )

        # PRZYCISK EKSPORTU (Ustawiony zaraz pod filtrami, a nad tabelą)
        csv_dane = df_firmy.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Eksportuj tę listę do Excela (CSV)", 
            data=csv_dane, 
            file_name=f"baza_firm_{datetime.now().strftime('%Y-%m-%d')}.csv", 
            mime="text/csv"
        )

        st.markdown(f"Znaleziono firm: **{len(df_firmy)}**")

        event = st.dataframe(
            df_firmy,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True
        )

        if len(event.selection.rows) > 0:
            indeks_wiersza = event.selection.rows[0]
            st.session_state.wybrana_firma_id = int(df_firmy.iloc[indeks_wiersza]['id'])
            st.session_state.wybrana_firma_nazwa = str(df_firmy.iloc[indeks_wiersza]['nazwa'])
            st.rerun()

        st.subheader("➕ Dodaj nową firmę")
        with st.form("Dodaj firmę", clear_on_submit=True):
            nazwa = st.text_input("Nazwa firmy")
            kategoria = st.selectbox("Kategoria", ["Sponsor", "Barter"])
            submitted = st.form_submit_button("Dodaj firmę")

            if submitted:
                if nazwa:
                    dodaj_firme(nazwa, kategoria)
                    st.toast(f"Firma '{nazwa}' została dodana do bazy danych.")
                    st.rerun()
                else: 
                    st.error("Nazwa firmy nie może być pusta.")


# dashboard
with tab_dashboard:
    st.header("Analiza Kontaktów i Współpracy")
    conn = sqlite3.connect('database.db')
    df_f = pd.read_sql_query("SELECT kategoria FROM Firma", conn)
    df_i = pd.read_sql_query("SELECT status, projekt FROM Interakcja", conn)
    conn.close()
    
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Wszystkie firmy w bazie", len(df_f))
    kpi2.metric("Pozyskane współprace", len(df_i[df_i['status'] == 'Sukces']))
    kpi3.metric("Interakcje", len(df_i))
    
    st.divider()
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("🏢 Podział firm ze względu na kategorię")
        if not df_f.empty:
            kat_counts = df_f['kategoria'].value_counts()
            
            # Tworzymy wykres kołowy za pomocą matplotlib
            fig, ax = plt.subplots(figsize=(6, 6))
            # Ustawiamy ciemny motyw wykresu, żeby pasował do Streamlita, albo definiujemy kolory
            colors = ['#4F46E5', '#10B981'] if len(kat_counts) <= 2 else None
            
            ax.pie(
                kat_counts, 
                labels=kat_counts.index, 
                autopct='%1.1f%%', 
                startangle=90, 
                colors=colors,
                textprops={'fontsize': 14, 'color': 'white' if st.get_option("theme.base") == "dark" else "black"}
            )
            # Przezroczyste tło wykresu, żeby idealnie wtapiał się w interfejs
            fig.patch.set_alpha(0.0)
            ax.patch.set_alpha(0.0)
            
            st.pyplot(fig)
            
    with col_chart2:
        st.subheader("📈 Efektywność kontaktu")
        if not df_i.empty: 
            st.bar_chart(df_i['status'].value_counts())



# granty i dofinansowania
with tab_granty:
    # Pobieramy pełną bazę grantów bez filtrów, aby zasilić kalendarz
    df_wszystkie_granty = pobierz_granty(sortowanie_projekt="Wszystkie")
    
    # 1. SEKCJA: KALENDARZ TERMINÓW (DEADLINES)
    st.subheader("📅 Harmonogram składania wniosków")
    
    if not df_wszystkie_granty.empty:
        # Przygotowanie wydarzeń (events) w formacie akceptowanym przez streamlit-calendar
        events = []
        
        # Słownik kolorów dla poszczególnych statusów
        kolory_statusow = {
            "W przygotowaniu": "#FFA500",  # Pomarańczowy
            "Złożony": "#3498DB",          # Niebieski
            "Zaakceptowany": "#2ECC71",    # Zielony
            "Odrzucony": "#E74C3C"         # Czerwony
        }
        
        for _, row in df_wszystkie_granty.iterrows():
            if row['Deadline']:  # Upewniamy się, że data istnieje
                status_grantu = row['Status']
                kolor = kolory_statusow.get(status_grantu, "#95A5A6") # Domyślny szary
                
                events.append({
                    "title": f"⏱️ [{row['Projekt']}] {row['Nazwa Grantu']}",
                    "start": row['Deadline'],
                    "end": row['Deadline'],
                    "backgroundColor": kolor,
                    "borderColor": kolor,
                    "allDay": True
                })
        
        # Konfiguracja opcji FullCalendar
        calendar_options = {
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek"
            },
            "initialView": "dayGridMonth",
            "locale": "pl", # Polski język kalendarza
            "firstDay": 1   # Poniedziałek jako pierwszy dzień tygodnia
        }
        
        # Renderowanie kalendarza
        calendar(events=events, options=calendar_options, key="granty_calendar")
        
        # Mała legenda pod kalendarzem
        st.markdown(
            "<div style='display: flex; gap: 15px; font-size: 0.85rem; justify-content: center; margin-top: -10px;'>"
            "<span>🟠 W przygotowaniu</span>"
            "<span>🔵 Złożony</span>"
            "<span>🟢 Zaakceptowany</span>"
            "<span>🔴 Odrzucony</span>"
            "</div>", 
            unsafe_allow_html=True
        )
    else:
        st.info("Brak grantów z przypisanymi terminami do wyświetlenia w kalendarzu.")
        
    st.markdown("---")
    
# 2. SEKCJA: WYSZUKIWARKA, FILTRY, LISTA I EDYCJA
    st.subheader("🔍 Zarządzanie wnioskami")
    
    # ------------------------------------------
    # WIDOK A: SZCZEGÓŁY I EDYCJA WYBRANEGO GRANTU
    # ------------------------------------------
    if st.session_state.wybrany_grant_id is not None:
        # Przycisk powrotu do listy grantów
        if st.button("⬅️ Powrót do listy grantów", key="back_to_grants"):
            st.session_state.wybrany_grant_id = None
            st.session_state.wybrany_grant_nazwa = None
            st.rerun()
            
        # Pobieramy dane tego konkretnego grantu z aktualnego widoku
        # (Wyszukujemy go po ID w pobranej bazie)
        df_szczegoly = df_wszystkie_granty[df_wszystkie_granty['id'] == st.session_state.wybrany_grant_id]
        
        if not df_szczegoly.empty:
            grant_data = df_szczegoly.iloc[0]
            
            st.markdown(f"## 📜 Grant: {grant_data['Nazwa Grantu']}")
            st.markdown(f"**Projekt BEST:** `{grant_data['Projekt']}` | **Instytucja:** *{grant_data['Instytucja']}*")
            st.markdown(f"**Kwota:** `{grant_data['Kwota (PLN)']} PLN` | **Deadline (DDL):** `{grant_data['Deadline']}`")
            
            # Przycisk z linkiem
            if grant_data['link']:
                st.link_button("🔗 Otwórz wniosek / dokumentację", grant_data['link'], type="secondary")
            else:
                st.caption("ℹ️ Brak przypisanego linku do tego wniosku.")
                
            st.info(f"**Dodatkowe notatki:**\n\n{grant_data['notatki'] if grant_data['notatki'] else '_Brak dodatkowych uwag._'}")
            
            # Formularz edycji wybranego grantu
            with st.expander("⚙️ Edytuj status, link lub usuń ten grant"):
                with st.form(key=f"edit_single_grant_form"):
                    col_ed1, col_ed2 = st.columns(2)
                    with col_ed1:
                        lista_statusow = ["W przygotowaniu", "Złożony", "Zaakceptowany", "Odrzucony"]
                        idx_statusu = lista_statusow.index(grant_data['Status']) if grant_data['Status'] in lista_statusow else 0
                        edytowany_status = st.selectbox("Zmień status:", lista_statusow, index=idx_statusu)
                    with col_ed2:
                        edytowany_link = st.text_input("Edytuj link URL:", value=grant_data['link'] if grant_data['link'] else "")
                        
                    btn_save, btn_del = st.columns([8, 2])
                    if btn_save.form_submit_button("💾 Zapisz zmiany", use_container_width=True):
                        aktualizuj_grant(st.session_state.wybrany_grant_id, edytowany_status, edytowany_link)
                        st.toast("Zmiany zostały zapisane!")
                        st.rerun()
                        
                    if btn_del.form_submit_button("🗑️ Trwale usuń grant", type="primary", use_container_width=True):
                        usun_grant(st.session_state.wybrany_grant_id)
                        st.session_state.wybrany_grant_id = None
                        st.session_state.wybrany_grant_nazwa = None
                        st.toast("Wniosek został pomyślnie usunięty.")
                        st.rerun()

    # ------------------------------------------
    # WIDOK B: LISTA WSZYSTKICH GRANTÓW (TABELA)
    # ------------------------------------------
    else:
        c_fil1, c_fil2 = st.columns(2)
        
        with c_fil1:
            lista_proj_grantow = pobierz_unikalne_projekty_grantow()
            wybrany_proj_grant = st.selectbox(
                "Filtruj po projekcie BEST:", 
                ["Wszystkie"] + lista_proj_grantow, 
                key="filter_grant_proj"
            )
            
        with c_fil2:
            kryterium_sortowania = st.selectbox(
                "Sortuj wyniki po:",
                ["Najbliższy termin (Deadline)", "Statusie (Alfabetycznie)"],
                key="sort_grant_criteria"
            )
            
        # Pobieramy dane z bazy uwzględniając filtr projektu
        df_granty_widok = pobierz_granty(sortowanie_projekt=wybrany_proj_grant)
        
        # Logika sortowania w pamięci
        if not df_granty_widok.empty:
            if kryterium_sortowania == "Najbliższy termin (Deadline)":
                df_granty_widok = df_granty_widok.sort_values(by="Deadline", ascending=True)
            elif kryterium_sortowania == "Statusie (Alfabetycznie)":
                df_granty_widok = df_granty_widok.sort_values(by="Status", ascending=True)

        if not df_granty_widok.empty:
            st.markdown(f"Znaleziono wniosków: **{len(df_granty_widok)}** (Kliknij wiersz, aby zobaczyć szczegóły i edytować)")
            
            # Renderujemy interaktywną tabelę z wyborem jednego wiersza!
            event_grant = st.dataframe(
                df_granty_widok, 
                use_container_width=True, 
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_order=["Nazwa Grantu", "Instytucja", "Kwota (PLN)", "Deadline", "Status", "Projekt"],
                key="granty_table"
            )
            
            # Reakcja na kliknięcie wiersza w tabeli grantów
            if len(event_grant.selection.rows) > 0:
                indeks_wiersza_g = event_grant.selection.rows[0]
                st.session_state.wybrany_grant_id = int(df_granty_widok.iloc[indeks_wiersza_g]['id'])
                st.session_state.wybrany_grant_nazwa = str(df_granty_widok.iloc[indeks_wiersza_g]['Nazwa Grantu'])
                st.rerun()
        else:
            st.info("Brak wniosków spełniających kryteria wyszukiwania.")

        st.markdown("---")
        
        # Formularz dodawania wyświetla się tylko w widoku listy głównej (porządek na ekranie szczegółów!)
        st.subheader("➕ Dodaj nowy wniosek grantowy / dofinansowanie")
        with st.form("formularz_nowego_grantu", clear_on_submit=True):
            g_nazwa = st.text_input("Nazwa Grantu / Programu:")
            g_instytucja = st.text_input("Instytucja przyznająca (np. Urząd Miasta):")
            
            col_form1, col_form2, col_form3 = st.columns(3)
            with col_form1:
                g_kwota = st.number_input("Wnioskowana kwota (PLN):", min_value=0.0, step=500.0, value=0.0)
            with col_form2:
                g_deadline = st.date_input("Termin złożenia (Deadline):", value=datetime.today())
            with col_form3:
                g_status = st.selectbox("Status początkowy:", ["W przygotowaniu", "Złożony", "Zaakceptowany", "Odrzucony"])
                
            g_projekt = st.text_input("Projekt BEST Łódź (np. EBEC, Żongler):")
            g_notatki = st.text_area("Dodatkowe uwagi (np. wymagane załączniki, kryteria):")
            g_link = st.text_input("Link do dokumentacji (opcjonalnie):", placeholder="https://...")
            
            submit_grant = st.form_submit_button("Zapisz wniosek grantowy")
            
            if submit_grant:
                if g_nazwa and g_instytucja and g_projekt:
                    g_deadline_str = g_deadline.strftime("%Y-%m-%d")
                    dodaj_grant(
                        nazwa=g_nazwa,
                        inst=g_instytucja,
                        kwota=g_kwota,
                        ddl=g_deadline_str,
                        status=g_status,
                        proj=g_projekt,
                        notatki=g_notatki,
                        link=g_link
                    )
                    st.toast(f"Pomyślnie zarejestrowano wniosek: {g_nazwa}")
                    st.rerun()
                else:
                    st.error("Nazwa, instytucja oraz projekt są polami wymaganymi!")
    