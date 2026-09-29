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
                "message": "Payment request successfully queued."
            }
    momo_service = MockMomoService()

# --- INITIALIZE SESSION STATE DATA ---
if "outlets_df" not in st.session_state:
    st.session_state.outlets_df = pd.DataFrame([
        {"ID": "OUT-101", "Business Name": "Kampala Care Pharmacy", "Phone": "256771234567",
            "Location": "Kampala Central", "Credit Limit (UGX)": 5000000, "Status": "Active"},
        {"ID": "OUT-102", "Business Name": "Mbarara Express Clinic", "Phone": "256788990011",
            "Location": "Mbarara Town", "Credit Limit (UGX)": 2500000, "Status": "Active"},
        {"ID": "OUT-103", "Business Name": "Jinja Life Pharma", "Phone": "256775001122",
            "Location": "Jinja Main St", "Credit Limit (UGX)": 1000000, "Status": "Review"}
    ])

if "inventory_df" not in st.session_state:
    st.session_state.inventory_df = pd.DataFrame([
        {"Item ID": "INV-001", "Product Name": "Amoxicillin 500mg (Box of 100)",
         "Unit Price (UGX)": 35000, "Stock Quantity": 450, "Category": "Antibiotics"},
        {"Item ID": "INV-002", "Product Name": "Paracetamol 500mg (Box of 100)",
         "Unit Price (UGX)": 12000, "Stock Quantity": 1200, "Category": "Analgesics"},
        {"Item ID": "INV-003", "Product Name": "Coartem 20/120 (Box of 30)",
         "Unit Price (UGX)": 85000, "Stock Quantity": 180, "Category": "Antimalarial"}
    ])

if "orders_df" not in st.session_state:
    st.session_state.orders_df = pd.DataFrame([
        {"OrderID": "ORD-9901", "Outlet": "Kampala Care Pharmacy",
            "Total Amount (UGX)": 175000, "Payment Method": "MTN MoMo", "Status": "Completed", "Date": "2026-09-28"},
        {"OrderID": "ORD-9902", "Outlet": "Mbarara Express Clinic",
            "Total Amount (UGX)": 425000, "Payment Method": "Trade Credit", "Status": "Approved", "Date": "2026-09-29"}
    ])

if "momo_logs" not in st.session_state:
    st.session_state.momo_logs = pd.DataFrame([
        {"TxID": "tx-9901", "Phone": "256771234567",
            "Amount (UGX)": 175000, "Reference": "MED-ORDER-880", "Status": "SUCCESS"},
        {"TxID": "tx-9902", "Phone": "256788990011",
            "Amount (UGX)": 425000, "Reference": "MED-ORDER-881", "Status": "SUCCESS"}
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
        "📦 Inventory & Admin Stock",
        "🏥 Drug Outlets & Credit",
        "📋 Master Order Logs"
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
            "Total Amount (UGX)": total_price,
            "Payment Method": payment_method,
            "Status": "Approved" if payment_method == "Trade Credit Line" else "Pending Payment",
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

            msg_lower = user_input.strip().lower()
            if "1" in msg_lower or "catalog" in msg_lower:
                items_str = "\n".join(
                    [f"{row['Product Name']} - UGX {row['Unit Price (UGX)']:,.0f}" for _, row in st.session_state.inventory_df.iterrows()])
                bot_reply = f"📦 **Available Stock Catalog:**\n{items_str}"
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

# --- 3. MTN MOMO GATEWAY ---
elif choice == "📱 MTN MoMo Gateway":
    st.header("📱 Direct Push MoMo Payment")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Trigger Direct Push Payment")
        momo_phone = st.text_input(
            "Subscriber Phone Number", value="256770665588")
        momo_amount = st.number_input(
            "Amount (UGX)", min_value=1000, value=150000, step=10000)
        order_ref = st.text_input(
            "Order Reference", value=f"MED-ORDER-{uuid.uuid4().hex[:3].upper()}")

        env_mode = st.radio("API Environment", [
                            "Sandbox Mode (Simulation)", "Production API (Live PIN Prompt)"], horizontal=True)

        if st.button("💳 Initiate MoMo Request Payment", type="primary"):
            st.info(f"Sending RequestToPay prompt to {momo_phone}...")

            tx_status = "PENDING_PROMPT" if "Production" in env_mode else "SUCCESS"
            new_tx = {
                "TxID": f"tx-{uuid.uuid4().hex[:4]}",
                "Phone": momo_phone,
                "Amount (UGX)": momo_amount,
                "Reference": order_ref,
                "Status": tx_status
            }
            st.session_state.momo_logs = pd.concat(
                [pd.DataFrame([new_tx]), st.session_state.momo_logs], ignore_index=True)

            if "Production" in env_mode:
                st.warning(
                    "⚠️ Live environment selected. Ensure production API credentials are set in environment variables.")
            else:
                st.success(
                    "✅ Payment Request Prompted! (Sandbox auto-approved).")

    with col2:
        st.subheader("MoMo Transaction Logs")
        st.dataframe(st.session_state.momo_logs, use_container_width=True)

# --- 4. ADMIN INVENTORY & STOCK MANAGEMENT ---
elif choice == "📦 Inventory & Admin Stock":
    st.header("📦 Warehouse Stock Inventory & Admin Management")

    tab1, tab2 = st.tabs(["📋 Current Stock View", "➕ Add / Restock Inventory"])

    with tab1:
        st.dataframe(st.session_state.inventory_df, use_container_width=True)

    with tab2:
        st.subheader("Add New Pharmaceutical Product")
        with st.form("add_stock_form"):
            col1, col2 = st.columns(2)
            with col1:
                item_name = st.text_input(
                    "Product Name & Unit Size", placeholder="e.g. Ciprofloxacin 500mg")
                category = st.selectbox(
                    "Category", ["Antibiotics", "Analgesics", "Antimalarial", "Vitamins", "Supplies"])
            with col2:
                unit_price = st.number_input(
                    "Unit Price (UGX)", min_value=500, value=25000, step=1000)
                quantity = st.number_input(
                    "Initial Stock Quantity", min_value=1, value=100)

            submit_stock = st.form_submit_button(
                "📦 Add Item to Inventory", type="primary")

            if submit_stock and item_name:
                new_item = {
                    "Item ID": f"INV-00{len(st.session_state.inventory_df) + 1}",
                    "Product Name": item_name,
                    "Unit Price (UGX)": unit_price,
                    "Stock Quantity": quantity,
                    "Category": category
                }
                st.session_state.inventory_df = pd.concat(
                    [pd.DataFrame([new_item]), st.session_state.inventory_df], ignore_index=True)
                st.success(f"Added '{item_name}' to inventory!")
                st.rerun()

# --- 5. DRUG OUTLETS & CREDIT ONBOARDING ---
elif choice == "🏥 Drug Outlets & Credit":
    st.header("🏥 Drug Outlets & Micro-Credit Eligibility")

    tab1, tab2 = st.tabs(["🏥 Registered Outlets", "➕ Onboard New Outlet"])

    with tab1:
        st.dataframe(st.session_state.outlets_df, use_container_width=True)

    with tab2:
        st.subheader("Register New Pharmacy / Drug Outlet")
        with st.form("onboard_outlet_form"):
            col1, col2 = st.columns(2)
            with col1:
                outlet_name = st.text_input(
                    "Business Name", placeholder="e.g. Mbale Health Pharma")
                phone = st.text_input(
                    "Phone Number", placeholder="256770000000")
            with col2:
                location = st.text_input(
                    "Location / District", placeholder="e.g. Mbale Central")
                credit_limit = st.number_input(
                    "Assigned Credit Limit (UGX)", min_value=0, value=2000000, step=500000)

            submit_outlet = st.form_submit_button(
                "🏥 Onboard Outlet", type="primary")

            if submit_outlet and outlet_name:
                new_outlet = {
                    "ID": f"OUT-10{len(st.session_state.outlets_df) + 1}",
                    "Business Name": outlet_name,
                    "Phone": phone,
                    "Location": location,
                    "Credit Limit (UGX)": credit_limit,
                    "Status": "Active"
                }
                st.session_state.outlets_df = pd.concat(
                    [pd.DataFrame([new_outlet]), st.session_state.outlets_df], ignore_index=True)
                st.success(
                    f"Registered outlet '{outlet_name}' with UGX {credit_limit:,.0f} credit line!")
                st.rerun()

# --- 6. MASTER ORDER LOGS ---
elif choice == "📋 Master Order Logs":
    st.header("📋 Master Order Logs & Tracking")
    st.dataframe(st.session_state.orders_df, use_container_width=True)
