# ten plik generuje fikcyjne dane do bazy danych SQLite dla tabel: 
# Firma, Uzytkownik, OsobaKontaktowa, Interakcja i Granty

import sqlite3
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker('pl_PL')

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

for i in range(10): 
    firma = fake.company()
    kategoria = random.choice(['Sponsor', 'Barter'])
    cursor.execute("INSERT INTO Firma (nazwa, kategoria) VALUES (?, ?)", (firma, kategoria))

for i in range(5):
    imie = fake.first_name()
    nazwisko = fake.last_name()
    email = f"{imie.lower()}.{nazwisko.lower()}@example.com"
    cursor.execute("INSERT INTO Uzytkownik (imie, nazwisko, email) VALUES (?, ?, ?)", (imie, nazwisko, email))

for i in range(15):
    imie = fake.first_name()
    nazwisko = fake.last_name()
    email = f"{imie.lower()}.{nazwisko.lower()}@example.com"
    telefon = fake.phone_number()
    cursor.execute("INSERT INTO OsobaKontaktowa (imie, nazwisko, email, telefon) VALUES (?, ?, ?, ?)", (imie, nazwisko, email, telefon))

    osoba_id = cursor.lastrowid
    firma_id = random.randint(1, 10)
    cursor.execute("INSERT INTO FirmaOsobaKontaktowa (osoba_id, firma_id) VALUES (?, ?)", (osoba_id, firma_id))

for i in range(20):
    id_firmy = random.randint(1, 10)
    id_uzytkownika = random.randint(1, 5)
    id_osoby_kontaktowej = random.randint(1, 15)
    data_interakcji = fake.date_time_this_year()
    status = random.choice(['Sukces', 'W trakcie', 'Odrzucone'])
    komentarz = fake.sentence()
    projekt = random.choice(['Projekt A', 'Projekt B', 'Projekt C'])
    kolejny_kontakt = fake.date_time_this_year(after_now=True)
    cursor.execute("INSERT INTO Interakcja (id_firmy, id_uzytkownika, id_osoby_kontaktowej, data_interakcji, status, komentarz, projekt, kolejny_kontakt) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (id_firmy, id_uzytkownika, id_osoby_kontaktowej, data_interakcji, status, komentarz, projekt, kolejny_kontakt))

conn.commit()
conn.close() 

def generuj_dane_testowe_grantow(liczba_grantow=12):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    instytucje = [
        "Urząd Miasta Łodzi (Wydział Edukacji)",
        "Urząd Marszałkowski Województwa Łódzkiego",
        "Ministerstwo Nauki i Wyższego Szkolnictwa",
        "Narodowe Centrum Badań i Rozwoju (NCBR)",
        "Fundacja Rozwoju Systemu Edukacji (FRSE)",
        "Łódzkie Centrum Wydarzeń"
    ]
    
    projekty_best = ["Targi Pracy", "Żongler", "Kurs Inżynierski", "EBEC", "Rekrutacja Jesienna", "Działalność Statutowa"]
    statusy = ["W przygotowaniu", "Złożony", "Zaakceptowany", "Odrzucony"]
    
    nazwy_grantow = [
        "Dotacja na promocję przedsiębiorczości wśród studentów",
        "Dofinansowanie kulturalnego festiwalu studenckiego",
        "Wniosek o grant na rozwój kompetencji inżynierskich",
        "Mikrogrant na integrację i aktywizację akademicką",
        "Fundusze na organizację ogólnopolskiego konkursu technologicznego",
        "Wsparcie logistyczne projektów edukacyjnych"
    ]

    print("Generowanie fikcyjnych grantów i dofinansowań...")
    
    for _ in range(liczba_grantow):
        nazwa = random.choice(nazwy_grantow) + f" - edycja {random.randint(2025, 2026)}"
        instytucja = random.choice(instytucje)
        kwota = round(random.uniform(5000.0, 75000.0), 2)
        status = random.choice(statusy)
        projekt = random.choice(projekty_best)
        notatki = "Wymagany wkład własny 10%. " + fake.sentence()
        
        # Generujemy termin składania wniosku: od 30 dni wstecz do 120 dni w przód
        dni_offset = random.randint(-30, 120)
        ddl_date = datetime.now() + timedelta(days=dni_offset)
        deadline = ddl_date.strftime("%Y-%m-%d")
        
        cursor.execute("""
            INSERT INTO Granty (nazwa, instytucja, kwota, deadline, status, projekt, notatki)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nazwa, instytucja, kwota, deadline, status, projekt, notatki))

    conn.commit()
    conn.close()

generuj_dane_testowe_grantow(liczba_grantow=12)