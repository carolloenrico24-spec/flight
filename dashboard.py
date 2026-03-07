"""
✈️ Flight Monitor Dashboard
"""

import json
import os
import subprocess
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Flight Monitor", page_icon="✈️", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Mono', monospace; background-color: #0a0a0f; color: #e8e8f0; }
.main .block-container { padding: 2rem 2.5rem; max-width: 1400px; }
section[data-testid="stSidebar"] { background: #0f0f1a !important; border-right: 1px solid #1e1e30; }
section[data-testid="stSidebar"] .block-container { padding: 1.5rem 1.2rem; }
h1, h2, h3 { font-family: 'Syne', sans-serif !important; letter-spacing: -0.03em; }
.flight-card { background: #0f0f1a; border: 1px solid #1e1e30; border-radius: 12px; padding: 1.4rem 1.6rem; margin-bottom: 0.5rem; }
.meta-label { font-size: 0.72rem; color: #555570; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 4px; }
.trend-up { color: #ff4757; } .trend-down { color: #2ed573; }
.tag { display:inline-block; background:#1a1a2e; border:1px solid #2a2a4a; border-radius:4px; padding:2px 8px; font-size:0.7rem; color:#888; letter-spacing:0.08em; text-transform:uppercase; }
.tag.alert-tag { background:#1a0a0a; border-color:#4a1a1a; color:#ff4757; }
.tag.ok-tag { background:#0a1a0a; border-color:#1a4a1a; color:#2ed573; }
.airport-chip { background:#1a1a2e; border:1px solid #2a52be; border-radius:8px; padding:8px 12px; font-size:0.8rem; color:#aab; margin-top:4px; }
.airport-code { font-family:'Syne',sans-serif; font-weight:700; color:#4a72de; font-size:0.95rem; }
.stButton > button { font-family:'DM Mono',monospace !important; font-size:0.8rem !important; letter-spacing:0.06em; text-transform:uppercase; border-radius:8px !important; }
.stTextInput > div > div > input, .stNumberInput > div > div > input { background:#0f0f1a !important; border:1px solid #1e1e30 !important; color:#e8e8f0 !important; font-family:'DM Mono',monospace !important; border-radius:8px !important; }
hr { border-color: #1e1e30; }
[data-testid="stMetric"] { background:#0f0f1a; border:1px solid #1e1e30; border-radius:10px; padding:1rem; }
.log-box { background:#07070d; border:1px solid #1e1e30; border-radius:10px; padding:1rem; font-family:'DM Mono',monospace; font-size:0.72rem; color:#556; max-height:220px; overflow-y:auto; white-space:pre-wrap; line-height:1.6; }
.section-title { font-family:'Syne',sans-serif; font-size:0.95rem; font-weight:700; color:#e8e8f0; margin-bottom:0.8rem; margin-top:1.2rem; padding-bottom:6px; border-bottom:1px solid #1e1e30; }
.date-hint { background:#0f0f1a; border:1px solid #1e1e2e; border-radius:6px; padding:8px 12px; font-size:0.75rem; color:#556; margin-top:4px; }
</style>
""", unsafe_allow_html=True)

CONFIG_FILE = Path("config.json")
HISTORY_FILE = Path("price_history.json")
LOG_FILE = Path("flight_monitor.log")

# ════════════════════════════════════════════════════════════════════════════
# AIRPORT DATABASE
# ════════════════════════════════════════════════════════════════════════════

AIRPORTS = [
    ("MXP","Milano Malpensa","Italia"), ("LIN","Milano Linate","Italia"),
    ("BGY","Milano Bergamo","Italia"), ("FCO","Roma Fiumicino","Italia"),
    ("CIA","Roma Ciampino","Italia"), ("VCE","Venezia Marco Polo","Italia"),
    ("NAP","Napoli Capodichino","Italia"), ("CTA","Catania","Italia"),
    ("PMO","Palermo","Italia"), ("BLQ","Bologna","Italia"),
    ("TRN","Torino Caselle","Italia"), ("FLR","Firenze Peretola","Italia"),
    ("GOA","Genova","Italia"), ("BRI","Bari","Italia"),
    ("PSA","Pisa","Italia"), ("VRN","Verona","Italia"),
    ("TSF","Treviso","Italia"), ("CAG","Cagliari","Italia"),
    ("AHO","Alghero","Italia"), ("OLB","Olbia Costa Smeralda","Italia"),
    ("SUF","Lamezia Terme","Italia"), ("REG","Reggio Calabria","Italia"),
    ("LHR","Londra Heathrow","UK"), ("LGW","Londra Gatwick","UK"),
    ("STN","Londra Stansted","UK"), ("LTN","Londra Luton","UK"),
    ("CDG","Parigi Charles de Gaulle","Francia"), ("ORY","Parigi Orly","Francia"),
    ("NCE","Nizza","Francia"), ("MRS","Marsiglia","Francia"),
    ("TLS","Tolosa","Francia"), ("LYS","Lione","Francia"),
    ("AMS","Amsterdam Schiphol","Paesi Bassi"),
    ("MAD","Madrid Barajas","Spagna"), ("BCN","Barcellona","Spagna"),
    ("PMI","Palma di Maiorca","Spagna"), ("IBZ","Ibiza","Spagna"),
    ("ACE","Lanzarote","Spagna"), ("TFS","Tenerife Sud","Spagna"),
    ("LPA","Gran Canaria","Spagna"), ("FUE","Fuerteventura","Spagna"),
    ("ALC","Alicante","Spagna"), ("SVQ","Siviglia","Spagna"),
    ("FRA","Francoforte","Germania"), ("MUC","Monaco di Baviera","Germania"),
    ("BER","Berlino","Germania"), ("HAM","Amburgo","Germania"),
    ("VIE","Vienna","Austria"), ("ZRH","Zurigo","Svizzera"),
    ("GVA","Ginevra","Svizzera"), ("BRU","Bruxelles","Belgio"),
    ("LIS","Lisbona","Portogallo"), ("OPO","Porto","Portogallo"),
    ("ATH","Atene","Grecia"), ("HER","Heraklion Creta","Grecia"),
    ("SKG","Salonicco","Grecia"), ("RHO","Rodi","Grecia"),
    ("CFU","Corfù","Grecia"), ("ZTH","Zante","Grecia"),
    ("KGS","Kos","Grecia"), ("JMK","Mykonos","Grecia"),
    ("DUB","Dublino","Irlanda"), ("CPH","Copenaghen","Danimarca"),
    ("ARN","Stoccolma Arlanda","Svezia"), ("OSL","Oslo Gardermoen","Norvegia"),
    ("HEL","Helsinki","Finlandia"), ("WAW","Varsavia","Polonia"),
    ("PRG","Praga","Rep. Ceca"), ("BUD","Budapest","Ungheria"),
    ("OTP","Bucarest","Romania"), ("SOF","Sofia","Bulgaria"),
    ("IST","Istanbul","Turchia"), ("SAW","Istanbul Sabiha Gökçen","Turchia"),
    ("AYT","Antalya","Turchia"), ("ADB","Smirne Izmir","Turchia"),
    ("DXB","Dubai","UAE"), ("AUH","Abu Dhabi","UAE"),
    ("DOH","Doha","Qatar"), ("RUH","Riyadh","Arabia Saudita"),
    ("CAI","Il Cairo","Egitto"), ("HRG","Hurghada","Egitto"),
    ("SSH","Sharm el-Sheikh","Egitto"), ("CMN","Casablanca","Marocco"),
    ("RAK","Marrakech","Marocco"), ("TUN","Tunisi","Tunisia"),
    ("DJE","Djerba","Tunisia"), ("ALG","Algeri","Algeria"),
    ("JNB","Johannesburg","Sud Africa"), ("CPT","Città del Capo","Sud Africa"),
    ("NBO","Nairobi","Kenya"), ("MBA","Mombasa","Kenya"),
    ("ADD","Addis Abeba","Etiopia"), ("DAR","Dar es Salaam","Tanzania"),
    ("ZNZ","Zanzibar","Tanzania"),
    ("JFK","New York JFK","USA"), ("EWR","New York Newark","USA"),
    ("LGA","New York LaGuardia","USA"), ("LAX","Los Angeles","USA"),
    ("ORD","Chicago O'Hare","USA"), ("MIA","Miami","USA"),
    ("SFO","San Francisco","USA"), ("BOS","Boston","USA"),
    ("ATL","Atlanta","USA"), ("DFW","Dallas Fort Worth","USA"),
    ("LAS","Las Vegas","USA"), ("SEA","Seattle","USA"),
    ("DEN","Denver","USA"), ("IAD","Washington Dulles","USA"),
    ("MCO","Orlando","USA"), ("TPA","Tampa","USA"),
    ("YYZ","Toronto Pearson","Canada"), ("YVR","Vancouver","Canada"),
    ("YUL","Montréal","Canada"), ("CUN","Cancún","Messico"),
    ("NRT","Tokyo Narita","Giappone"), ("HND","Tokyo Haneda","Giappone"),
    ("KIX","Osaka Kansai","Giappone"), ("CTS","Sapporo","Giappone"),
    ("ICN","Seoul Incheon","Corea del Sud"), ("PVG","Shanghai Pudong","Cina"),
    ("PEK","Pechino","Cina"), ("HKG","Hong Kong","Hong Kong"),
    ("SIN","Singapore Changi","Singapore"), ("BKK","Bangkok Suvarnabhumi","Tailandia"),
    ("DMK","Bangkok Don Mueang","Tailandia"), ("HKT","Phuket","Tailandia"),
    ("KUL","Kuala Lumpur","Malaysia"), ("DPS","Bali","Indonesia"),
    ("CGK","Jakarta","Indonesia"), ("MNL","Manila","Filippine"),
    ("DEL","Delhi","India"), ("BOM","Mumbai","India"),
    ("MAA","Chennai","India"), ("BLR","Bangalore","India"),
    ("CMB","Colombo","Sri Lanka"),
    ("SYD","Sydney","Australia"), ("MEL","Melbourne","Australia"),
    ("BNE","Brisbane","Australia"), ("PER","Perth","Australia"),
    ("AKL","Auckland","Nuova Zelanda"),
    ("GRU","São Paulo","Brasile"), ("GIG","Rio de Janeiro","Brasile"),
    ("EZE","Buenos Aires","Argentina"), ("BOG","Bogotà","Colombia"),
    ("LIM","Lima","Perù"), ("SCL","Santiago del Cile","Cile"),
    ("CUN","Cancún","Messico"), ("HAV","L'Avana","Cuba"),
    ("PUJ","Punta Cana","Rep. Dominicana"), ("MBJ","Montego Bay","Giamaica"),
]

def search_airports(query: str) -> list:
    if not query or len(query) < 2:
        return []
    q = query.lower().strip()
    results = []
    for code, name, country in AIRPORTS:
        score = 0
        if q == code.lower(): score = 100
        elif code.lower().startswith(q): score = 80
        elif name.lower().startswith(q): score = 70
        elif q in name.lower(): score = 50
        elif q in country.lower(): score = 30
        if score > 0:
            results.append((score, code, name, country))
    results.sort(reverse=True, key=lambda x: x[0])
    return [(c, n, co) for _, c, n, co in results[:8]]

def fmt_airport(code, name, country):
    return f"{code} — {name} ({country})"

def generate_dates(start: date, end: date, max_n: int = 5) -> list:
    delta = (end - start).days
    if delta <= 0: return [str(start)]
    if delta < max_n: return [str(start + timedelta(days=i)) for i in range(delta + 1)]
    step = delta // (max_n - 1)
    dates = [str(start + timedelta(days=i * step)) for i in range(max_n)]
    if str(end) not in dates: dates[-1] = str(end)
    return dates

# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def load_config():
    defaults = {"global_thresholds": {"alert_drop_percent": 10, "alert_drop_absolute": 30},
                "notification_recipients": [], "flights": []}
    if not CONFIG_FILE.exists(): return defaults
    with open(CONFIG_FILE) as f: data = json.load(f)
    for k, v in defaults.items(): data.setdefault(k, v)
    return data

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f: json.dump(cfg, f, indent=2, ensure_ascii=False)

def load_history():
    if not HISTORY_FILE.exists(): return {}
    with open(HISTORY_FILE) as f: return json.load(f)

def load_log(lines=80):
    if not LOG_FILE.exists(): return "Nessun log ancora."
    with open(LOG_FILE) as f: all_lines = f.readlines()
    return "".join(all_lines[-lines:])

def flight_key(f): return f"{f['origin']}-{f['destination']}-{f['date']}"

def price_stats(history, key):
    entries = history.get(key, [])
    if not entries: return {"current": None, "min": None, "max": None, "avg": None, "trend": None, "history": [], "last_check": None}
    prices = [e["price"] for e in entries]
    trend = None
    if len(prices) >= 2:
        diff = prices[-1] - prices[-2]
        trend = "up" if diff > 2 else ("down" if diff < -2 else "flat")
    return {"current": prices[-1], "min": min(prices), "max": max(prices),
            "avg": round(sum(prices)/len(prices), 0), "trend": trend,
            "history": entries, "last_check": entries[-1]["timestamp"]}

def check_env():
    missing = [v for v in ["SERPAPI_KEY","SMTP_USER","SMTP_PASSWORD"] if not os.environ.get(v)]
    return len(missing)==0, missing

# Session state per le selezioni aeroporto
for k in ["orig_sel","dest_sel"]:
    if k not in st.session_state: st.session_state[k] = None

# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown('<h2 style="font-family:Syne,sans-serif;font-size:1.3rem;margin-bottom:0.1rem;">✈️ Flight Monitor</h2>', unsafe_allow_html=True)
    st.markdown('<div class="meta-label" style="margin-bottom:1rem;">control panel</div>', unsafe_allow_html=True)

    config = load_config()
    env_ok, missing_vars = check_env()
    if env_ok:
    st.success("✓ Credenziali OK")
else:
    st.warning(f"⚠️ Mancano: {', '.join(missing_vars)}")

    st.divider()

    if st.button("▶ Esegui Check Ora", use_container_width=True, type="primary"):
        if not env_ok:
            st.error("Configura prima le credenziali nel .env")
        else:
            with st.spinner("Controllo in corso..."):
                r = subprocess.run([sys.executable, "flight_monitor.py"], capture_output=True, text=True)
            st.success("✓ Check completato!") if r.returncode == 0 else st.error(f"Errore: {r.stderr[:200]}")
            st.rerun()

    if st.button("🔄 Aggiorna", use_container_width=True): st.rerun()

    st.divider()

    with st.expander("🎯 Soglie Globali"):
        thresh = config.get("global_thresholds", {})
        np_ = st.number_input("Alert se calo %", 1, 50, int(thresh.get("alert_drop_percent", 10)))
        na_ = st.number_input("Alert se calo €", 1, 500, int(thresh.get("alert_drop_absolute", 30)))
        if st.button("💾 Salva soglie", use_container_width=True):
            config["global_thresholds"].update({"alert_drop_percent": np_, "alert_drop_absolute": na_})
            save_config(config); st.success("Salvato!"); st.rerun()

    st.divider()
    st.markdown('<div class="meta-label">➕ aggiungi volo</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ── AEROPORTO PARTENZA ──
    st.markdown('<div style="font-size:0.73rem;color:#555570;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:3px;">Partenza</div>', unsafe_allow_html=True)
    orig_q = st.text_input("Cerca partenza", placeholder="Milano, MXP, Roma...",
                            key="orig_q", label_visibility="collapsed")
    if orig_q:
        res = search_airports(orig_q)
        if res:
            opts = ["— seleziona —"] + [fmt_airport(*r) for r in res]
            ch = st.selectbox("", opts, key="orig_box", label_visibility="collapsed")
            if ch != "— seleziona —":
                code = ch.split(" — ")[0]
                st.session_state.orig_sel = next((r for r in res if r[0]==code), None)
        else:
            st.caption("Nessun risultato")
    if st.session_state.orig_sel:
        c, n, co = st.session_state.orig_sel
        st.markdown(f'<div class="airport-chip"><span class="airport-code">{c}</span> &nbsp;{n}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── AEROPORTO DESTINAZIONE ──
    st.markdown('<div style="font-size:0.73rem;color:#555570;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:3px;">Destinazione</div>', unsafe_allow_html=True)
    dest_q = st.text_input("Cerca destinazione", placeholder="New York, JFK, Tokyo...",
                            key="dest_q", label_visibility="collapsed")
    if dest_q:
        res2 = search_airports(dest_q)
        if res2:
            opts2 = ["— seleziona —"] + [fmt_airport(*r) for r in res2]
            ch2 = st.selectbox("", opts2, key="dest_box", label_visibility="collapsed")
            if ch2 != "— seleziona —":
                code2 = ch2.split(" — ")[0]
                st.session_state.dest_sel = next((r for r in res2 if r[0]==code2), None)
        else:
            st.caption("Nessun risultato")
    if st.session_state.dest_sel:
        c2, n2, co2 = st.session_state.dest_sel
        st.markdown(f'<div class="airport-chip"><span class="airport-code">{c2}</span> &nbsp;{n2}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── ETICHETTA ──
    lbl = st.text_input("Etichetta", placeholder="Vacanza estate NY", key="lbl")

    # ── DATE ANDATA (range flessibile) ──
    st.markdown('<div style="font-size:0.73rem;color:#555570;text-transform:uppercase;letter-spacing:0.1em;margin:8px 0 3px;">📅 Periodo andata</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: d_from = st.date_input("Dal", value=date.today()+timedelta(30), min_value=date.today(), key="d_from", label_visibility="collapsed")
    with c2: d_to = st.date_input("Al", value=date.today()+timedelta(37), min_value=date.today(), key="d_to", label_visibility="collapsed")

    if d_from and d_to and d_to >= d_from:
        n_d = min((d_to-d_from).days+1, 5)
        delta_d = (d_to-d_from).days
        st.markdown(f'<div class="date-hint">Controllerà {n_d} data{"" if n_d==1 else "e"} in {delta_d} giorni</div>', unsafe_allow_html=True)

    # ── DATE RITORNO (opzionale, range) ──
    use_ret = st.checkbox("Volo di ritorno", key="use_ret")
    if use_ret:
        st.markdown('<div style="font-size:0.73rem;color:#555570;text-transform:uppercase;letter-spacing:0.1em;margin:6px 0 3px;">📅 Periodo ritorno</div>', unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        with c3: r_from = st.date_input("Dal", value=d_to+timedelta(7), min_value=d_from, key="r_from", label_visibility="collapsed")
        with c4: r_to = st.date_input("Al", value=d_to+timedelta(14), min_value=d_from, key="r_to", label_visibility="collapsed")
    else:
        r_from = r_to = None

    # ── ADULTI + MAX PREZZO ──
    ca, cb = st.columns(2)
    with ca: adults = st.number_input("Adulti", 1, 9, 1, key="adults")
    with cb: max_p = st.number_input("Max €", 0, 9999, 0, key="max_p")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    if st.button("➕ Aggiungi volo", use_container_width=True, type="primary"):
        orig = st.session_state.orig_sel
        dest = st.session_state.dest_sel
        if not orig: st.error("Seleziona aeroporto di partenza")
        elif not dest: st.error("Seleziona aeroporto di destinazione")
        elif orig[0] == dest[0]: st.error("Partenza e destinazione uguali")
        elif d_to < d_from: st.error("La data 'Al' deve essere dopo 'Dal'")
        else:
            out_dates = generate_dates(d_from, d_to)
            ret_dates = generate_dates(r_from, r_to) if use_ret and r_from else [None]
            label = lbl or f"{orig[0]} → {dest[0]}"
            added = 0
            for od in out_dates:
                for rd in ret_dates:
                    entry = {
                        "label": label,
                        "origin": orig[0], "origin_name": orig[1],
                        "destination": dest[0], "destination_name": dest[1],
                        "date": od, "adults": adults, "currency": "EUR",
                    }
                    if rd: entry["return_date"] = rd
                    if max_p > 0: entry["max_price"] = max_p
                    config["flights"].append(entry)
                    added += 1
            save_config(config)
            st.session_state.orig_sel = None
            st.session_state.dest_sel = None
            st.success(f"✓ Aggiunto! {added} combinazione/i di date.")
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

config = load_config()
history = load_history()
flights = config.get("flights", [])

st.markdown("""
<div style="display:flex;align-items:baseline;gap:14px;margin-bottom:0.2rem;">
    <h1 style="font-family:Syne,sans-serif;font-size:2.2rem;font-weight:800;letter-spacing:-0.04em;margin:0;color:#e8e8f0;">Flight Monitor</h1>
    <span class="tag">dashboard</span>
</div>
""", unsafe_allow_html=True)
st.markdown(f'<div class="meta-label">{len(flights)} tratte monitorate · {datetime.now().strftime("%d/%m/%Y %H:%M")}</div>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

tab_flights, tab_notifications, tab_log = st.tabs(["✈️  Voli", "📧  Notifiche", "📋  Log"])

# ──────────────────────────────────────────────────────────────────────────
# TAB VOLI
# ──────────────────────────────────────────────────────────────────────────
with tab_flights:
    if not flights:
        st.markdown('<div style="background:#0f0f1a;border:1px dashed #2a2a3a;border-radius:12px;padding:40px;text-align:center;color:#333;margin-top:1rem;"><div style="font-size:1.5rem;margin-bottom:8px;">✈️</div><div>Nessun volo monitorato.<br><span style="font-size:0.8rem;color:#2a2a3a;">Cerca un aeroporto dal pannello laterale.</span></div></div>', unsafe_allow_html=True)
    else:
        all_stats = [price_stats(history, flight_key(f)) for f in flights]
        active = sum(1 for s in all_stats if s["current"])
        n_alerts = sum(1 for f,s in zip(flights,all_stats) if s["current"] and f.get("max_price") and s["current"]<=f["max_price"])
        n_drops = sum(1 for s in all_stats if s["trend"]=="down")

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Tratte", len(flights)); c2.metric("Con dati", active)
        c3.metric("🔴 Alert", n_alerts); c4.metric("📉 In calo", n_drops)
        st.markdown("<br>", unsafe_allow_html=True)

        try:
            import plotly.graph_objects as go
            has_plotly = True
        except: has_plotly = False

        # Raggruppa per label
        groups = {}
        for i, f in enumerate(flights):
            lbl = f.get("label", flight_key(f))
            groups.setdefault(lbl, []).append((i, f))

        for label, group in groups.items():
            f0 = group[0][1]
            st.markdown(f"""
            <div style="font-family:Syne,sans-serif;font-size:1rem;font-weight:700;color:#e8e8f0;
                        margin:16px 0 8px;padding-left:4px;border-left:3px solid #2a52be;">
                {label}
                <span style="font-size:0.72rem;color:#444;font-weight:400;margin-left:8px;">
                    {f0['origin']} → {f0['destination']} · {len(group)} data/e
                </span>
            </div>
            """, unsafe_allow_html=True)

            for i, f in group:
                k = flight_key(f)
                s = price_stats(history, k)
                is_alert = s["current"] and f.get("max_price") and s["current"] <= f["max_price"]
                t_icon = {"up":"↑","down":"↓","flat":"→",None:"—"}.get(s["trend"],"—")
                t_cls = {"up":"trend-up","down":"trend-down"}.get(s["trend"],"")

                ci, cp, cs, cd = st.columns([3,2,3,1])

                with ci:
                    ds = f["date"] + (f" → {f['return_date']}" if f.get("return_date") else "")
                    on = f.get("origin_name", f["origin"]); dn = f.get("destination_name", f["destination"])
                    st.markdown(f"""
                    <div class="flight-card">
                        <div style="font-size:0.95rem;font-weight:600;color:#e8e8f0;">📅 {ds}</div>
                        <div style="font-size:0.72rem;color:#555570;margin-top:4px;">{f['origin']} {on} → {f['destination']} {dn} · {f.get('adults',1)} pax</div>
                        <div style="margin-top:8px;">
                            {"<span class='tag alert-tag'>⚠️ SOTTO SOGLIA</span>" if is_alert else "<span class='tag ok-tag'>✓ ok</span>"}
                            {f"<span class='tag' style='margin-left:5px;'>Max €{f['max_price']}</span>" if f.get('max_price') else ""}
                        </div>
                    </div>""", unsafe_allow_html=True)

                with cp:
                    if s["current"]:
                        pc = "#ff4757" if is_alert else ("#2ed573" if s["trend"]=="down" else "#e8e8f0")
                        st.markdown(f'<div class="flight-card" style="text-align:center;"><div class="meta-label">prezzo attuale</div><div style="font-family:Syne,sans-serif;font-size:2.2rem;font-weight:800;color:{pc};line-height:1.1;">€{s["current"]}</div><div class="{t_cls}" style="font-size:1rem;margin-top:4px;">{t_icon}</div></div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="flight-card" style="text-align:center;"><div class="meta-label">prezzo attuale</div><div style="font-size:1.6rem;color:#2a2a3a;font-family:Syne,sans-serif;margin-top:8px;">—</div><div style="font-size:0.7rem;color:#333;margin-top:4px;">esegui check</div></div>', unsafe_allow_html=True)

                with cs:
                    if s["current"]:
                        lc = "—"
                        if s["last_check"]:
                            try: lc = datetime.fromisoformat(s["last_check"]).strftime("%d/%m %H:%M")
                            except: lc = s["last_check"][:16]
                        st.markdown(f'<div class="flight-card"><div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;"><div><div class="meta-label">minimo</div><div style="font-family:Syne,sans-serif;font-weight:700;color:#2ed573;">€{s["min"]}</div></div><div><div class="meta-label">massimo</div><div style="font-family:Syne,sans-serif;font-weight:700;color:#ff4757;">€{s["max"]}</div></div><div><div class="meta-label">media</div><div style="font-family:Syne,sans-serif;font-weight:700;">€{s["avg"]}</div></div><div><div class="meta-label">ultimo check</div><div style="font-size:0.75rem;color:#666;">{lc}</div></div></div></div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="flight-card" style="color:#2a2a3a;font-size:0.8rem;">Nessun dato ancora</div>', unsafe_allow_html=True)

                with cd:
                    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                    if st.button("🗑", key=f"del_{i}", help="Rimuovi"):
                        config["flights"].pop(i); save_config(config); st.rerun()

                if s["history"] and len(s["history"]) >= 2 and has_plotly:
                    xs = [e["timestamp"][:16].replace("T"," ") for e in s["history"]]
                    ys = [e["price"] for e in s["history"]]
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=xs,y=ys,fill='tozeroy',fillcolor='rgba(42,82,190,0.06)',line=dict(color='rgba(0,0,0,0)'),showlegend=False,hoverinfo='skip'))
                    fig.add_trace(go.Scatter(x=xs,y=ys,mode='lines+markers',line=dict(color='#2a52be',width=2),marker=dict(size=5,color='#4a72de',line=dict(color='#0a0a0f',width=1)),hovertemplate='€%{y}<br>%{x}<extra></extra>',showlegend=False))
                    if f.get("max_price"): fig.add_hline(y=f["max_price"],line_dash="dash",line_color="#ff4757",line_width=1,annotation_text=f"soglia €{f['max_price']}",annotation_font_color="#ff4757",annotation_font_size=10)
                    fig.update_layout(height=100,margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',xaxis=dict(showgrid=False,zeroline=False,tickfont=dict(size=9,color='#444')),yaxis=dict(showgrid=True,gridcolor='#1a1a2a',zeroline=False,tickfont=dict(size=9,color='#444'),tickprefix='€'))
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────
# TAB NOTIFICHE
# ──────────────────────────────────────────────────────────────────────────
with tab_notifications:
    st.markdown('<div class="section-title">📧 Destinatari Notifiche</div>', unsafe_allow_html=True)
    recipients = config.get("notification_recipients", [])

    if recipients:
        for idx, email in enumerate(recipients):
            ce, cr = st.columns([5,1])
            with ce: st.markdown(f'<div style="background:#0f0f1a;border:1px solid #1e1e30;border-radius:8px;padding:10px 14px;font-size:0.82rem;color:#aab;margin-bottom:6px;">📧 {email}</div>', unsafe_allow_html=True)
            with cr:
                if st.button("✕", key=f"rm_{idx}"):
                    config["notification_recipients"].pop(idx); save_config(config); st.rerun()
    else:
        st.markdown('<div style="background:#0f0f1a;border:1px dashed #2a2a3a;border-radius:10px;padding:20px;text-align:center;color:#333;font-size:0.85rem;margin-bottom:1rem;">Nessun destinatario configurato.</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Aggiungi destinatario</div>', unsafe_allow_html=True)
    with st.form("add_r", clear_on_submit=True):
        ci2, cb2 = st.columns([4,1])
        with ci2: new_em = st.text_input("Email", placeholder="mario@example.com", label_visibility="collapsed")
        with cb2: add_r = st.form_submit_button("➕", use_container_width=True)
        if add_r:
            e = new_em.strip().lower()
            if "@" not in e or "." not in e: st.error("Email non valida")
            elif e in config.get("notification_recipients",[]): st.warning("Già presente")
            else:
                config.setdefault("notification_recipients",[]).append(e)
                save_config(config); st.success(f"✓ {e}"); st.rerun()

    st.divider()
    st.markdown('<div class="section-title">Test notifica</div>', unsafe_allow_html=True)
    ct1, ct2 = st.columns([3,1])
    with ct1: test_r = st.selectbox("Invia a", recipients if recipients else ["— nessun destinatario —"], disabled=not recipients)
    with ct2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        send_t = st.button("📤 Test", disabled=not recipients, use_container_width=True)

    if send_t and recipients:
        ev_ok, ev_miss = check_env()
        if not ev_ok: st.error(f"Variabili mancanti: {', '.join(ev_miss)}")
        else:
            import smtplib
            from email.mime.multipart import MIMEMultipart as MM
            from email.mime.text import MIMEText as MT
            su = os.environ.get("SMTP_USER"); sp = os.environ.get("SMTP_PASSWORD")
            html = f'<div style="font-family:Arial,sans-serif;max-width:480px;margin:20px auto;background:#1a1a2e;border-radius:12px;padding:30px;color:white;"><div style="font-size:22px;font-weight:800;margin-bottom:10px;">✈️ Flight Monitor</div><div style="background:#0a0a1a;border-radius:8px;padding:16px;color:#2ed573;">✓ Email configurata correttamente.</div><div style="color:#555;font-size:12px;margin-top:16px;">{datetime.now().strftime("%d/%m/%Y %H:%M")}</div></div>'
            try:
                msg = MM("alternative"); msg["Subject"]="✈️ Flight Monitor — Test"; msg["From"]=f"Flight Monitor <{su}>"; msg["To"]=test_r
                msg.attach(MT(html,"html"))
                with smtplib.SMTP("smtp.gmail.com",587) as srv: srv.ehlo(); srv.starttls(); srv.login(su,sp); srv.sendmail(su,[test_r],msg.as_string())
                st.success(f"✓ Email inviata a {test_r}")
            except Exception as ex: st.error(f"Errore: {ex}")

# ──────────────────────────────────────────────────────────────────────────
# TAB LOG
# ──────────────────────────────────────────────────────────────────────────
with tab_log:
    st.markdown('<div class="section-title">📋 Log esecuzioni</div>', unsafe_allow_html=True)
    cl1, cl2 = st.columns([3,1])
    with cl2:
        if st.button("🔄 Aggiorna", use_container_width=True): st.rerun()
        if st.button("🗑 Pulisci", use_container_width=True):
            if LOG_FILE.exists(): LOG_FILE.write_text("")
            st.rerun()
    st.markdown(f'<div class="log-box">{load_log(100)}</div>', unsafe_allow_html=True)
