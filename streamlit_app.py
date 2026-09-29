import streamlit as st
import pandas as pd
import uuid
import datetime
import re

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="MedSupply Uganda | B2B Pharma Platform",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- 2. CUSTOM STYLING & HIGH-CONTRAST THEME ---
st.markdown("""
    <style>
    /* Global Background Theme */
    .stApp {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        color: #F8FAFC;
    }
    
    /* Layout Padding to Prevent Header Collisions */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        padding-left: 2.5rem;
        padding-right: 2.5rem;
    }
    
    /* WhatsApp Chat Bubble Styling */
    .chat-bubble-user {
        background-color: #059669;
        padding: 12px 16px;
        border-radius: 16px 16px 2px 16px;
        max-width: 75%;
        float: right;
        margin: 8px 0;
        font-size: 0.95rem;
        color: #FFFFFF;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .chat-bubble-bot {
        background-color: #1E293B;
        padding: 14px 18px;
        border-radius: 16px 16px 16px 2px;
        max-width: 80%;
        float: left;
        margin: 8px 0;
        border: 1px solid #334155;
        font-size: 0.95rem;
        color: #F8FAFC;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        line-height: 1.5;
    }
    .chat-time {
        font-size: 0.7rem;
        color: #94A3B8;
        margin-top: 4px;
        display: block;
    }
    
    /* Notification Cards */
    .notification-card {
        padding: 1.25rem;
        border-radius: 12px;
        background-color: #064E3B;
        border-left: 6px solid #10B981;
        margin-bottom: 1.2rem;
        color: #FFFFFF;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
    }
    .notification-card h4 {
        color: #34D399;
        margin-bottom: 0.5rem;
    }
    
    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .status-delivered { background-color: #059669; color: #FFFFFF; }
    .status-dispatched { background-color: #D97706; color: #FFFFFF; }
    .status-processing { background-color: #2563EB; color: #FFFFFF; }
    </style>
""", unsafe_allow_html=True)

# --- 3. SESSION STATE INITIALIZATION ---
if "outlets_df" not in st.session_state:
    st.session_state.outlets_df = pd.DataFrame([
        {
            "ID": "OUT-101",
            "Business Name": "Kampala Care Pharmacy",
            "Contact Name": "Dr. Sarah",
            "Phone": "+256771234567",
            "Email": "sarah@carepharma.com",
            "Location": "Kampala Central",
            "Credit Limit (UGX)": 5000000,
            "Used Credit (UGX)": 1500000,
            "Status": "Active"
        },
        {
            "ID": "OUT-102",
            "Business Name": "Mbarara Express Clinic",
            "Contact Name": "John Doe",
            "Phone": "+256788990011",
            "Email": "john@mbararaclinic.com",
            "Location": "Mbarara Town",
            "Credit Limit (UGX)": 2500000,
            "Used Credit (UGX)": 425000,
            "Status": "Active"
        }
    ])

# FIXED: Expiry Date initialized as python datetime.date objects to prevent editor crashes
if "inventory_df" not in st.session_state:
    st.session_state.inventory_df = pd.DataFrame([
        {
            "Item ID": "INV-001",
            "Product Name": "Amoxicillin 500mg (Box of 100)",
            "Category": "Antibiotics",
            "Unit Price (UGX)": 35000,
            "Stock Quantity": 450,
            "Batch Number": "AMX-2026-09A",
            "Expiry Date": datetime.date(2028, 6, 30),
            "NDA Reg No": "NDA/UG/MED-4821"
        },
        {
            "Item ID": "INV-002",
            "Product Name": "Paracetamol 500mg (Box of 100)",
            "Category": "Analgesics",
            "Unit Price (UGX)": 12000,
            "Stock Quantity": 120,  # Below 200 threshold for low stock alert
            "Batch Number": "PAR-2026-01C",
            "Expiry Date": datetime.date(2027, 12, 15),
            "NDA Reg No": "NDA/UG/MED-1029"
        },
        {
            "Item ID": "INV-003",
            "Product Name": "Coartem 20/120 (Box of 30)",
            "Category": "Antimalarial",
            "Unit Price (UGX)": 85000,
            "Stock Quantity": 180,
            "Batch Number": "CRT-2026-11B",
            "Expiry Date": datetime.date(2027, 8, 20),
            "NDA Reg No": "NDA/UG/MED-9930"
        }
    ])

if "orders_df" not in st.session_state:
    st.session_state.orders_df = pd.DataFrame([
        {
            "OrderID": "ORD-9901",
            "Outlet": "Kampala Care Pharmacy",
            "Recipient Name": "Dr. Sarah",
            "Recipient Phone": "+256771234567",
            "Recipient Email": "sarah@carepharma.com",
            "Product Name": "Amoxicillin 500mg (Box of 100)",
            "Quantity": 5,
            "Total Amount (UGX)": 175000,
            "Payment Method": "MTN Mobile Money",
            "Status": "Delivered",
            "Date": "2026-09-28",
            "Dispatch Time": "2026-09-28 09:30 AM",
            "Delivery Time": "2026-09-28 02:15 PM"
        },
        {
            "OrderID": "ORD-9902",
            "Outlet": "Mbarara Express Clinic",
            "Recipient Name": "John Doe",
            "Recipient Phone": "+256788990011",
            "Recipient Email": "john@mbararaclinic.com",
            "Product Name": "Coartem 20/120 (Box of 30)",
            "Quantity": 5,
            "Total Amount (UGX)": 425000,
            "Payment Method": "Trade Credit Line",
            "Status": "Dispatched",
            "Date": "2026-09-29",
            "Dispatch Time": "2026-09-29 11:00 AM",
            "Delivery Time": "Pending"
        }
    ])

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "bot",
            "msg": "👋 Welcome to **MedSupply Uganda Professional Support**.\n\nHow can I help you today? Click a quick topic below or type your inquiry.",
            "time": datetime.datetime.now().strftime("%H:%M")
        }
    ]

# Phone Validator Function


def validate_uganda_phone(phone_str):
    pattern = r"^\+256[0-9]{9}$"
    return re.match(pattern, phone_str) is not None


# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/medical-heart.png", width=60)
    st.title("MedSupply Uganda")
    st.caption("B2B Digital Pharma Platform")
    st.divider()

    menu = [
        "🛒 Place New Order",
        "🔔 Delivery Notifications",
        "🚚 Seller Control Center",
        "💬 WhatsApp Assistant",
        "📱 Payment Gateways",
        "📦 Inventory Management",
        "🏥 Outlets & Credit Lines",
        "📋 Master Order Logs"
    ]
    choice = st.selectbox("Navigation Menu", menu)

    unread_count = len(st.session_state.orders_df[st.session_state.orders_df["Status"].isin(
        ["Arrived", "Delivered"])])
    if unread_count > 0:
        st.success(f"🔔 **{unread_count} Order(s) Delivered!**")

# --- 5. PAGE ROUTING ---

# CHOICE 1: PLACE NEW ORDER
if choice == "🛒 Place New Order":
    st.header("🛒 Place Order & Notification Setup")
    st.caption(
        "Configure recipient details to receive instant notification alerts when the seller triggers delivery.")

    col_a, col_b = st.columns(2, gap="medium")

    with col_a:
        st.subheader("1. Order & Product Selection")
        selected_outlet_name = st.selectbox(
            "Select Registered Outlet",
            st.session_state.outlets_df["Business Name"].tolist()
        )

        outlet_data = st.session_state.outlets_df[st.session_state.outlets_df["Business Name"]
                                                  == selected_outlet_name].iloc[0]

        category_filter = st.selectbox("Filter Category", [
                                       "All"] + list(st.session_state.inventory_df["Category"].unique()))

        if category_filter != "All":
            filtered_inv = st.session_state.inventory_df[
                st.session_state.inventory_df["Category"] == category_filter]
        else:
            filtered_inv = st.session_state.inventory_df

        selected_item_name = st.selectbox(
            "Select Product", filtered_inv["Product Name"].tolist())
        item_row = st.session_state.inventory_df[st.session_state.inventory_df["Product Name"]
                                                 == selected_item_name].iloc[0]

        st.info(
            f"📋 **Batch No:** `{item_row['Batch Number']}` | **Expiry:** `{item_row['Expiry Date']}` | **NDA Reg:** `{item_row['NDA Reg No']}`")

        quantity = st.number_input("Quantity (Boxes)", min_value=1, value=5)

        discount = 0.0
        if quantity >= 50:
            discount = 0.10
            st.caption("🎉 10% Bulk Volume Discount Applied!")
        elif quantity >= 10:
            discount = 0.05
            st.caption("🎉 5% Tiered Volume Discount Applied!")

        base_price = quantity * item_row["Unit Price (UGX)"]
        total_price = base_price * (1 - discount)

    with col_b:
        st.subheader("2. Delivery Recipient Details")
        st.caption("Auto-filled from registered outlet profile:")

        recipient_name = st.text_input(
            "Recipient Full Name", value=outlet_data["Contact Name"])
        recipient_phone = st.text_input(
            "Recipient WhatsApp Number (+256...)", value=outlet_data["Phone"])
        recipient_email = st.text_input(
            "Recipient Email Address", value=outlet_data["Email"])

    st.divider()

    col_price, col_pay = st.columns([1, 2])
    with col_price:
        st.metric("Total Payable Amount", f"UGX {total_price:,.0f}",
                  delta=f"-UGX {base_price - total_price:,.0f}" if discount > 0 else None)

    with col_pay:
        payment_method = st.radio(
            "Payment Method",
            ["MTN Mobile Money", "Airtel Money",
                "Trade Credit Line", "Bank Wire Transfer"],
            horizontal=True
        )

    if st.button("🚀 Confirm Order & Register Recipient", type="primary", use_container_width=True):
        if not validate_uganda_phone(recipient_phone):
            st.error(
                "⚠️ Invalid Ugandan Phone Format! Ensure it starts with `+256` followed by 9 digits (e.g., +256770123456).")
        elif not recipient_name or not recipient_email:
            st.error("⚠️ Please ensure Recipient Name and Email are provided.")
        elif quantity > item_row["Stock Quantity"]:
            st.error(
                f"❌ Insufficient stock. Only {item_row['Stock Quantity']} units available.")
        else:
            st.session_state.inventory_df.loc[
                st.session_state.inventory_df["Product Name"] == selected_item_name, "Stock Quantity"
            ] -= quantity

            order_id = f"ORD-{uuid.uuid4().hex[:4].upper()}"

            new_order = {
                "OrderID": order_id,
                "Outlet": selected_outlet_name,
                "Recipient Name": recipient_name,
                "Recipient Phone": recipient_phone,
                "Recipient Email": recipient_email,
                "Product Name": selected_item_name,
                "Quantity": quantity,
                "Total Amount (UGX)": total_price,
                "Payment Method": payment_method,
                "Status": "Processing",
                "Date": str(datetime.date.today()),
                "Dispatch Time": "Pending",
                "Delivery Time": "Pending"
            }
            st.session_state.orders_df = pd.concat(
                [pd.DataFrame([new_order]), st.session_state.orders_df], ignore_index=True)

            if payment_method == "Trade Credit Line":
                st.session_state.outlets_df.loc[
                    st.session_state.outlets_df[
                        "Business Name"] == selected_outlet_name, "Used Credit (UGX)"
                ] += total_price

            st.success(
                f"✅ Order **{order_id}** successfully recorded! Delivery alerts routed to **{recipient_name} ({recipient_phone})**.")

# CHOICE 2: DELIVERY NOTIFICATIONS
elif choice == "🔔 Delivery Notifications":
    st.header("🔔 Live Delivery Notifications & Order Tracker")
    st.caption(
        "Real-time system updates sent to facility managers upon order fulfillment.")

    delivered_orders = st.session_state.orders_df[st.session_state.orders_df["Status"].isin([
                                                                                            "Arrived", "Delivered"])]

    if not delivered_orders.empty:
        for _, order in delivered_orders.iterrows():
            st.markdown(f"""
                <div class="notification-card">
                    <h4>🎉 DELIVERY CONFIRMED | Order {order['OrderID']}</h4>
                    <p><b>Facility Outlet:</b> {order['Outlet']} | <b>Line Item:</b> {order['Product Name']} ({order['Quantity']} Boxes)</p>
                    <p><b>Recipient:</b> {order['Recipient Name']} ({order['Recipient Phone']} / {order['Recipient Email']})</p>
                    <p><b>Status:</b> <span class="status-badge status-delivered">DELIVERED</span> | <b>Time:</b> {order['Delivery Time']}</p>
                </div>
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button(f"📄 View Invoice / POD", key=f"pod_{order['OrderID']}"):
                    st.info(
                        f"Downloading electronic Proof of Delivery for {order['OrderID']}...")
            with c2:
                if st.button(f"✅ Confirm Receipt", key=f"conf_{order['OrderID']}"):
                    st.success(
                        "Delivery receipt acknowledged by facility manager!")
            with c3:
                if st.button(f"⚠️ Report Issue", key=f"rep_{order['OrderID']}"):
                    st.warning("Issue ticket opened with MedSupply Support.")
    else:
        st.info("No new delivery alerts at this moment.")

    st.divider()
    st.subheader("📦 Interactive All Orders Tracker")

    search_q = st.text_input("🔍 Search by Order ID, Outlet, or Recipient Name")
    status_filter = st.multiselect("Filter by Status", options=[
                                   "Processing", "Dispatched", "Delivered"], default=["Processing", "Dispatched", "Delivered"])

    df_display = st.session_state.orders_df.copy()
    if search_q:
        df_display = df_display[
            df_display["OrderID"].str.contains(search_q, case=False) |
            df_display["Outlet"].str.contains(search_q, case=False) |
            df_display["Recipient Name"].str.contains(search_q, case=False)
        ]
    df_display = df_display[df_display["Status"].isin(status_filter)]

    st.dataframe(df_display, use_container_width=True)

# CHOICE 3: SELLER CONTROL CENTER
elif choice == "🚚 Seller Control Center":
    st.header("🚚 Seller Dashboard: Dispatch & Delivery Trigger")
    st.caption(
        "Manage B2B order fulfillments, upload Proof of Delivery (POD), and update real-time delivery statuses.")

    search_term = st.text_input(
        "Search Pending Shipments", placeholder="Enter Order ID or Facility Name...")

    orders_to_show = st.session_state.orders_df.copy()
    if search_term:
        orders_to_show = orders_to_show[
            orders_to_show["OrderID"].str.contains(search_term, case=False) |
            orders_to_show["Outlet"].str.contains(search_term, case=False)
        ]

    for idx, row in orders_to_show.iterrows():
        with st.container():
            st.markdown(
                f"##### Order ID: `{row['OrderID']}` — {row['Outlet']}")
            col1, col2, col3 = st.columns([2, 2, 2])

            col1.write(
                f"👤 **Recipient:** {row['Recipient Name']}\n📞 {row['Recipient Phone']}")
            col2.write(
                f"📦 **Item:** {row['Product Name']}\n💰 **Total:** UGX {row['Total Amount (UGX)']:,.0f}")
            col3.write(
                f"Status: **{row['Status']}**\nDispatch Time: *{row['Dispatch Time']}*")

            if row["Status"] != "Delivered":
                pod_file = st.file_uploader(f"Upload POD Image ({row['OrderID']})", type=[
                                            "png", "jpg", "pdf"], key=f"file_{row['OrderID']}")

                if st.button(f"🚚 Trigger Delivered", key=f"deliv_btn_{row['OrderID']}", type="primary"):
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")
                    st.session_state.orders_df.at[idx, "Status"] = "Delivered"
                    st.session_state.orders_df.at[idx,
                                                  "Delivery Time"] = now_str
                    st.success(
                        f"Delivery notification triggered and dispatched to {row['Recipient Name']} ({row['Recipient Phone']}) at {now_str}!")
                    st.rerun()
            else:
                st.write(f"✅ **Delivery Confirmed at {row['Delivery Time']}**")
            st.divider()

# CHOICE 4: WHATSAPP ASSISTANT
elif choice == "💬 WhatsApp Assistant":
    st.header("💬 Professional WhatsApp Business Assistant")

    col_chat, col_info = st.columns([3, 1])

    with col_info:
        st.subheader("Support Link")
        st.markdown(
            "[📲 Open WhatsApp Web](https://web.whatsapp.com/)", unsafe_allow_html=True)
        st.info("Operations Manager:\n**Okiror Innocent**\n+256763212490")

    with col_chat:
        for chat in st.session_state.chat_history:
            if chat["role"] == "user":
                st.markdown(f'''
                    <div class="chat-bubble-user">
                        <b>You:</b> {chat["msg"]}
                        <span class="chat-time">{chat["time"]}</span>
                    </div><div style="clear:both;"></div>
                ''', unsafe_allow_html=True)
            else:
                st.markdown(f'''
                    <div class="chat-bubble-bot">
                        <b>MedSupply Bot:</b><br>{chat["msg"]}
                        <span class="chat-time">{chat["time"]}</span>
                    </div><div style="clear:both;"></div>
                ''', unsafe_allow_html=True)

        st.write("**Quick Topics:**")
        c1, c2, c3, c4 = st.columns(4)
        quick_input = None
        if c1.button("📋 CATALOG"):
            quick_input = "CATALOG"
        if c2.button("💰 PRICES"):
            quick_input = "PRICES"
        if c3.button("🚚 STATUS"):
            quick_input = "STATUS"
        if c4.button("👤 MANAGER"):
            quick_input = "MANAGER"

        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_input("Type your message...", key="user_msg")
            submit_chat = st.form_submit_button("Send 📤")

        final_msg = quick_input or (user_input if submit_chat else None)

        if final_msg:
            now_t = datetime.datetime.now().strftime("%H:%M")
            st.session_state.chat_history.append(
                {"role": "user", "msg": final_msg, "time": now_t})
            msg_lower = final_msg.strip().lower()

            if "manager" in msg_lower or "contact" in msg_lower:
                bot_reply = "👤 **Manager Contact Details:**\n\n• **Name:** Okiror Innocent\n• **Phone:** +256763212490\n• **Role:** Operations & Credit Manager"
            elif "price" in msg_lower or "cost" in msg_lower or "catalog" in msg_lower:
                items_str = "\n".join(
                    [f"• **{r['Product Name']}**: UGX {r['Unit Price (UGX)']:,.0f}" for _, r in st.session_state.inventory_df.iterrows()])
                bot_reply = f"💰 **Wholesale Catalog & Prices:**\n\n{items_str}"
            elif "status" in msg_lower or "track" in msg_lower:
                recent = st.session_state.orders_df.head(3)
                orders_str = "\n".join(
                    [f"• **{r['OrderID']}** ({r['Outlet']}): {r['Status']}" for _, r in recent.iterrows()])
                bot_reply = f"🚚 **Recent Order Tracking Status:**\n\n{orders_str}"
            else:
                bot_reply = "Thank you for contacting MedSupply Uganda. Reply with **PRICES**, **MANAGER**, **CATALOG**, or **STATUS** for automated assistance."

            st.session_state.chat_history.append(
                {"role": "bot", "msg": bot_reply, "time": now_t})
            st.rerun()

# CHOICE 5: PAYMENT GATEWAYS
elif choice == "📱 Payment Gateways":
    st.header("📱 B2B Payment Gateway Integration")

    pay_tab1, pay_tab2, pay_tab3 = st.tabs(
        ["MTN Mobile Money", "Airtel Money", "Bank Wire Transfer"])

    with pay_tab1:
        st.subheader("MTN MoMo API Prompt Trigger")
        momo_phone = st.text_input(
            "Subscriber Phone Number", value="+256770665588")
        momo_amount = st.number_input(
            "Transaction Amount (UGX)", value=150000, step=10000)

        c_presets1, c_presets2 = st.columns(2)
        if c_presets1.button("Pay Full Amount"):
            pass
        if c_presets2.button("Pay 50% Deposit"):
            momo_amount = momo_amount / 2

        if st.button("💳 Trigger MoMo Push Prompt", type="primary"):
            if validate_uganda_phone(momo_phone):
                txn_id = f"TXN-MOMO-{uuid.uuid4().hex[:6].upper()}"
                st.success(
                    f"✅ USSD Prompt pushed to {momo_phone}! Reference ID: `{txn_id}`")
                st.info(
                    "Waiting for PIN confirmation on subscriber handset (45s timeout)...")
            else:
                st.error("Invalid phone number format! Use +256 prefix.")

    with pay_tab2:
        st.subheader("Airtel Money Merchant Checkout")
        airtel_phone = st.text_input(
            "Airtel Mobile Number", value="+256750123456")
        airtel_amount = st.number_input(
            "Amount (UGX)", value=150000, key="airtel_amt")
        if st.button("💳 Trigger Airtel Push Prompt"):
            st.success(f"Airtel Money prompt sent to {airtel_phone}!")

    with pay_tab3:
        st.subheader("Direct Bank Wire / EFT Details")
        st.write("**Bank:** Stanbic Bank Uganda")
        st.write("**Account Name:** MedSupply Uganda Limited")
        st.write("**Account Number:** 9030012345678")
        st.write("**Branch:** Kampala Corporate Branch")

# CHOICE 6: INVENTORY MANAGEMENT (ST.DATA_EDITOR FIXED)
elif choice == "📦 Inventory Management":
    st.header("📦 Warehouse Stock Management")
    st.caption(
        "Use inline editing to update live inventory stock counts or unit pricing.")

    # Low Stock Alerts Banner
    low_stock = st.session_state.inventory_df[st.session_state.inventory_df["Stock Quantity"] < 200]
    if not low_stock.empty:
        for _, row in low_stock.iterrows():
            st.warning(
                f"⚠️ **Low Stock Alert:** `{row['Product Name']}` has only **{row['Stock Quantity']}** boxes left in stock!")

    st.subheader("Interactive Stock Editor")

    # Safe DataFrame copy with date typing enforced
    df_to_edit = st.session_state.inventory_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_to_edit["Expiry Date"]):
        df_to_edit["Expiry Date"] = pd.to_datetime(
            df_to_edit["Expiry Date"]).dt.date

    edited_df = st.data_editor(
        df_to_edit,
        column_config={
            "Item ID": st.column_config.TextColumn("Item ID", required=True),
            "Product Name": st.column_config.TextColumn("Product Name", required=True),
            "Category": st.column_config.SelectboxColumn("Category", options=["Antibiotics", "Analgesics", "Antimalarial", "Medical Consumables"]),
            "Unit Price (UGX)": st.column_config.NumberColumn("Unit Price (UGX)", min_value=0, format="UGX %d"),
            "Stock Quantity": st.column_config.NumberColumn("Stock Quantity", min_value=0, step=1),
            "Batch Number": st.column_config.TextColumn("Batch Number"),
            "Expiry Date": st.column_config.DateColumn("Expiry Date", format="YYYY-MM-DD"),
            "NDA Reg No": st.column_config.TextColumn("NDA Reg No")
        },
        use_container_width=True,
        num_rows="dynamic",
        key="inventory_editor"
    )

    st.session_state.inventory_df = edited_df

# CHOICE 7: OUTLETS & CREDIT LINES
elif choice == "🏥 Outlets & Credit Lines":
    st.header("🏥 Registered Outlets & Credit Facilities")

    for _, row in st.session_state.outlets_df.iterrows():
        used = row["Used Credit (UGX)"]
        limit = row["Credit Limit (UGX)"]
        utilization = min(used / limit, 1.0)

        with st.expander(f"🏥 {row['Business Name']} ({row['Location']}) - Status: {row['Status']}"):
            st.write(
                f"**Contact Person:** {row['Contact Name']} | **Phone:** {row['Phone']} | **Email:** {row['Email']}")
            st.write(f"**Credit Usage:** UGX {used:,.0f} / UGX {limit:,.0f}")
            st.progress(utilization)
            if utilization > 0.8:
                st.warning("⚠️ High Credit Utilization Warning (>80%)")

# CHOICE 8: MASTER ORDER LOGS
elif choice == "📋 Master Order Logs":
    st.header("📋 Master Order Logs & Executive Analytics")

    kpi1, kpi2, kpi3 = st.columns(3)
    total_rev = st.session_state.orders_df["Total Amount (UGX)"].sum()
    total_orders = len(st.session_state.orders_df)
    pending_count = len(
        st.session_state.orders_df[st.session_state.orders_df["Status"] == "Processing"])

    kpi1.metric("Total Platform Revenue", f"UGX {total_rev:,.0f}")
    kpi2.metric("Total Orders Processed", total_orders)
    kpi3.metric("Pending Fulfillment", pending_count)

    st.divider()

    csv_data = st.session_state.orders_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Master Logs to CSV",
        data=csv_data,
        file_name=f"medsupply_master_logs_{datetime.date.today()}.csv",
        mime="text/csv"
    )

    st.dataframe(st.session_state.orders_df, use_container_width=True)
