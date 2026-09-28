import enum
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Enum, Text, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class OutletType(str, enum.Enum):
    CLASS_C_DRUG_SHOP = "CLASS_C_DRUG_SHOP"
    RETAIL_PHARMACY = "RETAIL_PHARMACY"


class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PROCESSING = "PROCESSING"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class DrugOutlet(Base):
    __tablename__ = "drug_outlets"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(255), nullable=False)
    nda_license_number = Column(String(100), unique=True, nullable=False)
    # WhatsApp ID e.g., 256770000000
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    outlet_type = Column(
        Enum(OutletType), default=OutletType.CLASS_C_DRUG_SHOP)
    location_district = Column(String(100), default="Kampala")
    # Calculated via Credit Engine
    credit_limit_ugx = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="outlet")


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    # e.g., Coartem 20/120mg Tabs
    product_name = Column(String(255), index=True, nullable=False)
    dosage = Column(String(100))
    unit_price_ugx = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=0)
    wholesaler_name = Column(String(255), nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    outlet_id = Column(Integer, ForeignKey("drug_outlets.id"), nullable=False)
    total_amount_ugx = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING_PAYMENT)
    momo_reference_id = Column(String(100), nullable=True)
    is_credit_trade = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    outlet = relationship("DrugOutlet", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    inventory_item_id = Column(Integer, ForeignKey(
        "inventory_items.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price_ugx = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
