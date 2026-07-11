# Pubblicazione su Hostinger + Supabase

Questa guida descrive il bootstrap iniziale. Dopo il primo deploy, ogni push su
`main` esegue test, pubblica una nuova immagine Docker e aggiorna l'app sulla VPS.

## 1. Supabase

1. Crea un progetto Supabase nella regione europea piu vicina alla VPS.
2. Imposta una password robusta per il database e conservala in un password manager.
3. Dal pulsante **Connect**, copia la stringa **Session pooler** (IPv4), adatta a
   una VPS Hostinger. Converti lo schema iniziale in `postgresql+psycopg://` e
   aggiungi `?sslmode=require`.
4. Non creare tabelle o modifiche allo schema dalla dashboard: le migrazioni nella
   cartella `alembic_migrations/` sono la fonte ufficiale dello schema.

## 2. DNS e VPS Hostinger

1. Scegli un dominio o sottodominio, ad esempio `gestionale.tuodominio.it`.
2. Crea un record DNS `A` verso l'IPv4 della VPS. Se usi IPv6, crea anche un record
   `AAAA` verso l'IPv6 della VPS.
3. Installa il template Ubuntu 24.04 con Docker di Hostinger, oppure installa Docker
   Engine e Docker Compose plugin.
4. Nel firewall della VPS consenti le porte TCP `22`, `80` e `443`; non esporre la
   porta dell'applicazione `8000`.
5. Crea una chiave SSH dedicata al deploy e aggiungi la chiave pubblica a
   `~/.ssh/authorized_keys` dell'utente di deploy sulla VPS.

## 3. Registry delle immagini sulla VPS

Accedi una volta al registry delle immagini GitHub dalla VPS. Serve un fine-grained
personal access token con sola autorizzazione **Packages: Read** per l'account
GitHub proprietario del repository:

```bash
echo "TOKEN_LETTURA_PACKAGES" | docker login ghcr.io -u PeppeFil --password-stdin
```

Rendi pubblico il package `ghcr.io/peppefil/7milacaffe-webapp`, oppure mantieni il
login precedente per consentire alla VPS di scaricarlo.

## 4. Segreti GitHub Actions

Nel repository GitHub, in **Settings → Secrets and variables → Actions**, crea:

| Segreto | Valore |
| --- | --- |
| `VPS_HOST` | IP pubblico o hostname della VPS |
| `VPS_PORT` | `22` (oppure la porta SSH scelta) |
| `VPS_USER` | Utente Linux di deploy |
| `VPS_SSH_PRIVATE_KEY` | Chiave privata SSH dedicata al deploy |
| `VPS_SSH_KNOWN_HOSTS` | Output di `ssh-keyscan -H IP_DELLA_VPS` verificato dall'amministratore della VPS |
| `VPS_APP_ENV` | Contenuto completo del file `.env`, partendo da `.env.example` e con valori reali |

Il workflow salta deliberatamente il deploy finché i segreti obbligatori non sono
presenti. Ad ogni deploy copia automaticamente `docker-compose.yml` e il contenuto
protetto di `VPS_APP_ENV` nella cartella `~/7milacaffe` dell'utente VPS.

Nel segreto `VPS_APP_ENV`, usa i valori di `.env.example`. Per il primo deploy lascia
le tre variabili `ADMIN_*`; il comando di inizializzazione crea l'amministratore una
sola volta. Dopo il primo accesso, rimuovi almeno `ADMIN_PASSWORD` dal segreto.

In alternativa, per il primo deploy manuale puoi copiare
`scripts/configure-production-env.sh` sulla VPS ed eseguire:

```bash
cd ~/7milacaffe
bash configure-production-env.sh NOME_DOMINIO
```

Il comando chiede localmente la stringa Supabase e la password dell'amministratore,
senza inviarle al repository.

## 5. Primo deploy e verifiche

1. Esegui il workflow **Test, publish and deploy** su GitHub Actions oppure fai push
   su `main`.
2. Controlla i log del job `deploy`: esegue `flask db upgrade`, crea il primo admin
   solo se non ne esiste uno, e ricrea i container.
3. Traefik, già fornito dal template Docker Hostinger, ottiene automaticamente il
   certificato HTTPS. Apri `https://DOMINIO/healthz`: deve rispondere
   `{ "status": "ok" }`.
4. Apri `https://DOMINIO/login`, accedi con l'amministratore iniziale, poi rimuovi
   `ADMIN_PASSWORD` dal file `.env` della VPS.
5. Esegui una vendita di prova e verifica su Supabase che dati e tabelle siano stati
   popolati.

## Aggiornamenti successivi

Per modifiche all'applicazione:

```bash
git add .
git commit -m "descrizione modifica"
git push origin main
```

GitHub Actions eseguirà i test, creerà l'immagine e aggiornerà la VPS.

Per cambiare il database, crea una migrazione e committala insieme al codice:

```bash
flask --app run:app db migrate -m "descrizione modifica"
flask --app run:app db upgrade
```

La migration sarà applicata automaticamente durante il deploy successivo.
