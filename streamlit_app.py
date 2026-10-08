"""
MedSupply Uganda - B2B pharma marketplace (single-file Streamlit app).

Streamlit Cloud > Settings > Secrets:
    ADMIN_EMAIL    = "you@example.com"
    ADMIN_PASSWORD = "a-long-random-password"
    DEMO_DATA      = false        # false = no sample customer/orders, no fake payments (use true while testing)
    SUPABASE_URL   = "https://xxxx.supabase.co"
    SUPABASE_KEY   = "service_role key (server-side only; never the anon key)"
    COMPANY_TIN    = "your URA TIN"      # optional, printed on invoices
    [smtp]                                # needed for order emails and password reset
    email = "..." ; password = "..." ; server = "smtp.gmail.com" ; port = 465
    # optional: WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_TOKEN

One-time Supabase SQL (SQL editor):
    create table app_state (id text primary key, data text not null, updated_at timestamptz default now());
    alter table app_state enable row level security;
"""
import datetime as dt
import hashlib
import hmac
import html
import json
import os
import random
import re
import secrets
import smtplib
import threading
import time
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="MedSupply Uganda | B2B Pharma Marketplace", page_icon="💊",
                   layout="wide", initial_sidebar_state="expanded")


# ======================================================================
# CONFIG & HELPERS
# ======================================================================
def secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return default


DEMO = str(secret("DEMO_DATA", True)).strip(
).lower() not in ("false", "0", "no")
MANAGER = {"name": "Okiror Innocent", "phone": "+256763212490"}
COMPANY = {"name": "MedSupply Uganda Limited", "bank": "Stanbic Bank Uganda", "acct": "9030012345678",
           "tin": secret("COMPANY_TIN", "")}
STATUSES = ["Processing", "Dispatched", "Delivered"]
STEP_ICONS = ["🕒", "🚚", "✅"]
CATS = {"Antibiotics": "💊", "Analgesics": "🩹", "Antimalarial": "🦟",
        "Medical Consumables": "🧤", "Fluids & Nutrition": "💧"}
PAY_METHODS = ["MTN Mobile Money", "Airtel Money",
               "Trade Credit Line", "Cash on Delivery"]
UNPAID = ("Pending Payment", "On Credit", "Pay on Delivery")
DB_FILE = os.environ.get("MEDSUPPLY_DB", "medsupply_db.json")
PW_ITER = 600_000
# VAT by category, e.g. {"Medical Consumables": 0.18}. Left empty (no VAT line) until you confirm the
# correct treatment of each category with URA or your accountant.
VAT_RATES = {}

# Streamlit 1.50+ replaced use_container_width with width="stretch"
_v = tuple(int(x) for x in re.findall(r"\d+", st.__version__)[:2])
FULL = {"width": "stretch"} if _v >= (1, 50) else {"use_container_width": True}


def ugx(n):
    try:
        return f"UGX {float(n):,.0f}"
    except Exception:
        return "UGX 0"


def esc(x): return html.escape(str(x))
def now(): return dt.datetime.now().strftime("%Y-%m-%d %I:%M %p")
def today(): return dt.date.today()
def valid_phone(p): return re.match(r"^\+256[0-9]{9}$", p.strip()) is not None
def valid_email(e): return re.match(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e.strip()) is not None


def disc_for(q): return 0.10 if q >= 50 else 0.05 if q >= 10 else 0.0
def vat_rate(cat): return float(VAT_RATES.get(cat, 0.0))


def hp(p, salt=None):
    salt = salt or secrets.token_hex(8)
    return f"{salt}${hashlib.pbkdf2_hmac('sha256', p.encode(), salt.encode(), PW_ITER).hex()}"


def check_pw(p, stored):
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hp(p, salt), stored)


def exp_days(x):
    try:
        if pd.isna(x):
            return 9999
        return (pd.to_datetime(x).date() - today()).days
    except Exception:
        return 9999


# ======================================================================
# THEME
# ======================================================================
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;800&family=Source+Sans+3:wght@400;600&display=swap');
:root{--ink:#10282B;--teal:#0E6B63;--sun:#F2B600;--paper:#F5F7F6;--line:#D9E2DF;--red:#C0392B}
@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
@keyframes pop{from{opacity:0;transform:scale(.94)}to{opacity:1;transform:scale(1)}}
@keyframes ring{0%,100%{box-shadow:0 0 0 0 rgba(14,107,99,.5)}50%{box-shadow:0 0 0 7px rgba(14,107,99,0)}}
@keyframes ringg{0%,100%{box-shadow:0 0 0 0 rgba(29,185,84,.55)}50%{box-shadow:0 0 0 7px rgba(29,185,84,0)}}
@keyframes drift{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
@keyframes bob{0%,100%{transform:translateY(0) rotate(-6deg)}50%{transform:translateY(-9px) rotate(4deg)}}
@keyframes sheen{from{transform:translateX(-130%)}to{transform:translateX(320%)}}
@keyframes ticker{to{transform:translateX(-100%)}}
@keyframes breathe{0%,100%{opacity:1}50%{opacity:.55}}
.stApp{background:var(--paper);font-family:'Source Sans 3',sans-serif}
.stApp h1,.stApp h2,.stApp h3{font-family:'Bricolage Grotesque',sans-serif;color:var(--ink);letter-spacing:-.01em}
.stApp .stMarkdown,.stApp label,.stApp [data-testid=stCaptionContainer]{color:var(--ink)}
.block-container{padding-top:1.5rem;max-width:1200px}
[data-testid=stSidebar]{background:var(--ink)}
[data-testid=stSidebar] *{color:#E8F1EF !important}
[data-testid=stSidebar] .stButton button{background:transparent;border:1px solid #4B6B6A}
[data-testid=stSidebar] [role=radiogroup] label{padding:7px 10px;border-radius:8px;transition:background .18s,padding-left .18s;width:100%}
[data-testid=stSidebar] [role=radiogroup] label:hover{background:#1B3E42;padding-left:16px}
@supports selector(:has(*)){
[data-testid=stSidebar] [role=radiogroup] label>div:first-child{display:none}
[data-testid=stSidebar] [role=radiogroup] label:has(input:checked){background:#1B3E42;box-shadow:inset 4px 0 0 var(--sun);padding-left:16px;font-weight:600}}
[data-testid=stVerticalBlockBorderWrapper]{background:#fff;border-radius:10px;border-color:var(--line);animation:rise .45s ease both;transition:transform .2s,box-shadow .2s}
[data-testid=stVerticalBlockBorderWrapper]:hover{transform:translateY(-2px);box-shadow:0 8px 22px rgba(16,40,43,.10)}
[data-testid=stColumn]:nth-child(2) [data-testid=stVerticalBlockBorderWrapper],[data-testid=column]:nth-child(2) [data-testid=stVerticalBlockBorderWrapper]{animation-delay:.07s}
[data-testid=stColumn]:nth-child(3) [data-testid=stVerticalBlockBorderWrapper],[data-testid=column]:nth-child(3) [data-testid=stVerticalBlockBorderWrapper]{animation-delay:.14s}
button[kind=primary]{background:var(--teal);border:0;font-weight:600;color:#fff}
button[kind=primary]:hover:not(:disabled){background:#0A524C}
.stButton button,.stDownloadButton button{transition:transform .12s,box-shadow .12s,background .15s}
.stButton button:hover:not(:disabled),.stDownloadButton button:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(16,40,43,.15)}
.stButton button:active:not(:disabled){transform:scale(.97)}
.hero{position:relative;overflow:hidden;background:linear-gradient(115deg,#10282B,#0F4B47,#10282B);background-size:220% 220%;animation:drift 14s ease infinite;border-left:8px solid var(--sun);border-radius:10px;padding:1.6rem 2rem;margin-bottom:1rem}
.hero:after{content:"💊";position:absolute;right:30px;top:12px;font-size:4.2rem;animation:bob 5.5s ease-in-out infinite}
.hero h1{color:#fff !important;font-size:2.1rem;margin:0 0 .3rem}
.hero p{color:#CFE0DC;margin:0 0 .8rem;font-size:1.05rem}
.chip{display:inline-block;background:#1B3E42;color:#fff;border-radius:6px;padding:4px 12px;margin:0 8px 6px 0;font-size:.88rem}
.ticker{overflow:hidden;white-space:nowrap;background:#E3F1EE;border-radius:8px;padding:7px 0;margin-bottom:1rem;color:var(--ink);font-size:.92rem}
.ticker div{display:inline-block;padding-left:100%;animation:ticker 38s linear infinite}
.ticker:hover div{animation-play-state:paused}
.pill{display:inline-block;padding:2px 10px;border-radius:99px;font-size:.78rem;font-weight:600;margin-right:4px}
.ok{background:#DDF3EC;color:#0A5A44}.low{background:#FFF1CC;color:#7A5A00;animation:breathe 3s ease infinite}
.out{background:#FBE1DE;color:#8E241C}.warn{background:#FFE9D2;color:#8A4B00}.info{background:#E1ECFA;color:#1B4F8A}
.ico{width:42px;height:42px;border-radius:12px;background:#E3F1EE;display:flex;align-items:center;justify-content:center;font-size:1.4rem}
.price{font-family:'Bricolage Grotesque',sans-serif;font-size:1.35rem;font-weight:800;color:var(--teal)}
.kpi{position:relative;overflow:hidden;background:#fff;border:1px solid var(--line);border-top:4px solid var(--teal);border-radius:10px;padding:.8rem 1rem;animation:pop .45s ease both}
.kpi.sun{border-top-color:var(--sun)}.kpi.red{border-top-color:var(--red)}
.kpi .l{font-size:.82rem;color:#567}.kpi .s{font-size:.8rem;color:#678}
.kpi .v{font-family:'Bricolage Grotesque',sans-serif;font-size:1.55rem;font-weight:800;color:var(--ink);line-height:1.25}
.kpi:after{content:"";position:absolute;top:0;left:0;width:35%;height:100%;background:linear-gradient(100deg,transparent,rgba(255,255,255,.7),transparent);animation:sheen 1.6s ease .5s 1 both}
.steps{display:flex;gap:6px;margin:.4rem 0 .6rem}
.steps span{flex:1;text-align:center;padding:5px;border-radius:6px;background:#E6ECEA;font-size:.82rem;color:#456;transition:background .4s}
.steps .done{background:var(--teal);color:#fff}
.steps .now{animation:ring 1.9s ease infinite}
.steps.cancel span{background:#FBE1DE;color:#8E241C}
.live{display:inline-block;width:9px;height:9px;border-radius:50%;background:#1DB954;margin-right:7px;animation:ringg 1.6s ease infinite}
.al{padding:8px 12px;border-radius:8px;background:#fff;border-left:5px solid var(--sun);margin-bottom:6px;animation:rise .4s ease both}
.al.red{border-left-color:var(--red)}.al.ok{border-left-color:#1DB954}.al.new{background:#FFFBEA;font-weight:600}
.tl{border-left:2px solid var(--line);margin-left:6px;padding-left:16px}
.tl div{position:relative;margin-bottom:8px;font-size:.92rem}
.tl div:before{content:"";position:absolute;left:-23px;top:6px;width:10px;height:10px;border-radius:50%;background:var(--teal)}
.empty{text-align:center;padding:2.2rem 1rem;border:2px dashed var(--line);border-radius:12px;color:#567;background:#fff}
.empty .big{font-size:2.6rem;animation:bob 4s ease-in-out infinite;display:inline-block}
@media(max-width:700px){.hero h1{font-size:1.5rem}.hero:after{display:none}}
@media(prefers-reduced-motion:reduce){*{animation:none !important;transition:none !important}}
</style>""", unsafe_allow_html=True)


# ======================================================================
# TABLE SCHEMAS
# ======================================================================
ORDER_COLS = ["OrderID", "Outlet", "Recipient Name", "Recipient Phone", "Recipient Email", "Delivery Location", "Items",
              "Product Name", "Batch Number", "Quantity", "Subtotal (UGX)", "Total Amount (UGX)", "Payment Method",
              "Payment Status", "Item Verified", "Status", "Date", "Placed At", "Dispatch Time", "Delivery Time",
              "Driver", "Driver Phone", "ETA", "Notes", "Timeline", "Account", "VAT (UGX)"]
TICKET_COLS = ["TicketID", "OrderID", "Outlet", "Contact",
               "Issue", "Details", "Status", "Created", "Response"]
INV_COLS = ["Item ID", "Product Name", "Category", "Unit Price (UGX)", "Stock Quantity", "Reorder Level",
            "Batch Number", "Expiry Date", "NDA Reg No", "Cost Price (UGX)", "Rx Only"]
BATCH_COLS = ["Item ID", "Batch Number", "Expiry Date", "Qty"]
OUTLET_COLS = ["ID", "Business Name", "Contact Name", "Phone", "Email", "Location", "License No", "Verified",
               "Credit Limit (UGX)", "Used Credit (UGX)", "Status"]
FRAMES = {"outlets": OUTLET_COLS, "inventory": INV_COLS, "batches": BATCH_COLS, "orders": ORDER_COLS,
          "tickets": TICKET_COLS, "audit": ["Time", "Actor", "Action"], "notifs": ["To", "Time", "Text", "Read"]}
TABLES = ("users",) + tuple(FRAMES)


# ======================================================================
# PERSISTENCE (Supabase if configured, otherwise a local JSON file)
# ======================================================================
def _sb():
    url, key = secret("SUPABASE_URL"), secret("SUPABASE_KEY")
    if not (url and key):
        return None
    url = str(url).strip().strip("\"'").rstrip("/")
    if not url.startswith("http"):
        url = "https://" + url
    # tolerate the API path being pasted in
    url = re.sub(r"/rest/v1$", "", url)
    return url, str(key).strip().strip("\"'")


def _explain(e):
    """Turn a low-level error into something the owner can act on."""
    if isinstance(e, requests.exceptions.ConnectionError):
        return ("Cannot reach Supabase. The project may be paused (restore it in the Supabase dashboard) "
                "or SUPABASE_URL is misspelled.")
    if isinstance(e, requests.exceptions.Timeout):
        return "Supabase did not answer in time. Try again in a moment."
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        c = e.response.status_code
        if c in (401, 403):
            return "Supabase rejected the key. Use the service_role key in SUPABASE_KEY."
        if c == 404:
            return "The app_state table was not found. Run the one-time SQL from the top of app.py."
        return f"Supabase returned HTTP {c}."
    return str(e)[:150]


def backend_read():
    """Returns ('ok', text) | ('empty', None) | ('error', message)."""
    sb = _sb()
    if sb:
        last = None
        for attempt in range(3):  # retry temporary network failures
            try:
                r = requests.get(f"{sb[0]}/rest/v1/app_state", params={"id": "eq.main", "select": "data"},
                                 headers={"apikey": sb[1], "Authorization": f"Bearer {sb[1]}"}, timeout=10)
                r.raise_for_status()
                rows = r.json()
                return ("ok", rows[0]["data"]) if rows else ("empty", None)
            except requests.exceptions.HTTPError as e:
                # wrong key or missing table won't fix itself, so no retry
                return "error", _explain(e)
            except Exception as e:
                last = e
                time.sleep(1 + attempt)
        return "error", _explain(last)
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, encoding="utf-8") as f:
                return "ok", f.read()
        except Exception as e:
            return "error", str(e)[:150]
    return "empty", None


def backend_write(blob):
    sb = _sb()
    try:
        if sb:
            for attempt in range(2):
                try:
                    r = requests.post(f"{sb[0]}/rest/v1/app_state", timeout=10, json={"id": "main", "data": blob},
                                      headers={"apikey": sb[1], "Authorization": f"Bearer {sb[1]}",
                                               "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"})
                    if r.status_code in (200, 201, 204):
                        return True
                except requests.exceptions.RequestException:
                    pass
                time.sleep(1)
            return False
        with open(DB_FILE + ".tmp", "w", encoding="utf-8") as f:
            f.write(blob)
        os.replace(DB_FILE + ".tmp", DB_FILE)
        return True
    except Exception:
        return False


def _clean(v):
    if v is None or (not isinstance(v, (str, list, dict)) and pd.isna(v)):
        return None
    if hasattr(v, "item") and not isinstance(v, str):
        v = v.item()
    if isinstance(v, dt.date):
        return v.isoformat()
    return v


def serialize(d=None):
    d = d if d is not None else db
    out = {"v": 2, "users": d["users"]}
    for t in FRAMES:
        out[t] = [{k: _clean(v) for k, v in r.items()}
                  for r in d[t].to_dict("records")]
    return json.dumps(out)


def fix_types(d):
    inv, bt, o, ot, n = d["inventory"], d["batches"], d["orders"], d["outlets"], d["notifs"]
    for c in ("Unit Price (UGX)", "Cost Price (UGX)"):
        inv[c] = pd.to_numeric(inv[c], errors="coerce").fillna(0.0)
    for c, dflt in (("Stock Quantity", 0), ("Reorder Level", 100)):
        inv[c] = pd.to_numeric(
            inv[c], errors="coerce").fillna(dflt).astype(int)
    inv["Rx Only"] = inv["Rx Only"].fillna(False).astype(bool)
    inv["Expiry Date"] = pd.to_datetime(
        inv["Expiry Date"], errors="coerce").dt.date
    bt["Qty"] = pd.to_numeric(bt["Qty"], errors="coerce").fillna(0).astype(int)
    bt["Expiry Date"] = pd.to_datetime(
        bt["Expiry Date"], errors="coerce").dt.date
    for c in ("Credit Limit (UGX)", "Used Credit (UGX)"):
        ot[c] = pd.to_numeric(ot[c], errors="coerce").fillna(0)
    ot["Verified"] = ot["Verified"].fillna(False).astype(bool)
    n["Read"] = n["Read"].fillna(False).astype(bool)
    numeric = ("Quantity", "Subtotal (UGX)", "Total Amount (UGX)", "VAT (UGX)")
    for c in ORDER_COLS:
        o[c] = pd.to_numeric(o[c], errors="coerce").fillna(
            0) if c in numeric else o[c].fillna("")
    for t in ("tickets", "audit"):
        d[t] = d[t].fillna("")
    return d


def deserialize(s):
    raw = json.loads(s)
    d = {"users": raw.get("users", {})}
    for t, cols in FRAMES.items():
        recs = raw.get(t) or []
        d[t] = pd.DataFrame(
            recs, columns=cols) if recs else pd.DataFrame(columns=cols)
    d = fix_types(d)
    if d["batches"].empty and not d["inventory"].empty:  # tolerate data saved without batches
        d["batches"] = pd.DataFrame({"Item ID": d["inventory"]["Item ID"], "Batch Number": d["inventory"]["Batch Number"],
                                     "Expiry Date": d["inventory"]["Expiry Date"], "Qty": d["inventory"]["Stock Quantity"]})
    return d


# ======================================================================
# SEED DATA
# ======================================================================
def sync_inventory(d=None):
    """Stock Quantity = in-date boxes across batches; Batch/Expiry shown = earliest-expiring sellable batch."""
    d = d if d is not None else db
    inv, bt = d["inventory"], d["batches"]
    for i, r in inv.iterrows():
        mine = bt[(bt["Item ID"] == r["Item ID"]) & (bt["Qty"] > 0)]
        if mine.empty:
            inv.at[i, "Stock Quantity"] = 0
            continue
        mine = mine.assign(_d=mine["Expiry Date"].map(exp_days))
        ok = mine[mine["_d"] >= 0]
        inv.at[i, "Stock Quantity"] = int(ok["Qty"].sum())
        pick = (ok if len(ok) else mine).sort_values("_d").iloc[0]
        inv.at[i, "Batch Number"] = pick["Batch Number"]
        inv.at[i, "Expiry Date"] = pick["Expiry Date"]


def build_order(oid, outlet, name, phone, email, addr, lines, method, notes="", ts=None, account=""):
    ts = ts or now()
    sub = sum(l["qty"] * l["price"] for l in lines)
    net = sum(l["qty"] * l["price"] * (1 - l["disc"]) for l in lines)
    vat = sum(l["qty"] * l["price"] * (1 - l["disc"])
              * l.get("vat", 0.0) for l in lines)
    pay = {"Trade Credit Line": "On Credit",
           "Cash on Delivery": "Pay on Delivery"}.get(method, "Pending Payment")
    per = {}
    for l in lines:
        per[l["name"].split(" (")[0]] = per.get(
            l["name"].split(" (")[0], 0) + l["qty"]
    return {"OrderID": oid, "Outlet": outlet, "Recipient Name": name, "Recipient Phone": phone, "Recipient Email": email,
            "Delivery Location": addr, "Items": json.dumps(lines),
            "Product Name": ", ".join(f"{k} ×{v}" for k, v in per.items()),
            "Batch Number": ", ".join(sorted({l["batch"] for l in lines})), "Quantity": sum(l["qty"] for l in lines),
            "Subtotal (UGX)": sub, "Total Amount (UGX)": net + vat, "Payment Method": method, "Payment Status": pay,
            "Item Verified": "Pending Inspection", "Status": "Processing", "Date": ts[:10], "Placed At": ts,
            "Dispatch Time": "Pending", "Delivery Time": "Pending", "Driver": "", "Driver Phone": "", "ETA": "",
            "Notes": notes, "Timeline": json.dumps([[ts, "Order placed"]]), "Account": account, "VAT (UGX)": vat}


def seed():
    admin_pw = secret("ADMIN_PASSWORD")
    generated = not admin_pw
    if generated:  # never ship a guessable default
        admin_pw = secrets.token_urlsafe(9)
        print(
            f"[MedSupply] ADMIN_PASSWORD is not set. One-time admin password: {admin_pw}", flush=True)
    admin = secret("ADMIN_EMAIL", "okirorinnocent49@gmail.com").strip().lower()
    users = {admin: dict(password=hp(admin_pw), business_name="MedSupply HQ", contact_name=MANAGER["name"],
                         phone=MANAGER["phone"], location="Kampala Central", role="Staff / Admin", favs=[],
                         default_pw=generated)}
    empty = {t: pd.DataFrame(columns=c) for t, c in FRAMES.items()}
    if not DEMO:
        return {"users": users, **empty}
    users["sarah@carepharma.com"] = dict(password=hp("password123"), business_name="Kampala Care Pharmacy",
                                         contact_name="Dr. Sarah", phone="+256771234567", location="Kampala Central",
                                         role="Customer / Buyer", favs=["INV-001"], default_pw=True)
    outlets = pd.DataFrame([
        {"ID": "OUT-101", "Business Name": "Kampala Care Pharmacy", "Contact Name": "Dr. Sarah", "Phone": "+256771234567",
         "Email": "sarah@carepharma.com", "Location": "Kampala Central", "License No": "PH-KLA-0412", "Verified": True,
         "Credit Limit (UGX)": 5000000, "Used Credit (UGX)": 1500000, "Status": "Active"},
        {"ID": "OUT-102", "Business Name": "Mbarara Express Clinic", "Contact Name": "John Doe", "Phone": "+256788990011",
         "Email": "john@mbararaclinic.com", "Location": "Mbarara Town", "License No": "CL-MBR-0233", "Verified": True,
         "Credit Limit (UGX)": 2500000, "Used Credit (UGX)": 425000, "Status": "Active"}], columns=OUTLET_COLS)
    d = dt.date
    base = [
        ["INV-001", "Amoxicillin 500mg (Box of 100)", "Antibiotics", 35000,
         450, 150, "AMX-2026-09A", d(2028, 6, 30), "NDA/UG/MED-4821"],
        ["INV-002", "Paracetamol 500mg (Box of 100)", "Analgesics", 12000,
         80, 150, "PAR-2026-01C", d(2027, 12, 15), "NDA/UG/MED-1029"],
        ["INV-003", "Coartem 20/120 (Box of 30)", "Antimalarial", 85000,
         180, 200, "CRT-2026-11B", d(2027, 8, 20), "NDA/UG/MED-9930"],
        ["INV-004", "Ciprofloxacin 500mg (Box of 100)", "Antibiotics", 48000,
         300, 100, "CIP-2026-05D", d(2027, 11, 30), "NDA/UG/MED-5512"],
        ["INV-005", "Ibuprofen 400mg (Box of 100)", "Analgesics", 18000,
         600, 200, "IBU-2026-03A", d(2028, 2, 28), "NDA/UG/MED-2204"],
        ["INV-006", "Nitrile Examination Gloves (Box of 100)", "Medical Consumables",
         28000, 90, 100, "GLV-2026-07F", d(2029, 1, 31), "NDA/UG/DEV-0731"],
        ["INV-007", "ORS Sachets (Box of 100)", "Fluids & Nutrition", 22000,
         260, 100, "ORS-2026-02B", d(2027, 1, 15), "NDA/UG/MED-3318"],
        ["INV-008", "Normal Saline 0.9% 500ml (Carton of 20)", "Fluids & Nutrition", 64000, 45, 60, "NSL-2026-08C", d(2027, 9, 30), "NDA/UG/MED-7746"]]
    inv = pd.DataFrame(base, columns=INV_COLS[:9])
    inv["Cost Price (UGX)"] = (inv["Unit Price (UGX)"] * 0.78).round(-2)
    inv["Rx Only"] = inv["Category"].isin(["Antibiotics", "Antimalarial"])
    batches = pd.DataFrame([[r[0], r[6], r[7], r[4]]
                           for r in base], columns=BATCH_COLS)
    extra = pd.DataFrame([["INV-002", "PAR-2025-08B", today() +
                         dt.timedelta(days=100), 40]], columns=BATCH_COLS)
    # a short-dated batch that FEFO ships first
    batches = pd.concat([batches, extra], ignore_index=True)
    sync_inventory({"inventory": inv, "batches": batches})
    rng, recs, rows = random.Random(7), inv.to_dict("records"), []
    customers = [("Kampala Care Pharmacy", "Dr. Sarah", "+256771234567", "sarah@carepharma.com", "Kampala Central, Plot 14 Acacia Ave"),
                 ("Mbarara Express Clinic", "John Doe", "+256788990011", "john@mbararaclinic.com", "Mbarara Town, High Street Plot 8")]

    def line(p, q): return {"id": p["Item ID"], "name": p["Product Name"], "batch": p["Batch Number"], "exp": str(p["Expiry Date"]),
                            "qty": q, "price": float(p["Unit Price (UGX)"]), "disc": disc_for(q),
                            "cost": float(p["Cost Price (UGX)"]), "vat": vat_rate(p["Category"])}
    for k in range(14):
        c, day = rng.choice(customers), today() - \
            dt.timedelta(days=rng.randint(4, 45))
        lines = [line(p, rng.choice([2, 5, 10, 12, 20, 50]))
                 for p in rng.sample(recs, rng.randint(1, 3))]
        ts = f"{day} 09:15 AM"
        o = build_order(f"ORD-{1001 + k}", *c, lines, rng.choice(["MTN Mobile Money", "Airtel Money", "Cash on Delivery"]),
                        ts=ts, account=c[3])
        o.update({"Status": "Delivered", "Payment Status": "Paid", "Item Verified": "Verified Correct",
                  "Dispatch Time": f"{day} 11:00 AM", "Delivery Time": f"{day} 03:30 PM", "Driver": "Moses K.", "Driver Phone": "+256700111222",
                  "Timeline": json.dumps([[ts, "Order placed"], [f"{day} 11:00 AM", "Dispatched"], [f"{day} 03:30 PM", "Delivered"]])})
        rows.append(o)
    d3, d1 = today() - dt.timedelta(days=3), today() - dt.timedelta(days=1)
    o = build_order("ORD-9901", *customers[0], [line(recs[0], 5)],
                    "MTN Mobile Money", ts=f"{d3} 08:40 AM", account=customers[0][3])
    o.update({"Status": "Delivered", "Payment Status": "Paid", "Item Verified": "Verified Correct", "Dispatch Time": f"{d3} 09:30 AM",
              "Delivery Time": f"{d3} 02:15 PM", "Driver": "Moses K.", "Driver Phone": "+256700111222",
              "Timeline": json.dumps([[f"{d3} 08:40 AM", "Order placed"], [f"{d3} 09:30 AM", "Dispatched"], [f"{d3} 02:15 PM", "Delivered"]])})
    rows.append(o)
    o = build_order("ORD-9902", *customers[1], [line(recs[2], 5)],
                    "Trade Credit Line", ts=f"{d1} 10:20 AM", account=customers[1][3])
    o.update({"Status": "Dispatched", "Dispatch Time": f"{d1} 11:00 AM", "Driver": "Grace A.", "Driver Phone": "+256700333444",
              "ETA": "Today by 5 PM", "Timeline": json.dumps([[f"{d1} 10:20 AM", "Order placed"], [f"{d1} 11:00 AM", "Dispatched"]])})
    rows.append(o)
    orders = pd.DataFrame(rows, columns=ORDER_COLS).sort_values(
        "Date", ascending=False, kind="stable").reset_index(drop=True)
    return {**empty, "users": users, "outlets": outlets, "inventory": inv, "batches": batches, "orders": orders}


@st.cache_resource
def get_db():
    status, data = backend_read()
    if status == "error":
        raise RuntimeError(data)
    if status == "ok":
        return deserialize(data)
    d = seed()
    sync_inventory(d)
    backend_write(serialize(d))
    return d


@st.cache_resource
def get_lock(): return threading.RLock()


@st.cache_resource
def get_saver(): return {"lock": threading.Lock(),
                         "ver": 0, "written": 0, "failed": False}


@st.cache_resource
def get_attempts(): return {}


try:
    db = get_db()
except Exception as e:
    st.error(f"Could not open the database: {e}\n\n"
             "The app stopped so that no data is overwritten. Fix the Supabase settings in Secrets "
             "(or restore the paused project), then press the button below.")
    if st.button("Try again", type="primary"):
        st.rerun()
    st.stop()
LOCK, SAVER, ATTEMPTS, ss = get_lock(), get_saver(), get_attempts(), st.session_state
sync_inventory()


def _persist(v):
    with SAVER["lock"]:
        if v <= SAVER["written"]:
            return  # a newer save already covered this one
        with LOCK:
            cur, blob = SAVER["ver"], serialize()
        ok = backend_write(blob)
        SAVER["failed"] = not ok
        if ok:
            SAVER["written"] = cur


def save():
    with LOCK:
        SAVER["ver"] += 1
        v = SAVER["ver"]
    threading.Thread(target=_persist, args=(v,), daemon=True).start()


def add_row(table, row, cap=None):
    with LOCK:
        rows = [row] + db[table].to_dict("records")
        db[table] = pd.DataFrame(
            rows[:cap] if cap else rows, columns=db[table].columns)


def log(action):
    add_row("audit", {"Time": now(), "Actor": ss.get(
        "user") or "guest", "Action": action}, cap=500)
    save()


def push(to, text):
    add_row("notifs", {"To": to, "Time": now(),
            "Text": text, "Read": False}, cap=300)
    save()


# ======================================================================
# NOTIFICATIONS (email + WhatsApp)
# ======================================================================
def _email(to, subject, text):
    try:
        s = st.secrets["smtp"]
        body = esc(text).replace("\n", "<br>")
        page = (f"<div style='font-family:Arial;max-width:560px;margin:auto;padding:20px;border:1px solid #ddd;border-radius:8px'>"
                f"<h2 style='color:#0E6B63'>MedSupply Uganda</h2><p>{body}</p>"
                f"<p style='color:#667;font-size:.85rem'>Questions? Call {MANAGER['phone']}</p></div>")
        msg = MIMEMultipart("alternative")
        msg["Subject"], msg["From"], msg[
            "To"] = subject, f"MedSupply Uganda <{s['email']}>", to
        msg.attach(MIMEText(page, "html"))
        port = int(s["port"])
        with (smtplib.SMTP_SSL(s["server"], port, timeout=8) if port == 465 else smtplib.SMTP(s["server"], port, timeout=8)) as srv:
            if port != 465:
                srv.starttls()
            srv.login(s["email"], s["password"])
            srv.sendmail(s["email"], to, msg.as_string())
        return "Email sent"
    except Exception as e:
        return f"Email not sent ({str(e)[:60]})"


def _whatsapp(phone, text):
    try:
        url = f"https://graph.facebook.com/v18.0/{st.secrets['WHATSAPP_PHONE_NUMBER_ID']}/messages"
        r = requests.post(url, headers={"Authorization": f"Bearer {st.secrets['WHATSAPP_TOKEN']}"}, timeout=8,
                          json={"messaging_product": "whatsapp", "to": phone.replace("+", "").strip(),
                                "type": "text", "text": {"body": text}})
        return "WhatsApp sent" if r.status_code == 200 else f"WhatsApp not sent ({r.json().get('error', {}).get('message', 'API error')})"
    except Exception as e:
        return f"WhatsApp not sent ({str(e)[:60]})"


def notify(o, headline):
    text = (f"Hello {o['Recipient Name']},\n{headline}\n\nOrder {o['OrderID']}: {o['Product Name']}\n"
            f"Total: {ugx(o['Total Amount (UGX)'])}\nDelivery to: {o['Delivery Location']}")
    return f"{_email(o['Recipient Email'], 'MedSupply order ' + o['OrderID'], text)} · {_whatsapp(o['Recipient Phone'], text)}"


# ======================================================================
# STATE & ORDER OPERATIONS
# ======================================================================
ss.setdefault("user", None)
ss.setdefault("cart", {})
ss.setdefault("chat", [
              ("bot", "Hello! Ask me about **prices**, **stock**, **credit**, **delivery**, **order status** or the **manager**.")])
user = db["users"].get(ss.user)
if ss.user and not user:
    ss.user = None
role = user["role"] if user else "Guest"
is_staff = role == "Staff / Admin"


def oidx(oid): return db["orders"].index[db["orders"]["OrderID"] == oid][0]
def get_order(oid): return db["orders"].loc[oidx(oid)]
def lines_of(o): return json.loads(o["Items"])


def customer_email(o):
    """Notifications are keyed by the buyer's login email, not the delivery contact's email."""
    acc = o.get("Account")
    return acc if isinstance(acc, str) and acc else o["Recipient Email"]


def upd(oid, **kw):
    with LOCK:
        i = oidx(oid)
        for k, v in kw.items():
            db["orders"].at[i, k] = v


def event(oid, text):
    with LOCK:
        i = oidx(oid)
        tl = json.loads(db["orders"].at[i, "Timeline"])
        tl.append([now(), text])
        db["orders"].at[i, "Timeline"] = json.dumps(tl)


def outlet_of(name):
    r = db["outlets"][db["outlets"]["Business Name"] == name]
    return r.iloc[0] if len(r) else None


def adjust_credit(name, delta):
    with LOCK:
        m = db["outlets"]["Business Name"] == name
        db["outlets"].loc[m, "Used Credit (UGX)"] = (
            db["outlets"].loc[m, "Used Credit (UGX)"] + delta).clip(lower=0)


def my_orders():
    o = db["orders"]
    return o if is_staff else o[o["Outlet"] == (user or {}).get("business_name", "")]


# ---- batch stock (first-expiry-first-out) ----------------------------
def allocate(iid, qty):
    """Earliest-expiring in-date batches first. Returns [(batch, qty, expiry)] or None if not enough stock."""
    bt = db["batches"]
    mine = bt[(bt["Item ID"] == iid) & (bt["Qty"] > 0)]
    mine = mine.assign(_d=mine["Expiry Date"].map(exp_days))
    mine = mine[mine["_d"] >= 0].sort_values("_d")
    if int(mine["Qty"].sum()) < qty:
        return None
    out, need = [], qty
    for _, r in mine.iterrows():
        take = min(need, int(r["Qty"]))
        out.append((r["Batch Number"], take, r["Expiry Date"]))
        need -= take
        if need == 0:
            break
    return out


def take_stock(iid, batch, qty):
    with LOCK:
        bt = db["batches"]
        bt.loc[(bt["Item ID"] == iid) & (
            bt["Batch Number"] == batch), "Qty"] -= qty


def put_stock(l):
    with LOCK:
        bt = db["batches"]
        m = (bt["Item ID"] == l["id"]) & (bt["Batch Number"] == l["batch"])
        if m.any():
            bt.loc[m, "Qty"] += l["qty"]
        else:
            add_row("batches", {"Item ID": l["id"], "Batch Number": l["batch"],
                                "Expiry Date": pd.to_datetime(l.get("exp"), errors="coerce").date(), "Qty": l["qty"]})


def receive_stock(iid, batch, qty, expiry):
    with LOCK:
        bt = db["batches"]
        m = (bt["Item ID"] == iid) & (bt["Batch Number"] == batch)
        if m.any():
            have = bt.loc[m, "Expiry Date"].iloc[0]
            if have != expiry:
                return f"Batch {batch} already exists with expiry {have}. Use a new batch number or the same expiry."
            bt.loc[m, "Qty"] += qty
        else:
            add_row("batches", {
                    "Item ID": iid, "Batch Number": batch, "Expiry Date": expiry, "Qty": qty})
        sync_inventory()
    save()
    return ""


def cart_lines():
    inv = db["inventory"].set_index("Item ID", drop=False)
    out_ = outlet_of(user["business_name"]) if user else None
    verified = out_ is not None and bool(out_["Verified"])
    out = []
    for iid, q in list(ss.cart.items()):
        if iid not in inv.index:
            ss.cart.pop(iid, None)
            continue
        r = inv.loc[iid]
        stock = int(r["Stock Quantity"])
        why = ("Expired" if stock <= 0 and exp_days(r["Expiry Date"]) < 0 else "Out of stock" if stock <= 0
               else "Needs licence verification" if bool(r["Rx Only"]) and not verified else "")
        q = max(1, min(int(q), stock)) if stock > 0 else int(q)
        ss.cart[iid] = q
        out.append({"id": iid, "name": r["Product Name"], "batch": r["Batch Number"], "qty": q, "price": float(r["Unit Price (UGX)"]),
                    "disc": disc_for(q), "stock": stock, "ok": not why, "why": why,
                    "cost": float(r["Cost Price (UGX)"]), "vat": vat_rate(r["Category"])})
    return out


def place_order(email, lines, name, phone, rec_email, addr, method, notes):
    u = db["users"][email]
    with LOCK:
        out = outlet_of(u["business_name"])
        if out is None or out["Status"] != "Active":
            return None, "Your outlet is not active. Call the manager to resolve this."
        inv = db["inventory"].set_index("Item ID", drop=False)
        final = []
        for l in lines:
            if l["id"] not in inv.index:
                return None, f"{l['name']} is no longer in the catalogue."
            if bool(inv.at[l["id"], "Rx Only"]) and not bool(out["Verified"]):
                return None, f"{l['name']} is prescription-only. It unlocks once we verify your licence."
            alloc = allocate(l["id"], l["qty"])
            if alloc is None:
                return None, f"Not enough in-date stock for {l['name']}. Reduce the quantity or remove it."
            for batch, take, exp in alloc:  # one order line per batch so every box is traceable
                final.append({"id": l["id"], "name": l["name"], "batch": batch, "exp": str(exp), "qty": take, "price": l["price"],
                              "disc": l["disc"], "cost": l["cost"], "vat": l["vat"]})
        o = build_order(f"ORD-{uuid.uuid4().hex[:5].upper()}", u["business_name"], name, phone, rec_email, addr, final,
                        method, notes, account=email)
        if method == "Trade Credit Line":
            avail = out["Credit Limit (UGX)"] - out["Used Credit (UGX)"]
            if not bool(out["Verified"]):
                return None, "Trade credit unlocks once we verify your licence. Choose another payment method."
            if o["Total Amount (UGX)"] > avail:
                return None, f"This order is above your available credit of {ugx(avail)}. Choose another payment method."
            adjust_credit(u["business_name"], o["Total Amount (UGX)"])
        for l in final:
            take_stock(l["id"], l["batch"], l["qty"])
        sync_inventory()
        add_row("orders", o)
    return o, ""


def cancel_order(oid, reason):
    with LOCK:
        o = get_order(oid)
        if o["Status"] != "Processing":
            return False
        for l in lines_of(o):
            put_stock(l)
        sync_inventory()
        if o["Payment Method"] == "Trade Credit Line" and o["Payment Status"] == "On Credit":
            adjust_credit(o["Outlet"], -o["Total Amount (UGX)"])
        upd(oid, **{"Status": "Cancelled",
            "Payment Status": "Refund due" if o["Payment Status"] == "Paid" else "Cancelled"})
        event(oid, f"Cancelled: {reason}")
    log(f"Cancelled {oid} ({reason})")
    push(customer_email(o), f"Order {oid} was cancelled. {reason}")
    push("staff", f"Order {oid} from {o['Outlet']} was cancelled.")
    return True


def mark_paid(oid):
    with LOCK:
        o = get_order(oid)
        if o["Payment Status"] not in UNPAID or o["Status"] == "Cancelled":
            return False
        if o["Payment Method"] == "Trade Credit Line":
            adjust_credit(o["Outlet"], -o["Total Amount (UGX)"])
        upd(oid, **{"Payment Status": "Paid"})
        event(oid, "Payment received")
    log(f"Payment received for {oid}")
    push(customer_email(o), f"Payment received for order {oid}. Thank you.")
    return True


def dispatch_order(oid, driver, phone, eta):
    with LOCK:
        if get_order(oid)["Status"] != "Processing":
            return None
        upd(oid, **{"Status": "Dispatched", "Dispatch Time": now(),
            "Driver": driver, "Driver Phone": phone, "ETA": eta})
        event(oid, f"Dispatched with {driver}")
    log(f"Dispatched {oid}")
    return get_order(oid)


def deliver_order(oid, pod_name=None):
    with LOCK:
        o = get_order(oid)
        if o["Status"] != "Dispatched":
            return None
        upd(oid, **{"Status": "Delivered", "Delivery Time": now(),
                    "Payment Status": "Paid" if o["Payment Status"] == "Pay on Delivery" else o["Payment Status"]})
        event(oid, "Delivered" + (f" (proof: {pod_name})" if pod_name else ""))
    log(f"Delivered {oid}")
    return get_order(oid)


def add_to_cart(iid):
    q = int(ss.get(f"q_{iid}", 1))
    stock = int(db["inventory"].loc[db["inventory"]
                ["Item ID"] == iid, "Stock Quantity"].iloc[0])
    ss.cart[iid] = min(stock, ss.cart.get(iid, 0) + q)
    ss.pop(f"cq_{iid}", None)
    st.toast(f"Added {q} box{'es' if q > 1 else ''} to your cart", icon="🧺")


def set_qty(iid): ss.cart[iid] = int(ss[f"cq_{iid}"])
def remove_item(iid): ss.cart.pop(iid, None); ss.pop(f"cq_{iid}", None)
def goto(p): ss.nav = p


def need_login():
    ss.nav = "account"
    st.toast("Log in or create an account to place orders.", icon="🔒")


def toggle_fav(iid):
    f = user["favs"]
    f.remove(iid) if iid in f else f.append(iid)
    save()


def cancel_cb(oid, reason):
    ss.flash = f"{oid} cancelled. Stock and credit were released." if cancel_order(
        oid, reason) else f"{oid} can no longer be cancelled."


def reorder_cb(oid):
    for l in lines_of(get_order(oid)):
        r = db["inventory"][db["inventory"]["Item ID"] == l["id"]]
        if len(r) and int(r.iloc[0]["Stock Quantity"]) > 0:
            ss.cart[l["id"]] = min(
                int(r.iloc[0]["Stock Quantity"]), ss.cart.get(l["id"], 0) + l["qty"])
            ss.pop(f"cq_{l['id']}", None)
    ss.nav = "cart"
    st.toast("Items added to your cart", icon="🔁")


def confirm_items_cb(oid):
    upd(oid, **{"Item Verified": "Verified Correct"})
    event(oid, "Customer confirmed items received")
    log(f"Items confirmed for {oid}")
    st.toast("Thanks. Items marked as received.", icon="✅")


def mark_paid_cb(oid):
    ss.flash = f"Payment recorded for {oid}." if mark_paid(
        oid) else f"{oid} has nothing left to pay."


def fc_risks():
    """Products forecast to run out soon (cached per day / order count / stock level)."""
    key = (str(today()), len(db["orders"]), int(
        db["inventory"]["Stock Quantity"].sum()))
    if ss.get("_fc_key") != key:
        try:
            import forecast
            ss["_fc_val"] = forecast.stockout_risks(db)
        except Exception:
            ss["_fc_val"] = []
        ss["_fc_key"] = key
    return ss.get("_fc_val", [])


# ---- login attempts and password reset codes (server-side, survive page refresh) ----
def locked_for(key):
    a = ATTEMPTS.get(key)
    return max(0, int(a["until"] - time.time())) if a else 0


def note_failure(key):
    a = ATTEMPTS.setdefault(key, {"fails": 0, "until": 0, "ts": time.time()})
    a["fails"] += 1
    a["ts"] = time.time()
    if a["fails"] >= 5:
        a["until"], a["fails"] = time.time() + 300, 0
    for k in [k for k, v in ATTEMPTS.items() if time.time() - v["ts"] > 3600 and v["until"] < time.time()]:
        ATTEMPTS.pop(k, None)


def start_reset(em):
    """Email a 6-digit code. Always behaves the same so nobody can probe which emails are registered."""
    u = db["users"].get(em)
    if u and time.time() - ATTEMPTS.get(f"reset:{em}", {}).get("ts", 0) > 60:
        code = f"{secrets.randbelow(10 ** 6):06d}"
        u["reset"] = {"h": hp(code), "exp": time.time() + 900, "tries": 0}
        ATTEMPTS[f"reset:{em}"] = {"fails": 0, "until": 0, "ts": time.time()}
        _email(em, "MedSupply password reset", f"Your password reset code is {code}. It expires in 15 minutes. "
               "If you did not ask for this, ignore this email.")
        save()


def finish_reset(em, code, new_pw):
    u = db["users"].get(em)
    r = u.get("reset") if u else None
    if not r or time.time() > r["exp"] or r["tries"] >= 5:
        return False
    if not check_pw(code.strip(), r["h"]):
        r["tries"] += 1
        save()
        return False
    u["password"], u["default_pw"] = hp(new_pw), False
    u.pop("reset", None)
    save()
    return True


user = db["users"].get(ss.user)
if ss.user and not user:
    ss.user = None


# ======================================================================
# UI HELPERS
# ======================================================================
def kpi_row(items):
    for i, (col, it) in enumerate(zip(st.columns(len(items)), items)):
        label, value, sub, tone = (list(it) + ["", ""])[:4]
        col.markdown(f"<div class='kpi {tone}' style='animation-delay:{i * .08:.2f}s'><div class='l'>{esc(label)}</div>"
                     f"<div class='v'>{esc(value)}</div><div class='s'>{esc(sub)}</div></div>", unsafe_allow_html=True)


def stepper(status):
    if status == "Cancelled":
        return '<div class="steps cancel"><span>✖ Cancelled</span></div>'
    i = STATUSES.index(status) if status in STATUSES else 0
    return '<div class="steps">' + "".join(
        f'<span class="{"done" if k <= i else ""} {"now" if k == i and status != "Delivered" else ""}">{STEP_ICONS[k]} {s}</span>'
        for k, s in enumerate(STATUSES)) + "</div>"


def timeline(o):
    items = "".join(f"<div><b>{esc(t)}</b> · {esc(e)}</div>" for t,
                    e in reversed(json.loads(o["Timeline"])))
    st.markdown(f"<div class='tl'>{items}</div>", unsafe_allow_html=True)


def empty(icon, title, hint):
    st.markdown(f"<div class='empty'><div class='big'>{icon}</div><h3 style='margin:.3rem 0'>{esc(title)}</h3><div>{esc(hint)}</div></div>",
                unsafe_allow_html=True)


def alert(text, tone=""):
    st.markdown(f"<div class='al {tone}'>{text}</div>", unsafe_allow_html=True)


def line_df(orders):
    cat = dict(zip(db["inventory"]["Item ID"], db["inventory"]["Category"]))
    rows = []
    for _, o in orders.iterrows():
        for l in lines_of(o):
            rev = l["qty"] * l["price"] * (1 - l["disc"])
            rows.append({"Date": o["Date"], "Outlet": o["Outlet"], "ID": l["id"], "Product": l["name"].split(" (")[0],
                         "Category": cat.get(l["id"], "Other"), "Qty": l["qty"], "Revenue": rev,
                         "Cost": l["qty"] * l.get("cost", 0.0)})
    return pd.DataFrame(rows, columns=["Date", "Outlet", "ID", "Product", "Category", "Qty", "Revenue", "Cost"])


def invoice_html(o):
    rows = "".join(f"<tr><td>{esc(l['name'])}</td><td>{esc(l['batch'])}</td><td class=r>{l['qty']}</td><td class=r>{ugx(l['price'])}</td>"
                   f"<td class=r>{int(l['disc'] * 100)}%</td><td class=r>{ugx(l['qty'] * l['price'] * (1 - l['disc']))}</td></tr>"
                   for l in lines_of(o))
    paid = o["Payment Status"] == "Paid"
    vat = float(o["VAT (UGX)"]) if pd.notna(o["VAT (UGX)"]) else 0.0
    vat_row = f"<br>VAT {ugx(vat)}" if vat > 0 else ""
    tin = f" · TIN {esc(COMPANY['tin'])}" if COMPANY["tin"] else ""
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>Invoice {esc(o['OrderID'])}</title><style>
body{{font-family:Arial,sans-serif;color:#10282B;max-width:760px;margin:30px auto;padding:0 20px}}
h1{{color:#0E6B63;margin:0}}table{{width:100%;border-collapse:collapse;margin:18px 0}}th,td{{padding:8px;border-bottom:1px solid #D9E2DF;text-align:left;font-size:14px}}
.r{{text-align:right}}.tot{{font-size:18px;font-weight:bold}}.stamp{{display:inline-block;border:3px solid {'#0A5A44' if paid else '#8A4B00'};color:{'#0A5A44' if paid else '#8A4B00'};padding:4px 12px;font-weight:bold;transform:rotate(-4deg)}}
</style></head><body><h1>{COMPANY['name']}</h1><p>Invoice {esc(o['OrderID'])} · {esc(o['Date'])}{tin}</p><span class=stamp>{esc(o['Payment Status']).upper()}</span>
<p><b>Bill to:</b> {esc(o['Outlet'])}<br>{esc(o['Recipient Name'])} · {esc(o['Recipient Phone'])}<br>{esc(o['Delivery Location'])}</p>
<table><tr><th>Product</th><th>Batch</th><th class=r>Boxes</th><th class=r>Unit price</th><th class=r>Discount</th><th class=r>Amount</th></tr>{rows}</table>
<p class=r>Subtotal {ugx(o['Subtotal (UGX)'])}<br>Volume discount −{ugx(o['Subtotal (UGX)'] - (o['Total Amount (UGX)'] - vat))}{vat_row}</p>
<p class='r tot'>Total {ugx(o['Total Amount (UGX)'])}</p><p>Payment method: {esc(o['Payment Method'])}</p>
<p style='font-size:12px;color:#567'>Bank: {COMPANY['bank']} · Account {COMPANY['acct']} · Questions? Call {MANAGER['phone']}. Open this file in a browser and choose Print to save as PDF.</p>
</body></html>"""


# ======================================================================
# SIDEBAR
# ======================================================================
LABELS = {"dash": "🏠 Dashboard", "market": "🛒 Marketplace", "cart": "🧺 Cart", "orders": "📦 My Orders", "seller": "🚚 Deliveries",
          "inv": "🏷️ Inventory", "outlets": "🏥 Outlets & Credit", "tickets": "🎫 Support", "logs": "📊 Order Logs",
          "alerts": "🔔 Notifications", "help": "💬 Help Assistant", "pay": "💳 Payments", "account": "👤 Account"}
MENUS = {"Staff / Admin": ["dash", "market", "seller", "inv", "outlets", "tickets", "logs", "alerts", "help", "pay", "account"],
         "Customer / Buyer": ["dash", "market", "cart", "orders", "tickets", "alerts", "help", "pay", "account"],
         "Guest": ["market", "help", "pay", "account"]}


def my_notifs():
    n = db["notifs"]
    if not user:
        return n.iloc[0:0]
    return n[(n["To"] == ss.user) | ((n["To"] == "staff") & is_staff)]


mo = my_orders() if user else db["orders"].iloc[0:0]
tk = db["tickets"]
badges = {"seller": len(db["orders"][db["orders"]["Status"].isin(["Processing", "Dispatched"])]) if is_staff else 0,
          "orders": len(mo[mo["Status"].isin(["Processing", "Dispatched"])]),
          "cart": sum(ss.cart.values()),
          "alerts": int((~my_notifs()["Read"].astype(bool)).sum()),
          "tickets": len(tk[tk["Status"] == "Open"]) if is_staff else (len(tk[(tk["Outlet"] == user["business_name"]) & (tk["Status"] == "Open")]) if user else 0)}

if ss.get("pending_nav"):
    ss.nav = ss.pop("pending_nav")
if ss.get("nav") not in MENUS[role]:
    ss.nav = MENUS[role][0]

with st.sidebar:
    st.markdown("### 💊 MedSupply Uganda")
    st.caption("Wholesale medicines for pharmacies and clinics")
    if user:
        st.markdown(f"**{user['contact_name']}**  \n{user['business_name']}")
        if st.button("Log out", **FULL):
            log("Logged out")
            ss.user, ss.cart = None, {}
            st.rerun()
    else:
        st.markdown(
            "You are browsing as a guest. Log in from **Account** to order.")
    st.divider()
    page = st.radio("Menu", MENUS[role], key="nav", label_visibility="collapsed",
                    format_func=lambda k: LABELS[k] + (f"  ({badges[k]})" if badges.get(k) else ""))
    if ss.cart and role == "Customer / Buyer" and page != "cart":
        cl = cart_lines()
        st.divider()
        st.markdown(
            f"🧺 **{sum(l['qty'] for l in cl)} boxes** · {ugx(sum(l['qty'] * l['price'] * (1 - l['disc']) for l in cl))}")
        st.button("Go to checkout", on_click=goto,
                  args=("cart",), key="side_cart", **FULL)
    st.divider()
    st.caption(f"Need help? Call {MANAGER['name']}: {MANAGER['phone']}")
    if is_staff and SAVER["failed"]:
        st.warning(
            "The last save to storage failed. Check the Supabase settings in Secrets.")

if ss.get("flash"):
    st.success(ss.pop("flash"))
if ss.pop("celebrate", False):
    st.balloons()


# ======================================================================
# DIALOGS
# ======================================================================
@st.dialog("Report a problem")
def ticket_dialog(oid):
    st.caption(f"Order {oid}")
    issue = st.selectbox("What went wrong?", ["Wrong item", "Damaged packaging", "Short delivery",
                                              "Expired or short-dated product", "Late delivery", "Billing issue", "Other"])
    det = st.text_area("Tell us what happened",
                       placeholder="Include product names, batch numbers and quantities.")
    if st.button("Send to support", type="primary", **FULL):
        if len(det.strip()) < 10:
            st.error("Add a few more details so support can act quickly.")
        else:
            o = get_order(oid)
            add_row("tickets", {"TicketID": f"TKT-{uuid.uuid4().hex[:4].upper()}", "OrderID": oid, "Outlet": o["Outlet"],
                                "Contact": f"{user['contact_name']} · {user['phone']}", "Issue": issue, "Details": det.strip(),
                                "Status": "Open", "Created": now(), "Response": ""})
            event(oid, f"Problem reported: {issue}")
            push("staff", f"New support ticket for {oid} ({issue}).")
            log(f"Ticket opened for {oid}")
            ss.flash = "Ticket sent. Support will contact you."
            st.rerun()


# ======================================================================
# PAGES
# ======================================================================
if page == "dash" and is_staff:
    o = db["orders"]
    live = o[o["Status"] != "Cancelled"]
    st.header("Operations dashboard")
    span = st.radio("Period", [7, 14, 30, 90], index=2, horizontal=True,
                    format_func=lambda d: f"Last {d} days", label_visibility="collapsed")
    since = today() - dt.timedelta(days=span)
    w = live[pd.to_datetime(live["Date"]).dt.date >=
             since] if len(live) else live
    ld = line_df(w)
    known = ld[ld["Cost"] > 0]
    margin_txt = f" · {(known['Revenue'].sum() - known['Cost'].sum()) / known['Revenue'].sum():.0%} gross margin" if len(
        known) and known["Revenue"].sum() else ""
    recv = live[live["Payment Status"].isin(
        UNPAID)]["Total Amount (UGX)"].sum()
    inv = db["inventory"]
    low_n = int((inv["Stock Quantity"] <= inv["Reorder Level"]).sum())
    kpi_row([("Revenue", ugx(w["Total Amount (UGX)"].sum()), f"{len(w)} orders in {span} days{margin_txt}", ""),
             ("Awaiting payment", ugx(
                 recv), f"{len(live[live['Payment Status'].isin(UNPAID)])} open invoices", "sun"),
             ("To ship", str(len(o[o["Status"] == "Processing"])),
              f"{len(o[o['Status'] == 'Dispatched'])} on the road", ""),
             ("Low stock items", str(low_n), "at or under reorder level", "red" if low_n else "")])
    st.write("")
    c1, c2 = st.columns([3, 2])
    with c1, st.container(border=True):
        st.subheader("Revenue per day")
        days = pd.date_range(since, today())
        if len(w):
            rev = w.assign(D=pd.to_datetime(w["Date"])).groupby(
                "D")["Total Amount (UGX)"].sum().reindex(days, fill_value=0)
            st.area_chart(rev.rename("Revenue (UGX)"),
                          color="#0E6B63", height=250)
        else:
            st.caption("No sales in this period.")
    with c2, st.container(border=True):
        st.subheader("Orders by status")
        if len(o):
            st.bar_chart(o.groupby("Status").size().rename(
                "Orders"), color="#F2B600", height=250)
        else:
            st.caption("No orders yet.")
    c3, c4 = st.columns(2)
    with c3, st.container(border=True):
        st.subheader("Best sellers")
        if ld.empty:
            st.caption("No sales in this period.")
        else:
            st.bar_chart(ld.groupby("Product")["Revenue"].sum().sort_values(
                ascending=False).head(6), color="#0E6B63", height=240)
    with c4, st.container(border=True):
        st.subheader("Top outlets")
        if w.empty:
            st.caption("No sales in this period.")
        else:
            st.bar_chart(w.groupby("Outlet")["Total Amount (UGX)"].sum().sort_values(
                ascending=False).head(6), color="#10282B", height=240)
    st.subheader("Needs attention")
    todo = []
    names = dict(zip(inv["Item ID"], inv["Product Name"]))
    for _, r in inv.iterrows():
        s, lvl = int(r["Stock Quantity"]), int(r["Reorder Level"])
        if s <= lvl:
            todo.append(("red" if s == 0 else "",
                        f"<b>{esc(r['Product Name'])}</b> has {s} boxes left (reorder at {lvl})", "inv"))
    bt = db["batches"]
    for _, b in bt[bt["Qty"] > 0].iterrows():
        dd, nm = exp_days(b["Expiry Date"]), esc(
            names.get(b["Item ID"], b["Item ID"]))
        if dd < 0:
            todo.append(
                ("red", f"<b>{nm}</b> batch {esc(b['Batch Number'])}: {int(b['Qty'])} boxes expired on {b['Expiry Date']}. Write off or return to the supplier.", "inv"))
        elif dd < 180:
            todo.append(
                ("", f"<b>{nm}</b> batch {esc(b['Batch Number'])} expires in {dd} days ({int(b['Qty'])} boxes)", "inv"))
    for p in fc_risks():
        todo.append(
            ("", f"<b>{esc(p)}</b> is forecast to run out within 2 weeks", "inv"))
    for _, r in db["outlets"].iterrows():
        if r["Credit Limit (UGX)"] and r["Used Credit (UGX)"] / r["Credit Limit (UGX)"] > .8:
            todo.append(
                ("red", f"<b>{esc(r['Business Name'])}</b> has used over 80% of its credit", "outlets"))
        if not bool(r["Verified"]):
            todo.append(
                ("", f"<b>{esc(r['Business Name'])}</b> is waiting for licence verification", "outlets"))
    if len(tk[tk["Status"] == "Open"]):
        todo.append(
            ("", f"<b>{len(tk[tk['Status'] == 'Open'])}</b> open support ticket(s)", "tickets"))
    if len(o[o["Status"] == "Processing"]):
        todo.append(
            ("", f"<b>{len(o[o['Status'] == 'Processing'])}</b> order(s) waiting to be dispatched", "seller"))
    if not todo:
        alert("Everything is on track. Nothing needs attention.", "ok")
    for i, (tone, text, target) in enumerate(todo[:12]):
        a, b = st.columns([6, 1])
        with a:
            alert(text, tone)
        b.button("Open", key=f"todo_{i}",
                 on_click=goto, args=(target,), **FULL)
    with st.expander("Recent activity"):
        st.dataframe(db["audit"].head(12), hide_index=True, **FULL)

elif page == "dash":
    first = user["contact_name"].split()[0]
    mine = my_orders()
    live = mine[mine["Status"] != "Cancelled"]
    out = outlet_of(user["business_name"])
    st.markdown(f"""<div class="hero"><h1>Good to see you, {esc(first)}</h1><p>{esc(user['business_name'])} · here is where your orders and credit stand today.</p></div>""",
                unsafe_allow_html=True)
    avail = (out["Credit Limit (UGX)"] -
             out["Used Credit (UGX)"]) if out is not None else 0
    spend30 = live[pd.to_datetime(live["Date"]).dt.date >= today(
    ) - dt.timedelta(days=30)]["Total Amount (UGX)"].sum() if len(live) else 0
    openo = mine[mine["Status"].isin(["Processing", "Dispatched"])]
    kpi_row([("Open orders", str(len(openo)), "being prepared or on the road", ""),
             ("Spent, last 30 days", ugx(spend30),
              f"{len(live)} orders in total", ""),
             ("Credit available", ugx(avail), "verified outlet" if out is not None and bool(
                 out["Verified"]) else "unlocks after verification", "sun"),
             ("To pay", ugx(live[live["Payment Status"].isin(UNPAID)]["Total Amount (UGX)"].sum()), "unpaid invoices", "")])
    st.write("")
    left, right = st.columns([3, 2])
    with left:
        st.subheader("On the way")
        if openo.empty:
            empty("📭", "No open orders",
                  "Browse the marketplace to place your next order.")
            st.button("Browse marketplace", on_click=goto, args=(
                "market",), type="primary", key="d_browse")
        for _, r in openo.iterrows():
            with st.container(border=True):
                st.markdown(f"**{r['OrderID']}** · {r['Product Name']}")
                st.markdown(stepper(r["Status"]), unsafe_allow_html=True)
                if r["Driver"]:
                    st.caption(f"Driver {r['Driver']} · {r['Driver Phone']}" +
                               (f" · ETA {r['ETA']}" if r["ETA"] else ""))
        if len(live):
            st.subheader("Spending")
            sp = live.assign(D=pd.to_datetime(live["Date"])).groupby("D")[
                "Total Amount (UGX)"].sum()
            st.area_chart(sp.rename("Spend (UGX)"),
                          color="#0E6B63", height=200)
    with right:
        st.subheader("Credit line")
        with st.container(border=True):
            if out is not None and out["Credit Limit (UGX)"] > 0:
                st.progress(min(out["Used Credit (UGX)"] / out["Credit Limit (UGX)"], 1.0),
                            text=f"{ugx(out['Used Credit (UGX)'])} used of {ugx(out['Credit Limit (UGX)'])}")
            else:
                st.caption(
                    "No credit line yet. Ask the manager to verify your licence.")
        st.subheader("Order again")
        ld = line_df(live)
        if ld.empty:
            st.caption("Your most-ordered products will appear here.")
        else:
            top = ld.groupby(["ID", "Product"])["Qty"].sum().sort_values(
                ascending=False).head(3).reset_index()
            for _, t in top.iterrows():
                with st.container(border=True):
                    a, b = st.columns([3, 1])
                    a.markdown(f"**{t['Product']}**")
                    a.caption(f"You have ordered {int(t['Qty'])} boxes")
                    st.session_state.setdefault(f"q_{t['ID']}", 5)
                    b.button(
                        "＋ Cart", key=f"re_{t['ID']}", on_click=add_to_cart, args=(t["ID"],))

elif page == "market":
    first = user["contact_name"].split()[0] if user else None
    st.markdown(f"""<div class="hero"><h1>{f'Welcome back, {esc(first)}' if first else 'Order verified medicines in minutes'}</h1>
        <p>Wholesale stock for pharmacies, clinics and hospitals across Uganda.</p>
        <span class="chip">NDA-registered stock</span><span class="chip">Trade credit up to UGX 5M</span>
        <span class="chip">Order alerts on WhatsApp and email</span></div>""", unsafe_allow_html=True)
    st.markdown("<div class='ticker'><div>Every product shows its batch number, expiry date and NDA registration &nbsp;•&nbsp; "
                "Buy 10+ boxes and save 5%, buy 50+ and save 10% &nbsp;•&nbsp; Verified outlets can pay on trade credit &nbsp;•&nbsp; "
                "Pay with MTN Mobile Money, Airtel Money or cash on delivery &nbsp;•&nbsp; Track every delivery live</div></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([3, 1.3, 1.3])
    q = c1.text_input(
        "Search", placeholder="Search by product, category or NDA number", label_visibility="collapsed")
    cat = c2.selectbox("Category", ["All categories"] + sorted(
        db["inventory"]["Category"].dropna().unique()), label_visibility="collapsed")
    sort = c3.selectbox("Sort", ["Name A–Z", "Price: low to high",
                        "Price: high to low", "Most stock"], label_visibility="collapsed")
    f1, f2, _ = st.columns([1, 1, 3])
    only_stock = f1.toggle("In stock only", True)
    favs_only = f2.toggle("★ Favourites", False, disabled=not user)
    df = db["inventory"]
    if cat != "All categories":
        df = df[df["Category"] == cat]
    if only_stock:
        df = df[df["Stock Quantity"] > 0]
    if favs_only and user:
        df = df[df["Item ID"].isin(user["favs"])]
    if q:
        df = df[df[["Product Name", "Category", "NDA Reg No"]].apply(
            lambda c: c.astype(str).str.contains(q, case=False, regex=False)).any(axis=1)]
    key, asc = {"Name A–Z": ("Product Name", True), "Price: low to high": ("Unit Price (UGX)", True),
                "Price: high to low": ("Unit Price (UGX)", False), "Most stock": ("Stock Quantity", False)}[sort]
    df = df.sort_values(key, ascending=asc)
    st.caption(f"{len(df)} product{'s' if len(df) != 1 else ''}")
    if df.empty:
        empty("🔍", "No products match",
              "Try a shorter word, switch off In stock only, or choose All categories.")
    favs = user["favs"] if user else []
    outv = outlet_of(user["business_name"]) if user and not is_staff else None
    can_rx = outv is not None and bool(outv["Verified"])
    cols = st.columns(3)
    for i, (_, r) in enumerate(df.iterrows()):
        iid, stock, dd = r["Item ID"], int(
            r["Stock Quantity"]), exp_days(r["Expiry Date"])
        lvl = int(r["Reorder Level"]) if pd.notna(r["Reorder Level"]) else 100
        if stock == 0 and dd < 0:
            cls, lab = "out", "Expired"
        elif stock == 0:
            cls, lab = "out", "Out of stock"
        elif stock <= lvl:
            cls, lab = "low", f"Low stock · {stock} left"
        else:
            cls, lab = "ok", f"In stock · {stock}"
        short = "<span class='pill warn'>Short-dated</span>" if 0 <= dd < 180 else ""
        rx = "<span class='pill info'>Prescription only</span>" if bool(
            r["Rx Only"]) else ""
        exp = "n/a" if dd == 9999 else pd.to_datetime(
            r["Expiry Date"]).strftime("%b %Y")
        with cols[i % 3], st.container(border=True):
            h1, h2 = st.columns([4, 1])
            h1.markdown(f"<div style='display:flex;gap:8px;align-items:center'><div class='ico'>{CATS.get(r['Category'], '💊')}</div>"
                        f"<div><span class='pill {cls}'>{lab}</span>{short}{rx}</div></div>", unsafe_allow_html=True)
            h2.button("★" if iid in favs else "☆", key=f"fav_{iid}", on_click=toggle_fav, args=(
                iid,), disabled=not user, help="Save to favourites")
            st.markdown(f"**{r['Product Name']}**")
            st.markdown(
                f"<span class='price'>{ugx(r['Unit Price (UGX)'])}</span> per box", unsafe_allow_html=True)
            st.caption(
                f"{r['Category']} · Batch {r['Batch Number']} · Expires {exp} · {r['NDA Reg No']}")
            if not user:
                st.button(
                    "Log in to order", key=f"o_{iid}", type="primary", on_click=need_login, **FULL)
            elif is_staff:
                st.caption("Staff preview. Buyers order from here.")
            elif stock == 0:
                st.button("Unavailable", key=f"o_{iid}", disabled=True, **FULL)
            elif bool(r["Rx Only"]) and not can_rx:
                st.button("Verified outlets only",
                          key=f"o_{iid}", disabled=True, **FULL)
            else:
                a, b = st.columns([1, 2])
                a.number_input("Boxes", 1, stock, 1,
                               key=f"q_{iid}", label_visibility="collapsed")
                b.button("Add to cart", key=f"o_{iid}", type="primary", on_click=add_to_cart, args=(
                    iid,), **FULL)

elif page == "cart":
    st.header("Your cart")
    lines = cart_lines()
    if not lines:
        empty("🧺", "Your cart is empty",
              "Add products from the marketplace and they will appear here.")
        st.button("Browse marketplace", on_click=goto, args=(
            "market",), type="primary", key="c_browse")
    else:
        left, right = st.columns([3, 2])
        with left:
            for l in lines:
                with st.container(border=True):
                    a, b, c, d = st.columns([4, 2, 2, 1])
                    a.markdown(f"**{l['name']}**")
                    a.caption(
                        f"{ugx(l['price'])} per box · Batch {l['batch']}")
                    if l["ok"]:
                        b.number_input("Boxes", 1, l["stock"], l["qty"], key=f"cq_{l['id']}", on_change=set_qty, args=(l["id"],),
                                       label_visibility="collapsed")
                    else:
                        b.error(l["why"])
                    c.markdown(
                        f"**{ugx(l['qty'] * l['price'] * (1 - l['disc']))}**")
                    if l["disc"]:
                        c.caption(f"{int(l['disc'] * 100)}% volume discount")
                    d.button("🗑️", key=f"rm_{l['id']}", on_click=remove_item, args=(
                        l["id"],), help="Remove")
        sub = sum(l["qty"] * l["price"] for l in lines)
        net = sum(l["qty"] * l["price"] * (1 - l["disc"]) for l in lines)
        vat = sum(l["qty"] * l["price"] * (1 - l["disc"]) * l["vat"]
                  for l in lines)
        tot = net + vat
        out = outlet_of(user["business_name"])
        avail = (out["Credit Limit (UGX)"] -
                 out["Used Credit (UGX)"]) if out is not None else 0
        with right, st.container(border=True):
            st.subheader("Checkout")
            st.markdown(f"Subtotal **{ugx(sub)}**  \nVolume discount **−{ugx(sub - net)}**" + (
                f"  \nVAT **{ugx(vat)}**" if vat else ""))
            st.metric("Total to pay", ugx(tot))
            name = st.text_input(
                "Recipient name", user["contact_name"], key="ck_name")
            phone = st.text_input(
                "WhatsApp number", user["phone"], help="Format: +256 followed by 9 digits", key="ck_phone")
            email = st.text_input(
                "Email for order updates", ss.user, key="ck_email")
            addr = st.text_input(
                "Delivery address", user["location"], placeholder="e.g. Plot 12 Kampala Road, Kampala", key="ck_addr")
            notes = st.text_input("Delivery instructions (optional)",
                                  placeholder="e.g. Ask for the pharmacist on duty", key="ck_notes")
            pay = st.radio("Payment", PAY_METHODS,
                           horizontal=True, key="ck_pay")
            if pay == "Trade Credit Line":
                if out is not None and bool(out["Verified"]):
                    st.caption(f"Available credit: {ugx(avail)}")
                else:
                    st.warning(
                        "Trade credit unlocks once we verify your licence.")
            if st.button("Place order", type="primary", disabled=not all(l["ok"] for l in lines), **FULL):
                if not valid_phone(phone):
                    st.error(
                        "Phone number must start with +256 followed by 9 digits.")
                elif not valid_email(email):
                    st.error("Enter a valid email address.")
                elif not addr.strip() or not name.strip():
                    st.error("Enter the recipient name and delivery address.")
                else:
                    with st.status("Placing your order…", expanded=True) as status:
                        st.write("Checking stock and expiry dates")
                        o, err = place_order(ss.user, lines, name.strip(), phone.strip(
                        ), email.strip(), addr.strip(), pay, notes.strip())
                        if err:
                            status.update(label=err, state="error")
                        else:
                            st.write("Stock reserved")
                            st.write("Sending email and WhatsApp alerts")
                            res = notify(o, "We received your order.")
                            push(
                                "staff", f"New order {o['OrderID']} from {o['Outlet']} for {ugx(o['Total Amount (UGX)'])}.")
                            push(
                                ss.user, f"Order {o['OrderID']} placed. We will notify you when it is dispatched.")
                            log(f"Placed {o['OrderID']} ({ugx(o['Total Amount (UGX)'])})")
                            status.update(label="Order placed",
                                          state="complete")
                            ss.cart = {}
                            ss.flash = f"Order {o['OrderID']} placed for {addr.strip()}. {res}"
                            ss.celebrate, ss.pending_nav = True, "orders"
                            time.sleep(.7)
                            st.rerun()

elif page == "orders":
    st.header("My Orders")
    mine = my_orders()
    f1, f2 = st.columns([2, 3])
    show = f1.radio("Show", ["All", "Open", "Delivered", "Cancelled"],
                    horizontal=True, label_visibility="collapsed")
    term = f2.text_input(
        "Search", placeholder="Search by order ID or product", label_visibility="collapsed")
    if show == "Open":
        mine = mine[mine["Status"].isin(["Processing", "Dispatched"])]
    elif show != "All":
        mine = mine[mine["Status"] == show]
    if term:
        mine = mine[mine["OrderID"].str.contains(
            term, case=False, regex=False) | mine["Product Name"].str.contains(term, case=False, regex=False)]
    if mine.empty:
        empty("📦", "No orders here yet",
              "Open the marketplace to place your first one.")
    for _, o in mine.iterrows():
        oid = o["OrderID"]
        with st.container(border=True):
            a, b = st.columns([3, 2])
            a.markdown(f"**{oid}** · {o['Product Name']}")
            a.caption(
                f"{o['Delivery Location']} · Batch {o['Batch Number']} · {o['Date']}")
            b.markdown(
                f"**{ugx(o['Total Amount (UGX)'])}**  \n{o['Payment Method']} · {o['Payment Status']}")
            st.markdown(stepper(o["Status"]), unsafe_allow_html=True)
            if o["Driver"] and o["Status"] == "Dispatched":
                st.markdown(f"🚚 **{o['Driver']}** · [{o['Driver Phone']}](tel:{o['Driver Phone']})" + (
                    f" · ETA {o['ETA']}" if o["ETA"] else ""))
            if o["Status"] == "Delivered":
                st.caption(
                    f"Delivered {o['Delivery Time']} · Items: {o['Item Verified']}")
            with st.expander("Items and tracking"):
                for l in lines_of(o):
                    st.markdown(
                        f"• {l['name']} × {l['qty']} · batch {l['batch']} · {ugx(l['qty'] * l['price'] * (1 - l['disc']))}")
                timeline(o)
            x, y, z, w = st.columns(4)
            if o["Status"] == "Processing":
                x.button("Cancel order", key=f"x_{oid}", on_click=cancel_cb, args=(
                    oid, "Cancelled by customer"), **FULL)
            if o["Status"] == "Delivered" and o["Item Verified"] != "Verified Correct":
                y.button("Confirm items received", key=f"c_{oid}", on_click=confirm_items_cb, args=(
                    oid,), type="primary", **FULL)
            if o["Status"] == "Delivered" and z.button("Report a problem", key=f"r_{oid}", **FULL):
                ticket_dialog(oid)
            if o["Status"] != "Cancelled":
                w.button(
                    "Order again", key=f"ro_{oid}", on_click=reorder_cb, args=(oid,), **FULL)
            st.download_button("Download invoice", invoice_html(
                o).encode(), f"invoice_{oid}.html", "text/html", key=f"inv_{oid}")

elif page == "seller":
    st.header("Deliveries")

    @st.fragment(run_every=15)
    def seller_board():
        o = db["orders"]
        st.markdown(
            f"<span class='live'></span>Live board · updated {dt.datetime.now():%H:%M:%S}", unsafe_allow_html=True)
        kpi_row([("Processing", str(len(o[o["Status"] == "Processing"])), "", ""), ("Dispatched", str(len(o[o["Status"] == "Dispatched"])), "", "sun"),
                 ("Delivered", str(
                     len(o[o["Status"] == "Delivered"])), "", ""),
                 ("Awaiting payment", str(len(o[o["Payment Status"].isin(UNPAID) & (o["Status"] != "Cancelled")])), "", "red")])
        st.write("")
        c1, c2 = st.columns([3, 2])
        term = c1.text_input("Search", placeholder="Search by order ID or facility",
                             label_visibility="collapsed", key="s_q")
        queue = c2.radio("Queue", ["Open", "Processing", "Dispatched", "Delivered", "Cancelled", "All"], horizontal=True,
                         label_visibility="collapsed", key="s_queue")
        df = o
        if queue == "Open":
            df = df[df["Status"].isin(["Processing", "Dispatched"])]
        elif queue != "All":
            df = df[df["Status"] == queue]
        if term:
            df = df[df["OrderID"].str.contains(
                term, case=False, regex=False) | df["Outlet"].str.contains(term, case=False, regex=False)]
        if df.empty:
            empty("🎉", "All caught up", "No orders are waiting in this queue.")
        for _, r in df.iterrows():
            oid, s = r["OrderID"], r["Status"]
            with st.container(border=True):
                a, b, c = st.columns(3)
                a.markdown(f"**{oid}** · {r['Outlet']}")
                a.caption(
                    f"{r['Recipient Name']} · {r['Recipient Phone']}\n\n{r['Delivery Location']}")
                b.markdown(r["Product Name"])
                b.caption(
                    f"Batch {r['Batch Number']} · {ugx(r['Total Amount (UGX)'])}")
                c.markdown(f"Items: **{r['Item Verified']}**")
                c.caption(f"{r['Payment Method']} · {r['Payment Status']}")
                st.markdown(stepper(s), unsafe_allow_html=True)
                if r["Notes"]:
                    st.caption(f"📝 {r['Notes']}")
                if r["Driver"]:
                    st.caption(f"🚚 {r['Driver']} · {r['Driver Phone']}" +
                               (f" · ETA {r['ETA']}" if r["ETA"] else ""))
                if s == "Processing":
                    with st.expander("Dispatch this order"), st.form(f"disp_{oid}"):
                        d1, d2, d3 = st.columns(3)
                        dn = d1.text_input("Driver name", key=f"dn_{oid}")
                        dp = d2.text_input(
                            "Driver phone", "+256", key=f"dp_{oid}")
                        eta = d3.text_input(
                            "ETA", placeholder="e.g. Today 4 PM", key=f"eta_{oid}")
                        if st.form_submit_button("Confirm dispatch", type="primary"):
                            if not dn.strip() or not valid_phone(dp):
                                st.error(
                                    "Enter the driver name and a phone number like +256700000000.")
                            else:
                                fresh = dispatch_order(
                                    oid, dn.strip(), dp.strip(), eta.strip())
                                if fresh is None:
                                    ss.flash = f"{oid} was already handled by someone else."
                                else:
                                    push(customer_email(
                                        fresh), f"Order {oid} is on its way with {dn.strip()}.")
                                    ss.flash = f"{oid} dispatched. {notify(fresh, f'Your order is on its way. Driver {dn.strip()} {dp.strip()}.')}"
                                st.rerun()
                if s == "Dispatched":
                    st.file_uploader("Proof of delivery (optional)", type=[
                                     "png", "jpg", "pdf"], key=f"f_{oid}")
                    x, y, _ = st.columns([2, 2, 2])
                    if x.button("Mark delivered and send alerts", key=f"v_{oid}", type="primary"):
                        pod = ss.get(f"f_{oid}")
                        fresh = deliver_order(oid, pod.name if pod else None)
                        if fresh is None:
                            ss.flash = f"{oid} was already updated by someone else."
                        else:
                            push(customer_email(
                                fresh), f"Order {oid} was delivered. Please confirm the items.")
                            ss.flash = f"{oid} delivered. {notify(fresh, 'Your order has been delivered.')}"
                            ss.celebrate = True
                        st.rerun()
                    if y.button("Flag wrong item", key=f"m_{oid}"):
                        upd(oid, **{"Item Verified": "Wrong item flagged"})
                        event(oid, "Staff flagged a wrong item")
                        log(f"Wrong item flagged on {oid}")
                        st.rerun()
                x, y, _ = st.columns([2, 2, 2])
                if r["Payment Status"] in UNPAID and s != "Cancelled":
                    x.button("Record payment received",
                             key=f"p_{oid}", on_click=mark_paid_cb, args=(oid,))
                if s == "Processing":
                    with y.popover("Cancel order"):
                        why = st.text_input(
                            "Reason", key=f"why_{oid}", placeholder="e.g. Out of stock at warehouse")
                        st.button("Confirm cancellation", key=f"cc_{oid}", on_click=cancel_cb, args=(
                            oid, why.strip() or "Cancelled by staff"))
                with st.expander("Tracking history"):
                    timeline(r)
    seller_board()

elif page == "inv":
    st.header("Inventory")
    inv, bt = db["inventory"], db["batches"]
    live_b = bt[bt["Qty"] > 0]
    bdays = live_b["Expiry Date"].map(exp_days)
    kpi_row([("Products", str(len(inv)), "", ""), ("Stock value", ugx((inv["Stock Quantity"] * inv["Unit Price (UGX)"]).sum()), "in-date stock at selling price", ""),
             ("Low stock", str(int((inv["Stock Quantity"] <= inv["Reorder Level"]).sum(
             ))), "at or under reorder level", "sun"),
             ("Batches expiring in 6 months", str(int(((bdays >= 0) & (bdays < 180)).sum())), f"{int((bdays < 0).sum())} expired batch(es) still on the shelf", "red")])
    st.write("")
    t1, t2, t3, t4, t5 = st.tabs(
        ["Stock levels", "Batches", "Receive stock", "Edit catalogue", "Demand forecast"])
    with t1:
        if len(inv):
            st.bar_chart(inv.set_index("Product Name")[
                         ["Stock Quantity", "Reorder Level"]], color=["#0E6B63", "#F2B600"], height=300)
        for _, r in inv.iterrows():
            if int(r["Stock Quantity"]) <= int(r["Reorder Level"]):
                alert(f"<b>{esc(r['Product Name'])}</b> has {r['Stock Quantity']} boxes left (reorder at {r['Reorder Level']})",
                      "red" if r["Stock Quantity"] == 0 else "")
    with t2:
        st.caption(
            "Orders ship the earliest-expiring in-date batch first. Expired batches are never sold.")
        nm = dict(zip(inv["Item ID"], inv["Product Name"]))
        view = bt.assign(Product=bt["Item ID"].map(
            nm), Days=bt["Expiry Date"].map(exp_days))
        view["Status"] = view["Days"].map(
            lambda d: "Expired" if d < 0 else "Short-dated" if d < 180 else "OK")
        view = view[view["Qty"] > 0].sort_values(
            "Days")[["Product", "Batch Number", "Expiry Date", "Qty", "Days", "Status"]]
        if view.empty:
            st.caption("No batches in stock.")
        else:
            st.dataframe(view.rename(
                columns={"Days": "Days to expiry", "Qty": "Boxes"}), hide_index=True, **FULL)
        n_exp = int(bt[bt["Expiry Date"].map(exp_days) < 0]["Qty"].sum())
        if n_exp and st.button(f"Write off {n_exp} expired boxes", type="primary"):
            with LOCK:
                db["batches"].loc[db["batches"]
                                  ["Expiry Date"].map(exp_days) < 0, "Qty"] = 0
                sync_inventory()
            log(f"Wrote off {n_exp} expired boxes")
            ss.flash = f"Wrote off {n_exp} expired boxes."
            st.rerun()
        st.markdown("**Correct a batch**")
        st.caption("Double-click a cell to change the batch number, expiry date or number of boxes, "
                   "then press Save batch changes. Product stock updates automatically.")
        if bt.empty:
            st.caption("No batches yet. Use the Receive stock tab to add one.")
        else:
            bview = bt.copy()
            bview.insert(1, "Product", bview["Item ID"].map(nm))
            bedit = st.data_editor(
                bview, hide_index=True, key="batch_editor", num_rows="fixed", disabled=["Item ID", "Product"],
                column_config={"Expiry Date": st.column_config.DateColumn("Expiry Date", format="YYYY-MM-DD"),
                               "Qty": st.column_config.NumberColumn("Boxes", min_value=0, step=1)}, **FULL)
            if st.button("Save batch changes", type="primary"):
                nb = bedit.drop(columns=["Product"]).copy()
                nb["Batch Number"] = nb["Batch Number"].fillna(
                    "").astype(str).str.strip()
                nb["Qty"] = pd.to_numeric(
                    nb["Qty"], errors="coerce").fillna(0).astype(int)
                nb["Expiry Date"] = pd.to_datetime(
                    nb["Expiry Date"], errors="coerce").dt.date
                if (nb["Batch Number"] == "").any():
                    st.error("Every batch needs a batch number.")
                elif nb["Expiry Date"].isna().any():
                    st.error("Every batch needs a valid expiry date.")
                elif nb.duplicated(["Item ID", "Batch Number"]).any():
                    st.error(
                        "Two batches of the same product cannot share a batch number.")
                else:
                    with LOCK:
                        db["batches"] = nb[BATCH_COLS].reset_index(drop=True)
                        sync_inventory()
                    log("Edited batch details")
                    ss.pop("batch_editor", None)
                    ss.flash = "Batch changes saved."
                    st.rerun()
    with t3, st.form("receive"):
        st.caption(
            "Record a new delivery from your supplier. It is added as its own batch; older batches stay on record.")
        if inv.empty:
            st.info("Add products under Edit catalogue first.")
        pick = st.selectbox("Product", inv["Product Name"])
        r1, r2, r3 = st.columns(3)
        add_q = r1.number_input("Boxes received", 1, 100000, 100)
        new_b = r2.text_input("Batch number")
        new_e = r3.date_input("Expiry date", today() + dt.timedelta(days=540))
        if st.form_submit_button("Add to stock", type="primary"):
            if inv.empty:
                st.error("Add a product to the catalogue first.")
            elif not new_b.strip():
                st.error(
                    "Enter the batch number from the supplier's delivery note.")
            elif new_e <= today():
                st.error("The expiry date must be in the future.")
            else:
                iid = inv.loc[inv["Product Name"] == pick, "Item ID"].iloc[0]
                err = receive_stock(iid, new_b.strip(), int(add_q), new_e)
                if err:
                    st.error(err)
                else:
                    log(f"Received {add_q} × {pick} (batch {new_b.strip()})")
                    ss.flash = f"Added {add_q} boxes of {pick} as batch {new_b.strip()}."
                    st.rerun()
    with t4:
        st.caption("Edit product details, tick Rx Only for prescription medicines, and add rows at the bottom. "
                   "Stock, batch and expiry come from the Batches tab, so use Receive stock to add boxes.")
        edited = st.data_editor(
            db["inventory"], num_rows="dynamic", key="inv_editor", **FULL,
            disabled=["Item ID", "Stock Quantity",
                      "Batch Number", "Expiry Date"],
            column_config={"Category": st.column_config.SelectboxColumn("Category", options=list(CATS)),
                           "Unit Price (UGX)": st.column_config.NumberColumn(min_value=0, format="%d"),
                           "Cost Price (UGX)": st.column_config.NumberColumn(min_value=0, format="%d"),
                           "Reorder Level": st.column_config.NumberColumn(min_value=0, step=1),
                           "Rx Only": st.column_config.CheckboxColumn("Rx Only", help="Prescription-only: verified outlets only"),
                           "Expiry Date": st.column_config.DateColumn(format="YYYY-MM-DD")})
        if st.button("Save changes", type="primary"):
            d = edited[edited["Product Name"].notna() & (
                edited["Product Name"].astype(str).str.strip() != "")].copy()
            used = set(d["Item ID"].dropna().astype(str))
            n = 1
            for i in d.index:
                if pd.isna(d.at[i, "Item ID"]) or not str(d.at[i, "Item ID"]).strip():
                    while f"INV-{n:03d}" in used:
                        n += 1
                    d.at[i, "Item ID"] = f"INV-{n:03d}"
                    used.add(f"INV-{n:03d}")
            for c_, dflt in (("Stock Quantity", 0), ("Unit Price (UGX)", 0), ("Cost Price (UGX)", 0), ("Reorder Level", 100)):
                d[c_] = pd.to_numeric(
                    d[c_], errors="coerce").fillna(dflt).astype(int)
            d["Category"] = d["Category"].fillna("Medical Consumables")
            d["Rx Only"] = d["Rx Only"].fillna(False).astype(bool)
            d["Expiry Date"] = pd.to_datetime(
                d["Expiry Date"], errors="coerce").dt.date
            with LOCK:
                db["inventory"] = d.drop_duplicates(
                    "Item ID").reset_index(drop=True)
                db["batches"] = db["batches"][db["batches"]["Item ID"].isin(
                    db["inventory"]["Item ID"])].reset_index(drop=True)
                sync_inventory()
            log("Edited the product catalogue")
            ss.pop("inv_editor", None)
            ss.flash = "Inventory saved."
            st.rerun()
    with t5:
        try:
            from forecast import render_forecast_tab
            render_forecast_tab(st, db, ugx, **FULL)
        except ImportError:
            st.info("Add forecast.py next to this file to see demand forecasts.")

elif page == "outlets":
    st.header("Outlets & Credit")
    ot = db["outlets"]
    kpi_row([("Outlets", str(len(ot)), f"{int(ot['Verified'].astype(bool).sum())} verified", ""),
             ("Credit extended", ugx(ot["Credit Limit (UGX)"].sum()), "", ""),
             ("Credit in use", ugx(ot["Used Credit (UGX)"].sum()), "owed to MedSupply", "sun")])
    st.write("")
    if ot.empty:
        empty("🏥", "No outlets yet",
              "Pharmacies and clinics appear here when they register.")
    for i, r in ot.iterrows():
        used, limit = r["Used Credit (UGX)"], r["Credit Limit (UGX)"]
        spent = db["orders"][(db["orders"]["Outlet"] == r["Business Name"]) & (
            db["orders"]["Status"] != "Cancelled")]["Total Amount (UGX)"].sum()
        with st.container(border=True):
            badge = "<span class='pill ok'>Verified</span>" if bool(
                r["Verified"]) else "<span class='pill warn'>Awaiting verification</span>"
            st.markdown(
                f"**{r['Business Name']}** · {r['Location']} · {r['Status']} {badge}", unsafe_allow_html=True)
            st.caption(
                f"{r['Contact Name']} · {r['Phone']} · {r['Email']} · Licence {r['License No']} · Lifetime orders {ugx(spent)}")
            st.progress(min(used / limit, 1.0) if limit else 0.0,
                        text=f"{ugx(used)} used of {ugx(limit)}")
            if limit and used / limit > 0.8:
                st.warning("This outlet has used more than 80% of its credit.")
            with st.expander("Manage"):
                m1, m2, m3 = st.columns(3)
                ver = m1.checkbox("Licence verified", bool(
                    r["Verified"]), key=f"ver_{r['ID']}")
                lim = m2.number_input("Credit limit (UGX)", 0, 100_000_000, int(
                    limit), 100_000, key=f"lim_{r['ID']}")
                stat = m3.selectbox("Status", [
                                    "Active", "Suspended"], index=0 if r["Status"] == "Active" else 1, key=f"st_{r['ID']}")
                if st.button("Save outlet", key=f"sv_{r['ID']}", type="primary"):
                    db["outlets"].loc[i, ["Verified", "Credit Limit (UGX)", "Status"]] = [
                        ver, lim, stat]
                    log(
                        f"Updated outlet {r['Business Name']}: verified={ver}, limit={lim}, status={stat}")
                    push(
                        r["Email"], f"Your account settings were updated. Credit limit: {ugx(lim)}.")
                    ss.flash = f"{r['Business Name']} updated."
                    st.rerun()
                p1, p2 = st.columns([2, 1])
                rep = p1.number_input("Record a repayment (UGX)", 0, int(
                    max(used, 0)), 0, 50_000, key=f"rep_{r['ID']}")
                if p2.button("Record repayment", key=f"rp_{r['ID']}", disabled=rep == 0):
                    adjust_credit(r["Business Name"], -rep)
                    log(f"Repayment of {ugx(rep)} from {r['Business Name']}")
                    ss.flash = f"Recorded {ugx(rep)} from {r['Business Name']}."
                    st.rerun()

elif page == "tickets":
    st.header("Support")
    if is_staff:
        flt = st.radio("Show", ["Open", "Resolved", "All"],
                       horizontal=True, label_visibility="collapsed")
        t = tk if flt == "All" else tk[tk["Status"] == flt]
        if t.empty:
            empty("🎫", "No tickets",
                  "Problems reported by customers will show up here.")
        for _, r in t.iterrows():
            with st.container(border=True):
                st.markdown(f"**{r['TicketID']}** · {r['Outlet']} · order {r['OrderID']} <span class='pill {'ok' if r['Status'] == 'Resolved' else 'warn'}'>{r['Status']}</span>",
                            unsafe_allow_html=True)
                st.caption(f"{r['Issue']} · {r['Contact']} · {r['Created']}")
                st.write(r["Details"])
                if r["Status"] == "Open":
                    resp = st.text_input(
                        "Response to customer", key=f"rs_{r['TicketID']}")
                    if st.button("Resolve and notify", key=f"rv_{r['TicketID']}", type="primary"):
                        if not resp.strip():
                            st.error(
                                "Write a short response before resolving.")
                        else:
                            db["tickets"].loc[db["tickets"]["TicketID"] == r["TicketID"], [
                                "Status", "Response"]] = ["Resolved", resp.strip()]
                            em = db["outlets"].loc[db["outlets"]
                                                   ["Business Name"] == r["Outlet"], "Email"]
                            if len(em):
                                push(
                                    em.iloc[0], f"Support replied on {r['TicketID']}: {resp.strip()}")
                            log(f"Resolved {r['TicketID']}")
                            ss.flash = f"{r['TicketID']} resolved."
                            st.rerun()
                else:
                    st.caption(f"Response: {r['Response']}")
    elif user:
        mine_t = tk[tk["Outlet"] == user["business_name"]]
        if mine_t.empty:
            empty("🎫", "No tickets yet",
                  "Open a delivered order and choose Report a problem if something is wrong.")
            st.button("Go to my orders", on_click=goto,
                      args=("orders",), key="t_orders")
        for _, r in mine_t.iterrows():
            with st.container(border=True):
                st.markdown(f"**{r['TicketID']}** · order {r['OrderID']} <span class='pill {'ok' if r['Status'] == 'Resolved' else 'warn'}'>{r['Status']}</span>",
                            unsafe_allow_html=True)
                st.caption(f"{r['Issue']} · {r['Created']}")
                st.write(r["Details"])
                if r["Response"]:
                    st.info(f"Support: {r['Response']}")

elif page == "logs":
    st.header("Order Logs")
    o = db["orders"]
    t1, t2 = st.tabs(["Orders", "Audit trail"])
    with t1:
        f1, f2, f3, f4 = st.columns(4)
        sts = f1.multiselect(
            "Status", ["Processing", "Dispatched", "Delivered", "Cancelled"], default=[])
        pays = f2.multiselect("Payment", sorted(
            o["Payment Status"].unique()), default=[])
        outs = f3.multiselect("Outlet", sorted(
            o["Outlet"].unique()), default=[])
        rng_ = f4.date_input(
            "Dates", (today() - dt.timedelta(days=90), today()))
        f = o
        if sts:
            f = f[f["Status"].isin(sts)]
        if pays:
            f = f[f["Payment Status"].isin(pays)]
        if outs:
            f = f[f["Outlet"].isin(outs)]
        if isinstance(rng_, (tuple, list)) and len(rng_) == 2 and len(f):
            dd_ = pd.to_datetime(f["Date"]).dt.date
            f = f[(dd_ >= rng_[0]) & (dd_ <= rng_[1])]
        fl = f[f["Status"] != "Cancelled"]
        kpi_row([("Revenue", ugx(fl["Total Amount (UGX)"].sum()), "excludes cancelled", ""), ("Orders", str(len(f)), "", ""),
                 ("Average order", ugx(
                     fl["Total Amount (UGX)"].mean() if len(fl) else 0), "", "sun"),
                 ("Waiting to ship", str(len(f[f["Status"] == "Processing"])), "", "red")])
        st.write("")
        flat = f.drop(columns=["Items", "Timeline"])
        st.download_button("Download CSV", flat.to_csv(
            index=False).encode(), f"medsupply_orders_{today()}.csv", "text/csv")
        st.dataframe(flat, hide_index=True, **FULL)
        if len(f):
            pick = st.selectbox("Invoice for order", f["OrderID"])
            st.download_button("Download invoice", invoice_html(
                get_order(pick)).encode(), f"invoice_{pick}.html", "text/html", key="log_inv")
    with t2:
        st.dataframe(db["audit"], hide_index=True, **FULL)

elif page == "alerts":
    st.header("Notifications")
    n = my_notifs()
    if n.empty:
        empty("🔔", "You are all caught up",
              "Order updates, payments and support replies appear here.")
    else:
        if st.button("Mark all as read"):
            db["notifs"].loc[n.index, "Read"] = True
            save()
            st.rerun()
        for _, r in n.head(40).iterrows():
            alert(f"{esc(r['Text'])}<br><small style='color:#678'>{esc(r['Time'])}</small>",
                  "" if r["Read"] else "new")

elif page == "help":
    st.header("Help Assistant")
    st.caption(
        f"For anything else, call {MANAGER['name']} on {MANAGER['phone']}.")

    def reply(t):
        tl = t.lower()
        inv = db["inventory"]
        if any(w in tl for w in ("manager", "contact", "call")):
            return f"**{MANAGER['name']}**, Operations & Credit Manager: {MANAGER['phone']}"
        words = re.findall(r"[a-z]{4,}", tl)
        hit = inv[inv["Product Name"].str.lower().apply(
            lambda n: any(w in n for w in words))] if words else inv.iloc[0:0]
        if len(hit) and len(hit) < len(inv):
            return "\n".join(f"• **{r['Product Name']}**: {ugx(r['Unit Price (UGX)'])} · {r['Stock Quantity']} boxes in stock · expires {r['Expiry Date']}"
                             for _, r in hit.iterrows())
        if any(w in tl for w in ("price", "cost", "catalog")):
            return "\n".join(f"• **{r['Product Name']}**: {ugx(r['Unit Price (UGX)'])}" for _, r in inv.iterrows()) or "The catalogue is empty."
        if "stock" in tl or "available" in tl:
            return "\n".join(f"• **{r['Product Name']}**: {r['Stock Quantity']} boxes" for _, r in inv.iterrows()) or "The catalogue is empty."
        if any(w in tl for w in ("credit", "limit")):
            if not user:
                return "Log in to see your credit line. Verified outlets can pay on trade credit."
            out = outlet_of(user["business_name"])
            return f"Your available credit is **{ugx(out['Credit Limit (UGX)'] - out['Used Credit (UGX)'])}**." if out is not None else "No credit line found."
        if any(w in tl for w in ("discount", "bulk", "volume")):
            return "Buy **10+ boxes** of a product and save **5%**. Buy **50+** and save **10%**."
        if any(w in tl for w in ("pay", "momo", "mobile money", "airtel", "bank")):
            return "We accept **MTN Mobile Money**, **Airtel Money**, **trade credit** (verified outlets) and **cash on delivery**. See the Payments page."
        if any(w in tl for w in ("deliver", "driver", "ship")):
            return "Once your order is dispatched you will see the driver's name, phone and ETA under **My Orders**."
        if any(w in tl for w in ("status", "track", "order")):
            if not user:
                return "Log in from the Account page to see your orders."
            m = my_orders().head(3)
            return "\n".join(f"• **{r['OrderID']}**: {r['Status']}" for _, r in m.iterrows()) or "You have no orders yet."
        return "I can help with **prices**, **stock**, **credit**, **discounts**, **payments**, **delivery**, **order status** or **manager** contact."

    quick = None
    for col, (lab, k) in zip(st.columns(5), [("📋 Catalog", "catalog"), ("💰 Prices", "prices"), ("🚚 Order status", "status"),
                                             ("🏷️ Discounts", "discount"), ("👤 Manager", "manager")]):
        if col.button(lab, **FULL):
            quick = k
    typed = st.chat_input("Ask about prices, stock or orders")
    if msg := (quick or typed):
        ss.chat += [("user", msg), ("bot", reply(msg))]
    for who, text in ss.chat:
        with st.chat_message("user" if who == "user" else "assistant"):
            st.markdown(text)

elif page == "pay":
    st.header("Payments")
    if DEMO:
        st.caption("Demo mode: the payment buttons do not move real money.")
    t0, t1, t2 = st.tabs(["Outstanding", "Mobile money", "Bank transfer"])
    with t0:
        if not user:
            empty("🔒", "Log in to see your invoices",
                  "Outstanding payments appear here after you sign in.")
        else:
            mo_ = my_orders()
            due = mo_[mo_["Payment Status"].isin(
                UNPAID) & (mo_["Status"] != "Cancelled")]
            if due.empty:
                empty("✅", "Nothing to pay", "All your invoices are settled.")
            for _, r in due.iterrows():
                with st.container(border=True):
                    a, b = st.columns([3, 1])
                    a.markdown(f"**{r['OrderID']}** · {r['Product Name']}")
                    a.caption(
                        f"{r['Payment Method']} · {r['Payment Status']} · {r['Date']}")
                    b.markdown(f"**{ugx(r['Total Amount (UGX)'])}**")
                    if is_staff:
                        b.button("Record payment", key=f"pn_{r['OrderID']}", on_click=mark_paid_cb, args=(
                            r["OrderID"],), type="primary")
                    elif DEMO:
                        b.button("Pay now (demo)", key=f"pn_{r['OrderID']}", on_click=mark_paid_cb, args=(
                            r["OrderID"],), type="primary")
                    else:
                        b.caption(
                            "Pay by bank transfer and quote the order ID. We mark it paid once received.")
    with t1:
        if DEMO:
            net = st.radio("Network", ["MTN", "Airtel"], horizontal=True)
            ph = st.text_input(
                f"{net} number", user["phone"] if user else "+256", key=f"{net}_p")
            amt = st.number_input("Amount (UGX)", 1000,
                                  value=150000, step=10000, key=f"{net}_a")
            if st.button(f"Request {net} payment of {ugx(amt)}", type="primary", key=f"{net}_b"):
                if valid_phone(ph):
                    st.success(
                        f"Payment request sent to {ph}. Reference: TXN-{uuid.uuid4().hex[:6].upper()}")
                else:
                    st.error("Enter the number as +256 followed by 9 digits.")
        else:
            st.info(
                "Mobile money collection is not connected yet. Please pay by bank transfer and quote your order ID.")
    with t2:
        st.markdown(
            f"**Bank:** {COMPANY['bank']}  \n**Account name:** {COMPANY['name']}  \n**Account number:** {COMPANY['acct']}")
        st.caption("Use your order ID as the payment reference.")

elif page == "account":
    st.header("Account")
    if user:
        if user.get("default_pw"):
            st.warning(
                "You are using a temporary password. Change it under Security.")
        tabs = st.tabs(["Profile", "Security"] +
                       (["Team"] if is_staff else []))
        with tabs[0], st.form("profile"):
            st.caption(f"{ss.user} · {role}")
            p1, p2 = st.columns(2)
            nm = p1.text_input("Contact person", user["contact_name"])
            ph = p2.text_input("WhatsApp number", user["phone"])
            lc = st.text_input("Default delivery location", user["location"])
            if st.form_submit_button("Save profile", type="primary"):
                if not nm.strip() or not lc.strip():
                    st.error("Name and location cannot be empty.")
                elif not valid_phone(ph):
                    st.error(
                        "Phone number must start with +256 followed by 9 digits.")
                else:
                    user.update(contact_name=nm.strip(),
                                phone=ph.strip(), location=lc.strip())
                    db["outlets"].loc[db["outlets"]["Email"] == ss.user, [
                        "Contact Name", "Phone", "Location"]] = [nm.strip(), ph.strip(), lc.strip()]
                    log("Updated profile")
                    ss.flash = "Profile saved."
                    st.rerun()
        with tabs[1], st.form("chpw"):
            cur = st.text_input("Current password", type="password")
            n1 = st.text_input("New password (8+ characters)", type="password")
            n2 = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Change password", type="primary"):
                if not check_pw(cur, user["password"]):
                    st.error("Current password is incorrect.")
                elif len(n1) < 8:
                    st.error("Use at least 8 characters.")
                elif n1 != n2:
                    st.error("The two passwords do not match.")
                else:
                    user["password"], user["default_pw"] = hp(n1), False
                    log("Changed password")
                    ss.flash = "Password changed."
                    st.rerun()
        if is_staff:
            with tabs[2], st.form("team"):
                st.caption(
                    "Add another staff member who can manage orders, stock and credit.")
                t1_, t2_ = st.columns(2)
                te, tn = t1_.text_input("Email").strip(
                ).lower(), t1_.text_input("Name")
                tp, tw = t2_.text_input(
                    "Phone", placeholder="+256700000000"), t2_.text_input("Temporary password", type="password")
                if st.form_submit_button("Add team member", type="primary"):
                    if not (valid_email(te) and tn.strip() and valid_phone(tp) and len(tw) >= 8):
                        st.error(
                            "Enter a valid email, name, phone and a password of 8+ characters.")
                    elif te in db["users"]:
                        st.error("That email already has an account.")
                    else:
                        db["users"][te] = dict(password=hp(tw), business_name="MedSupply HQ", contact_name=tn.strip(), phone=tp,
                                               location="Kampala Central", role="Staff / Admin", favs=[], default_pw=True)
                        log(f"Added staff member {te}")
                        ss.flash = f"{tn.strip()} can now log in."
                        st.rerun()
    else:
        if secret("ADMIN_PASSWORD") is None:
            st.warning(
                "Owner: ADMIN_PASSWORD is not set in Secrets. A one-time admin password was written to the app logs. Set one, then reboot.")
        t1, t2, t3 = st.tabs(["Log in", "Create account", "Reset password"])
        with t1, st.form("login"):
            em = st.text_input("Email").strip().lower()
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Log in", type="primary", **FULL):
                wait = locked_for(em)
                if wait:
                    st.error(
                        f"Too many attempts. Try again in {wait} seconds.")
                elif em in db["users"] and check_pw(pw, db["users"][em]["password"]):
                    ATTEMPTS.pop(em, None)
                    ss.user = em
                    log("Logged in")
                    ss.flash = f"Welcome back, {db['users'][em]['contact_name'].split()[0]}."
                    ss.pending_nav = "dash"
                    st.rerun()
                else:
                    note_failure(em)
                    st.error(
                        "Email or password is incorrect. Check both, or create an account.")
        with t2, st.form("signup"):
            c1, c2 = st.columns(2)
            biz = c1.text_input("Pharmacy or business name *")
            nm = c1.text_input("Contact person *")
            em = c1.text_input("Email *").strip().lower()
            lic = c1.text_input("Facility licence number *",
                                help="We verify this before unlocking trade credit.")
            ph = c2.text_input("WhatsApp number *",
                               placeholder="+256770000000")
            loc = c2.text_input(
                "Location *", placeholder="e.g. Kampala Central, Plot 14 Acacia Ave")
            pw = c2.text_input("Password * (8+ characters)", type="password")
            if st.form_submit_button("Create account", type="primary", **FULL):
                if not all([biz, nm, em, ph, loc, pw, lic]):
                    st.error("Fill in every field marked *.")
                elif not valid_email(em):
                    st.error("Enter a valid email address.")
                elif not valid_phone(ph):
                    st.error(
                        "Phone number must start with +256 followed by 9 digits.")
                elif len(pw) < 8:
                    st.error("Use a password of at least 8 characters.")
                elif em in db["users"]:
                    st.error("That email already has an account. Log in instead.")
                elif biz.strip() in set(db["outlets"]["Business Name"]):
                    st.error(
                        "A business with that name is already registered. Use a more specific name.")
                else:
                    db["users"][em] = dict(password=hp(pw), business_name=biz.strip(), contact_name=nm.strip(), phone=ph.strip(),
                                           location=loc.strip(), role="Customer / Buyer", favs=[], default_pw=False)
                    add_row("outlets", {"ID": f"OUT-{uuid.uuid4().hex[:3].upper()}", "Business Name": biz.strip(), "Contact Name": nm.strip(),
                                        "Phone": ph.strip(), "Email": em, "Location": loc.strip(), "License No": lic.strip(), "Verified": False,
                                        "Credit Limit (UGX)": 0, "Used Credit (UGX)": 0, "Status": "Active"})
                    ss.user = em
                    log(f"New account {biz.strip()}")
                    push(
                        "staff", f"New outlet {biz.strip()} is waiting for licence verification.")
                    ss.flash = "Account created. You can order now. Trade credit unlocks after we verify your licence."
                    ss.pending_nav = "dash"
                    st.rerun()
        with t3:
            if not secret("smtp"):
                st.info(
                    f"Password reset by email is not set up yet. Please call {MANAGER['name']} on {MANAGER['phone']}.")
            else:
                with st.form("reset_ask"):
                    st.caption(
                        "Step 1: we email a 6-digit code to the address on your account.")
                    em = st.text_input("Registered email").strip().lower()
                    if st.form_submit_button("Send code", **FULL):
                        if valid_email(em):
                            start_reset(em)
                        st.success(
                            "If that email is registered, a code is on its way. It expires in 15 minutes.")
                with st.form("reset_do"):
                    st.caption(
                        "Step 2: enter the code and choose a new password.")
                    em2 = st.text_input("Registered email ").strip().lower()
                    code = st.text_input("6-digit code")
                    p1 = st.text_input(
                        "New password (8+ characters)", type="password")
                    p2 = st.text_input("Confirm new password", type="password")
                    if st.form_submit_button("Reset password", type="primary", **FULL):
                        if not all([em2, code, p1]):
                            st.error("Fill in every field.")
                        elif len(p1) < 8:
                            st.error("Use at least 8 characters.")
                        elif p1 != p2:
                            st.error("The two passwords do not match.")
                        elif finish_reset(em2, code, p1):
                            log(f"Password reset for {em2}")
                            st.success("Password updated. You can log in now.")
                        else:
                            st.error(
                                "That code is wrong or has expired. Request a new one.")
