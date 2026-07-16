CREATE TABLE Firma (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nazwa TEXT NOT NULL,
kategoria TEXT
);

CREATE TABLE OsobaKontaktowa (
id INTEGER PRIMARY KEY AUTOINCREMENT,
imie TEXT NOT NULL,
nazwisko TEXT NOT NULL,
email TEXT,
telefon TEXT
);

CREATE TABLE FirmaOsobaKontaktowa (
firma_id INTEGER,
osoba_id INTEGER,
PRIMARY KEY (firma_id, osoba_id),
FOREIGN KEY (firma_id) REFERENCES Firma(id),
FOREIGN KEY (osoba_id) REFERENCES OsobaKontaktowa(id)
);

CREATE TABLE Uzytkownik (
id INTEGER PRIMARY KEY AUTOINCREMENT,
imie TEXT NOT NULL,
nazwisko TEXT NOT NULL,
email TEXT
);

CREATE TABLE Interakcja (
id INTEGER PRIMARY KEY AUTOINCREMENT,
id_firmy INTEGER NOT NULL,
id_uzytkownika INTEGER NOT NULL,
id_osoby_kontaktowej INTEGER,
data_interakcji DATETIME NOT NULL,
status TEXT NOT NULL,
komentarz TEXT,
projekt TEXT,
kolejny_kontakt DATETIME,
sciezka_pliku TEXT,

FOREIGN KEY (id_firmy) REFERENCES Firma(id),
FOREIGN KEY (id_uzytkownika) REFERENCES Uzytkownik(id),
FOREIGN KEY (id_osoby_kontaktowej) REFERENCES OsobaKontaktowa(id)
);

CREATE TABLE Grant (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nazwa TEXT NOT NULL,
instytucja TEXT,
kwota REAL,
deadline TEXT, -- Format YYYY-MM-DD
status TEXT, -- 'W przygotowaniu', 'Złożony', 'Zaakceptowany', 'Odrzucony'
projekt TEXT, 
notatki TEXT,
link TEXT
);
