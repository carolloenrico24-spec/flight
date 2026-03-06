# ✈️ Flight Monitor

Monitora prezzi voli, invia alert email quando scendono. Dashboard visiva su Streamlit.

---

## Struttura file

```
flight-monitor/
├── flight_monitor.py          # Script check prezzi + invio email
├── dashboard.py               # Dashboard Streamlit
├── config.json                # Voli + destinatari (safe to commit)
├── requirements.txt
├── .env                       # ⚠️ Credenziali locali — NON committare
├── .gitignore
└── .github/
    └── workflows/
        └── monitor.yml        # GitHub Actions: check automatico ogni 6h
```

---

## Setup locale

### 1. Installa dipendenze
```bash
pip install -r requirements.txt
```

### 2. Configura .env
Apri `.env` e inserisci la Gmail **App Password** (vedi sotto).
La SerpAPI key è già inserita.

### 3. Genera Gmail App Password
1. Vai su [myaccount.google.com](https://myaccount.google.com) → Sicurezza
2. Attiva **Verifica in 2 passaggi**
3. Cerca "App password" → crea password per "Mail"
4. Copia i 16 caratteri → incollali in `.env` come `SMTP_PASSWORD`

### 4. Avvia la dashboard
```bash
streamlit run dashboard.py
```
Apre su http://localhost:8501

### 5. Aggiungi destinatari email
Dalla dashboard → tab **Notifiche** → aggiungi gli indirizzi che devono ricevere gli alert.
Puoi anche inviare un'email di test direttamente dall'interfaccia.

### 6. Aggiungi voli da monitorare
Dal pannello laterale della dashboard → "Aggiungi volo".

### 7. Test manuale
```bash
python flight_monitor.py
```

---

## Deploy su GitHub (check automatico gratuito)

### Step 1 — Crea repo GitHub
```bash
git init
git add .
# ⚠️ Verifica che .env NON sia incluso:
git status  # .env non deve apparire
git commit -m "init flight monitor"
git remote add origin https://github.com/TUO-USERNAME/flight-monitor.git
git push -u origin main
```

### Step 2 — Aggiungi GitHub Secrets
Su GitHub → Settings → Secrets and variables → Actions → New repository secret

Aggiungi questi 3 secrets (copiando i valori dal tuo .env):

| Nome secret | Valore |
|-------------|--------|
| `SERPAPI_KEY` | la tua SerpAPI key |
| `SMTP_USER` | magazzino.kymera@gmail.com |
| `SMTP_PASSWORD` | la App Password Gmail (16 caratteri) |

### Step 3 — Attiva GitHub Actions
Il file `.github/workflows/monitor.yml` è già configurato.
Vai su Actions → abilita i workflow → il check partirà automaticamente ogni 6 ore.
Puoi anche lanciarlo manualmente dal tab Actions → "Run workflow".

### Step 4 — Dashboard su Streamlit Cloud (opzionale)
1. Vai su [share.streamlit.io](https://share.streamlit.io)
2. Connetti il repo GitHub
3. Entry point: `dashboard.py`
4. In Advanced settings → Secrets, aggiungi:
```toml
SERPAPI_KEY = "tua-key"
SMTP_USER = "magazzino.kymera@gmail.com"
SMTP_PASSWORD = "tua-app-password"
```
5. Deploy → URL pubblico pronto

---

## Come funziona la logica alert

Un alert scatta se **almeno una** condizione è vera:

| Condizione | Parametro | Default |
|---|---|---|
| Prezzo ≤ soglia | `max_price` per volo | — |
| Calo % vs media storica | `alert_drop_percent` | 10% |
| Calo % vs ultima rilevazione | `alert_drop_percent` | 10% |
| Calo assoluto € | `alert_drop_absolute` | 30€ |

---

## Gestione destinatari email

I destinatari si gestiscono **solo dalla dashboard** (tab Notifiche):
- Aggiungi email → vengono salvate in `config.json`
- Rimuovi in un click
- Test email diretto dall'interfaccia

`config.json` è safe da committare perché non contiene credenziali.

---

## Calcolo chiamate SerpAPI (free: 100/mese)

| Voli | Frequenza | Chiamate/mese |
|------|-----------|---------------|
| 2 | ogni 24h | ~60 ✅ |
| 3 | ogni 24h | ~90 ✅ |
| 3 | ogni 12h | ~180 ❌ |

Per più voli: piano SerpAPI $50/mese (5.000 chiamate).

---

## Troubleshooting

**Email non arriva**: Stai usando la password normale Gmail invece della App Password.

**SERPAPI_KEY not found**: Verifica che `.env` esista nella stessa cartella dello script.

**No flights found**: Controlla codice IATA e che la data non sia passata.

**Dashboard non mostra dati**: Esegui prima `python flight_monitor.py` per generare `price_history.json`.
