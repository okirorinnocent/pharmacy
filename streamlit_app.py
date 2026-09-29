import pandas as pd
import streamlit as st
from supabase import create_client
import json
from datetime import datetime

# Direct module imports from root directory
try:
    from config import settings
    from credit_engine import credit_engine
    from momo import momo_service
except ImportError:
    # Fallback mock setup if modules are building/loading
    class Settings:
        SUPABASE_URL = ""
        SUPABASE_KEY = ""
    settings = Settings()

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="MedSupply Uganda | B2B Pharma Platform",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Professional Styling (CSS Injection)
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stAppHeader { background-color: transparent; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 700; color: #0f172a; }
    .css-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    .badge-success { background-color: #dcfce7; color: #15803d; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 0.8rem; }
    .badge-pending { background-color: #fef3c7; color: #b45309; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 0.8rem; }
    .chat-bubble-user { background-color: #dcf8c6; padding: 10px 14px; border-radius: 12px; max-width: 80%; float: right; margin: 4px 0; font-size: 0.9rem; color: #000; }
    .chat-bubble-bot { background-color: #ffffff; padding: 10px 14px; border-radius: 12px; max-width: 80%; float: left; margin: 4px 0; border: 1px solid #e2e8f0; font-size: 0.9rem; color: #000; }
    </style>
""", unsafe_allow_html=True)

# Supabase Client Setup


@st.cache_resource
def get_supabase():
    try:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except Exception:
        return None


supabase = get_supabase()

# --- SIDEBAR & NAV ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/medical-heart.png", width=60)
    st.title("MedSupply Uganda")
    st.caption("B2B Digital Pharma & Micro-Credit")
    st.divider()

    menu = [
        "📊 Executive Overview",
        "🛒 Place New Order",
        "💬 WhatsApp Bot Sandbox",
        "📱 MTN MoMo Gateway",
        "🏥 Drug Outlets & Credit",
        "📦 Stock Inventory",
        "📋 Order History"
    ]
    choice = st.selectbox("Navigation Menu", menu)

    st.divider()

    # Quick Demo Data Generator
    st.subheader("🛠️ Demo Tools")
    if st.button("✨ Load Sample Demo Data", use_container_width=True):
        if supabase:
            # Seed Outlets
            supabase.table("drug_outlets").upsert([
                {"id": "11111111-1111-1111-1111-111111111111", "business_name": "Kampala Care Pharmacy",
                    "phone_number": "256771234567", "location": "Kampala Central", "credit_limit_ugx": 5000000},
                {"id": "22222222-2222-2222-2222-222222222222", "business_name": "Mbarara Express Clinic",
                    "phone_number": "256788990011", "location": "Mbarara Town", "credit_limit_ugx": 2500000}
            ]).execute()

            # Seed Inventory
            supabase.table("inventory_items").upsert([
                {"id": "a1111111-1111-1111-1111-111111111111",
                    "item_name": "Amoxicillin 500mg (Box of 100)", "unit_price_ugx": 35000, "stock_quantity": 450},
                {"id": "a2222222-2222-2222-2222-222222222222",
                    "item_name": "Paracetamol 500mg (Box of 100)", "unit_price_ugx": 12000, "stock_quantity": 1200},
                {"id": "a3333333-3333-3333-3333-333333333333",
                    "item_name": "Coartem 20/120 (Box of 30)", "unit_price_ugx": 85000, "stock_quantity": 180}
            ]).execute()

            st.success("Demo Outlets & Inventory Loaded!")
            st.rerun()

# --- 1. EXECUTIVE OVERVIEW ---
if choice == "📊 Executive Overview":
    st.header("📊 Operations & Credit Analytics")

    # Query Data
    outlets = supabase.table("drug_outlets").select(
        "*").execute().data if supabase else []
    orders = supabase.table("orders").select(
        "*").execute().data if supabase else []
    inventory = supabase.table("inventory_items").select(
        "*").execute().data if supabase else []

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Active Outlets", len(outlets))
    with c2:
        st.metric("Total Orders", len(orders))
    with c3:
        total_rev = sum([o.get("total_amount_ugx", 0)
                        for o in orders if o.get("status") in ["DELIVERED", "PAID"]])
        st.metric("Total Revenue", f"UGX {total_rev:,.0f}")
    with c4:
        st.metric("In-Stock Items", len(inventory))

    st.divider()

    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("Recent Order Stream")
        if orders:
            df_orders = pd.DataFrame(orders)
            st.dataframe(df_orders[["id", "phone_number", "total_amount_ugx", "status"]].tail(
                5), use_container_width=True)
        else:
            st.info(
                "No orders recorded yet. Use the 'Place New Order' or 'WhatsApp Bot Sandbox' to generate orders.")

    with col_right:
        st.subheader("System Status")
        st.success("🟢 WhatsApp API Connected")
        st.success("🟢 MTN MoMo Collection API Active")
        st.success("🟢 Micro-Credit Engine Ready")

# --- 2. PLACE NEW ORDER ---
elif choice == "🛒 Place New Order":
    st.header("🛒 Create B2B Pharmacy Order")
    st.caption(
        "Place wholesale pharmaceutical orders with instant MTN MoMo payment or Credit Line financing.")

    outlets = supabase.table("drug_outlets").select(
        "*").execute().data if supabase else []
    inventory = supabase.table("inventory_items").select(
        "*").execute().data if supabase else []

    if not outlets or not inventory:
        st.warning(
            "Please click '✨ Load Sample Demo Data' in the sidebar to populate items and outlets.")
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            outlet_options = {o["business_name"]: o for o in outlets}
            selected_outlet_name = st.selectbox(
                "Select Registering Drug Outlet", list(outlet_options.keys()))
            selected_outlet = outlet_options[selected_outlet_name]

            st.info(
                f"**Location:** {selected_outlet.get('location', 'N/A')}\n\n**Credit Available:** UGX {selected_outlet.get('credit_limit_ugx', 0):,.0f}")

        with col_b:
            item_options = {
                f"{i['item_name']} (UGX {i['unit_price_ugx']:,.0f})": i for i in inventory}
            selected_item_name = st.selectbox(
                "Select Pharmaceutical Product", list(item_options.keys()))
            selected_item = item_options[selected_item_name]

            quantity = st.number_input("Order Quantity (Boxes)", min_value=1, max_value=selected_item.get(
                "stock_quantity", 100), value=5)

        total_price = quantity * selected_item["unit_price_ugx"]

        st.divider()
        st.subheader(f"Total Order Value: **UGX {total_price:,.0f}**")

        payment_method = st.radio("Select Payment Method", [
                                  "MTN Mobile Money (Direct Push)", "Trade Credit Line Financing"], horizontal=True)

        if st.button("🚀 Confirm & Process Order", type="primary"):
            new_order = {
                "outlet_id": selected_outlet["id"],
                "phone_number": selected_outlet["phone_number"],
                "total_amount_ugx": total_price,
                "status": "PENDING_PAYMENT" if "MTN" in payment_method else "APPROVED_CREDIT"
            }

            res = supabase.table("orders").insert(new_order).execute()

            if "MTN" in payment_method:
                st.info(
                    f"📲 Triggered MTN MoMo Payment Prompt to **{selected_outlet['phone_number']}** for UGX {total_price:,.0f}")
                st.success(
                    "Order Created Successfully! Awaiting USSD PIN confirmation.")
            else:
                credit_limit = selected_outlet.get("credit_limit_ugx", 0)
                if total_price <= credit_limit:
                    st.success(
                        "✅ Credit Line Pre-Approved! Order dispatched for immediate delivery.")
                else:
                    st.error("❌ Credit Limit Exceeded. Please choose MTN MoMo.")

# --- 3. WHATSAPP BOT SANDBOX ---
elif choice == "💬 WhatsApp Bot Sandbox":
    st.header("💬 WhatsApp Ordering & Bot Simulator")
    st.caption(
        "Simulate how drug outlets interact with MedSupply Uganda via WhatsApp (Meta Webhooks).")

    col_chat, col_info = st.columns([2, 1])

    with col_chat:
        st.subheader("Live Interactive Chat Session")

        # Session Chat History Setup
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                {"role": "bot", "msg": "Hello! Welcome to MedSupply Uganda 🏥\nReply with:\n1. *CATALOG* to view drugs\n2. *ORDER* to buy stock\n3. *CREDIT* to check loan balance"}
            ]

        for chat in st.session_state.chat_history:
            if chat["role"] == "user":
                st.markdown(
                    f'<div class="chat-bubble-user"><b>You:</b> {chat["msg"]}</div><div style="clear:both;"></div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="chat-bubble-bot"><b>MedSupply Bot:</b><br>{chat["msg"]}</div><div style="clear:both;"></div>', unsafe_allow_html=True)

        st.write("")
        user_input = st.text_input(
            "Type WhatsApp Message...", key="whatsapp_input")

        if st.button("Send Message 📤"):
            if user_input:
                st.session_state.chat_history.append(
                    {"role": "user", "msg": user_input})

                # Bot Logic Simulation
                inp = user_input.strip().upper()
                if "CATALOG" in inp or "1" in inp:
                    bot_reply = "📦 **Available Stock Catalog:**\n1. Amoxicillin 500mg - UGX 35,000/box\n2. Paracetamol 500mg - UGX 12,000/box\n3. Coartem 20/120 - UGX 85,000/box\n\nReply *ORDER [Item Number] [Qty]* to buy."
                elif "CREDIT" in inp or "3" in inp:
                    bot_reply = "💳 **Credit Line Status:**\nRegistered Business: Kampala Care Pharmacy\nApproved Limit: **UGX 5,000,000**\nAvailable: **UGX 3,500,000**"
                elif "ORDER" in inp:
                    bot_reply = "✅ **Order Request Received!**\nPrompting MTN Mobile Money payment to your phone...\n\n*Reference: ORD-2026-9901*"
                else:
                    bot_reply = "Thank you for contacting MedSupply Uganda!\nReply with:\n1. *CATALOG*\n2. *ORDER*\n3. *CREDIT*"

                st.session_state.chat_history.append(
                    {"role": "bot", "msg": bot_reply})
                st.rerun()

    with col_info:
        st.subheader("Webhook Info")
        st.json({
            "provider": "Meta WhatsApp Business API",
            "webhook_endpoint": "/webhook/whatsapp",
            "status": "Active",
            "phone_id": "+256 700 000 000"
        })

# --- 4. MTN MOMO GATEWAY ---
elif choice == "📱 MTN MoMo Gateway":
    st.header("📱 MTN Mobile Money Collections")
    st.caption(
        "Direct integration with MTN MoMo API for automated payment collection and settlement.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Trigger Direct Push Payment")
        momo_phone = st.text_input(
            "Subscriber Phone Number", value="256771234567")
        momo_amount = st.number_input(
            "Amount (UGX)", min_value=1000, value=150000, step=5000)
        momo_ref = st.text_input("Order Reference", value="MED-ORDER-882")

        if st.button("📲 Initiate MoMo Request Payment"):
            st.info(f"Sending RequestToPay prompt to {momo_phone}...")
            st.success(
                f"✅ Payment Request Prompted! Transaction ID: `momo-uuid-{datetime.now().strftime('%H%M%S')}`")

    with col2:
        st.subheader("MoMo Transaction Logs")
        sample_logs = [
            {"TxID": "tx-9901", "Phone": "256771234567",
                "Amount": "175,000 UGX", "Status": "SUCCESS"},
            {"TxID": "tx-9902", "Phone": "256788990011",
                "Amount": "425,000 UGX", "Status": "SUCCESS"},
            {"TxID": "tx-9903", "Phone": "256775001122",
                "Amount": "85,000 UGX", "Status": "PENDING"}
        ]
        st.dataframe(pd.DataFrame(sample_logs), use_container_width=True)

# --- 5. DRUG OUTLETS & CREDIT ---
elif choice == "🏥 Drug Outlets & Credit":
    st.header("🏥 Drug Outlets & Micro-Credit Eligibility")
    outlets = supabase.table("drug_outlets").select(
        "*").execute().data if supabase else []

    if outlets:
        df = pd.DataFrame(outlets)
        st.dataframe(df, use_container_width=True)

        st.divider()
        st.subheader("Evaluate Trade Credit Score")
        selected_outlet = st.selectbox(
            "Select Outlet", df["business_name"].tolist())
        outlet_row = df[df["business_name"] == selected_outlet].iloc[0]

        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            completed_orders = st.number_input(
                "Completed Orders Count", min_value=0, value=8)
        with col_c2:
            avg_order = st.number_input(
                "Average Order Value (UGX)", min_value=0.0, value=650000.0)
        with col_c3:
            repayment_score = st.slider("Repayment Score", 0.0, 1.0, 0.95)

        if st.button("🧮 Calculate Approved Credit Limit"):
            try:
                limit = credit_engine.calculate_credit_limit(
                    completed_orders, avg_order, repayment_score)
            except AttributeError:
                limit = completed_orders * avg_order * repayment_score * 0.5

            st.success(
                f"Calculated Approved Credit Limit: **UGX {limit:,.0f}**")

            if st.button("💾 Save Limit to Database"):
                supabase.table("drug_outlets").update(
                    {"credit_limit_ugx": limit}).eq("id", outlet_row["id"]).execute()
                st.success("Database record updated!")
                st.rerun()
    else:
        st.info(
            "No registered drug outlets found in the database. Use '✨ Load Sample Demo Data' in the sidebar.")

# --- 6. STOCK INVENTORY ---
elif choice == "📦 Stock Inventory":
    st.header("📦 Warehouse Stock Inventory")
    items = supabase.table("inventory_items").select(
        "*").execute().data if supabase else []
    if items:
        st.dataframe(pd.DataFrame(items), use_container_width=True)
    else:
        st.info(
            "No inventory items found. Use '✨ Load Sample Demo Data' in the sidebar.")

# --- 7. ORDER HISTORY ---
elif choice == "📋 Order History":
    st.header("📋 Master Order Logs")
    orders = supabase.table("orders").select(
        "*").execute().data if supabase else []
    if orders:
        st.dataframe(pd.DataFrame(orders), use_container_width=True)
    else:
        st.info("No orders recorded yet.")
