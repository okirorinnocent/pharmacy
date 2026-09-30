import streamlit as st
import pandas as pd
import uuid
import datetime
import re
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="MedSupply Uganda | Premier B2B Pharma Marketplace",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ADVANCED JUMIA-INSPIRED HIGH-CONTRAST CSS THEME ---
st.markdown("""
    <style>
    /* Global Background Theme */
    .stApp {
        background: linear-gradient(135deg, #0B0F19 0%, #111827 100%);
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        color: #F9FAFB;
    }
    
    /* Smooth Entrance Keyframe Animations */
    @keyframes slideUp {
        from { transform: translateY(20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    @keyframes pulseGlow {
        0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
        70% { box-shadow: 0 0 0 12px rgba(16, 185, 129, 0); }
        100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        padding-left: 2rem;
        padding-right: 2rem;
        animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }

    /* Jumia Style Hero Banner Header */
    .hero-container {
        background: linear-gradient(135deg, #064E3B 0%, #022C22 100%);
        border: 1px solid #059669;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(5, 150, 105, 0.25);
    }
    .hero-title {
        color: #34D399;
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .hero-subtitle {
        color: #E5E7EB;
        font-size: 1.05rem;
        margin-bottom: 1.2rem;
    }
    .feature-badge {
        display: inline-block;
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid #10B981;
        color: #6EE7B7;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 8px;
        margin-bottom: 8px;
    }

    /* E-Commerce Product Cards (Jumia Marketplace Style) */
    .jumia-card {
        background: #1F2937;
        border: 1px solid #374151;
        border-radius: 14px;
        padding: 1.25rem;
        margin-bottom: 1.2rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    .jumia-card:hover {
        transform: translateY(-8px);
        border-color: #10B981;
        box-shadow: 0 14px 28px rgba(16, 185, 129, 0.2);
    }
    .discount-tag {
        position: absolute;
        top: 12px;
        right: 12px;
        background: #DC2626;
        color: #FFFFFF;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        text-transform: uppercase;
    }
    .card-title {
        color: #F9FAFB;
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 0.4rem;
    }
    .card-price {
        color: #10B981;
        font-size: 1.3rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .card-meta {
        color: #9CA3AF;
        font-size: 0.85rem;
        line-height: 1.4;
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
        animation: slideUp 0.2s ease-out;
    }
    .chat-bubble-bot {
        background-color: #1F2937;
        padding: 14px 18px;
        border-radius: 16px 16px 16px 2px;
        max-width: 80%;
        float: left;
        margin: 8px 0;
        border: 1px solid #374151;
        font-size: 0.95rem;
        color: #F9FAFB;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        line-height: 1.5;
        animation: slideUp 0.2s ease-out;
    }
    .chat-time {
        font-size: 0.7rem;
        color: #9CA3AF;
        margin-top: 4px;
        display: block;
    }

    /* Notification Cards with Glow Effect */
    .notification-card {
        padding: 1.25rem;
        border-radius: 12px;
        background-color: #064E3B;
        border-left: 6px solid #10B981;
        margin-bottom: 1.2rem;
        color: #FFFFFF;
        animation: slideUp 0.3s ease-out, pulseGlow 3s infinite;
    }
    .notification-card h4 {
        color: #34D399;
        margin-bottom: 0.5rem;
    }

    /* Animated Status Badges */
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

    /* Button Styling */
    div.stButton > button[kind="primary"] {
        transition: all 0.25s ease-in-out !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    div.stButton > button[kind="primary"]:hover:not(:disabled) {
        transform: scale(1.02) !important;
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4) !important;
    }
    </style>
""", unsafe_allow_html=True)


# --- AUTOMATIC EMAIL DISPATCH UTILITY ---
def send_delivery_email(recipient_email, recipient_name, delivery_location, order_id, product_name, quantity, total_amount, delivery_time):
    """Sends an automatic order/delivery notification email to the customer with location details."""
    subject = f"📦 Order Notification: {order_id} - MedSupply Uganda"

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
            <h2 style="color: #059669;">MedSupply Uganda</h2>
            <hr style="border: 0; border-top: 1px solid #eeeeee;">
            <p>Dear <strong>{recipient_name}</strong>,</p>
            <p>Your order <strong>{order_id}</strong> has been successfully processed/updated.</p>
            
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 6px; margin: 15px 0;">
                <h4 style="margin-top: 0; color: #1e293b;">Order Summary</h4>
                <p><strong>Order ID:</strong> {order_id}<br>
                <strong>Product:</strong> {product_name} ({quantity} Boxes)<br>
                <strong>Total Amount:</strong> UGX {total_amount:,.0f}<br>
                <strong>Delivery Destination:</strong> {delivery_location}<br>
                <strong>Timestamp:</strong> {delivery_time}</p>
            </div>
            
            <p>Please log in to your account portal to track live status and delivery updates.</p>
            <p style="font-size: 0.85rem; color: #64748b;">MedSupply Uganda Operations Team<br>Contact: +256763212490</p>
        </div>
    </body>
    </html>
    """

    try:
        if "smtp" not in st.secrets:
            return False, "SMTP credentials missing in st.secrets. Please configure secrets.toml."

        smtp_server = st.secrets["smtp"]["server"]
        smtp_port = int(st.secrets["smtp"]["port"])
        sender_email = st.secrets["smtp"]["email"]
        sender_password = st.secrets["smtp"]["password"]

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"MedSupply Uganda <{sender_email}>"
        msg["To"] = recipient_email
        msg.attach(MIMEText(html_content, "html"))

        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient_email, msg.as_string())
        else:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient_email, msg.as_string())

        return True, f"Email successfully sent to {recipient_email}"
    except Exception as e:
        return False, f"Failed to send email to {recipient_email}: {str(e)}"


# --- WHATSAPP INSTANT PUSH UTILITY ---
def send_whatsapp_notification(recipient_phone, recipient_name, delivery_location, order_id, product_name, quantity, total_amount):
    """Sends an automated WhatsApp notification via Meta WhatsApp Cloud API with location details."""
    try:
        if "WHATSAPP_TOKEN" not in st.secrets or "WHATSAPP_PHONE_NUMBER_ID" not in st.secrets:
            return False, "WhatsApp API credentials missing in secrets."

        token = st.secrets["WHATSAPP_TOKEN"]
        phone_number_id = st.secrets["WHATSAPP_PHONE_NUMBER_ID"]

        # Clean phone number format for Meta API (digits only, no '+')
        formatted_phone = recipient_phone.replace("+", "").strip()

        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": formatted_phone,
            "type": "text",
            "text": {
                "body": (
                    f"📦 *MedSupply Uganda Notification*\n\n"
                    f"Dear *{recipient_name}*,\n"
                    f"Your order *{order_id}* status update:\n\n"
                    f"• *Item:* {product_name} ({quantity} Boxes)\n"
                    f"• *Total Amount:* UGX {total_amount:,.0f}\n"
                    f"• *Delivery Destination:* {delivery_location}\n\n"
                    f"Log in to your portal for live tracking & delivery updates."
                )
            }
        }

        response = requests.post(url, headers=headers,
                                 json=payload, timeout=10)
        res_data = response.json()

        if response.status_code == 200:
            return True, f"WhatsApp alert sent to {recipient_phone}"
        else:
            err_msg = res_data.get("error", {}).get("message", "API Error")
            return False, f"WhatsApp dispatch failed: {err_msg}"

    except Exception as e:
        return False, f"WhatsApp exception: {str(e)}"


# --- 3. GLOBAL SHARED STATE INITIALIZATION ---
@st.cache_resource
def get_global_database():
    """Returns persistent data shared across ALL connected browser sessions/users."""
    user_accounts = {
        "okirorinnocent49@gmail.com": {
            "password": "admin",
            "business_name": "MedSupply HQ",
            "contact_name": "Okiror Innocent",
            "phone": "+256763212490",
            "location": "Kampala Central",
            "role": "Staff / Admin"
        },
        "sarah@carepharma.com": {
            "password": "password123",
            "business_name": "Kampala Care Pharmacy",
            "contact_name": "Dr. Sarah",
            "phone": "+256771234567",
            "location": "Kampala Central",
            "role": "Customer / Buyer"
        }
    }

    outlets_df = pd.DataFrame([
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

    inventory_df = pd.DataFrame([
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
            "Stock Quantity": 120,
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

    orders_df = pd.DataFrame([
        {
            "OrderID": "ORD-9901",
            "Outlet": "Kampala Care Pharmacy",
            "Recipient Name": "Dr. Sarah",
            "Recipient Phone": "+256771234567",
            "Recipient Email": "sarah@carepharma.com",
            "Delivery Location": "Kampala Central, Plot 14 Acacia Ave",
            "Product Name": "Amoxicillin 500mg (Box of 100)",
            "Batch Number": "AMX-2026-09A",
            "Quantity": 5,
            "Total Amount (UGX)": 175000,
            "Payment Method": "MTN Mobile Money",
            "Payment Status": "Paid on Delivery",
            "Item Verified": "Verified Correct",
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
            "Delivery Location": "Mbarara Town, High Street Plot 8",
            "Product Name": "Coartem 20/120 (Box of 30)",
            "Batch Number": "CRT-2026-11B",
            "Quantity": 5,
            "Total Amount (UGX)": 425000,
            "Payment Method": "Trade Credit Line",
            "Payment Status": "Pending Payment",
            "Item Verified": "Pending Inspection",
            "Status": "Dispatched",
            "Date": "2026-09-29",
            "Dispatch Time": "2026-09-29 11:00 AM",
            "Delivery Time": "Pending"
        }
    ])

    return {
        "users": user_accounts,
        "outlets": outlets_df,
        "inventory": inventory_df,
        "orders": orders_df
    }


# Load global memory state
db = get_global_database()

# Session state initializations
if "current_user" not in st.session_state:
    st.session_state["current_user"] = None

if "order_placed" not in st.session_state:
    st.session_state["order_placed"] = False

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "bot",
            "msg": "👋 Welcome to **MedSupply Uganda Support**.\n\nHow can I help you today?",
            "time": datetime.datetime.now().strftime("%H:%M")
        }
    ]


def validate_uganda_phone(phone_str):
    pattern = r"^\+256[0-9]{9}$"
    return re.match(pattern, phone_str) is not None


# --- 4. SIDEBAR NAVIGATION & USER AUTHENTICATION ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/medical-heart.png", width=60)
    st.title("MedSupply Uganda")
    st.caption("B2B Digital Pharma Marketplace")
    st.divider()

    # User Account Status Indicator
    if st.session_state.get("current_user") and st.session_state["current_user"] in db["users"]:
        user_info = db["users"][st.session_state["current_user"]]
        st.success(
            f"👤 **Logged in as:**\n{user_info['contact_name']}\n*({user_info['business_name']})*")
        if st.button("🚪 Log Out", type="secondary"):
            st.session_state["current_user"] = None
            st.session_state["order_placed"] = False
            st.rerun()
    else:
        st.warning("🔒 **Not Logged In**\nSign up or log in to place orders.")

    st.divider()

    # Determine user role
    user_role = "Guest"
    if st.session_state.get("current_user") and st.session_state["current_user"] in db["users"]:
        user_role = db["users"][st.session_state["current_user"]]["role"]

    # Navigation Options
    if user_role == "Staff / Admin":
        menu = [
            "🛒 Wholesale Marketplace",
            "📦 Inventory Management",
            "🚚 Seller Control Center",
            "🏥 Outlets & Credit Lines",
            "📋 Master Order Logs",
            "🔔 Delivery Notifications",
            "💬 WhatsApp Assistant",
            "📱 Payment Gateways",
            "🔐 Account Portal"
        ]
    elif user_role == "Customer / Buyer":
        menu = [
            "🛒 Wholesale Marketplace",
            "🔔 Delivery Notifications",
            "💬 WhatsApp Assistant",
            "📱 Payment Gateways",
            "🔐 Account Portal"
        ]
    else:
        menu = [
            "🛒 Wholesale Marketplace",
            "🔐 Account Portal",
            "💬 WhatsApp Assistant",
            "📱 Payment Gateways"
        ]

    choice = st.selectbox("Navigation Menu", menu)

    unread_count = len(
        db["orders"][db["orders"]["Status"].isin(["Arrived", "Delivered"])])
    if unread_count > 0:
        st.success(f"🔔 **{unread_count} Order(s) Delivered!**")

# --- 5. PAGE ROUTING ---

# CHOICE: WHOLESALE MARKETPLACE (JUMIA STYLE SHOWCASE)
if choice == "🛒 Wholesale Marketplace":
    st.markdown("""
        <div class="hero-container">
            <div class="hero-title">💊 MedSupply B2B Pharma Express</div>
            <div class="hero-subtitle">Uganda's Premier Digital Wholesale Marketplace for Pharmacies, Clinics & Hospitals.</div>
            <div>
                <span class="feature-badge">⚡ Same-Day Delivery</span>
                <span class="feature-badge">🛡️️ NDA Quality Certified</span>
                <span class="feature-badge">💳 Up to UGX 5M Trade Credit</span>
                <span class="feature-badge">📲 Instant WhatsApp Tracking</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Search & Filter Row
    col_search, col_cat = st.columns([3, 1])
    with col_search:
        search_query = st.text_input("🔍 Search Wholesale Products, Active Ingredients, or NDA Reg Numbers...",
                                     placeholder="e.g. Amoxicillin, Paracetamol, Coartem...")
    with col_cat:
        category_filter = st.selectbox(
            "Category", ["All Categories"] + list(db["inventory"]["Category"].unique()))

    # Filter Inventory
    filtered_df = db["inventory"].copy()
    if category_filter != "All Categories":
        filtered_df = filtered_df[filtered_df["Category"] == category_filter]
    if search_query:
        filtered_df = filtered_df[
            filtered_df["Product Name"].str.contains(search_query, case=False) |
            filtered_df["Category"].str.contains(search_query, case=False) |
            filtered_df["NDA Reg No"].str.contains(search_query, case=False)
        ]

    st.subheader("🔥 Popular Wholesale Deals")

    # Marketplace Product Grid (3 Columns)
    cols = st.columns(3)
    for idx, (_, item) in enumerate(filtered_df.iterrows()):
        with cols[idx % 3]:
            st.markdown(f"""
                <div class="jumia-card">
                    <span class="discount-tag">NDA VERIFIED</span>
                    <div class="card-title">📦 {item['Product Name']}</div>
                    <div class="card-price">UGX {item['Unit Price (UGX)']:,.0f} <span style="font-size:0.8rem; font-weight:normal; color:#9CA3AF;">/ box</span></div>
                    <div class="card-meta">
                        • <b>Category:</b> {item['Category']}<br>
                        • <b>Batch:</b> <code>{item['Batch Number']}</code><br>
                        • <b>Stock:</b> {item['Stock Quantity']} units remaining<br>
                        • <b>Expiry:</b> {item['Expiry Date']}
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if st.button(f"🛒 Select {item['Product Name'][:15]}...", key=f"buy_btn_{item['Item ID']}", type="primary", use_container_width=True):
                if not st.session_state.get("current_user"):
                    st.warning(
                        "🔒 Please log in via **🔐 Account Portal** to place orders.")
                else:
                    st.session_state["selected_product"] = item["Product Name"]
                    # Reset placement state when switching products
                    st.session_state["order_placed"] = False
                    st.info(
                        f"Selected **{item['Product Name']}**. Configure order details below.")

    st.divider()

    # Place Order Checkout Form
    if st.session_state.get("current_user") and st.session_state["current_user"] in db["users"]:
        user_info = db["users"][st.session_state["current_user"]]
        st.subheader("📝 Complete Your Wholesale Order")

        col_order1, col_order2 = st.columns(2, gap="medium")
        with col_order1:
            default_item = st.session_state.get(
                "selected_product", db["inventory"]["Product Name"].iloc[0])
            selected_item_name = st.selectbox("Confirm Product", db["inventory"]["Product Name"].tolist(), index=list(
                db["inventory"]["Product Name"]).index(default_item) if default_item in list(db["inventory"]["Product Name"]) else 0)

            item_row = db["inventory"][db["inventory"]
                                       ["Product Name"] == selected_item_name].iloc[0]
            quantity = st.number_input(
                "Quantity (Boxes)", min_value=1, value=5)

            discount = 0.0
            if quantity >= 50:
                discount = 0.10
                st.caption("🎉 10% Bulk Volume Discount Applied!")
            elif quantity >= 10:
                discount = 0.05
                st.caption("🎉 5% Tiered Volume Discount Applied!")

            base_price = quantity * item_row["Unit Price (UGX)"]
            total_price = base_price * (1 - discount)

        with col_order2:
            recipient_name = st.text_input(
                "Recipient Full Name *", value=user_info["contact_name"])
            recipient_phone = st.text_input(
                "Recipient WhatsApp (+256...) *", value=user_info["phone"])
            recipient_email = st.text_input(
                "Recipient Email *", value=st.session_state["current_user"])

            # --- DELIVERY LOCATION FIELD ---
            delivery_location = st.text_input("Delivery Physical Address / City *", value=user_info.get(
                "location", "Kampala Central"), placeholder="e.g. Plot 12 Kampala Road, Kampala")

            payment_method = st.radio("Payment Method", [
                                      "MTN Mobile Money", "Airtel Money", "Trade Credit Line", "Cash on Delivery"], horizontal=True)

        st.metric("Total Payable Amount", f"UGX {total_price:,.0f}",
                  delta=f"-UGX {base_price - total_price:,.0f}" if discount > 0 else None)

        # Handle Disabled State Post-Confirmation
        is_disabled = st.session_state.get("order_placed", False)
        button_label = "✅ Order Confirmed & Dispatched" if is_disabled else "🚀 Confirm Order & Dispatch Alerts"

        if st.button(button_label, type="primary", use_container_width=True, disabled=is_disabled):
            if not validate_uganda_phone(recipient_phone):
                st.error(
                    "⚠️️ Invalid Ugandan Phone Format! Ensure it starts with `+256` followed by 9 digits.")
            elif not delivery_location.strip():
                st.error("⚠️ Please specify a valid physical delivery address.")
            elif quantity > item_row["Stock Quantity"]:
                st.error("❌ Order quantity exceeds available warehouse stock.")
            else:
                # Mark order button as disabled immediately
                st.session_state["order_placed"] = True

                db["inventory"].loc[db["inventory"]["Product Name"] ==
                                    selected_item_name, "Stock Quantity"] -= quantity

                order_id = f"ORD-{uuid.uuid4().hex[:4].upper()}"

                new_order = {
                    "OrderID": order_id,
                    "Outlet": user_info["business_name"],
                    "Recipient Name": recipient_name,
                    "Recipient Phone": recipient_phone,
                    "Recipient Email": recipient_email,
                    "Delivery Location": delivery_location,
                    "Product Name": selected_item_name,
                    "Batch Number": item_row["Batch Number"],
                    "Quantity": quantity,
                    "Total Amount (UGX)": total_price,
                    "Payment Method": payment_method,
                    "Payment Status": "Pending Payment",
                    "Item Verified": "Pending Inspection",
                    "Status": "Processing",
                    "Date": str(datetime.date.today()),
                    "Dispatch Time": "Pending",
                    "Delivery Time": "Pending"
                }

                db["orders"] = pd.concat(
                    [pd.DataFrame([new_order]), db["orders"]], ignore_index=True)

                exact_time_now = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

                # Send Email
                email_sent, email_msg = send_delivery_email(
                    recipient_email=recipient_email,
                    recipient_name=recipient_name,
                    delivery_location=delivery_location,
                    order_id=order_id,
                    product_name=selected_item_name,
                    quantity=quantity,
                    total_amount=total_price,
                    delivery_time=exact_time_now
                )

                # Send WhatsApp Push
                wa_sent, wa_msg = send_whatsapp_notification(
                    recipient_phone=recipient_phone,
                    recipient_name=recipient_name,
                    delivery_location=delivery_location,
                    order_id=order_id,
                    product_name=selected_item_name,
                    quantity=quantity,
                    total_amount=total_price
                )

                st.success(
                    f"✅ Order **{order_id}** placed successfully! Delivering to: **{delivery_location}**")
                st.info(f"📧 **Email:** {email_msg} | 📲 **WhatsApp:** {wa_msg}")
                st.rerun()

        # Option to Place New Order
        if is_disabled:
            if st.button("➕ Place Another Order", type="secondary", use_container_width=True):
                st.session_state["order_placed"] = False
                st.rerun()

# CHOICE: ACCOUNT PORTAL
elif choice == "🔐 Account Portal":
    st.header("🔐 User Account Portal")
    st.caption("Create an account, log in, or recover forgotten credentials.")

    tab_login, tab_signup, tab_reset = st.tabs(
        ["🔑 Log In", "📝 Create New Account", "🔑 Reset Password"])

    with tab_login:
        st.subheader("Login to Your Account")
        with st.form("login_form", clear_on_submit=False):
            login_email = st.text_input(
                "Account Email Address", key="login_email_input").strip().lower()
            login_pass = st.text_input(
                "Password", type="password", key="login_pass_input")
            submit_login = st.form_submit_button(
                "🔑 Log In", type="primary", use_container_width=True)

        if submit_login:
            if not login_email or not login_pass:
                st.error("⚠️ Please fill in both email and password.")
            elif login_email in db["users"]:
                if db["users"][login_email]["password"] == login_pass:
                    st.session_state["current_user"] = login_email
                    st.success(
                        f"Welcome back, {db['users'][login_email]['contact_name']}!")
                    st.rerun()
                else:
                    st.error("❌ Incorrect password. Please try again.")
            else:
                st.error(
                    "❌ Account not found. Please register first under 'Create New Account'.")

    with tab_signup:
        st.subheader("Register Pharmacy / Clinic Account")
        with st.form("signup_form", clear_on_submit=False):
            col_reg1, col_reg2 = st.columns(2)
            with col_reg1:
                new_biz = st.text_input(
                    "Pharmacy / Business Name *", placeholder="e.g. Kampala Care Pharmacy", key="reg_biz")
                new_name = st.text_input(
                    "Contact Person Full Name *", placeholder="e.g. Dr. Jane Okello", key="reg_name")
                new_email = st.text_input(
                    "Email Address *", placeholder="e.g. igirado27@gmail.com", key="reg_email").strip().lower()

            with col_reg2:
                new_phone = st.text_input(
                    "WhatsApp Mobile (+256...) *", placeholder="e.g. +256770665588", key="reg_phone")
                new_loc = st.text_input(
                    "Physical Location / City *", placeholder="e.g. Kampala Central, Plot 14 Acacia Ave", key="reg_loc")
                new_pass = st.text_input(
                    "Create Password *", type="password", key="reg_pass")

            submit_signup = st.form_submit_button(
                "📝 Register Account", type="primary", use_container_width=True)

        if submit_signup:
            if not new_biz or not new_name or not new_email or not new_phone or not new_loc or not new_pass:
                st.error("⚠️ Please fill in all required fields marked with *.")
            elif not validate_uganda_phone(new_phone):
                st.error(
                    "⚠️ Invalid Ugandan Phone Format! Ensure it starts with `+256` followed by 9 digits.")
            elif new_email in db["users"]:
                st.error(
                    "⚠️ An account with this email already exists. Please log in.")
            else:
                assigned_role = "Staff / Admin" if new_email == "okirorinnocent49@gmail.com" else "Customer / Buyer"

                db["users"][new_email] = {
                    "password": new_pass,
                    "business_name": new_biz,
                    "contact_name": new_name,
                    "phone": new_phone,
                    "location": new_loc,
                    "role": assigned_role
                }

                new_outlet = {
                    "ID": f"OUT-{uuid.uuid4().hex[:3].upper()}",
                    "Business Name": new_biz,
                    "Contact Name": new_name,
                    "Phone": new_phone,
                    "Email": new_email,
                    "Location": new_loc,
                    "Credit Limit (UGX)": 1000000,
                    "Used Credit (UGX)": 0,
                    "Status": "Active"
                }
                db["outlets"] = pd.concat(
                    [pd.DataFrame([new_outlet]), db["outlets"]], ignore_index=True)

                st.session_state["current_user"] = new_email
                st.success(
                    "🎉 Account successfully registered! You are now logged in.")
                st.rerun()

    with tab_reset:
        st.subheader("Reset Forgotten Password")
        with st.form("reset_form", clear_on_submit=False):
            reset_email = st.text_input(
                "Registered Email Address *", key="reset_email_input").strip().lower()
            reset_phone = st.text_input(
                "Registered Phone Number (+256...) *", key="reset_phone_input").strip()
            reset_new_pass = st.text_input(
                "Enter New Password *", type="password", key="reset_pass_input")
            reset_confirm_pass = st.text_input(
                "Confirm New Password *", type="password", key="reset_confirm_pass_input")

            submit_reset = st.form_submit_button(
                "🔐 Reset Password", type="primary", use_container_width=True)

        if submit_reset:
            if not reset_email or not reset_phone or not reset_new_pass or not reset_confirm_pass:
                st.error("⚠️ Please fill in all required fields.")
            elif reset_new_pass != reset_confirm_pass:
                st.error("❌ Passwords do not match.")
            elif reset_email not in db["users"]:
                st.error("❌ Account not found.")
            elif db["users"][reset_email]["phone"].strip() != reset_phone:
                st.error("❌ Phone number does not match our records.")
            else:
                db["users"][reset_email]["password"] = reset_new_pass
                st.success("✅ Password successfully updated!")

# CHOICE: DELIVERY NOTIFICATIONS
elif choice == "🔔 Delivery Notifications":
    st.header("🔔 Live Delivery Notifications & Order Tracker")

    delivered_orders = db["orders"][db["orders"]
                                    ["Status"].isin(["Arrived", "Delivered"])]

    if not delivered_orders.empty:
        for idx, order in delivered_orders.iterrows():
            st.markdown(f"""
                <div class="notification-card">
                    <h4>🎉 DELIVERY CONFIRMED | Order {order['OrderID']}</h4>
                    <p><b>Facility Outlet:</b> {order['Outlet']} | <b>Line Item:</b> {order['Product Name']} ({order['Quantity']} Boxes)</p>
                    <p><b>Delivery Destination:</b> {order.get('Delivery Location', 'Registered Outlet Address')}</p>
                    <p><b>Batch Verification:</b> `{order['Batch Number']}` | <b>Item Accuracy:</b> {order['Item Verified']}</p>
                    <p><b>Recipient:</b> {order['Recipient Name']} ({order['Recipient Phone']} / {order['Recipient Email']})</p>
                    <p><b>Status:</b> <span class="status-badge status-delivered">DELIVERED</span> | <b>Timestamp:</b> {order['Delivery Time']}</p>
                </div>
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button(f"📄 View Invoice / POD", key=f"pod_{order['OrderID']}"):
                    st.info(
                        f"Downloading electronic Proof of Delivery for {order['OrderID']}...")
            with c2:
                if st.button(f"✅ Confirm Item & Paid", key=f"conf_{order['OrderID']}"):
                    real_idx = db["orders"][db["orders"]
                                            ["OrderID"] == order["OrderID"]].index[0]
                    db["orders"].at[real_idx, "Payment Status"] = "Paid on Delivery"
                    db["orders"].at[real_idx, "Item Verified"] = "Verified Correct"
                    st.success("Delivery & Payment Confirmed!")
                    st.rerun()
            with c3:
                if st.button(f"⚠️ Report Issue", key=f"rep_{order['OrderID']}"):
                    st.warning("Issue ticket opened with MedSupply Support.")
    else:
        st.info("No active delivery notifications.")

    st.divider()
    st.subheader("📦 Order Tracker")

    search_q = st.text_input(
        "🔍 Search by Order ID, Outlet, Location, or Recipient Name")
    status_filter = st.multiselect("Filter by Status", options=[
                                   "Processing", "Dispatched", "Delivered"], default=["Processing", "Dispatched", "Delivered"])

    df_display = db["orders"].copy()
    if search_q:
        df_display = df_display[
            df_display["OrderID"].str.contains(search_q, case=False) |
            df_display["Outlet"].str.contains(search_q, case=False) |
            df_display["Recipient Name"].str.contains(search_q, case=False) |
            df_display["Delivery Location"].str.contains(search_q, case=False)
        ]
    df_display = df_display[df_display["Status"].isin(status_filter)]

    if user_role == "Customer / Buyer":
        customer_cols = ["OrderID", "Outlet", "Product Name", "Delivery Location", "Batch Number",
                         "Quantity", "Total Amount (UGX)", "Payment Status", "Item Verified", "Status", "Delivery Time"]
        st.dataframe(df_display[customer_cols], use_container_width=True)
    else:
        st.dataframe(df_display, use_container_width=True)

# CHOICE: SELLER CONTROL CENTER
elif choice == "🚚 Seller Control Center":
    st.header("🚚 Seller Dashboard: Dispatch & Delivery Trigger")

    @st.fragment(run_every=5)
    def render_live_seller_dashboard():
        search_term = st.text_input(
            "Search Pending Shipments", placeholder="Enter Order ID or Facility Name...", key="seller_search")

        orders_to_show = db["orders"].copy()
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
                    f"👤 **Recipient:** {row['Recipient Name']}\n📞 {row['Recipient Phone']}\n📧 {row['Recipient Email']}\n📍 **Destination:** {row.get('Delivery Location', 'N/A')}")
                col2.write(
                    f"📦 **Item:** {row['Product Name']} ({row['Quantity']} Boxes)\n🏷️ **Batch:** `{row['Batch Number']}`\n💰 **Total:** UGX {row['Total Amount (UGX)']:,.0f}")
                col3.write(
                    f"Status: **{row['Status']}**\nPayment: **{row['Payment Status']}**\nTimestamp: *{row['Delivery Time']}*")

                if row["Status"] != "Delivered":
                    st.file_uploader(f"Upload POD Image ({row['OrderID']})", type=[
                                     "png", "jpg", "pdf"], key=f"file_{row['OrderID']}")

                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button(f"🚚 Trigger Delivered & Send Alerts", key=f"deliv_btn_{row['OrderID']}", type="primary"):
                            exact_time_now = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

                            real_idx = db["orders"][db["orders"]
                                                    ["OrderID"] == row["OrderID"]].index[0]
                            db["orders"].at[real_idx, "Status"] = "Delivered"
                            db["orders"].at[real_idx,
                                            "Delivery Time"] = exact_time_now
                            db["orders"].at[real_idx,
                                            "Payment Status"] = "Paid on Delivery"
                            db["orders"].at[real_idx,
                                            "Item Verified"] = "Verified Correct Item"

                            email_sent, email_msg = send_delivery_email(
                                recipient_email=row["Recipient Email"],
                                recipient_name=row["Recipient Name"],
                                delivery_location=row.get(
                                    "Delivery Location", "Facility Outlet"),
                                order_id=row["OrderID"],
                                product_name=row["Product Name"],
                                quantity=row["Quantity"],
                                total_amount=row["Total Amount (UGX)"],
                                delivery_time=exact_time_now
                            )

                            wa_sent, wa_msg = send_whatsapp_notification(
                                recipient_phone=row["Recipient Phone"],
                                recipient_name=row["Recipient Name"],
                                delivery_location=row.get(
                                    "Delivery Location", "Facility Outlet"),
                                order_id=row["OrderID"],
                                product_name=row["Product Name"],
                                quantity=row["Quantity"],
                                total_amount=row["Total Amount (UGX)"]
                            )

                            st.success(
                                f"Delivery & Payment confirmed for {row['Recipient Name']} at {exact_time_now}!")
                            st.info(
                                f"📧 **Email:** {email_msg} | 📲 **WhatsApp:** {wa_msg}")
                            st.rerun()
                    with col_btn2:
                        if st.button(f"❌ Detect Mismatch Item", key=f"mismatch_{row['OrderID']}"):
                            real_idx = db["orders"][db["orders"]
                                                    ["OrderID"] == row["OrderID"]].index[0]
                            db["orders"].at[real_idx,
                                            "Item Verified"] = "⚠️ Wrong Item Flagged"
                            st.error(
                                f"Mismatch flagged for Order {row['OrderID']}!")
                            st.rerun()
                else:
                    st.write(
                        f"✅ **Delivery Confirmed at {row['Delivery Time']}** | **Payment: {row['Payment Status']}**")
                st.divider()

    render_live_seller_dashboard()

# CHOICE: WHATSAPP ASSISTANT
elif choice == "💬 WhatsApp Assistant":
    st.header("💬 Professional WhatsApp Assistant")

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
                    [f"• **{r['Product Name']}**: UGX {r['Unit Price (UGX)']:,.0f}" for _, r in db["inventory"].iterrows()])
                bot_reply = f"💰 **Wholesale Catalog & Prices:**\n\n{items_str}"
            elif "status" in msg_lower or "track" in msg_lower:
                recent = db["orders"].head(3)
                orders_str = "\n".join(
                    [f"• **{r['OrderID']}** ({r['Outlet']}): {r['Status']}" for _, r in recent.iterrows()])
                bot_reply = f"🚚 **Recent Order Tracking Status:**\n\n{orders_str}"
            else:
                bot_reply = "Thank you for contacting MedSupply Uganda. Reply with **PRICES**, **MANAGER**, **CATALOG**, or **STATUS** for automated assistance."

            st.session_state.chat_history.append(
                {"role": "bot", "msg": bot_reply, "time": now_t})
            st.rerun()

# CHOICE: PAYMENT GATEWAYS
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

# CHOICE: INVENTORY MANAGEMENT
elif choice == "📦 Inventory Management":
    st.header("📦 Warehouse Stock Management")

    low_stock = db["inventory"][db["inventory"]["Stock Quantity"] < 200]
    if not low_stock.empty:
        for _, row in low_stock.iterrows():
            st.warning(
                f"⚠️ **Low Stock Alert:** `{row['Product Name']}` has only **{row['Stock Quantity']}** boxes left!")

    with st.expander("➕ Add New Item to Inventory", expanded=True):
        with st.form("add_item_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                item_id = st.text_input(
                    "Item ID *", value=f"INV-{len(db['inventory'])+1:03d}")
                prod_name = st.text_input(
                    "Product Name *", placeholder="e.g. Ciprofloxacin 500mg")
                category = st.selectbox(
                    "Category *", ["Antibiotics", "Analgesics", "Antimalarial", "Medical Consumables"])
                unit_price = st.number_input(
                    "Unit Price (UGX) *", min_value=0, value=25000, step=1000)
            with c2:
                stock_qty = st.number_input(
                    "Stock Quantity (Boxes) *", min_value=0, value=100, step=10)
                batch_no = st.text_input(
                    "Batch Number *", value=f"BAT-2026-{uuid.uuid4().hex[:3].upper()}")
                exp_date = st.date_input(
                    "Expiry Date *", value=datetime.date(2028, 1, 1))
                nda_reg = st.text_input(
                    "NDA Reg No *", value="NDA/UG/MED-1000")

            add_submit = st.form_submit_button(
                "📦 Save Item to Inventory", type="primary", use_container_width=True)

            if add_submit:
                if not prod_name or not item_id or not batch_no:
                    st.error("⚠️ Please fill in all required fields.")
                else:
                    new_item = {
                        "Item ID": item_id,
                        "Product Name": prod_name,
                        "Category": category,
                        "Unit Price (UGX)": unit_price,
                        "Stock Quantity": stock_qty,
                        "Batch Number": batch_no,
                        "Expiry Date": exp_date,
                        "NDA Reg No": nda_reg
                    }
                    db["inventory"] = pd.concat(
                        [db["inventory"], pd.DataFrame([new_item])], ignore_index=True)
                    st.success(f"✅ Item **{prod_name}** added to inventory!")
                    st.rerun()

    st.subheader("Interactive Stock Editor")

    def update_inventory():
        edited_state = st.session_state.get("inventory_editor")
        if not edited_state:
            return
        for row_idx, changes in edited_state.get("edited_rows", {}).items():
            for col, value in changes.items():
                db["inventory"].at[row_idx, col] = value
        for new_row in edited_state.get("added_rows", []):
            db["inventory"] = pd.concat(
                [db["inventory"], pd.DataFrame([new_row])], ignore_index=True)
        if edited_state.get("deleted_rows"):
            db["inventory"] = db["inventory"].drop(
                edited_state["deleted_rows"]).reset_index(drop=True)

    st.data_editor(
        db["inventory"],
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
        key="inventory_editor",
        on_change=update_inventory
    )

# CHOICE: OUTLETS & CREDIT LINES
elif choice == "🏥 Outlets & Credit Lines":
    st.header("🏥 Registered Outlets & Credit Facilities")

    for _, row in db["outlets"].iterrows():
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

# CHOICE: MASTER ORDER LOGS
elif choice == "📋 Master Order Logs":
    st.header("📋 Master Order Logs & Executive Analytics")

    @st.fragment(run_every=5)
    def render_live_master_logs():
        kpi1, kpi2, kpi3 = st.columns(3)
        total_rev = db["orders"]["Total Amount (UGX)"].sum()
        total_orders = len(db["orders"])
        pending_count = len(
            db["orders"][db["orders"]["Status"] == "Processing"])

        kpi1.metric("Total Platform Revenue", f"UGX {total_rev:,.0f}")
        kpi2.metric("Total Orders Processed", total_orders)
        kpi3.metric("Pending Fulfillment", pending_count)

        st.divider()

        csv_data = db["orders"].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Master Logs to CSV",
            data=csv_data,
            file_name=f"medsupply_master_logs_{datetime.date.today()}.csv",
            mime="text/csv"
        )

        st.dataframe(db["orders"], use_container_width=True)

    render_live_master_logs()
