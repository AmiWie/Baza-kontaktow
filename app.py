import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt
from streamlit_calendar import calendar
import psycopg2

# ==========================================
# 🔒 BLOKADA BEZPIECZEŃSTWA (GOOGLE AUTH)
# ==========================================
if not st.user.is_logged_in:
    st.set_page_config(page_title="Logowanie | Baza Kontaktów BEST", page_icon="🔒")
    st.title("🔒 Baza Kontaktów i Współpracy BEST")
    st.write("Dostęp do systemu mają wyłącznie uprawnieni członkowie organizacji.")
    st.info("Zaloguj się swoim kontem Google Workspace, aby odblokować dostęp.")
    
    if st.button("🔑 Zaloguj się przez Google Workspace", type="primary"):
        st.login()
        
    st.stop()  # Zatrzymuje wykonywanie reszty kodu dla niezalogowanych!


# ==========================================
# FUNKCJE DO OBSŁUGI BAZY DANYCH
# ==========================================

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
        query += " AND nazwa LIKE %s"
        params.append('%' + nazwa_do_szukania + '%')

    if kategoria_do_szukania and kategoria_do_szukania != "Wszyscy":
        query += " AND kategoria = %s"
        params.append(kategoria_do_szukania)

    if projekt_do_szukania and projekt_do_szukania != "Wszystkie":
        query += " AND id IN (SELECT DISTINCT id_firmy FROM Interakcja WHERE projekt = %s)"
        params.append(projekt_do_szukania)

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def dodaj_firme(nazwa, kategoria):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Firma (nazwa, kategoria) VALUES (%s, %s) RETURNING id", (nazwa, kategoria))
    nowa_firma_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return nowa_firma_id

def pobierz_historie_interakcji(id_firmy):
    conn = pobierz_polaczenie()
    query = """
    SELECT 
        Interakcja.id,
        Interakcja.data_interakcji AS "Data", 
        CONCAT(Uzytkownik.imie, ' ', Uzytkownik.nazwisko) AS "Uzytkownik",
        Interakcja.status AS "Status", 
        Interakcja.komentarz AS "Komentarz", 
        Interakcja.projekt AS "Projekt",
        Interakcja.sciezka_pliku
    FROM Interakcja
    JOIN Uzytkownik ON Interakcja.id_uzytkownika = Uzytkownik.id
    WHERE Interakcja.id_firmy = %s
    ORDER BY Interakcja.data_interakcji DESC
    """
    df = pd.read_sql_query(query, conn, params=(id_firmy,))
    conn.close()
    return df

def pobierz_uzytkownikow():
    conn = pobierz_polaczenie()
    df = pd.read_sql_query("SELECT id, CONCAT(imie, ' ', nazwisko) AS nazwa FROM Uzytkownik", conn)
    conn.close()
    return df

def dodaj_interakcje(id_firmy, id_uzytkownika, data_int, status, komentarz, projekt, kolejny_kont, sciezka_pliku=None):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    query = """
    INSERT INTO Interakcja (id_firmy, id_uzytkownika, data_interakcji, status, komentarz, projekt, kolejny_kontakt, sciezka_pliku)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (id_firmy, id_uzytkownika, data_int, status, komentarz, projekt, kolejny_kont, sciezka_pliku))
    conn.commit()
    conn.close()

def pobierz_unikalne_projekty():
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    df = pd.read_sql_query(
        "SELECT DISTINCT projekt FROM Interakcja WHERE projekt IS NOT NULL", 
        conn
    )
    conn.close()
    return df['projekt'].tolist()

def pobierz_osoby_kontaktowe(id_firmy):
    conn = pobierz_polaczenie()
    query = """
    SELECT 
        CONCAT(OsobaKontaktowa.imie, ' ', OsobaKontaktowa.nazwisko) AS "Osoba kontaktowa",
        OsobaKontaktowa.email AS "E-mail",
        OsobaKontaktowa.telefon AS "Telefon"
    FROM OsobaKontaktowa
    JOIN FirmaOsobaKontaktowa ON OsobaKontaktowa.id = FirmaOsobaKontaktowa.osoba_id
    WHERE FirmaOsobaKontaktowa.firma_id = %s
    """
    df = pd.read_sql_query(query, conn, params=(id_firmy,))
    conn.close()
    return df

def dodaj_osobe_kontaktowa(id_firmy, imie, nazwisko, email, telefon):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO OsobaKontaktowa (imie, nazwisko, email, telefon) VALUES (%s, %s, %s, %s) RETURNING id",
        (imie, nazwisko, email, telefon)
    )
    osoba_id = cursor.fetchone()[0]
    
    cursor.execute(
        "INSERT INTO FirmaOsobaKontaktowa (firma_id, osoba_id) VALUES (%s, %s)", 
        (id_firmy, osoba_id)
    )
    
    conn.commit()
    conn.close()

def dopasuj_lub_stworz_uzytkownika(imie_nazwisko_lub_email):
    """Szuka użytkownika po imieniu/nazwisku lub emailu w bazie."""
    conn = pobierz_polaczenie()
    czysty_wpis = (imie_nazwisko_lub_email or "").strip()
    
    query = """
    SELECT id, CONCAT(imie, ' ', nazwisko) AS pelna_nazwa 
    FROM Uzytkownik 
    WHERE CONCAT(imie, ' ', nazwisko) ILIKE %s OR email ILIKE %s
    """
    try:
        df = pd.read_sql_query(query, conn, params=(czysty_wpis, czysty_wpis))
    except Exception:
        # Fallback jeśli tabela Uzytkownik nie ma jeszcze kolumny email
        query_fallback = "SELECT id, CONCAT(imie, ' ', nazwisko) AS pelna_nazwa FROM Uzytkownik WHERE CONCAT(imie, ' ', nazwisko) ILIKE %s"
        df = pd.read_sql_query(query_fallback, conn, params=(czysty_wpis,))
        
    conn.close()
    
    if not df.empty:
        return int(df.iloc[0]['id']), df.iloc[0]['pelna_nazwa']
    return None, czysty_wpis

def usun_interakcje(id_interakcji):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Interakcja WHERE id = %s", (id_interakcji,))
    conn.commit()
    conn.close()

def usun_firme_i_relacje(id_firmy):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Interakcja WHERE id_firmy = %s", (id_firmy,))
    cursor.execute("DELETE FROM FirmaOsobaKontaktowa WHERE firma_id = %s", (id_firmy,))
    cursor.execute("DELETE FROM Firma WHERE id = %s", (id_firmy,))
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
    WHERE Interakcja.id_uzytkownika = %s 
      AND Interakcja.kolejny_kontakt IS NOT NULL 
      AND Interakcja.status = 'W trakcie'
    ORDER BY Interakcja.kolejny_kontakt ASC
    """
    df = pd.read_sql_query(query, conn, params=(id_uzytkownika,))
    conn.close()
    return df

def pobierz_granty(sortowanie_projekt=None):
    conn = pobierz_polaczenie()
    query = 'SELECT id, nazwa AS "Nazwa Grantu", instytucja AS "Instytucja", kwota AS "Kwota (PLN)", deadline AS "Deadline", status AS "Status", projekt AS "Projekt", notatki, link FROM Granty'
    if sortowanie_projekt and sortowanie_projekt != "Wszystkie":
        query += " WHERE projekt = %s"
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
        "INSERT INTO Granty (nazwa, instytucja, kwota, deadline, status, projekt, notatki, link) " \
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (nazwa, inst, kwota, ddl, status, proj, notatki, link)
    )
    conn.commit()
    conn.close()

def pobierz_unikalne_projekty_grantow():
    conn = pobierz_polaczenie()
    df = pd.read_sql_query(
        "SELECT DISTINCT projekt FROM Granty WHERE projekt IS NOT NULL", 
        conn
    )
    conn.close()
    return df['projekt'].tolist()

def usun_grant(id_grantu):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Granty WHERE id = %s", (id_grantu,))
    conn.commit()
    conn.close()

def aktualizuj_status_interakcji(id_interakcji, nowy_status):
    conn = pobierz_polaczenie()
    cursor = conn.cursor()
    cursor.execute("UPDATE Interakcja SET status = %s WHERE id = %s", (nowy_status, id_interakcji))
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


# ==========================================
# INTERFEJS I STAN SESJI ZALOGOWANEGO
# ==========================================

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

# Dane zalogowanego użytkownika odczytane wprost z konta Google Workspace
user_email = st.user.email
user_name = st.user.name or user_email

# Próba powiązania konta Google z rekordem w tabeli Uzytkownik w Supabase
db_user_id, display_name = dopasuj_lub_stworz_uzytkownika(user_name)
if not db_user_id:
    db_user_id, display_name = dopasuj_lub_stworz_uzytkownika(user_email)

st.session_state.zalogowany_uzytkownik_id = db_user_id

# Pasek boczny z profilem i przyciskiem wylogowania
st.sidebar.title("👤 Twój profil")
st.sidebar.write(f"Zalogowano: **{user_name}**")
st.sidebar.caption(f"E-mail: `{user_email}`")

if db_user_id:
    st.sidebar.success(f"🔓 Baza powiązana (ID: {db_user_id})")
else:
    st.sidebar.warning("⚠️ Twój profil nie figuruje jeszcze w tabeli `Uzytkownik`. Dodaj wiersz z tym mailem/nazwiskiem w Supabase.")

if st.sidebar.button("🚪 Wyloguj się"):
    st.logout()

tab_firmy, tab_dashboard, tab_granty = st.tabs([
    "🏢 Baza Firm", 
    "📊 Dashboard", 
    "📜 Granty & Dofinansowania"
])


# ==========================================
# ZAKŁADKA 1: BAZA FIRM
# ==========================================
with tab_firmy:
    if st.session_state.zalogowany_uzytkownik_id:
        df_follow = pobierz_pilne_follow_upy(st.session_state.zalogowany_uzytkownik_id)
        if not df_follow.empty:
            st.error("🚨 **Pilne follow-upy na dziś!** Skontaktuj się z firmami i odznacz status:")
            
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
                
                if col_f4.button("✅", key=f"f_succ_{row['id']}", use_container_width=True):
                    aktualizuj_status_interakcji(int(row['id']), "Sukces")
                    st.toast("Status zaktualizowany na Sukces!")
                    st.rerun()
                    
                if col_f5.button("❌", key=f"f_fail_{row['id']}", use_container_width=True):
                    aktualizuj_status_interakcji(int(row['id']), "Odrzucone")
                    st.toast("Status zaktualizowany na Odrzucone.")
                    st.rerun()

    if st.session_state.wybrana_firma_id is not None:
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
            h1, h2, h3, h4, h5, h6 = st.columns([1.5, 1.5, 1.5, 3.5, 1.5, 1])
            h1.markdown("**Data**")
            h2.markdown("**Użytkownik**")
            h3.markdown("**Status**")
            h4.markdown("**Komentarz**")
            h5.markdown("**Załącznik**")
            h6.markdown("**Akcja**")
            st.divider()
            
            for index, row in df_historia.iterrows():
                c1, c2, c3, c4, c5, c6 = st.columns([1.5, 1.5, 1.5, 3.5, 1.5, 1])
                c1.write(row['Data'])
                c2.write(row['Uzytkownik'])
                c3.write(row['Status'])
                c4.write(row['Komentarz'])
                
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
                
                if c6.button("🗑️", key=f"del_int_{row['id']}"):
                    if 'sciezka_pliku' in row and row['sciezka_pliku'] and os.path.exists(row['sciezka_pliku']):
                        try:
                            os.remove(row['sciezka_pliku'])
                        except:
                            pass
                    usun_interakcje(int(row['id']))
                    st.toast("Notatka usunięta.")
                    st.rerun()
        else:
            st.info("Brak zarejestrowanej historii.")
        
        st.subheader("➕ Dodaj nową interakcję")
        
        if st.session_state.zalogowany_uzytkownik_id is None:
            st.warning("👈 Twoje konto Google nie zostało jeszcze połączone z ID użytkownika w bazie. Poproś administratora o dopisanie Twoich danych.")
        else:
            with st.form("formularz_interakcji", clear_on_submit=True):
                st.info(f"Zapisujesz kontakt jako: **{user_name}**")
                
                data_int = st.date_input("Data kontaktu:", value=None)
                status_int = st.selectbox("Status:", ["W trakcie", "Sukces", "Odrzucone"])
                projekt_int = st.text_input("Projekt:")
                komentarz_int = st.text_area("Notatka z rozmowy:")
                kolejny_kont = st.date_input("Kiedy odezwać się kolejny raz? (Opcjonalnie):", value=None)
                wgrany_plik = st.file_uploader("Załącz plik (PDF, DOCX):", type=["pdf", "docx"])

                submitted_interakcja = st.form_submit_button("Zapisz kontakt")
                
                if submitted_interakcja:
                    if data_int and komentarz_int:
                        data_int_str = data_int.strftime("%Y-%m-%d") if data_int else None
                        kolejny_kont_str = kolejny_kont.strftime("%Y-%m-%d") if kolejny_kont else None
                        
                        sciezka_zapisu = None
                        if wgrany_plik is not None:
                            os.makedirs("uploads", exist_ok=True)
                            sciezka_zapisu = os.path.join("uploads", f"{int(datetime.now().timestamp())}_{wgrany_plik.name}")
                            with open(sciezka_zapisu, "wb") as f:
                                f.write(wgrany_plik.getbuffer())
                        
                        dodaj_interakcje(
                            id_firmy=st.session_state.wybrana_firma_id,
                            id_uzytkownika=st.session_state.zalogowany_uzytkownik_id,
                            data_int=data_int_str,
                            status=status_int,
                            komentarz=komentarz_int,
                            projekt=projekt_int,
                            kolejny_kont=kolejny_kont_str,
                            sciezka_pliku=sciezka_zapisu
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

        st.divider()
        st.subheader("➕ Dodaj nową firmę i kontakt")

        with st.form("formularz_nowej_firmy_i_kontaktu", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                f_nazwa = st.text_input("Nazwa firmy *")
            with col_f2:
                f_kategoria = st.selectbox("Kategoria *", ["Sponsor", "Barter", "Inna"])
                
            st.markdown("---")
            st.caption("👤 Dane osoby kontaktowej (Opcjonalnie – możesz zostawić puste)")
            
            col_o1, col_o2 = st.columns(2)
            with col_o1:
                o_imie = st.text_input("Imię:")
                o_email = st.text_input("E-mail:")
            with col_o2:
                o_nazwisko = st.text_input("Nazwisko:")
                o_telefon = st.text_input("Telefon:")
                
            submitted_all = st.form_submit_button("Zapisz firmę i kontakt")
            
            if submitted_all:
                if f_nazwa:
                    nowe_id_firmy = dodaj_firme(f_nazwa, f_kategoria)
                    komunikat = f"Pomyślnie dodano firmę: {f_nazwa}"

                    if o_imie:
                        dodaj_osobe_kontaktowa(
                            id_firmy=nowe_id_firmy,
                            imie=o_imie,
                            nazwisko=o_nazwisko,
                            email=o_email,
                            telefon=o_telefon
                        )
                        komunikat += f" wraz z kontaktem: {o_imie} {o_nazwisko}"
                    
                    st.success(komunikat)
                    st.rerun()
                else:
                    st.error("Nazwa firmy jest wymagana!")


# ==========================================
# ZAKŁADKA 2: DASHBOARD
# ==========================================
with tab_dashboard:
    st.header("Analiza Kontaktów i Współpracy")
    conn = pobierz_polaczenie()
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
            
            fig, ax = plt.subplots(figsize=(6, 6))
            colors = ['#4F46E5', '#10B981'] if len(kat_counts) <= 2 else None
            
            ax.pie(
                kat_counts, 
                labels=kat_counts.index, 
                autopct='%1.1f%%', 
                startangle=90, 
                colors=colors,
                textprops={'fontsize': 14, 'color': 'white' if st.get_option("theme.base") == "dark" else "black"}
            )
            fig.patch.set_alpha(0.0)
            ax.patch.set_alpha(0.0)
            
            st.pyplot(fig)
            
    with col_chart2:
        st.subheader("📈 Efektywność kontaktu")
        if not df_i.empty: 
            st.bar_chart(df_i['status'].value_counts())


# ==========================================
# ZAKŁADKA 3: GRANTY I DOFINANSOWANIA
# ==========================================
with tab_granty:
    df_wszystkie_granty = pobierz_granty(sortowanie_projekt="Wszystkie")
    
    st.subheader("📅 Harmonogram składania wniosków")
    
    if not df_wszystkie_granty.empty:
        events = []
        
        kolory_statusow = {
            "W przygotowaniu": "#FFA500",
            "Złożony": "#3498DB",
            "Zaakceptowany": "#2ECC71",
            "Odrzucony": "#E74C3C"
        }
        
        for _, row in df_wszystkie_granty.iterrows():
            if row['Deadline']:  
                status_grantu = row['Status']
                kolor = kolory_statusow.get(status_grantu, "#95A5A6")
                
                events.append({
                    "title": f"⏱️ [{row['Projekt']}] {row['Nazwa Grantu']}",
                    "start": row['Deadline'],
                    "end": row['Deadline'],
                    "backgroundColor": kolor,
                    "borderColor": kolor,
                    "allDay": True
                })
        
        calendar_options = {
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek"
            },
            "initialView": "dayGridMonth",
            "locale": "pl",
            "firstDay": 1
        }
        
        calendar(events=events, options=calendar_options, key="granty_calendar")
        
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
    
    st.subheader("🔍 Zarządzanie wnioskami")
    
    if st.session_state.wybrany_grant_id is not None:
        if st.button("⬅️ Powrót do listy grantów", key="back_to_grants"):
            st.session_state.wybrany_grant_id = None
            st.session_state.wybrany_grant_nazwa = None
            st.rerun()
            
        df_szczegoly = df_wszystkie_granty[df_wszystkie_granty['id'] == st.session_state.wybrany_grant_id]
        
        if not df_szczegoly.empty:
            grant_data = df_szczegoly.iloc[0]
            
            st.markdown(f"## 📜 Grant: {grant_data['Nazwa Grantu']}")
            st.markdown(f"**Projekt:** `{grant_data['Projekt']}` | **Instytucja:** *{grant_data['Instytucja']}*")
            st.markdown(f"**Kwota:** `{grant_data['Kwota (PLN)']} PLN` | **Deadline (DDL):** `{grant_data['Deadline']}`")
            
            if grant_data['link']:
                st.link_button("🔗 Otwórz wniosek / dokumentację", grant_data['link'], type="secondary")
            else:
                st.caption("ℹ️ Brak przypisanego linku do tego wniosku.")
                
            st.info(f"**Dodatkowe notatki:**\n\n{grant_data['notatki'] if grant_data['notatki'] else '_Brak dodatkowych uwag._'}")
            
            with st.expander("⚙️ Edytuj status, link lub usuń ten grant"):
                with st.form(key="edit_single_grant_form"):
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

    else:
        c_fil1, c_fil2 = st.columns(2)
        
        with c_fil1:
            lista_proj_grantow = pobierz_unikalne_projekty_grantow()
            wybrany_proj_grant = st.selectbox(
                "Filtruj po projekcie:", 
                ["Wszystkie"] + lista_proj_grantow, 
                key="filter_grant_proj"
            )
            
        with c_fil2:
            kryterium_sortowania = st.selectbox(
                "Sortuj wyniki po:",
                ["Najbliższy termin (Deadline)", "Statusie (Alfabetycznie)"],
                key="sort_grant_criteria"
            )
            
        df_granty_widok = pobierz_granty(sortowanie_projekt=wybrany_proj_grant)
        
        if not df_granty_widok.empty:
            if kryterium_sortowania == "Najbliższy termin (Deadline)":
                df_granty_widok = df_granty_widok.sort_values(by="Deadline", ascending=True)
            elif kryterium_sortowania == "Statusie (Alfabetycznie)":
                df_granty_widok = df_granty_widok.sort_values(by="Status", ascending=True)

        if not df_granty_widok.empty:
            st.markdown(f"Znaleziono wniosków: **{len(df_granty_widok)}** (Kliknij wiersz, aby zobaczyć szczegóły i edytować)")
            
            event_grant = st.dataframe(
                df_granty_widok, 
                use_container_width=True, 
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_order=["Nazwa Grantu", "Instytucja", "Kwota (PLN)", "Deadline", "Status", "Projekt"],
                key="granty_table"
            )
            
            if len(event_grant.selection.rows) > 0:
                indeks_wiersza_g = event_grant.selection.rows[0]
                st.session_state.wybrany_grant_id = int(df_granty_widok.iloc[indeks_wiersza_g]['id'])
                st.session_state.wybrany_grant_nazwa = str(df_granty_widok.iloc[indeks_wiersza_g]['Nazwa Grantu'])
                st.rerun()
        else:
            st.info("Brak wniosków spełniających kryteria wyszukiwania.")

        st.markdown("---")
        
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
                
            g_projekt = st.text_input("Projekt:")
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