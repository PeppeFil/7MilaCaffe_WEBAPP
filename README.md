# 7MilaCaffe WebApp

Gestionale web MVC per negozio fisico specializzato in cialde, capsule compatibili, macchinette da caffè, accessori e kit degustazione.

## Stack
- Backend: Python + Flask
- Architettura: MVC con Service Layer
- ORM: SQLAlchemy
- DB: SQLite (sviluppo), migrabile a PostgreSQL/MySQL
- Frontend: Jinja2 + Bootstrap + CSS custom responsive
- Grafici: Chart.js
- Auth: Flask-Login con ruoli `Admin` e `Operatore`
- Export: CSV + PDF (report vendite giornaliere)

## Struttura progetto
```text
7MilaCaffe_WEBAPP/
├── app/
│   ├── controllers/
│   ├── models/
│   ├── services/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   ├── templates/
│   │   ├── analysis/
│   │   ├── inventory/
│   │   ├── movements/
│   │   ├── products/
│   │   ├── report/
│   │   ├── sales/
│   │   └── settings/
│   ├── utils/
│   ├── extensions.py
│   └── __init__.py
├── migrations/
│   └── schema.sql
├── seed/
│   ├── init_db.py
│   └── seed_demo.py
├── tests/
│   ├── conftest.py
│   ├── test_auth_roles.py
│   └── test_sales_flow.py
├── config.py
├── requirements.txt
└── run.py
```

## Funzionalità principali
- Login/logout con ruoli:
  - `Admin`: accesso completo
  - `Operatore`: cassa + consultazione dati consentiti
- Dashboard con KPI:
  - incasso giornaliero
  - numero vendite giornaliere
  - pezzi venduti
  - alert sotto scorta
  - top prodotto del giorno
  - trend 7 giorni
  - sintesi magazzino
- Gestione prodotti:
  - CRUD completo
  - duplicazione prodotto
  - ricerca e filtri avanzati
  - import/export CSV
  - disattivazione logica
- Cassa / Vendite:
  - ricerca rapida prodotti
  - carrello dinamico
  - sconti percentuali/fissi
  - metodo pagamento
  - ricevuta stampabile
  - salvataggio testata + righe vendita
  - scarico automatico magazzino
  - blocco vendite oltre disponibilità
  - annullamento vendita con ripristino stock
- Magazzino:
  - vista disponibilità
  - stati disponibile/quasi esaurito/esaurito
  - movimenti manuali (Admin)
  - tracciamento movimenti automatici da vendita
- Analisi:
  - vendite giornaliere/settimanali/mensili
  - fatturato categoria
  - prodotti più/meno venduti
  - margine stimato
  - media scontrino
  - metodi pagamento
- Report:
  - vendite giornaliere CSV/PDF
  - magazzino CSV
  - movimenti CSV
  - sotto scorta CSV
  - top prodotti CSV

## Modello dati
Tabelle principali (SQLAlchemy + `migrations/schema.sql`):
- `users`
- `roles`
- `products`
- `sales`
- `sale_items`
- `inventory_movements`
- `categories`
- `suppliers`
- `activity_logs`

Sono definiti:
- chiavi primarie
- chiavi esterne
- vincoli di unicità (es. username, email, barcode)
- timestamp creazione/aggiornamento
- indici per ricerca e performance

## Setup rapido
1. Crea virtualenv:
```bash
python -m venv .venv
```
2. Attiva venv:
```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1
```
3. Installa dipendenze:
```bash
pip install -r requirements.txt
```
4. Inizializza DB e seed demo:
```bash
python seed/init_db.py --reset --seed
```
5. Avvia app:
```bash
python run.py
```
Su Windows, se `python` o `py` non funzionano oppure PowerShell blocca `Activate.ps1`, usa direttamente:
```powershell
.\.venv\Scripts\python.exe .\run.py
```
Oppure avvia:
```bat
start.bat
```
6. Apri:
```text
http://127.0.0.1:5000/login
```

## Credenziali demo
- Admin
  - username: `admin`
  - password: `admin123`
- Operatore
  - username: `operatore`
  - password: `operator123`

## Route principali
- `/login`
- `/dashboard`
- `/cassa`
- `/prodotti`
- `/prodotti/nuovo`
- `/prodotti/<id>/modifica`
- `/magazzino`
- `/movimenti`
- `/vendite`
- `/vendite/<id>`
- `/analisi`
- `/report`
- `/impostazioni`

## Test
Esecuzione test base:
```bash
pytest -q
```

Copertura minima inclusa:
- autenticazione e autorizzazioni ruolo
- flusso vendita con decremento stock
- annullamento vendita con ripristino stock
- blocco vendita con stock insufficiente

## Pubblicazione

Per eseguire l'app su una VPS Hostinger con Docker, Supabase PostgreSQL, HTTPS e
deploy automatico da GitHub Actions, segui [DEPLOYMENT.md](DEPLOYMENT.md).

## Note evolutive consigliate
- integrazione scanner barcode reale
- gestione IVA e fiscalità per ricevuta fiscale
- multi-store / multi-cassa
- audit log consultabile da UI
- API REST dedicate per POS esterno
