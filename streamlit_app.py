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

# --- MODERN STYLING & CUSTOM COLOR SCHEME ---
st.markdown("""
    <style>
    /* Global App Background & Font */
    .stApp {
        background-color: #F1F5F9;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Header & Card Containers */
    .metric-card {
        background: #FFFFFF;
        padding: 1.25rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #E2E8F0;
        text-align: center;
    }
    
    /* WhatsApp Chat Styles */
    .chat-bubble-user {
        background: #DCF8C6;
        padding: 12px 16px;
        border-radius: 16px 16px 0px 16px;
        max-width: 75%;
        float: right;
        margin: 6px 0;
        font-size: 0.95rem;
        color: #0F172A;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .chat-bubble-bot {
        background: #FFFFFF;
        padding: 12px 16px;
        border-radius: 16px 16px 16px 0px;
        max-width: 75%;
        float: left;
        margin: 6px 0;
        border: 1px solid #E2E8F0;
        font-size: 0.95rem;
        color: #0F172A;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    /* Custom Notification Banner */
    .notification-box {
        padding: 1rem;
        border-radius: 8px;
        background-color: #EFF6FF;
        border-left: 5px solid #3B82F6;
        margin-bottom: 1rem;
        color: #1E3A8A;
    }
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
         "Location": "Kampala Central", "Credit Limit (UGX)": 5000000, "Used Credit (UGX)": 1500000, "Status": "Active"},
        {"ID": "OUT-102", "Business Name": "Mbarara Express Clinic", "Phone": "256788990011",
         "Location": "Mbarara Town", "Credit Limit (UGX)": 2500000, "Used Credit (UGX)": 425000, "Status": "Active"},
        {"ID": "OUT-103", "Business Name": "Jinja Life Pharma", "Phone": "256775001122",
         "Location": "Jinja Main St", "Credit Limit (UGX)": 1000000, "Used Credit (UGX)": 0, "Status": "Review"}
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
         "Total Amount (UGX)": 175000, "Payment Method": "MTN Mobile Money", "Status": "Arrived", "Date": "2026-09-28", "Notified": True},
        {"OrderID": "ORD-9902", "Outlet": "Mbarara Express Clinic",
         "Total Amount (UGX)": 425000, "Payment Method": "Trade Credit Line", "Status": "Dispatched", "Date": "2026-09-29", "Notified": False}
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
        {"role": "bot", "msg": "👋 Welcome to **MedSupply Uganda**!\n\nOptions:\n1. Type **CATALOG** to see available stock.\n2. Type **STATUS** to track your recent orders.\n3. Type **CREDIT** to view your balance."}
    ]

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/medical-heart.png", width=60)
    st.title("MedSupply Uganda")
    st.caption("B2B Digital Pharma & Micro-Credit Platform")
    st.divider()

    menu = [
        "🛒 Place New Order",
        "🔔 Order Tracking & Notifications",
        "💬 WhatsApp Bot Sandbox",
        "📱 MTN MoMo Gateway",
        "📦 Inventory Management",
        "🏥 Drug Outlets & Credit",
        "📋 Master Order Logs"
    ]
    choice = st.selectbox("Navigation Menu", menu)

    # Calculate unread notifications count
    unread_count = len(
        st.session_state.orders_df[st.session_state.orders_df["Status"] == "Arrived"])
    if unread_count > 0:
        st.info(
            f"🔔 **{unread_count} Order(s) Arrived!** Check the tracking page.")

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
        # Stock Check
        if quantity > item_row["Stock Quantity"]:
            st.error(
                f"❌ Insufficient stock. Only {item_row['Stock Quantity']} units available.")
        else:
            # Deduct inventory
            st.session_state.inventory_df.loc[st.session_state.inventory_df["Product Name"]
                                              == selected_item, "Stock Quantity"] -= quantity

            # Record Order
            order_id = f"ORD-{uuid.uuid4().hex[:4].upper()}"
            new_order = {
                "OrderID": order_id,
                "Outlet": selected_outlet,
                "Total Amount (UGX)": total_price,
                "Payment Method": payment_method,
                "Status": "Processing",
                "Date": str(datetime.date.today()),
                "Notified": False
            }
            st.session_state.orders_df = pd.concat(
                [pd.DataFrame([new_order]), st.session_state.orders_df], ignore_index=True)

            # Update outlet credit usage if chosen
            if payment_method == "Trade Credit Line":
                st.session_state.outlets_df.loc[st.session_state.outlets_df["Business Name"]
                                                == selected_outlet, "Used Credit (UGX)"] += total_price

            st.success(
                f"✅ Order **{order_id}** placed successfully! Status: Processing.")

# --- 2. ORDER TRACKING & NOTIFICATIONS ---
elif choice == "🔔 Order Tracking & Notifications":
    st.header("🔔 Order Notifications & Delivery Tracking")
    st.caption("Track order status in real time and receive delivery alerts.")

    # Show active notification banner for arrived items
    arrived_orders = st.session_state.orders_df[st.session_state.orders_df["Status"] == "Arrived"]
    if not arrived_orders.empty:
        for _, order in arrived_orders.iterrows():
            st.markdown(
                f'<div class="notification-box">🎉 <b>Delivery Notification:</b> Order <b>{order["OrderID"]}</b> for <b>{order["Outlet"]}</b> has ARRIVED at the delivery point!</div>',
                unsafe_allow_html=True
            )

    st.subheader("📦 Order Delivery Status")

    # Allow manual status change simulation (e.g. mark as Dispatched / Arrived)
    for idx, row in st.session_state.orders_df.iterrows():
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        col1.write(f"**{row['OrderID']}** ({row['Outlet']})")
        col2.write(f"UGX {row['Total Amount (UGX)']:,.0f}")
        col3.write(f"Status: **{row['Status']}**")

        # Admin button to simulate arrival for testing
        if row["Status"] != "Arrived":
            if col4.button(f"Simulate Arrival", key=f"btn_{row['OrderID']}"):
                st.session_state.orders_df.at[idx, "Status"] = "Arrived"
                st.rerun()
        else:
            col4.write("✅ Delivered")

# --- 3. WHATSAPP BOT SANDBOX ---
elif choice == "💬 WhatsApp Bot Sandbox":
    st.header("💬 Interactive WhatsApp Assistant")
    st.caption("Simulates dynamic 2-way conversation with context memory.")

    # Render previous messages
    for chat in st.session_state.chat_history:
        if chat["role"] == "user":
            st.markdown(
                f'<div class="chat-bubble-user"><b>You:</b> {chat["msg"]}</div><div style="clear:both;"></div>', unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="chat-bubble-bot"><b>MedSupply Bot:</b><br>{chat["msg"]}</div><div style="clear:both;"></div>', unsafe_allow_html=True)

    st.write("")
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("Type message here...", key="user_msg")
        submit_chat = st.form_submit_button("Send 📤")

    if submit_chat and user_input:
        st.session_state.chat_history.append(
            {"role": "user", "msg": user_input})
        msg_lower = user_input.strip().lower()

        # Conversational Response Engine
        if "1" in msg_lower or "catalog" in msg_lower or "stock" in msg_lower:
            items_str = "\n".join(
                [f"• *{row['Product Name']}*: UGX {row['Unit Price (UGX)']:,.0f} ({row['Stock Quantity']} left)" for _, row in st.session_state.inventory_df.iterrows()])
            bot_reply = f"📦 **Current Medicine Catalog:**\n\n{items_str}\n\n*Reply with 'Order [item name]' to buy stock.*"

        elif "2" in msg_lower or "status" in msg_lower or "track" in msg_lower or "arrived" in msg_lower:
            recent_orders = st.session_state.orders_df.head(3)
            orders_str = "\n".join(
                [f"• *{row['OrderID']}*: {row['Status']} (Amount: UGX {row['Total Amount (UGX)']:,.0f})" for _, row in recent_orders.iterrows()])
            bot_reply = f"🚚 **Your Recent Orders & Delivery Status:**\n\n{orders_str}"

        elif "3" in msg_lower or "credit" in msg_lower:
            bot_reply = "💳 **Micro-Credit Overview:**\nApproved Limit: **UGX 5,000,000**\nAvailable Limit: **UGX 3,500,000**\nStatus: *Eligible for instant order dispatch.*"

        else:
            bot_reply = f"Thanks for your message: *\"{user_input}\"*\n\nHow can I help?\n• Type **CATALOG** to see drugs\n• Type **STATUS** to check delivery alerts\n• Type **CREDIT** for loan status"

        st.session_state.chat_history.append({"role": "bot", "msg": bot_reply})
        st.rerun()

# --- 4. MTN MOMO GATEWAY ---
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
                    "⚠️ Live environment selected. Ensure production API credentials are set.")
            else:
                st.success(
                    "✅ Payment Request Prompted! (Sandbox auto-approved).")

    with col2:
        st.subheader("MoMo Transaction Logs")
        st.dataframe(st.session_state.momo_logs, use_container_width=True)

# --- 5. ADMIN INVENTORY & STOCK MANAGEMENT ---
elif choice == "📦 Inventory Management":
    st.header("📦 Warehouse Stock & Inventory Control")

    tab1, tab2 = st.tabs(["📋 Current Stock View", "➕ Restock / Add Inventory"])

    with tab1:
        st.dataframe(st.session_state.inventory_df, use_container_width=True)

    with tab2:
        st.subheader("Add New Product")
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

# --- 6. DRUG OUTLETS & CREDIT ONBOARDING ---
elif choice == "🏥 Drug Outlets & Credit":
    st.header("🏥 Registered Pharmacy Outlets & Credit Lines")

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
                    "Used Credit (UGX)": 0,
                    "Status": "Active"
                }
                st.session_state.outlets_df = pd.concat(
                    [pd.DataFrame([new_outlet]), st.session_state.outlets_df], ignore_index=True)
                st.success(
                    f"Registered outlet '{outlet_name}' with UGX {credit_limit:,.0f} credit line!")
                st.rerun()

# --- 7. MASTER ORDER LOGS ---
elif choice == "📋 Master Order Logs":
    st.header("📋 Master Order Logs & Delivery Audit")
    st.dataframe(st.session_state.orders_df, use_container_width=True)
