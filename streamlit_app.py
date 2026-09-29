import pandas as pd
import streamlit as st
from supabase import create_client

# Direct imports from root directory files
from config import settings
from credit_engine import credit_engine

# --- STREAMLIT DASHBOARD PAGE CONFIGURATION ---
st.set_page_config(
    page_title="MedSupply Uganda Dashboard",
    page_icon="🏥",
    layout="wide"
)

# Initialize Supabase Sync Client for Streamlit
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

st.title("🏥 MedSupply Uganda — Operations Dashboard")

menu = ["Overview", "Drug Outlets & Credit", "Inventory Management", "Orders"]
choice = st.sidebar.selectbox("Navigation", menu)

if choice == "Overview":
    st.header("System Overview")

    outlets_res = supabase.table("drug_outlets").select("id").execute()
    outlets_count = len(outlets_res.data or [])

    orders_res = supabase.table("orders").select(
        "id, total_amount_ugx, status").execute()
    orders_data = orders_res.data or []

    col1, col2, col3 = st.columns(3)
    col1.metric("Registered Outlets", outlets_count)
    col2.metric("Total Orders", len(orders_data))

    total_rev = sum([o["total_amount_ugx"]
                    for o in orders_data if o.get("status") == "DELIVERED"])
    col3.metric("Revenue (UGX)", f"{total_rev:,.0f}")

elif choice == "Drug Outlets & Credit":
    st.header("Drug Outlets & Micro-Credit Eligibility")
    outlets = supabase.table("drug_outlets").select("*").execute().data

    if outlets:
        df = pd.DataFrame(outlets)
        st.dataframe(df, use_container_width=True)

        st.subheader("Evaluate Trade Credit")
        selected_outlet = st.selectbox(
            "Select Outlet", df["business_name"].tolist())
        outlet_row = df[df["business_name"] == selected_outlet].iloc[0]

        completed_orders = st.number_input(
            "Completed Orders Count", min_value=0, value=5)
        avg_order = st.number_input(
            "Average Order Value (UGX)", min_value=0.0, value=500000.0)
        repayment_score = st.slider("Repayment Score", 0.0, 1.0, 0.9)

        if st.button("Calculate Approved Limit"):
            limit = credit_engine.calculate_credit_limit(
                completed_orders, avg_order, repayment_score
            )
            st.success(f"Calculated Credit Limit: UGX {limit:,.0f}")

            if st.button("Save Limit to Database"):
                supabase.table("drug_outlets").update(
                    {"credit_limit_ugx": limit}
                ).eq("id", outlet_row["id"]).execute()
                st.info("Updated successfully!")
    else:
        st.info("No registered drug outlets found in the database.")

elif choice == "Inventory Management":
    st.header("Stock Inventory")
    items = supabase.table("inventory_items").select("*").execute().data
    if items:
        st.dataframe(pd.DataFrame(items), use_container_width=True)
    else:
        st.info("No inventory items found.")

elif choice == "Orders":
    st.header("Order Logs")
    orders = supabase.table("orders").select("*").execute().data
    if orders:
        st.dataframe(pd.DataFrame(orders), use_container_width=True)
    else:
        st.info("No orders recorded yet.")
