from fastapi import APIRouter, Request, Response, Query
from app.config import settings
from app.supabase_client import get_supabase
from app.services.whatsapp import whatsapp_service

router = APIRouter(prefix="/webhook", tags=["WhatsApp Supabase Webhook"])


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(status_code=403)


@router.post("")
async def handle_whatsapp_incoming(request: Request):
    body = await request.json()
    supabase = get_supabase()

    try:
        entry = body.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "ignored"}

        message = messages[0]
        from_phone = message.get("from")  # e.g., '256770000000'
        text_body = message.get("text", {}).get("body", "").strip()

        # 1. Fetch Drug Shop from Supabase PostgreSQL
        response = await supabase.table("drug_outlets") \
            .select("*") \
            .eq("phone_number", from_phone) \
            .execute()

        if not response.data:
            msg = "Welcome to MedSupply Uganda! 🏥\nYour shop is not registered. Contact support on 0770000000 to upload your NDA license."
            await whatsapp_service.send_text_message(from_phone, msg)
            return {"status": "unregistered"}

        outlet = response.data[0]

        # 2. Handle Medicine Search
        if "search" in text_body.lower():
            search_term = text_body.lower().replace("search", "").strip()

            # Query inventory using PostgreSQL ilike search
            items_res = await supabase.table("inventory_items") \
                .select("*") \
                .ilike("product_name", f"%{search_term}%") \
                .limit(5) \
                .execute()

            items = items_res.data
            if not items:
                reply = f"No medicines found matching '{search_term}'."
            else:
                reply = "💊 *Available Wholesale Medicine Stock:*\n\n"
                for item in items:
                    reply += f"• *ID {item['id']}*: {item['product_name']}\n  Price: UGX {item['unit_price_ugx']:,.0f} | Supplier: {item['wholesaler_name']}\n\n"
                reply += "Reply with: *Order [Item ID] [Quantity]*"

            await whatsapp_service.send_text_message(from_phone, reply)

        # 3. Handle Order Creation
        elif text_body.lower().startswith("order"):
            parts = text_body.split()
            if len(parts) >= 3:
                item_id, qty = int(parts[1]), int(parts[2])

                # Fetch Item
                item_res = await supabase.table("inventory_items").select("*").eq("id", item_id).single().execute()
                item = item_res.data

                total_price = item["unit_price_ugx"] * qty

                # Insert Order into Supabase
                order_res = await supabase.table("orders").insert({
                    "outlet_id": outlet["id"],
                    "total_amount_ugx": total_price,
                    "status": "PENDING_PAYMENT"
                }).execute()

                order_id = order_res.data[0]["id"]

                # Insert Order Item
                await supabase.table("order_items").insert({
                    "order_id": order_id,
                    "inventory_item_id": item["id"],
                    "quantity": qty,
                    "unit_price_ugx": item["unit_price_ugx"]
                }).execute()

                confirmation = f"🛍️ *Order Confirmation #{order_id}*\nItem: {item['product_name']} x {qty}\nTotal: *UGX {total_price:,.0f}*"
                await whatsapp_service.send_text_message(from_phone, confirmation)

    except Exception as e:
        print(f"Supabase Processing Error: {str(e)}")

    return {"status": "ok"}
