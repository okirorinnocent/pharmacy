import streamlit as st
import pandas as pd
import uuid
import datetime

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

# --- SAFE SERVICE IMPORTS & FALLBACK DEFINITIONS ---
try:
    from momo import momo_service
except Exception:
    class MockMomoService:
        @staticmethod
        def request_to_pay(phone_number, amount, reference_id=None):
            return {
                "status": 202,
                "reference_id": reference_id or str(uuid.uuid4())[:8],
                "message": "Payment request successfully queued in Sandbox."
            }
    momo_service = MockMomoService()

# Safe Supabase Loading
try:
    from supabase import create_client
    from config import settings
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
except Exception:
    supabase = None

# --- INITIALIZE SESSION STATE DATA (PREVENTS EMPTY TABLES) ---
if "outlets_df" not in st.session_state:
    st.session_state.outlets_df = pd.DataFrame([
        {"ID": "OUT-101", "Business Name": "Kampala Care Pharmacy", "Phone": "256771234567",
            "Location": "Kampala Central", "Credit Limit (UGX)": "5,000,000", "Status": "Active"},
        {"ID": "OUT-102", "Business Name": "Mbarara Express Clinic", "Phone": "256788990011",
            "Location": "Mbarara Town", "Credit Limit (UGX)": "2,500,000", "Status": "Active"},
        {"ID": "OUT-103", "Business Name": "Jinja Life Pharma", "Phone": "256775001122",
            "Location": "Jinja Main St", "Credit Limit (UGX)": "1,000,000", "Status": "Review"}
    ])

if "inventory_df" not in st.session_state:
    st.session_state.inventory_df = pd.DataFrame([
        {"Item ID": "INV-001", "Product Name": "Amoxicillin 500mg (Box of 100)",
         "Unit Price (UGX)": 35000, "In Stock": 450, "Category": "Antibiotics"},
        {"Item ID": "INV-002", "Product Name": "Paracetamol 500mg (Box of 100)",
         "Unit Price (UGX)": 12000, "In Stock": 1200, "Category": "Analgesics"},
        {"Item ID": "INV-003", "Product Name": "Coartem 20/120 (Box of 30)",
         "Unit Price (UGX)": 85000, "In Stock": 180, "Category": "Antimalarial"}
    ])

if "orders_df" not in st.session_state:
    st.session_state.orders_df = pd.DataFrame([
        {"OrderID": "ORD-9901", "Outlet": "Kampala Care Pharmacy",
            "Total Amount (UGX)": "175,000", "Payment Method": "MTN MoMo", "Status": "Completed", "Date": "2026-09-28"},
        {"OrderID": "ORD-9902", "Outlet": "Mbarara Express Clinic",
            "Total Amount (UGX)": "425,000", "Payment Method": "Trade Credit", "Status": "Approved", "Date": "2026-09-29"}
    ])

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "bot", "msg": "Hello! Welcome to MedSupply Uganda 🏥\nReply with:\n1. *CATALOG* to view drugs\n2. *ORDER* to buy stock\n3. *CREDIT* to check loan balance\n4. *MANAGER* to speak to support"}
    ]

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/medical-heart.png", width=60)
    st.title("MedSupply Uganda")
    st.caption("B2B Digital Pharma & Micro-Credit")
    st.divider()

    menu = [
        "🛒 Place New Order",
        "💬 WhatsApp Bot Sandbox",
        "📱 MTN MoMo Gateway",
        "🏥 Drug Outlets & Credit",
        "📦 Stock Inventory",
        "📋 Order History"
    ]
    choice = st.selectbox("Navigation Menu", menu)

# --- 1. PLACE NEW ORDER ---
if choice == "🛒 Place New Order":
    st.header("🛒 Create B2B Pharmacy Order")
    st.caption(
        "Place wholesale pharmaceutical orders with instant MTN MoMo payment or Credit Line financing.")

    col_a, col_b = st.columns(2)
    with col_a:
        selected_outlet = st.selectbox(
            "Select Registering Drug Outlet", st.session_state.outlets_df["Business Name"].tolist())
    with col_b:
        selected_item = st.selectbox(
            "Select Pharmaceutical Product", st.session_state.inventory_df["Product Name"].tolist())
        quantity = st.number_input(
            "Order Quantity (Boxes)", min_value=1, value=5)

    item_row = st.session_state.inventory_df[st.session_state.inventory_df["Product Name"]
                                             == selected_item].iloc[0]
    total_price = quantity * item_row["Unit Price (UGX)"]

    st.divider()
    st.subheader(f"Total Order Value: **UGX {total_price:,.0f}**")

    payment_method = st.radio("Select Payment Method", [
                              "MTN Mobile Money", "Trade Credit Line"], horizontal=True)

    if st.button("🚀 Confirm & Process Order", type="primary"):
        new_order = {
            "OrderID": f"ORD-{uuid.uuid4().hex[:4].upper()}",
            "Outlet": selected_outlet,
            "Total Amount (UGX)": f"{total_price:,.0f}",
            "Payment Method": payment_method,
            "Status": "Processing",
            "Date": str(datetime.date.today())
        }
        st.session_state.orders_df = pd.concat(
            [pd.DataFrame([new_order]), st.session_state.orders_df], ignore_index=True)
        st.success("Order Created and Recorded Successfully!")

# --- 2. WHATSAPP BOT SANDBOX ---
elif choice == "💬 WhatsApp Bot Sandbox":
    st.header("💬 WhatsApp Dynamic Bot Simulator")

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
                bot_reply = "🛒 **Order Request Initiated!**\nReply with the item name and quantity you need."
            elif "3" in msg_lower or "credit" in msg_lower:
                bot_reply = "💳 **Micro-Credit Line Status:**\nApproved Limit: **UGX 5,000,000**\nAvailable Balance: **UGX 3,500,000**"
            elif "manager" in msg_lower or "support" in msg_lower or "reach" in msg_lower:
                bot_reply = "📞 **Support Contacts:**\nAccount Manager: +256 770 000 000\nEmail: support@medsupply.co.ug"
            else:
                bot_reply = "Thank you for contacting MedSupply Uganda!\nReply with:\n1. *CATALOG*\n2. *ORDER*\n3. *CREDIT*\n4. *MANAGER*"

            st.session_state.chat_history.append(
                {"role": "bot", "msg": bot_reply})
            st.rerun()

# --- 3. MTN MOMO GATEWAY ---
elif choice == "📱 MTN MoMo Gateway":
    st.header("📱 Direct Push MoMo Payment")

    col1, col2 = st.columns([1, 1])
    with col1:
        momo_phone = st.text_input(
            "Subscriber Phone Number", value="256770665588")
        momo_amount = st.number_input(
            "Amount (UGX)", min_value=1000, value=150000)
        order_ref = st.text_input("Order Reference", value="MED-ORDER-882")

        if st.button("💳 Initiate MoMo Request Payment", type="primary"):
            if hasattr(momo_service, 'request_to_pay'):
                res = momo_service.request_to_pay(
                    momo_phone, momo_amount, order_ref)
                st.info(f"Sending RequestToPay prompt to {momo_phone}...")
                st.success("✅ Payment Request Prompted!")
            else:
                st.error("MoMo Service initialisation error.")

    with col2:
        st.subheader("MoMo Transaction Logs")
        st.dataframe(pd.DataFrame([
            {"TxID": "tx-9901", "Phone": "256771234567",
                "Amount": "175,000 UGX", "Status": "SUCCESS"},
            {"TxID": "tx-9902", "Phone": "256788990011",
                "Amount": "425,000 UGX", "Status": "SUCCESS"},
            {"TxID": "tx-9903", "Phone": "256775001122",
                "Amount": "85,000 UGX", "Status": "PENDING"}
        ]), use_container_width=True)

# --- 4. DRUG OUTLETS & CREDIT ---
elif choice == "🏥 Drug Outlets & Credit":
    st.header("🏥 Drug Outlets & Micro-Credit Eligibility")
    st.dataframe(st.session_state.outlets_df, use_container_width=True)

# --- 5. STOCK INVENTORY ---
elif choice == "📦 Stock Inventory":
    st.header("📦 Warehouse Stock Inventory")
    st.dataframe(st.session_state.inventory_df, use_container_width=True)

# --- 6. ORDER HISTORY ---
elif choice == "📋 Order History":
    st.header("📋 Master Order Logs")
    st.dataframe(st.session_state.orders_df, use_container_width=True)
