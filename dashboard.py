"""
✈️ Flight Monitor Dashboard
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Flight Monitor",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Mono', monospace;
    background-color: #0a0a0f;
    color: #e8e8f0;
}
.main .block-container { padding: 2rem 2.5rem; max-width: 1400px; }
section[data-testid="stSidebar"] { background: #0f0f1a !important; border-right: 1px solid #1e1e30; }
section[data-testid="stSidebar"] .block-container { padding: 1.5rem 1.2rem; }
h1, h2, h3 { font-family: 'Syne', sans-serif !important; letter-spacing: -0.03em; }

.flight-card {
    background: #0f0f1a; border: 1px solid #1e1e30; border-radius: 12px;
    padding: 1.4rem 1.6rem; margin-bottom: 0.5rem; transition: border-color 0.2s;
}
.flight-card:hover { border-color: #3a3a5c; }

.route-label { font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 700; color: #e8e8f0; }
.meta-label { font-size: 0.72rem; color: #555570; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 4px; }
.trend-up { color: #ff4757; }
.trend-down { color: #2ed573; }

.tag { display:inline-block; background:#1a1a2e; border:1px solid #2a2a4a; border-radius:4px;
       padding:2px 8px; font-size:0.7rem; color:#888; letter-spacing:0.08em; text-transform:uppercase; }
.tag.alert-tag { background:#1a0a0a; border-color:#4a1a1a; color:#ff4757; }
.tag.ok-tag { background:#0a1a0a; border-color:#1a4a1a; color:#2ed573; }

.recipient-chip {
    display: inline-flex; align-items: center; gap: 6px;
    background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 20px;
    padding: 4px 12px; font-size: 0.75rem; color: #aab; margin: 3px;
}

.stButton > button {
    font-family: 'DM Mono', monospace !important; font-size: 0.8rem !important;
    letter-spacing: 0.06em; text-transform: uppercase; border-radius: 8px !important;
}
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: #0f0f1a !important; border: 1px solid #1e1e30 !important;
    color: #e8e8f0 !important; font-family: 'DM Mono', monospace !important; border-radius: 8px !important;
}
hr { border-color: #1e1e30; }
[data-testid="stMetric"] { background: #0f0f1a; border: 1px solid #1e1e30; border-radius: 10px; padding: 1rem; }
.log-box {
    background: #07070d; border: 1px solid #1e1e30; border-radius: 10px; padding: 1rem;
    font-family: 'DM Mono', monospace; font-size: 0.72rem; color: #556;
    max-height: 220px; overflow-y: auto; white-space: pre-wrap; line-height: 1.6;
}
.section-title {
    font-family: 'Syne', sans-serif; font-size: 0.95rem; font-weight: 700;
    color: #e8e8f0; margin-bottom: 0.8rem; margin-top: 1.2rem;
    padding-bottom: 6px; border-bottom: 1px solid #1e1e30;
}
</style>
""", unsafe_allow_html=True)

# ─── PATHS ──────────────────────────────────────────────────────────────────
CONFIG_FILE = Path("config.json")
HISTORY_FILE = Path("price_history.json")
LOG_FILE = Path("flight_monitor.log")


# ─── HELPERS ────────────────────────────────────────────────────────────────

def load_config() -> dict:
    defaults = {
        "global_thresholds": {"alert_drop_percent": 10, "alert_drop_absolute": 30},
        "notification_recipients": [],
        "flights": []
    }
    if not CONFIG_FILE.exists():
        return defaults
    with open(CONFIG_FILE) as f:
        data = json.load(f)
    for k, v in defaults.items():
        data.setdefault(k, v)
    return data


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def load_history() -> dict:
    if not HISTORY_FILE.exists():
        return {}
    with open(HISTORY_FILE) as f:
        return json.load(f)


def load_log(lines: int = 80) -> str:
    if not LOG_FILE.exists():
        return "Nessun log ancora. Esegui il primo check."
    with open(LOG_FILE) as f:
        all_lines = f.readlines()
    return "".join(all_lines[-lines:])


def get_flight_key(flight: dict) -> str:
    return f"{flight['origin']}-{flight['destination']}-{flight['date']}"


def get_price_stats(history: dict, key: str) -> dict:
    entries = history.get(key, [])
    if not entries:
        return {"current": None, "min": None, "max": None, "avg": None,
                "trend": None, "history": [], "last_check": None}
    prices = [e["price"] for e in entries]
    timestamps = [e["timestamp"] for e in entries]
    trend = None
    if len(prices) >= 2:
        diff = prices[-1] - prices[-2]
        trend = "up" if diff > 2 else ("down" if diff < -2 else "flat")
    return {
        "current": prices[-1], "min": min(prices), "max": max(prices),
        "avg": round(sum(prices) / len(prices), 0), "trend": trend,
        "history": entries, "last_check": timestamps[-1]
    }


def check_env() -> tuple[bool, list[str]]:
    """Verifica che le variabili d'ambiente siano configurate."""
    missing = []
    for var in ["SERPAPI_KEY", "SMTP_USER", "SMTP_PASSWORD"]:
        if not os.environ.get(var):
            missing.append(var)
    return len(missing) == 0, missing


# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown('<h2 style="font-family:Syne,sans-serif;font-size:1.3rem;margin-bottom:0.1rem;">✈️ Flight Monitor</h2>', unsafe_allow_html=True)
    st.markdown('<div class="meta-label" style="margin-bottom:1.2rem;">control panel</div>', unsafe_allow_html=True)

    config = load_config()

    # ── Env check ──
    env_ok, missing_vars = check_env()
    if not env_ok:
        st.warning(f"⚠️ Variabili mancanti nel .env:\n`{'`, `'.join(missing_vars)}`")
    else:
        st.success("✓ Credenziali configurate")

    st.divider()

    # ── Run check ──
    st.markdown('<div class="meta-label">azioni</div>', unsafe_allow_html=True)
    if st.button("▶ Esegui Check Ora", use_container_width=True, type="primary"):
        if not env_ok:
            st.error("Configura prima le variabili d'ambiente nel file .env")
        else:
            with st.spinner("Controllo voli in corso..."):
                result = subprocess.run(
                    [sys.executable, "flight_monitor.py"],
                    capture_output=True, text=True
                )
            if result.returncode == 0:
                st.success("✓ Check completato!")
            else:
                st.error(f"Errore: {result.stderr[:300]}")
            st.rerun()

    if st.button("🔄 Aggiorna dashboard", use_container_width=True):
        st.rerun()

    st.divider()

    # ── Soglie globali ──
    with st.expander("🎯 Soglie Globali"):
        thresh = config.get("global_thresholds", {})
        new_pct = st.number_input("Alert se calo %", min_value=1, max_value=50,
                                   value=int(thresh.get("alert_drop_percent", 10)))
        new_abs = st.number_input("Alert se calo €", min_value=1, max_value=500,
                                   value=int(thresh.get("alert_drop_absolute", 30)))
        if st.button("💾 Salva soglie", use_container_width=True):
            config["global_thresholds"]["alert_drop_percent"] = new_pct
            config["global_thresholds"]["alert_drop_absolute"] = new_abs
            save_config(config)
            st.success("Salvato!")
            st.rerun()

    st.divider()

    # ── Aggiungi volo ──
    st.markdown('<div class="meta-label">aggiungi volo</div>', unsafe_allow_html=True)
    with st.form("add_flight_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_origin = st.text_input("Da (IATA)", placeholder="MXP", max_chars=3).upper().strip()
        with col2:
            new_dest = st.text_input("A (IATA)", placeholder="JFK", max_chars=3).upper().strip()
        new_label = st.text_input("Etichetta", placeholder="Milano → NY Giugno")
        new_date = st.date_input("Data andata")
        use_return = st.checkbox("Volo di ritorno")
        new_return = st.date_input("Data ritorno", value=None) if use_return else None
        col3, col4 = st.columns(2)
        with col3:
            new_adults = st.number_input("Adulti", min_value=1, max_value=9, value=1)
        with col4:
            new_max_price = st.number_input("Max €", min_value=0, value=0)

        if st.form_submit_button("➕ Aggiungi volo", use_container_width=True):
            if new_origin and new_dest:
                new_flight = {
                    "label": new_label or f"{new_origin} → {new_dest}",
                    "origin": new_origin,
                    "destination": new_dest,
                    "date": str(new_date),
                    "adults": new_adults,
                    "currency": "EUR",
                }
                if new_return:
                    new_flight["return_date"] = str(new_return)
                if new_max_price > 0:
                    new_flight["max_price"] = new_max_price
                config["flights"].append(new_flight)
                save_config(config)
                st.success(f"✓ Aggiunto!")
                st.rerun()
            else:
                st.error("Inserisci origine e destinazione.")


# ════════════════════════════════════════════════════════════════════════════
# MAIN — HEADER
# ════════════════════════════════════════════════════════════════════════════

config = load_config()
history = load_history()
flights = config.get("flights", [])

st.markdown("""
<div style="display:flex;align-items:baseline;gap:14px;margin-bottom:0.2rem;">
    <h1 style="font-family:Syne,sans-serif;font-size:2.2rem;font-weight:800;
               letter-spacing:-0.04em;margin:0;color:#e8e8f0;">Flight Monitor</h1>
    <span class="tag">dashboard</span>
</div>
""", unsafe_allow_html=True)
st.markdown(f'<div class="meta-label">{len(flights)} voli · {datetime.now().strftime("%d/%m/%Y %H:%M")}</div>',
            unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB LAYOUT
# ════════════════════════════════════════════════════════════════════════════

tab_flights, tab_notifications, tab_log = st.tabs(["✈️  Voli", "📧  Notifiche", "📋  Log"])


# ──────────────────────────────────────────────────────────────────────────
# TAB 1 — VOLI
# ──────────────────────────────────────────────────────────────────────────

with tab_flights:
    if not flights:
        st.info("Nessun volo monitorato. Aggiungine uno dal pannello laterale.")
    else:
        # Summary metrics
        all_stats = [get_price_stats(history, get_flight_key(f)) for f in flights]
        active = sum(1 for s in all_stats if s["current"] is not None)
        n_alerts = sum(1 for f, s in zip(flights, all_stats)
                       if s["current"] and f.get("max_price") and s["current"] <= f["max_price"])
        n_drops = sum(1 for s in all_stats if s["trend"] == "down")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Voli monitorati", len(flights))
        c2.metric("Con dati", active)
        c3.metric("🔴 In alert", n_alerts)
        c4.metric("📉 In calo", n_drops)

        st.markdown("<br>", unsafe_allow_html=True)

        try:
            import plotly.graph_objects as go
            has_plotly = True
        except ImportError:
            has_plotly = False

        for i, flight in enumerate(flights):
            key = get_flight_key(flight)
            stats = get_price_stats(history, key)

            is_alert = (stats["current"] and flight.get("max_price") and
                        stats["current"] <= flight["max_price"])
            trend_icon = {"up": "↑", "down": "↓", "flat": "→", None: "—"}.get(stats["trend"], "—")
            trend_class = {"up": "trend-up", "down": "trend-down"}.get(stats["trend"], "")

            col_info, col_price, col_stats, col_del = st.columns([3, 2, 3, 1])

            with col_info:
                date_str = flight["date"]
                if flight.get("return_date"):
                    date_str += f" → {flight['return_date']}"
                st.markdown(f"""
                <div class="flight-card">
                    <div class="route-label">{flight.get('label', key)}</div>
                    <div style="font-size:0.75rem;color:#555570;margin-top:6px;">
                        📅 {date_str} &nbsp;·&nbsp; 👤 {flight.get('adults', 1)} adulto/i
                    </div>
                    <div style="margin-top:10px;">
                        {"<span class='tag alert-tag'>⚠️ SOTTO SOGLIA</span>" if is_alert else "<span class='tag ok-tag'>✓ ok</span>"}
                        {f"<span class='tag' style='margin-left:6px;'>Max €{flight['max_price']}</span>" if flight.get('max_price') else ""}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_price:
                if stats["current"]:
                    price_color = "#ff4757" if is_alert else ("#2ed573" if stats["trend"] == "down" else "#e8e8f0")
                    st.markdown(f"""
                    <div class="flight-card" style="text-align:center;">
                        <div class="meta-label">prezzo attuale</div>
                        <div style="font-family:Syne,sans-serif;font-size:2.2rem;font-weight:800;
                                    color:{price_color};line-height:1.1;">€{stats['current']}</div>
                        <div class="{trend_class}" style="font-size:1rem;margin-top:4px;">{trend_icon}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="flight-card" style="text-align:center;">
                        <div class="meta-label">prezzo attuale</div>
                        <div style="font-size:1.6rem;color:#2a2a3a;font-family:Syne,sans-serif;margin-top:8px;">—</div>
                        <div style="font-size:0.7rem;color:#333;margin-top:4px;">nessun dato</div>
                    </div>
                    """, unsafe_allow_html=True)

            with col_stats:
                if stats["current"]:
                    last_check_str = "—"
                    if stats["last_check"]:
                        try:
                            dt = datetime.fromisoformat(stats["last_check"])
                            last_check_str = dt.strftime("%d/%m %H:%M")
                        except Exception:
                            last_check_str = stats["last_check"][:16]
                    st.markdown(f"""
                    <div class="flight-card">
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                            <div><div class="meta-label">minimo</div>
                                 <div style="font-family:Syne,sans-serif;font-weight:700;color:#2ed573;">€{stats['min']}</div></div>
                            <div><div class="meta-label">massimo</div>
                                 <div style="font-family:Syne,sans-serif;font-weight:700;color:#ff4757;">€{stats['max']}</div></div>
                            <div><div class="meta-label">media</div>
                                 <div style="font-family:Syne,sans-serif;font-weight:700;">€{stats['avg']}</div></div>
                            <div><div class="meta-label">ultimo check</div>
                                 <div style="font-size:0.75rem;color:#666;">{last_check_str}</div></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown('<div class="flight-card" style="color:#2a2a3a;font-size:0.8rem;">Esegui il primo check</div>',
                                unsafe_allow_html=True)

            with col_del:
                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                if st.button("🗑", key=f"del_{i}", help="Rimuovi volo"):
                    config["flights"].pop(i)
                    save_config(config)
                    st.rerun()

            # Chart
            if stats["history"] and len(stats["history"]) >= 2 and has_plotly:
                entries = stats["history"]
                xs = [e["timestamp"][:16].replace("T", " ") for e in entries]
                ys = [e["price"] for e in entries]
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=xs, y=ys, fill='tozeroy',
                                         fillcolor='rgba(42,82,190,0.06)',
                                         line=dict(color='rgba(0,0,0,0)'),
                                         showlegend=False, hoverinfo='skip'))
                fig.add_trace(go.Scatter(x=xs, y=ys, mode='lines+markers',
                                         line=dict(color='#2a52be', width=2),
                                         marker=dict(size=5, color='#4a72de',
                                                     line=dict(color='#0a0a0f', width=1)),
                                         hovertemplate='€%{y}<br>%{x}<extra></extra>',
                                         showlegend=False))
                if flight.get("max_price"):
                    fig.add_hline(y=flight["max_price"], line_dash="dash", line_color="#ff4757",
                                  line_width=1,
                                  annotation_text=f"soglia €{flight['max_price']}",
                                  annotation_font_color="#ff4757", annotation_font_size=10)
                fig.update_layout(height=110, margin=dict(l=0, r=0, t=0, b=0),
                                   paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                   xaxis=dict(showgrid=False, zeroline=False,
                                              tickfont=dict(size=9, color='#444')),
                                   yaxis=dict(showgrid=True, gridcolor='#1a1a2a', zeroline=False,
                                              tickfont=dict(size=9, color='#444'), tickprefix='€'))
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────
# TAB 2 — NOTIFICHE (gestione destinatari)
# ──────────────────────────────────────────────────────────────────────────

with tab_notifications:
    st.markdown('<div class="section-title">📧 Destinatari Notifiche Email</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.8rem;color:#666;margin-bottom:1.2rem;">Le email di alert vengono inviate a questi indirizzi. Puoi aggiungerne o rimuoverne quanti vuoi.</div>',
                unsafe_allow_html=True)

    recipients = config.get("notification_recipients", [])

    # Current recipients
    if recipients:
        st.markdown('<div class="meta-label" style="margin-bottom:8px;">destinatari attivi</div>', unsafe_allow_html=True)
        for idx, email in enumerate(recipients):
            col_email, col_remove = st.columns([5, 1])
            with col_email:
                st.markdown(f"""
                <div style="background:#0f0f1a;border:1px solid #1e1e30;border-radius:8px;
                            padding:10px 14px;font-size:0.82rem;color:#aab;margin-bottom:6px;">
                    📧 {email}
                </div>
                """, unsafe_allow_html=True)
            with col_remove:
                if st.button("✕", key=f"rm_rcpt_{idx}", help=f"Rimuovi {email}"):
                    config["notification_recipients"].pop(idx)
                    save_config(config)
                    st.success(f"Rimosso: {email}")
                    st.rerun()
    else:
        st.markdown("""
        <div style="background:#0f0f1a;border:1px dashed #2a2a3a;border-radius:10px;
                    padding:20px;text-align:center;color:#333;font-size:0.85rem;margin-bottom:1rem;">
            Nessun destinatario configurato.<br>Aggiungi almeno un indirizzo email per ricevere gli alert.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Add recipient
    st.markdown('<div class="section-title">Aggiungi destinatario</div>', unsafe_allow_html=True)
    with st.form("add_recipient_form", clear_on_submit=True):
        col_input, col_btn = st.columns([4, 1])
        with col_input:
            new_email = st.text_input("Indirizzo email", placeholder="mario@example.com",
                                      label_visibility="collapsed")
        with col_btn:
            add_clicked = st.form_submit_button("➕ Aggiungi", use_container_width=True)

        if add_clicked:
            new_email = new_email.strip().lower()
            if "@" not in new_email or "." not in new_email:
                st.error("Inserisci un indirizzo email valido.")
            elif new_email in config.get("notification_recipients", []):
                st.warning("Questo indirizzo è già nella lista.")
            else:
                config.setdefault("notification_recipients", []).append(new_email)
                save_config(config)
                st.success(f"✓ Aggiunto: {new_email}")
                st.rerun()

    st.divider()

    # Send test email
    st.markdown('<div class="section-title">Test notifica</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.8rem;color:#666;margin-bottom:0.8rem;">Invia una email di test per verificare che tutto funzioni.</div>',
                unsafe_allow_html=True)

    col_test1, col_test2 = st.columns([3, 1])
    with col_test1:
        test_recipient = st.selectbox(
            "Invia test a",
            options=recipients if recipients else ["— nessun destinatario —"],
            disabled=len(recipients) == 0
        )
    with col_test2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        send_test = st.button("📤 Invia test", disabled=len(recipients) == 0, use_container_width=True)

    if send_test and recipients:
        env_ok, missing_vars = check_env()
        if not env_ok:
            st.error(f"Variabili d'ambiente mancanti: {', '.join(missing_vars)}")
        else:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            smtp_user = os.environ.get("SMTP_USER")
            smtp_password = os.environ.get("SMTP_PASSWORD")

            test_html = f"""
            <div style="font-family:Arial,sans-serif;max-width:500px;margin:20px auto;
                        background:#1a1a2e;border-radius:12px;padding:30px;color:white;">
                <div style="font-size:22px;font-weight:800;margin-bottom:10px;">✈️ Flight Monitor</div>
                <div style="color:#8899cc;margin-bottom:20px;">Email di test</div>
                <div style="background:#0a0a1a;border-radius:8px;padding:16px;color:#2ed573;font-size:14px;">
                    ✓ La configurazione email funziona correttamente.<br>
                    Riceverai gli alert su questo indirizzo quando i prezzi scenderanno.
                </div>
                <div style="color:#555;font-size:12px;margin-top:16px;">
                    Inviato il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}
                </div>
            </div>
            """

            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = "✈️ Flight Monitor — Test notifica"
                msg["From"] = f"Flight Monitor <{smtp_user}>"
                msg["To"] = test_recipient
                msg.attach(MIMEText(test_html, "html"))

                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.ehlo()
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_user, [test_recipient], msg.as_string())

                st.success(f"✓ Email di test inviata a {test_recipient}")
            except Exception as e:
                st.error(f"Errore invio: {str(e)}\nVerifica App Password e credenziali nel .env")

    st.divider()

    # Info box
    st.markdown("""
    <div style="background:#0f0f1a;border:1px solid #1e1e2e;border-radius:10px;padding:16px 20px;">
        <div style="font-size:0.75rem;color:#555570;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;">
            Come funziona
        </div>
        <div style="font-size:0.8rem;color:#666;line-height:1.7;">
            Le email vengono inviate dall'account Gmail configurato nel file <code style="color:#aab;">.env</code> (SMTP_USER).<br>
            I destinatari qui configurati ricevono l'alert ogni volta che lo script rileva un calo di prezzo.<br>
            Puoi aggiungere più destinatari — riceveranno tutti la stessa email.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────
# TAB 3 — LOG
# ──────────────────────────────────────────────────────────────────────────

with tab_log:
    st.markdown('<div class="section-title">📋 Log esecuzioni</div>', unsafe_allow_html=True)

    col_log1, col_log2 = st.columns([3, 1])
    with col_log2:
        if st.button("🔄 Aggiorna", use_container_width=True):
            st.rerun()
        if st.button("🗑 Pulisci log", use_container_width=True):
            if LOG_FILE.exists():
                LOG_FILE.write_text("")
            st.rerun()

    log_content = load_log(100)
    st.markdown(f'<div class="log-box">{log_content}</div>', unsafe_allow_html=True)
