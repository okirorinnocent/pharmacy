import streamlit as st
import pandas as pd
import uuid
import re
import smtplib
import hashlib
import requests
import datetime as dt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

st.set_page_config(page_title="MedSupply Uganda | B2B Pharma Marketplace", page_icon="💊",
                   layout="wide", initial_sidebar_state="expanded")

MANAGER = {"name": "Okiror Innocent", "phone": "+256763212490"}
STATUSES = ["Processing", "Dispatched", "Delivered"]
def ugx(n): return f"UGX {n:,.0f}"
def hp(p): return hashlib.sha256(p.encode()).hexdigest()
def valid_phone(p): return re.match(r"^\+256[0-9]{9}$", p.strip()) is not None


# ---------- THEME ----------
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;800&family=Source+Sans+3:wght@400;600&display=swap');
:root{--ink:#10282B;--teal:#0E6B63;--sun:#F2B600;--paper:#F5F7F6;--line:#D9E2DF}
.stApp{background:var(--paper);font-family:'Source Sans 3',sans-serif}
.stApp h1,.stApp h2,.stApp h3{font-family:'Bricolage Grotesque',sans-serif;color:var(--ink);letter-spacing:-.01em}
.stApp .stMarkdown,.stApp label,.stApp [data-testid=stCaptionContainer]{color:var(--ink)}
.block-container{padding-top:1.5rem;max-width:1200px}
[data-testid=stSidebar]{background:var(--ink)}
[data-testid=stSidebar] *{color:#E8F1EF !important}
[data-testid=stSidebar] .stButton button{background:transparent;border:1px solid #4B6B6A}
[data-testid=stVerticalBlockBorderWrapper]{background:#fff;border-radius:10px;border-color:var(--line)}
button[kind=primary]{background:var(--teal);border:0;font-weight:600;color:#fff}
button[kind=primary]:hover:not(:disabled){background:#0A524C}
.hero{background:var(--ink);border-left:8px solid var(--sun);border-radius:10px;padding:1.6rem 2rem;margin-bottom:1.2rem}
.hero h1{color:#fff !important;font-size:2.1rem;margin:0 0 .3rem}
.hero p{color:#CFE0DC;margin:0 0 .8rem;font-size:1.05rem}
.chip{display:inline-block;background:#1B3E42;color:#fff;border-radius:6px;padding:4px 12px;margin:0 8px 6px 0;font-size:.88rem}
.pill{display:inline-block;padding:2px 10px;border-radius:99px;font-size:.78rem;font-weight:600}
.ok{background:#DDF3EC;color:#0A5A44}.low{background:#FFF1CC;color:#7A5A00}.out{background:#FBE1DE;color:#8E241C}
.price{font-family:'Bricolage Grotesque',sans-serif;font-size:1.35rem;font-weight:800;color:var(--teal)}
.steps{display:flex;gap:6px;margin:.4rem 0 .6rem}
.steps span{flex:1;text-align:center;padding:4px;border-radius:6px;background:#E6ECEA;font-size:.82rem;color:#456}
.steps .done{background:var(--teal);color:#fff}
</style>""", unsafe_allow_html=True)


# ---------- NOTIFICATIONS ----------
def _email(to, subject, text):
    try:
        s = st.secrets["smtp"]
        html = (f"<div style='font-family:Arial;max-width:560px;margin:auto;padding:20px;border:1px solid #ddd;border-radius:8px'>"
                f"<h2 style='color:#0E6B63'>MedSupply Uganda</h2><p>{text.replace(chr(10), '<br>')}</p>"
                f"<p style='color:#667;font-size:.85rem'>Questions? Call {MANAGER['phone']}</p></div>")
        msg = MIMEMultipart("alternative")
        msg["Subject"], msg["From"], msg[
            "To"] = subject, f"MedSupply Uganda <{s['email']}>", to
        msg.attach(MIMEText(html, "html"))
        port = int(s["port"])
        with (smtplib.SMTP_SSL(s["server"], port) if port == 465 else smtplib.SMTP(s["server"], port)) as srv:
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
        r = requests.post(url, headers={"Authorization": f"Bearer {st.secrets['WHATSAPP_TOKEN']}"}, timeout=10,
                          json={"messaging_product": "whatsapp", "to": phone.replace("+", "").strip(),
                                "type": "text", "text": {"body": text}})
        return "WhatsApp sent" if r.status_code == 200 else f"WhatsApp not sent ({r.json().get('error', {}).get('message', 'API error')})"
    except Exception as e:
        return f"WhatsApp not sent ({str(e)[:60]})"


def notify(o, headline):
    text = (f"Hello {o['Recipient Name']},\n{headline}\n\nOrder {o['OrderID']}: {o['Product Name']} x {o['Quantity']} boxes\n"
            f"Total: {ugx(o['Total Amount (UGX)'])}\nDelivery to: {o['Delivery Location']}")
    return f"{_email(o['Recipient Email'], 'MedSupply order ' + o['OrderID'], text)} · {_whatsapp(o['Recipient Phone'], text)}"


# ---------- SHARED DATA ----------
@st.cache_resource
def get_db():
    users = {
        "okirorinnocent49@gmail.com": dict(password=hp("admin"), business_name="MedSupply HQ", contact_name="Okiror Innocent",
                                           phone="+256763212490", location="Kampala Central", role="Staff / Admin"),
        "sarah@carepharma.com": dict(password=hp("password123"), business_name="Kampala Care Pharmacy", contact_name="Dr. Sarah",
                                     phone="+256771234567", location="Kampala Central", role="Customer / Buyer")}
    outlets = pd.DataFrame([
        {"ID": "OUT-101", "Business Name": "Kampala Care Pharmacy", "Contact Name": "Dr. Sarah", "Phone": "+256771234567",
         "Email": "sarah@carepharma.com", "Location": "Kampala Central", "Credit Limit (UGX)": 5000000, "Used Credit (UGX)": 1500000, "Status": "Active"},
        {"ID": "OUT-102", "Business Name": "Mbarara Express Clinic", "Contact Name": "John Doe", "Phone": "+256788990011",
         "Email": "john@mbararaclinic.com", "Location": "Mbarara Town", "Credit Limit (UGX)": 2500000, "Used Credit (UGX)": 425000, "Status": "Active"}])
    inv = pd.DataFrame([
        {"Item ID": "INV-001", "Product Name": "Amoxicillin 500mg (Box of 100)", "Category": "Antibiotics", "Unit Price (UGX)": 35000,
         "Stock Quantity": 450, "Batch Number": "AMX-2026-09A", "Expiry Date": dt.date(2028, 6, 30), "NDA Reg No": "NDA/UG/MED-4821"},
        {"Item ID": "INV-002", "Product Name": "Paracetamol 500mg (Box of 100)", "Category": "Analgesics", "Unit Price (UGX)": 12000,
         "Stock Quantity": 120, "Batch Number": "PAR-2026-01C", "Expiry Date": dt.date(2027, 12, 15), "NDA Reg No": "NDA/UG/MED-1029"},
        {"Item ID": "INV-003", "Product Name": "Coartem 20/120 (Box of 30)", "Category": "Antimalarial", "Unit Price (UGX)": 85000,
         "Stock Quantity": 180, "Batch Number": "CRT-2026-11B", "Expiry Date": dt.date(2027, 8, 20), "NDA Reg No": "NDA/UG/MED-9930"}])
    orders = pd.DataFrame([
        {"OrderID": "ORD-9901", "Outlet": "Kampala Care Pharmacy", "Recipient Name": "Dr. Sarah", "Recipient Phone": "+256771234567",
         "Recipient Email": "sarah@carepharma.com", "Delivery Location": "Kampala Central, Plot 14 Acacia Ave",
         "Product Name": "Amoxicillin 500mg (Box of 100)", "Batch Number": "AMX-2026-09A", "Quantity": 5, "Total Amount (UGX)": 175000,
         "Payment Method": "MTN Mobile Money", "Payment Status": "Paid on Delivery", "Item Verified": "Verified Correct",
         "Status": "Delivered", "Date": "2026-09-28", "Dispatch Time": "2026-09-28 09:30 AM", "Delivery Time": "2026-09-28 02:15 PM"},
        {"OrderID": "ORD-9902", "Outlet": "Mbarara Express Clinic", "Recipient Name": "John Doe", "Recipient Phone": "+256788990011",
         "Recipient Email": "john@mbararaclinic.com", "Delivery Location": "Mbarara Town, High Street Plot 8",
         "Product Name": "Coartem 20/120 (Box of 30)", "Batch Number": "CRT-2026-11B", "Quantity": 5, "Total Amount (UGX)": 425000,
         "Payment Method": "Trade Credit Line", "Payment Status": "Pending Payment", "Item Verified": "Pending Inspection",
         "Status": "Dispatched", "Date": "2026-09-29", "Dispatch Time": "2026-09-29 11:00 AM", "Delivery Time": "Pending"}])
    return {"users": users, "outlets": outlets, "inventory": inv, "orders": orders}


db = get_db()
ss = st.session_state
ss.setdefault("user", None)
ss.setdefault("chat", [
              ("bot", "Hello! Ask me about **prices**, **catalog**, **order status** or **manager** contact.")])
user = db["users"].get(ss.user)
role = user["role"] if user else "Guest"
is_staff = role == "Staff / Admin"
def now(): return dt.datetime.now().strftime("%Y-%m-%d %I:%M %p")


def upd(oid, **kw):
    i = db["orders"].index[db["orders"]["OrderID"] == oid][0]
    for k, v in kw.items():
        db["orders"].at[i, k] = v


def stepper(status):
    i = STATUSES.index(status) if status in STATUSES else 0
    return '<div class="steps">' + "".join(f'<span class="{"done" if k <= i else ""}">{s}</span>' for k, s in enumerate(STATUSES)) + "</div>"


def my_orders():
    o = db["orders"]
    return o if is_staff else o[o["Outlet"] == (user or {}).get("business_name", "")]


# ---------- SIDEBAR NAVIGATION ----------
LABELS = {"market": "🛒 Marketplace", "orders": "📦 My Orders", "seller": "🚚 Deliveries", "inv": "🏷️ Inventory",
          "outlets": "🏥 Outlets & Credit", "logs": "📊 Order Logs", "help": "💬 Help Assistant", "pay": "💳 Payments", "account": "👤 Account"}
MENUS = {"Staff / Admin": ["market", "seller", "inv", "outlets", "logs", "help", "pay", "account"],
         "Customer / Buyer": ["market", "orders", "help", "pay", "account"],
         "Guest": ["market", "help", "pay", "account"]}
open_n = len(db["orders"][db["orders"]["Status"] != "Delivered"]) if is_staff else \
    len(my_orders()[my_orders()["Status"] != "Delivered"]) if user else 0

with st.sidebar:
    st.markdown("### 💊 MedSupply Uganda")
    st.caption("Wholesale medicines for pharmacies and clinics")
    if user:
        st.markdown(f"**{user['contact_name']}**  \n{user['business_name']}")
        if st.button("Log out", use_container_width=True):
            ss.user = None
            st.rerun()
    else:
        st.markdown(
            "You are browsing as a guest. Log in from **Account** to order.")
    st.divider()
    page = st.radio("Menu", MENUS[role], label_visibility="collapsed",
                    format_func=lambda k: LABELS[k] + (f"  ({open_n})" if k in ("seller", "orders") and open_n else ""))
    st.divider()
    st.caption(f"Need help? Call {MANAGER['name']}: {MANAGER['phone']}")

if ss.get("flash"):
    st.success(ss.pop("flash"))


# ---------- ORDER DIALOG ----------
@st.dialog("Place wholesale order")
def order_dialog(pname):
    u = db["users"][ss.user]
    row = db["inventory"][db["inventory"]["Product Name"] == pname].iloc[0]
    stock = int(row["Stock Quantity"])
    st.markdown(
        f"**{pname}**  \n{ugx(row['Unit Price (UGX)'])} per box · {stock} in stock")
    qty = st.number_input("Quantity (boxes)", 1, stock, min(5, stock))
    disc = 0.10 if qty >= 50 else 0.05 if qty >= 10 else 0
    if disc:
        st.caption(f"{int(disc * 100)}% volume discount applied")
    total = qty * row["Unit Price (UGX)"] * (1 - disc)
    c1, c2 = st.columns(2)
    name = c1.text_input("Recipient name", u["contact_name"])
    phone = c2.text_input(
        "WhatsApp number", u["phone"], help="Format: +256 followed by 9 digits")
    email = st.text_input("Email for order updates", ss.user)
    addr = st.text_input(
        "Delivery address", u["location"], placeholder="e.g. Plot 12 Kampala Road, Kampala")
    pay = st.radio("Payment", ["MTN Mobile Money", "Airtel Money",
                   "Trade Credit Line", "Cash on Delivery"], horizontal=True)
    st.metric("Total to pay", ugx(total))
    if st.button("Confirm order", type="primary", use_container_width=True):
        out = db["outlets"][db["outlets"]
                            ["Business Name"] == u["business_name"]]
        avail = (out.iloc[0]["Credit Limit (UGX)"] -
                 out.iloc[0]["Used Credit (UGX)"]) if len(out) else 0
        if not valid_phone(phone):
            st.error("Phone number must start with +256 followed by 9 digits.")
        elif not addr.strip() or not name.strip():
            st.error("Enter the recipient name and delivery address.")
        elif pay == "Trade Credit Line" and total > avail:
            st.error(
                f"This order is above your available credit of {ugx(avail)}. Choose another payment method.")
        else:
            oid = f"ORD-{uuid.uuid4().hex[:4].upper()}"
            o = {"OrderID": oid, "Outlet": u["business_name"], "Recipient Name": name, "Recipient Phone": phone,
                 "Recipient Email": email, "Delivery Location": addr, "Product Name": pname, "Batch Number": row["Batch Number"],
                 "Quantity": qty, "Total Amount (UGX)": total, "Payment Method": pay, "Payment Status": "Pending Payment",
                 "Item Verified": "Pending Inspection", "Status": "Processing", "Date": str(dt.date.today()),
                 "Dispatch Time": "Pending", "Delivery Time": "Pending"}
            db["inventory"].loc[db["inventory"]["Product Name"]
                                == pname, "Stock Quantity"] -= qty
            db["orders"] = pd.concat(
                [pd.DataFrame([o]), db["orders"]], ignore_index=True)
            if pay == "Trade Credit Line":
                db["outlets"].loc[db["outlets"]["Business Name"] ==
                                  u["business_name"], "Used Credit (UGX)"] += total
            ss.flash = f"Order {oid} placed for {addr}. {notify(o, 'We received your order.')}"
            st.rerun()


# ---------- PAGES ----------
if page == "market":
    first = user["contact_name"].split()[0] if user else None
    st.markdown(f"""<div class="hero"><h1>{f'Welcome back, {first}' if first else 'Order verified medicines in minutes'}</h1>
        <p>Wholesale stock for pharmacies, clinics and hospitals across Uganda.</p>
        <span class="chip">NDA-registered stock</span><span class="chip">Trade credit up to UGX 5M</span>
        <span class="chip">Order alerts on WhatsApp and email</span></div>""", unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    q = c1.text_input(
        "Search", placeholder="Search by product, category or NDA number", label_visibility="collapsed")
    cat = c2.selectbox("Category", ["All categories"] + sorted(
        db["inventory"]["Category"].unique()), label_visibility="collapsed")
    df = db["inventory"]
    if cat != "All categories":
        df = df[df["Category"] == cat]
    if q:
        df = df[df[["Product Name", "Category", "NDA Reg No"]].apply(
            lambda c: c.astype(str).str.contains(q, case=False, regex=False)).any(axis=1)]
    if df.empty:
        st.info(
            "No products match your search. Try a shorter word or choose All categories.")
    cols = st.columns(3)
    for i, (_, r) in enumerate(df.iterrows()):
        stock = int(r["Stock Quantity"])
        cls, lab = ("out", "Out of stock") if stock == 0 else (
            "low", f"Low stock · {stock} left") if stock < 200 else ("ok", f"In stock · {stock}")
        with cols[i % 3], st.container(border=True):
            st.markdown(
                f"<span class='pill {cls}'>{lab}</span>", unsafe_allow_html=True)
            st.markdown(f"**{r['Product Name']}**")
            st.markdown(
                f"<span class='price'>{ugx(r['Unit Price (UGX)'])}</span> per box", unsafe_allow_html=True)
            st.caption(
                f"{r['Category']} · Batch {r['Batch Number']} · Expires {r['Expiry Date']:%b %Y} · {r['NDA Reg No']}")
            if st.button("Order now" if user else "Log in to order", key=f"o_{r['Item ID']}", type="primary",
                         use_container_width=True, disabled=stock == 0):
                if user:
                    order_dialog(r["Product Name"])
                else:
                    st.toast(
                        "Log in or create an account from the Account page to place orders.", icon="🔒")

elif page == "orders":
    st.header("My Orders")
    mine = my_orders()
    if mine.empty:
        st.info("You have no orders yet. Open the Marketplace to place your first one.")
    for _, o in mine.iterrows():
        with st.container(border=True):
            a, b = st.columns([3, 2])
            a.markdown(
                f"**{o['OrderID']}** · {o['Product Name']} × {o['Quantity']}")
            a.caption(
                f"{o['Delivery Location']} · Batch {o['Batch Number']} · {o['Date']}")
            b.markdown(
                f"**{ugx(o['Total Amount (UGX)'])}**  \n{o['Payment Method']} · {o['Payment Status']}")
            st.markdown(stepper(o["Status"]), unsafe_allow_html=True)
            if o["Status"] == "Delivered":
                st.caption(
                    f"Delivered {o['Delivery Time']} · Items: {o['Item Verified']}")
                x, y, _ = st.columns([1, 1, 2])
                if o["Item Verified"] != "Verified Correct" and x.button("Confirm items received", key=f"c_{o['OrderID']}"):
                    upd(o["OrderID"], **{"Item Verified": "Verified Correct",
                        "Payment Status": "Paid on Delivery"})
                    st.rerun()
                if y.button("Report a problem", key=f"r_{o['OrderID']}"):
                    st.toast(
                        f"Support will contact you about {o['OrderID']}.", icon="📨")

elif page == "seller":
    st.header("Deliveries")
    st.caption(
        "Update each order as it moves. Customers are alerted by email and WhatsApp when it is delivered.")

    @st.fragment(run_every=10)
    def seller_board():
        c1, c2 = st.columns([3, 1])
        term = c1.text_input("Search", placeholder="Search by order ID or facility",
                             label_visibility="collapsed", key="s_q")
        show_all = c2.toggle("Show delivered", key="s_all")
        df = db["orders"]
        if not show_all:
            df = df[df["Status"] != "Delivered"]
        if term:
            df = df[df["OrderID"].str.contains(
                term, case=False, regex=False) | df["Outlet"].str.contains(term, case=False, regex=False)]
        if df.empty:
            st.success("All caught up. No orders are waiting.")
        for _, o in df.iterrows():
            with st.container(border=True):
                a, b, c = st.columns(3)
                a.markdown(f"**{o['OrderID']}** · {o['Outlet']}")
                a.caption(
                    f"{o['Recipient Name']} · {o['Recipient Phone']}\n\n{o['Delivery Location']}")
                b.markdown(f"{o['Product Name']} × {o['Quantity']}")
                b.caption(
                    f"Batch {o['Batch Number']} · {ugx(o['Total Amount (UGX)'])}")
                c.markdown(f"Items: **{o['Item Verified']}**")
                c.caption(f"Payment: {o['Payment Status']}")
                st.markdown(stepper(o["Status"]), unsafe_allow_html=True)
                if o["Status"] == "Processing" and st.button("Mark as dispatched", key=f"d_{o['OrderID']}"):
                    upd(o["OrderID"], **
                        {"Status": "Dispatched", "Dispatch Time": now()})
                    st.rerun()
                if o["Status"] == "Dispatched":
                    st.file_uploader("Proof of delivery (optional)", type=[
                                     "png", "jpg", "pdf"], key=f"f_{o['OrderID']}")
                    x, y, _ = st.columns([2, 2, 2])
                    if x.button("Mark delivered and send alerts", key=f"v_{o['OrderID']}", type="primary"):
                        upd(o["OrderID"], **{"Status": "Delivered", "Delivery Time": now(), "Payment Status": "Paid on Delivery",
                                             "Item Verified": "Verified Correct"})
                        ss.flash = f"{o['OrderID']} delivered. {notify(db['orders'].loc[db['orders']['OrderID'] == o['OrderID']].iloc[0], 'Your order has been delivered.')}"
                        st.rerun()
                    if y.button("Flag wrong item", key=f"m_{o['OrderID']}"):
                        upd(o["OrderID"], **
                            {"Item Verified": "Wrong item flagged"})
                        st.rerun()
    seller_board()

elif page == "inv":
    st.header("Inventory")
    for _, r in db["inventory"][db["inventory"]["Stock Quantity"] < 200].iterrows():
        st.warning(
            f"Low stock: {r['Product Name']} has {r['Stock Quantity']} boxes left.")
    st.caption(
        "Edit cells directly, add rows at the bottom, then select Save changes.")
    cats = ["Antibiotics", "Analgesics", "Antimalarial", "Medical Consumables"]
    edited = st.data_editor(db["inventory"], num_rows="dynamic", use_container_width=True, key="inv_editor", column_config={
        "Category": st.column_config.SelectboxColumn("Category", options=cats),
        "Unit Price (UGX)": st.column_config.NumberColumn(min_value=0, format="%d"),
        "Stock Quantity": st.column_config.NumberColumn(min_value=0, step=1),
        "Expiry Date": st.column_config.DateColumn(format="YYYY-MM-DD")})
    if st.button("Save changes", type="primary"):
        clean = edited.dropna(
            subset=["Item ID", "Product Name"]).reset_index(drop=True)
        db["inventory"] = clean
        ss.flash = "Inventory saved."
        st.rerun()

elif page == "outlets":
    st.header("Outlets & Credit")
    for _, r in db["outlets"].iterrows():
        used, limit = r["Used Credit (UGX)"], r["Credit Limit (UGX)"]
        with st.container(border=True):
            st.markdown(
                f"**{r['Business Name']}** · {r['Location']} · {r['Status']}")
            st.caption(f"{r['Contact Name']} · {r['Phone']} · {r['Email']}")
            st.progress(min(used / limit, 1.0),
                        text=f"{ugx(used)} used of {ugx(limit)}")
            if used / limit > 0.8:
                st.warning("This outlet has used more than 80% of its credit.")

elif page == "logs":
    st.header("Order Logs")
    o = db["orders"]
    k1, k2, k3 = st.columns(3)
    k1.metric("Revenue", ugx(o["Total Amount (UGX)"].sum()))
    k2.metric("Orders", len(o))
    k3.metric("Waiting to ship", len(o[o["Status"] == "Processing"]))
    st.download_button("Download CSV", o.to_csv(index=False).encode(
    ), f"medsupply_orders_{dt.date.today()}.csv", "text/csv")
    st.dataframe(o, use_container_width=True, hide_index=True)

elif page == "help":
    st.header("Help Assistant")
    st.caption(
        f"For anything else, call {MANAGER['name']} on {MANAGER['phone']}.")

    def reply(t):
        t = t.lower()
        if any(w in t for w in ("manager", "contact", "call")):
            return f"**{MANAGER['name']}**, Operations & Credit Manager: {MANAGER['phone']}"
        if any(w in t for w in ("price", "cost", "catalog")):
            return "\n".join(f"• **{r['Product Name']}**: {ugx(r['Unit Price (UGX)'])}" for _, r in db["inventory"].iterrows())
        if any(w in t for w in ("status", "track", "order")):
            if not user:
                return "Log in from the Account page to see your orders."
            m = my_orders().head(3)
            return "\n".join(f"• **{r['OrderID']}**: {r['Status']}" for _, r in m.iterrows()) or "You have no orders yet."
        return "I can help with **prices**, **catalog**, **order status** or **manager** contact."

    quick = None
    for col, (lab, key) in zip(st.columns(4), [("📋 Catalog", "catalog"), ("💰 Prices", "prices"), ("🚚 Order status", "status"), ("👤 Manager", "manager")]):
        if col.button(lab, use_container_width=True):
            quick = key
    typed = st.chat_input("Ask about prices, stock or orders")
    if msg := (quick or typed):
        ss.chat += [("user", msg), ("bot", reply(msg))]
    for who, text in ss.chat:
        with st.chat_message("user" if who == "user" else "assistant"):
            st.markdown(text)

elif page == "pay":
    st.header("Payments")
    st.caption("Demo mode: these forms do not move real money yet.")
    default = user["phone"] if user else "+256"
    tabs = st.tabs(["MTN Mobile Money", "Airtel Money", "Bank transfer"])
    for tab, prov in zip(tabs[:2], ["MTN", "Airtel"]):
        with tab:
            ph = st.text_input(f"{prov} number", default, key=f"{prov}_p")
            amt = st.number_input("Amount (UGX)", 1000,
                                  value=150000, step=10000, key=f"{prov}_a")
            if st.button(f"Request {prov} payment of {ugx(amt)}", type="primary", key=f"{prov}_b"):
                if valid_phone(ph):
                    st.success(
                        f"Payment request sent to {ph}. Reference: TXN-{uuid.uuid4().hex[:6].upper()}")
                else:
                    st.error("Enter the number as +256 followed by 9 digits.")
    with tabs[2]:
        st.markdown(
            "**Bank:** Stanbic Bank Uganda  \n**Account name:** MedSupply Uganda Limited  \n**Account number:** 9030012345678")

elif page == "account":
    st.header("Account")
    if user:
        with st.container(border=True):
            st.markdown(
                f"**{user['contact_name']}** · {user['business_name']}")
            st.caption(
                f"{ss.user} · {user['phone']} · {user['location']} · {role}")
    else:
        t1, t2, t3 = st.tabs(["Log in", "Create account", "Reset password"])
        with t1, st.form("login"):
            em = st.text_input("Email").strip().lower()
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Log in", type="primary", use_container_width=True):
                if em in db["users"] and db["users"][em]["password"] == hp(pw):
                    ss.user = em
                    st.rerun()
                else:
                    st.error(
                        "Email or password is incorrect. Check both, or create an account.")
        with t2, st.form("signup"):
            c1, c2 = st.columns(2)
            biz = c1.text_input("Pharmacy or business name *")
            nm = c1.text_input("Contact person *")
            em = c1.text_input("Email *").strip().lower()
            ph = c2.text_input("WhatsApp number *",
                               placeholder="+256770000000")
            loc = c2.text_input(
                "Location *", placeholder="e.g. Kampala Central, Plot 14 Acacia Ave")
            pw = c2.text_input("Password *", type="password")
            if st.form_submit_button("Create account", type="primary", use_container_width=True):
                if not all([biz, nm, em, ph, loc, pw]):
                    st.error("Fill in every field marked *.")
                elif not valid_phone(ph):
                    st.error(
                        "Phone number must start with +256 followed by 9 digits.")
                elif em in db["users"]:
                    st.error("That email already has an account. Log in instead.")
                else:
                    db["users"][em] = dict(password=hp(
                        pw), business_name=biz, contact_name=nm, phone=ph, location=loc, role="Customer / Buyer")
                    db["outlets"] = pd.concat([pd.DataFrame([{"ID": f"OUT-{uuid.uuid4().hex[:3].upper()}", "Business Name": biz, "Contact Name": nm,
                                                              "Phone": ph, "Email": em, "Location": loc, "Credit Limit (UGX)": 1000000,
                                                              "Used Credit (UGX)": 0, "Status": "Active"}]), db["outlets"]], ignore_index=True)
                    ss.user = em
                    ss.flash = "Account created. You are logged in."
                    st.rerun()
        with t3, st.form("reset"):
            em = st.text_input("Registered email").strip().lower()
            ph = st.text_input("Registered phone (+256...)").strip()
            p1 = st.text_input("New password", type="password")
            p2 = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Reset password", type="primary", use_container_width=True):
                if not all([em, ph, p1]):
                    st.error("Fill in every field.")
                elif p1 != p2:
                    st.error("The two passwords do not match.")
                elif em not in db["users"] or db["users"][em]["phone"].strip() != ph:
                    st.error("Email and phone do not match any account.")
                else:
                    db["users"][em]["password"] = hp(p1)
                    st.success("Password updated. You can log in now.")
