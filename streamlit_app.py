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

# --- MODERN STYLING & COMPETITIVE UI COLOR SCHEME ---
st.markdown("""
    <style>
    /* Global Competitive Background Theme */
    .stApp {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        color: #F8FAFC;
    }
    
    /* Dynamic WhatsApp Chat Styling */
    .chat-bubble-user {
        background: #059669;
        padding: 12px 16px;
        border-radius: 16px 16px 0px 16px;
        max-width: 75%;
        float: right;
        margin: 8px 0;
        font-size: 0.95rem;
        color: #FFFFFF;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .chat-bubble-bot {
        background: #334155;
        padding: 14px 18px;
        border-radius: 16px 16px 16px 0px;
        max-width: 80%;
        float: left;
        margin: 8px 0;
        border: 1px solid #475569;
        font-size: 0.95rem;
        color: #F8FAFC;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        line-height: 1.5;
    }
    
    /* Dynamic Delivery Notification Banners */
    .notification-card {
        padding: 1.25rem;
        border-radius: 12px;
        background-color: #064E3B;
        border-left: 6px solid #10B981;
        margin-bottom: 1.2rem;
        color: #ECFDF5;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    </style>
""", unsafe_allow_html=True)

# --- INITIALIZE SESSION STATE DATA ---
if "outlets_df" not in st.session_state:
    st.session_state.outlets_df = pd.DataFrame([
        {"ID": "OUT-101", "Business Name": "Kampala Care Pharmacy", "Phone": "256771234567",
         "Location": "Kampala Central", "Credit Limit (UGX)": 5000000, "Used Credit (UGX)": 1500000, "Status": "Active"},
        {"ID": "OUT-102", "Business Name": "Mbarara Express Clinic", "Phone": "256788990011",
         "Location": "Mbarara Town", "Credit Limit (UGX)": 2500000, "Used Credit (UGX)": 425000, "Status": "Active"}
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
        {"OrderID": "ORD-9901", "Outlet": "Kampala Care Pharmacy", "Recipient Name": "Dr. Sarah",
         "Recipient Phone": "256771234567", "Recipient Email": "sarah@carepharma.com",
         "Total Amount (UGX)": 175000, "Payment Method": "MTN Mobile Money", "Status": "Arrived", "Date": "2026-09-28"},
        {"OrderID": "ORD-9902", "Outlet": "Mbarara Express Clinic", "Recipient Name": "John Doe",
         "Recipient Phone": "256788990011", "Recipient Email": "john@mbararaclinic.com",
         "Total Amount (UGX)": 425000, "Payment Method": "Trade Credit Line", "Status": "Dispatched", "Date": "2026-09-29"}
    ])

if "momo_logs" not in st.session_state:
    st.session_state.momo_logs = pd.DataFrame([
        {"TxID": "tx-9901", "Phone": "256771234567",
            "Amount (UGX)": 175000, "Reference": "MED-ORDER-880", "Status": "SUCCESS"}
    ])

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "bot", "msg": "👋 Welcome to **MedSupply Uganda Professional Support**.\n\nHow can I help you today? Type keywords like **CATALOG**, **PRICES**, **MANAGER**, **COMPANY**, or **STATUS**."}
    ]

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/medical-heart.png", width=60)
    st.title("MedSupply Uganda")
    st.caption("B2B Digital Pharma Platform")
    st.divider()

    menu = [
        "🛒 Place New Order & Recipient Info",
        "🔔 Delivery Notifications & Alerts",
        "🚚 Seller Delivery Control Center",
        "💬 WhatsApp Professional Assistant",
        "📱 MTN MoMo Gateway",
        "📦 Inventory Management",
        "🏥 Drug Outlets & Credit",
        "📋 Master Order Logs"
    ]
    choice = st.selectbox("Navigation Menu", menu)

    unread_count = len(st.session_state.orders_df[st.session_state.orders_df["Status"].isin(
        ["Arrived", "Delivered"])])
    if unread_count > 0:
        st.info(
            f"🔔 **{unread_count} Order(s) Delivered!** Check delivery notifications.")

# --- 1. PLACE NEW ORDER & RECIPIENT DETAILS ---
if choice == "🛒 Place New Order & Recipient Info":
    st.header("🛒 Place Order & Delivery Notification Setup")
    st.caption(
        "Provide recipient details to receive instant notification alerts when the seller triggers delivery.")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("1. Order & Product Selection")
        selected_outlet = st.selectbox(
            "Select Registered Outlet", st.session_state.outlets_df["Business Name"].tolist())
        selected_item = st.selectbox(
            "Select Product", st.session_state.inventory_df["Product Name"].tolist())
        quantity = st.number_input("Quantity (Boxes)", min_value=1, value=5)

    with col_b:
        st.subheader("2. Delivery Recipient Details")
        recipient_name = st.text_input(
            "Recipient Full Name", placeholder="e.g. Dr. Jane Okello")
        recipient_phone = st.text_input(
            "Recipient Mobile Phone (WhatsApp)", placeholder="e.g. 256770123456")
        recipient_email = st.text_input(
            "Recipient Email Address", placeholder="e.g. jane@clinic.com")

    item_row = st.session_state.inventory_df[st.session_state.inventory_df["Product Name"]
                                             == selected_item].iloc[0]
    total_price = quantity * item_row["Unit Price (UGX)"]

    st.divider()
    st.subheader(f"Total Amount Payable: **UGX {total_price:,.0f}**")
    payment_method = st.radio(
        "Payment Method", ["MTN Mobile Money", "Trade Credit Line"], horizontal=True)

    if st.button("🚀 Confirm Order & Register Recipient", type="primary"):
        if not recipient_name or not recipient_phone:
            st.error(
                "⚠️ Please enter the Recipient's Name and Phone Number to receive delivery notifications.")
        elif quantity > item_row["Stock Quantity"]:
            st.error(
                f"❌ Insufficient stock. Only {item_row['Stock Quantity']} units available.")
        else:
            st.session_state.inventory_df.loc[st.session_state.inventory_df["Product Name"]
                                              == selected_item, "Stock Quantity"] -= quantity
            order_id = f"ORD-{uuid.uuid4().hex[:4].upper()}"

            new_order = {
                "OrderID": order_id,
                "Outlet": selected_outlet,
                "Recipient Name": recipient_name,
                "Recipient Phone": recipient_phone,
                "Recipient Email": recipient_email,
                "Total Amount (UGX)": total_price,
                "Payment Method": payment_method,
                "Status": "Processing",
                "Date": str(datetime.date.today())
            }
            st.session_state.orders_df = pd.concat(
                [pd.DataFrame([new_order]), st.session_state.orders_df], ignore_index=True)

            if payment_method == "Trade Credit Line":
                st.session_state.outlets_df.loc[st.session_state.outlets_df["Business Name"]
                                                == selected_outlet, "Used Credit (UGX)"] += total_price

            st.success(
                f"✅ Order **{order_id}** recorded! Delivery notification alerts will be sent to **{recipient_name} ({recipient_phone})**.")

# --- 2. ORDER TRACKING & NOTIFICATIONS ---
elif choice == "🔔 Delivery Notifications & Alerts":
    st.header("🔔 Live Delivery Notifications")
    st.caption(
        "System alerts sent to recipients when sellers trigger item delivery.")

    delivered_orders = st.session_state.orders_df[st.session_state.orders_df["Status"].isin([
                                                                                            "Arrived", "Delivered"])]
    if not delivered_orders.empty:
        for _, order in delivered_orders.iterrows():
            st.markdown(
                f"""
                <div class="notification-card">
                    <h4>🎉 DELIVERY NOTIFICATION ALERT</h4>
                    <p><b>Order ID:</b> {order['OrderID']} | <b>Outlet:</b> {order['Outlet']}</p>
                    <p><b>Attention:</b> {order['Recipient Name']} ({order['Recipient Phone']} / {order['Recipient Email']})</p>
                    <p><b>Status:</b> Your package has been marked as <b>DELIVERED</b> by the supplier.</p>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("No active delivery notifications at the moment.")

    st.subheader("📦 All Orders Tracker")
    st.dataframe(st.session_state.orders_df, use_container_width=True)

# --- 3. SELLER DELIVERY CONTROL CENTER ---
elif choice == "🚚 Seller Delivery Control Center":
    st.header("🚚 Seller Dashboard: Trigger Item Delivery")
    st.caption(
        "When a seller marks an order as delivered, real-time alerts are sent to the registered recipient.")

    for idx, row in st.session_state.orders_df.iterrows():
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        col1.write(f"**{row['OrderID']}**\n*{row['Outlet']}*")
        col2.write(
            f"👤 Recipient: **{row['Recipient Name']}**\n📞 {row['Recipient Phone']}")
        col3.write(f"Status: **{row['Status']}**")

        if row["Status"] not in ["Arrived", "Delivered"]:
            if col4.button("🚚 Trigger Delivered", key=f"deliv_btn_{row['OrderID']}"):
                st.session_state.orders_df.at[idx, "Status"] = "Delivered"
                st.success(
                    f"Notification triggered and dispatched to {row['Recipient Name']} ({row['Recipient Phone']})!")
                st.rerun()
        else:
            col4.write("✅ Delivery Confirmed")

# --- 4. WHATSAPP BOT SANDBOX ---
elif choice == "💬 WhatsApp Professional Assistant":
    st.header("💬 Professional WhatsApp Assistant")

    for chat in st.session_state.chat_history:
        if chat["role"] == "user":
            st.markdown(
                f'<div class="chat-bubble-user"><b>You:</b> {chat["msg"]}</div><div style="clear:both;"></div>', unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="chat-bubble-bot"><b>MedSupply Bot:</b><br>{chat["msg"]}</div><div style="clear:both;"></div>', unsafe_allow_html=True)

    st.write("")
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("Type your message...", key="user_msg")
        submit_chat = st.form_submit_button("Send 📤")

    if submit_chat and user_input:
        st.session_state.chat_history.append(
            {"role": "user", "msg": user_input})
        msg_lower = user_input.strip().lower()

        if any(term in msg_lower for term in ["manager", "contact", "person", "support", "innocent", "okiror"]):
            bot_reply = "👤 **Manager Contact Details:**\n\n• **Name:** Okiror Innocent\n• **Phone:** +256763212490\n• **Role:** Operations & Credit Manager"

        elif any(term in msg_lower for term in ["price", "cost", "how much"]):
            matched = [f"• **{r['Product Name']}**: UGX {r['Unit Price (UGX)']:,.0f}" for _, r in st.session_state.inventory_df.iterrows(
            ) if any(w in r["Product Name"].lower() for w in msg_lower.split())]
            if matched:
                bot_reply = "💰 **Product Price Quote:**\n\n" + \
                    "\n".join(matched)
            else:
                items_str = "\n".join(
                    [f"• **{r['Product Name']}**: UGX {r['Unit Price (UGX)']:,.0f}" for _, r in st.session_state.inventory_df.iterrows()])
                bot_reply = f"💰 **Wholesale Prices:**\n\n{items_str}"

        elif any(term in msg_lower for term in ["company", "about"]):
            bot_reply = "🏢 **About MedSupply Uganda:**\n\nMedSupply Uganda is a B2B digital pharmaceutical platform providing healthcare facilities with authentic medicines and trade credit financing."

        elif any(term in msg_lower for term in ["status", "track", "delivery", "arrived"]):
            recent = st.session_state.orders_df.head(3)
            orders_str = "\n".join(
                [f"• **{r['OrderID']}** ({r['Recipient Name']}): {r['Status']}" for _, r in recent.iterrows()])
            bot_reply = f"🚚 **Order Status:**\n\n{orders_str}"

        else:
            bot_reply = "Thank you for reaching out. Reply with **PRICES**, **MANAGER**, **COMPANY**, or **STATUS** for details."

        st.session_state.chat_history.append({"role": "bot", "msg": bot_reply})
        st.rerun()

# --- 5. MTN MOMO GATEWAY ---
elif choice == "📱 MTN MoMo Gateway":
    st.header("📱 MTN MoMo Payment Gateway")
    momo_phone = st.text_input("Subscriber Phone", value="256770665588")
    momo_amount = st.number_input("Amount (UGX)", value=150000)
    if st.button("💳 Trigger MoMo Prompt", type="primary"):
        st.success(f"Payment prompt sent to {momo_phone}!")

# --- 6. INVENTORY MANAGEMENT ---
elif choice == "📦 Inventory Management":
    st.header("📦 Warehouse Stock Management")
    st.dataframe(st.session_state.inventory_df, use_container_width=True)

# --- 7. DRUG OUTLETS ---
elif choice == "🏥 Drug Outlets & Credit":
    st.header("🏥 Outlets & Credit Lines")
    st.dataframe(st.session_state.outlets_df, use_container_width=True)

# --- 8. MASTER LOGS ---
elif choice == "📋 Master Order Logs":
    st.header("📋 Master Order Logs")
    st.dataframe(st.session_state.orders_df, use_container_width=True)
