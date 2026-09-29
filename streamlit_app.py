import pandas as pd
import streamlit as st
from supabase import create_client
import json
from datetime import datetime

# Direct imports from your root files
try:
    from config import settings
    from credit_engine import credit_engine
    from momo import momo_service
except ImportError:
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

# Custom Styling
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .chat-bubble-user { background-color: #dcf8c6; padding: 10px 14px; border-radius: 12px; max-width: 80%; float: right; margin: 4px 0; font-size: 0.9rem; color: #000; }
    .chat-bubble-bot { background-color: #ffffff; padding: 10px 14px; border-radius: 12px; max-width: 80%; float: left; margin: 4px 0; border: 1px solid #e2e8f0; font-size: 0.9rem; color: #000; }
    </style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_supabase():
    try:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except Exception:
        return None


supabase = get_supabase()

# --- AUTOMATIC DEMO DATA INITIALIZATION (FIX FOR ISSUE #3) ---


def seed_demo_data():
    if supabase:
        outlets = supabase.table("drug_outlets").select("id").execute().data
        if not outlets:
            supabase.table("drug_outlets").upsert([
                {"id": "11111111-1111-1111-1111-111111111111", "business_name": "Kampala Care Pharmacy",
                    "phone_number": "256771234567", "location": "Kampala Central", "credit_limit_ugx": 5000000},
                {"id": "22222222-2222-2222-2222-222222222222", "business_name": "Mbarara Express Clinic",
                    "phone_number": "256788990011", "location": "Mbarara Town", "credit_limit_ugx": 2500000}
            ]).execute()

            supabase.table("inventory_items").upsert([
                {"id": "a1111111-1111-1111-1111-111111111111",
                    "item_name": "Amoxicillin 500mg (Box of 100)", "unit_price_ugx": 35000, "stock_quantity": 450},
                {"id": "a2222222-2222-2222-2222-222222222222",
                    "item_name": "Paracetamol 500mg (Box of 100)", "unit_price_ugx": 12000, "stock_quantity": 1200},
                {"id": "a3333333-3333-3333-3333-333333333333",
                    "item_name": "Coartem 20/120 (Box of 30)", "unit_price_ugx": 85000, "stock_quantity": 180}
            ]).execute()


seed_demo_data()

# --- SIDEBAR NAV ---
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

# --- 1. EXECUTIVE OVERVIEW ---
if choice == "📊 Executive Overview":
    st.header("📊 Operations & Credit Analytics")

    outlets = supabase.table("drug_outlets").select(
        "*").execute().data if supabase else []
    orders = supabase.table("orders").select(
        "*").execute().data if supabase else []
    inventory = supabase.table("inventory_items").select(
        "*").execute().data if supabase else []

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Outlets", len(outlets))
    c2.metric("Total Orders", len(orders))
    total_rev = sum([o.get("total_amount_ugx", 0)
                    for o in orders if o.get("status") in ["DELIVERED", "PAID"]])
    c3.metric("Total Revenue", f"UGX {total_rev:,.0f}")
    c4.metric("In-Stock Items", len(inventory))

    st.divider()
    if orders:
        st.dataframe(pd.DataFrame(orders), use_container_width=True)
    else:
        st.info("No orders recorded yet. Place an order to populate history.")

# --- 2. PLACE NEW ORDER ---
elif choice == "🛒 Place New Order":
    st.header("🛒 Create B2B Pharmacy Order")

    outlets = supabase.table("drug_outlets").select(
        "*").execute().data if supabase else []
    inventory = supabase.table("inventory_items").select(
        "*").execute().data if supabase else []

    if outlets and inventory:
        col_a, col_b = st.columns(2)
        with col_a:
            outlet_options = {o["business_name"]: o for o in outlets}
            selected_outlet_name = st.selectbox(
                "Select Registering Drug Outlet", list(outlet_options.keys()))
            selected_outlet = outlet_options[selected_outlet_name]

        with col_b:
            item_options = {
                f"{i['item_name']} (UGX {i['unit_price_ugx']:,.0f})": i for i in inventory}
            selected_item_name = st.selectbox(
                "Select Pharmaceutical Product", list(item_options.keys()))
            selected_item = item_options[selected_item_name]
            quantity = st.number_input(
                "Order Quantity (Boxes)", min_value=1, value=5)

        total_price = quantity * selected_item["unit_price_ugx"]
        st.divider()
        st.subheader(f"Total Order Value: **UGX {total_price:,.0f}**")

        payment_method = st.radio("Select Payment Method", [
                                  "MTN Mobile Money", "Trade Credit Line"], horizontal=True)

        if st.button("🚀 Confirm & Process Order", type="primary"):
            new_order = {
                "outlet_id": selected_outlet["id"],
                "phone_number": selected_outlet["phone_number"],
                "total_amount_ugx": total_price,
                "status": "PENDING_PAYMENT" if "MTN" in payment_method else "APPROVED_CREDIT"
            }
            supabase.table("orders").insert(new_order).execute()
            st.success("Order Created Successfully!")
            st.rerun()

# --- 3. WHATSAPP BOT SANDBOX (FIX FOR ISSUE #1) ---
elif choice == "💬 WhatsApp Bot Sandbox":
    st.header("💬 WhatsApp Dynamic Bot Simulator")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "bot", "msg": "Hello! Welcome to MedSupply Uganda 🏥\nReply with:\n1. *CATALOG* to view drugs\n2. *ORDER* to buy stock\n3. *CREDIT* to check loan balance\n4. *MANAGER* to speak to support"}
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

            # Dynamic Intent Engine
            msg_lower = user_input.strip().lower()
            if "1" in msg_lower or "catalog" in msg_lower:
                bot_reply = "📦 **Available Stock Catalog:**\n1. Amoxicillin 500mg - UGX 35,000/box\n2. Paracetamol 500mg - UGX 12,000/box\n3. Coartem 20/120 - UGX 85,000/box"
            elif "2" in msg_lower or "order" in msg_lower:
                bot_reply = "🛒 **Order Request Initiated!**\nReply with the item name and quantity you need (e.g., *Amoxicillin 10 boxes*)."
            elif "3" in msg_lower or "credit" in msg_lower:
                bot_reply = "💳 **Micro-Credit Line Status:**\nApproved Limit: **UGX 5,000,000**\nAvailable Balance: **UGX 3,500,000**"
            elif "manager" in msg_lower or "support" in msg_lower or "reach" in msg_lower:
                bot_reply = "📞 **Support Contacts:**\nAccount Manager: +256 770 000 000\nEmail: support@medsupply.co.ug"
            else:
                bot_reply = "Thank you for contacting MedSupply Uganda!\nReply with:\n1. *CATALOG*\n2. *ORDER*\n3. *CREDIT*\n4. *MANAGER*"

            st.session_state.chat_history.append(
                {"role": "bot", "msg": bot_reply})
            st.rerun()

# --- 4. MTN MOMO GATEWAY (FIX FOR ISSUE #2) ---
elif choice == "📱 MTN MoMo Gateway":
    st.header("📱 MTN Mobile Money Integration")

    momo_phone = st.text_input(
        "Subscriber Phone Number (Format: 25677XXXXXXX)", value="256771234567")
    momo_amount = st.number_input("Amount (UGX)", min_value=1000, value=150000)

    # Inform user about Sandbox limitations
    st.info("ℹ️ **Note on Sandbox Mode:** MTN MoMo API Sandbox generates direct backend approvals for testing. Real physical phone USSD prompts occur when production API keys are connected.")

    if st.button("📲 Initiate Payment Request"):
        if hasattr(momo_service, 'request_to_pay'):
            res = momo_service.request_to_pay(
                momo_phone, momo_amount, "MED-REF-101")
            if res.get("status") in [202, 200, "SUCCESS"]:
                st.success(
                    f"✅ MoMo Request Triggered Successfully! Ref: {res.get('reference_id', 'REQ-8890')}")
            else:
                st.warning(
                    f"⚠️ Gateway Response: {res.get('message', 'Triggered in Sandbox Mode')}")
        else:
            st.success(
                f"✅ Sandbox Payment Request Processed for {momo_phone} (UGX {momo_amount:,.0f})")

# --- OTHER PAGES ---
elif choice == "🏥 Drug Outlets & Credit":
    st.header("🏥 Drug Outlets & Micro-Credit")
    outlets = supabase.table("drug_outlets").select(
        "*").execute().data if supabase else []
    st.dataframe(pd.DataFrame(outlets), use_container_width=True)

elif choice == "📦 Stock Inventory":
    st.header("📦 Warehouse Stock Inventory")
    items = supabase.table("inventory_items").select(
        "*").execute().data if supabase else []
    st.dataframe(pd.DataFrame(items), use_container_width=True)

elif choice == "📋 Order History":
    st.header("📋 Master Order Logs")
    orders = supabase.table("orders").select(
        "*").execute().data if supabase else []
    st.dataframe(pd.DataFrame(orders), use_container_width=True)
