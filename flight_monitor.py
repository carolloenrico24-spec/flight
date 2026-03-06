"""
✈️ Flight Price Monitor
Legge credenziali da variabili d'ambiente (.env locale o GitHub Secrets).
Legge voli e destinatari da config.json (sicuro da committare).
"""

import json
import os
import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests

# Carica .env se presente (locale)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # In produzione usa le variabili d'ambiente dirette

# ─── LOGGING ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("flight_monitor.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ─── PATHS ──────────────────────────────────────────────────────────────────
CONFIG_FILE = Path("config.json")
PRICE_HISTORY_FILE = Path("price_history.json")


# ════════════════════════════════════════════════════════════════════════════
# CREDENZIALI DA ENV
# ════════════════════════════════════════════════════════════════════════════

def get_credentials() -> dict:
    """Legge le credenziali SOLO da variabili d'ambiente. Mai da config.json."""
    serpapi_key = os.environ.get("SERPAPI_KEY")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    missing = []
    if not serpapi_key:
        missing.append("SERPAPI_KEY")
    if not smtp_user:
        missing.append("SMTP_USER")
    if not smtp_password:
        missing.append("SMTP_PASSWORD")

    if missing:
        raise EnvironmentError(
            f"Variabili d'ambiente mancanti: {', '.join(missing)}\n"
            f"Controlla il file .env o i GitHub Secrets."
        )

    return {
        "serpapi_key": serpapi_key,
        "smtp_user": smtp_user,
        "smtp_password": smtp_password,
    }


# ════════════════════════════════════════════════════════════════════════════
# CONFIG (voli + destinatari — sicuro da committare)
# ════════════════════════════════════════════════════════════════════════════

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        log.error("config.json non trovato.")
        raise FileNotFoundError("config.json non trovato")
    with open(CONFIG_FILE) as f:
        return json.load(f)


# ════════════════════════════════════════════════════════════════════════════
# PRICE HISTORY
# ════════════════════════════════════════════════════════════════════════════

def load_price_history() -> dict:
    if PRICE_HISTORY_FILE.exists():
        with open(PRICE_HISTORY_FILE) as f:
            return json.load(f)
    return {}


def save_price_history(history: dict):
    with open(PRICE_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


# ════════════════════════════════════════════════════════════════════════════
# SERPAPI — GOOGLE FLIGHTS
# ════════════════════════════════════════════════════════════════════════════

def fetch_flight_price(flight: dict, api_key: str) -> dict | None:
    params = {
        "engine": "google_flights",
        "departure_id": flight["origin"],
        "arrival_id": flight["destination"],
        "outbound_date": flight["date"],
        "currency": flight.get("currency", "EUR"),
        "hl": "it",
        "api_key": api_key,
    }

    if flight.get("return_date"):
        params["return_date"] = flight["return_date"]
        params["type"] = "1"
    else:
        params["type"] = "2"

    if flight.get("adults"):
        params["adults"] = flight["adults"]

    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        all_flights = data.get("best_flights", []) + data.get("other_flights", [])
        if not all_flights:
            log.warning(f"Nessun volo trovato per {flight['origin']}→{flight['destination']} il {flight['date']}")
            return None

        prices = [f.get("price") for f in all_flights if f.get("price")]
        if not prices:
            return None

        min_price = min(prices)
        cheapest = next(f for f in all_flights if f.get("price") == min_price)
        first_leg = cheapest.get("flights", [{}])[0]

        return {
            "price": min_price,
            "airline": first_leg.get("airline", "N/D"),
            "departure_time": first_leg.get("departure_airport", {}).get("time", "N/D"),
            "arrival_time": first_leg.get("arrival_airport", {}).get("time", "N/D"),
            "duration": cheapest.get("total_duration", 0),
            "stops": len(cheapest.get("flights", [])) - 1,
            "booking_token": cheapest.get("booking_token", ""),
        }

    except requests.exceptions.RequestException as e:
        log.error(f"Errore API per {flight['origin']}→{flight['destination']}: {e}")
        return None
    except (KeyError, ValueError) as e:
        log.error(f"Errore parsing per {flight['origin']}→{flight['destination']}: {e}")
        return None


# ════════════════════════════════════════════════════════════════════════════
# ALERT LOGIC
# ════════════════════════════════════════════════════════════════════════════

def should_alert(flight: dict, current_price: float, history: dict, global_thresholds: dict) -> tuple[bool, str]:
    flight_key = f"{flight['origin']}-{flight['destination']}-{flight['date']}"

    max_price = flight.get("max_price") or global_thresholds.get("max_price")
    drop_percent = flight.get("alert_drop_percent") or global_thresholds.get("alert_drop_percent", 10)
    drop_absolute = flight.get("alert_drop_absolute") or global_thresholds.get("alert_drop_absolute")

    reasons = []

    if max_price and current_price <= max_price:
        reasons.append(f"prezzo (€{current_price}) sotto soglia massima (€{max_price})")

    if flight_key in history and history[flight_key]:
        prices = [entry["price"] for entry in history[flight_key]]
        avg_price = sum(prices) / len(prices)
        last_price = prices[-1]

        if len(prices) >= 2:
            pct_drop_from_avg = ((avg_price - current_price) / avg_price) * 100
            pct_drop_from_last = ((last_price - current_price) / last_price) * 100

            if pct_drop_from_avg >= drop_percent:
                reasons.append(f"calo del {pct_drop_from_avg:.1f}% rispetto alla media storica (€{avg_price:.0f})")
            if pct_drop_from_last >= drop_percent:
                reasons.append(f"calo del {pct_drop_from_last:.1f}% rispetto all'ultima rilevazione (€{last_price:.0f})")

        if drop_absolute and (last_price - current_price) >= drop_absolute:
            reasons.append(f"calo di €{last_price - current_price:.0f} rispetto all'ultima rilevazione")

    if reasons:
        return True, " | ".join(reasons)
    return False, ""


# ════════════════════════════════════════════════════════════════════════════
# EMAIL
# ════════════════════════════════════════════════════════════════════════════

def send_email_alert(alerts: list[dict], recipients: list[str], smtp_user: str, smtp_password: str):
    if not alerts or not recipients:
        return

    sender = f"Flight Monitor <{smtp_user}>"
    subject = f"✈️ {len(alerts)} alert voli — {datetime.now().strftime('%d/%m/%Y %H:%M')}"

    rows_html = ""
    for a in alerts:
        f = a["flight"]
        d = a["data"]
        stops_label = "diretto" if d["stops"] == 0 else f"{d['stops']} scalo/i"
        duration_h = d["duration"] // 60
        duration_m = d["duration"] % 60

        rows_html += f"""
        <tr>
            <td style="padding:16px; border-bottom:1px solid #f0f0f0;">
                <div style="font-size:20px; font-weight:700; color:#1a1a2e;">
                    {f['origin']} → {f['destination']}
                </div>
                <div style="color:#666; font-size:13px; margin-top:2px;">
                    {f['date']}{f" → {f['return_date']}" if f.get('return_date') else ''} · {f.get('label', '')}
                </div>
            </td>
            <td style="padding:16px; border-bottom:1px solid #f0f0f0; text-align:center;">
                <div style="font-size:28px; font-weight:800; color:#e63946;">€{d['price']}</div>
                <div style="color:#888; font-size:12px;">{d['airline']}</div>
            </td>
            <td style="padding:16px; border-bottom:1px solid #f0f0f0;">
                <div style="color:#333; font-size:13px;">🕐 {d['departure_time']} → {d['arrival_time']}</div>
                <div style="color:#333; font-size:13px;">⏱ {duration_h}h {duration_m}m · {stops_label}</div>
                <div style="color:#e63946; font-size:12px; margin-top:6px; font-weight:600;">{a['reason']}</div>
            </td>
            <td style="padding:16px; border-bottom:1px solid #f0f0f0; text-align:center;">
                <a href="https://www.google.com/travel/flights"
                   style="background:#1a1a2e; color:white; padding:10px 18px; border-radius:8px;
                          text-decoration:none; font-size:13px; font-weight:600;">
                    Cerca →
                </a>
            </td>
        </tr>
        """

    html_body = f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#f5f5f5;font-family:'Segoe UI',Arial,sans-serif;">
        <div style="max-width:680px;margin:30px auto;background:white;border-radius:16px;
                    box-shadow:0 4px 24px rgba(0,0,0,0.08);overflow:hidden;">
            <div style="background:#1a1a2e;padding:28px 32px;">
                <div style="font-size:26px;font-weight:800;color:white;">✈️ Flight Monitor</div>
                <div style="color:#8899cc;font-size:14px;margin-top:4px;">
                    {len(alerts)} alert trovati · {datetime.now().strftime('%d/%m/%Y alle %H:%M')}
                </div>
            </div>
            <table style="width:100%;border-collapse:collapse;">
                <thead><tr style="background:#f8f8f8;">
                    <th style="padding:12px 16px;text-align:left;color:#999;font-size:11px;text-transform:uppercase;">Tratta</th>
                    <th style="padding:12px 16px;text-align:center;color:#999;font-size:11px;text-transform:uppercase;">Prezzo</th>
                    <th style="padding:12px 16px;text-align:left;color:#999;font-size:11px;text-transform:uppercase;">Dettagli</th>
                    <th style="padding:12px 16px;text-align:center;color:#999;font-size:11px;text-transform:uppercase;">Azione</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
            <div style="padding:20px 32px;background:#f8f8f8;color:#aaa;font-size:12px;text-align:center;">
                Flight Monitor · I prezzi potrebbero variare al momento della prenotazione
            </div>
        </div>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipients, msg.as_string())
        log.info(f"✅ Email inviata a: {recipients}")
    except Exception as e:
        log.error(f"❌ Errore invio email: {e}")
        raise


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def run():
    log.info("=" * 60)
    log.info("▶ Flight Monitor avviato")
    log.info("=" * 60)

    creds = get_credentials()
    config = load_config()

    flights = config.get("flights", [])
    thresholds = config.get("global_thresholds", {})
    # Destinatari letti da config.json (gestiti dalla dashboard)
    recipients = config.get("notification_recipients", [])

    if not recipients:
        log.warning("⚠️ Nessun destinatario configurato. Aggiungi destinatari dalla dashboard.")

    history = load_price_history()
    alerts_to_send = []

    for flight in flights:
        flight_key = f"{flight['origin']}-{flight['destination']}-{flight['date']}"
        label = flight.get("label", flight_key)
        log.info(f"Controllo: {label}")

        result = fetch_flight_price(flight, creds["serpapi_key"])
        if result is None:
            log.warning(f"  → Nessun dato, skip")
            continue

        current_price = result["price"]
        log.info(f"  → €{current_price} ({result['airline']})")

        if flight_key not in history:
            history[flight_key] = []

        history[flight_key].append({
            "price": current_price,
            "timestamp": datetime.now().isoformat(),
            "airline": result["airline"]
        })
        history[flight_key] = history[flight_key][-90:]

        should_send, reason = should_alert(flight, current_price, history, thresholds)
        if should_send:
            log.info(f"  ⚠️  ALERT: {reason}")
            alerts_to_send.append({"flight": flight, "data": result, "reason": reason})
        else:
            log.info(f"  ✓ Nessun alert")

    save_price_history(history)

    if alerts_to_send and recipients:
        log.info(f"\n📧 Invio email con {len(alerts_to_send)} alert a {recipients}...")
        send_email_alert(alerts_to_send, recipients, creds["smtp_user"], creds["smtp_password"])
    elif alerts_to_send and not recipients:
        log.warning("⚠️ Alert trovati ma nessun destinatario — email non inviata.")
    else:
        log.info("\n✓ Nessun alert in questo ciclo")

    log.info("▶ Ciclo completato\n")


if __name__ == "__main__":
    run()
