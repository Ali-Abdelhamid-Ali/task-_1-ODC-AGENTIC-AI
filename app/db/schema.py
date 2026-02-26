from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import String,Integer,Boolean,DateTime,Date,Numeric,ForeignKey,UniqueConstraint,func,text,Identity
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

UTC_NOW = text("timezone('utc', now())")

class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    customer_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)

    email: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(50))

    billing_address1: Mapped[Optional[str]] = mapped_column(String(200))
    billing_city: Mapped[Optional[str]] = mapped_column(String(100))
    billing_country: Mapped[Optional[str]] = mapped_column(String(100))

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    sales_orders: Mapped[List["SalesOrder"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )

class Vendor(Base):
    __tablename__ = "vendors"

    vendor_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    vendor_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    vendor_name: Mapped[str] = mapped_column(String(200), nullable=False)

    email: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(50))

    address_line1: Mapped[Optional[str]] = mapped_column(String(200))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(100))

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    bills: Mapped[List["Bill"]] = relationship(back_populates="vendor")
    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship(back_populates="vendor")
    assets: Mapped[List["Asset"]] = relationship(back_populates="vendor")

class Site(Base):
    __tablename__ = "sites"

    site_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    site_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    site_name: Mapped[str] = mapped_column(String(200), nullable=False)

    address_line1: Mapped[Optional[str]] = mapped_column(String(200))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    time_zone: Mapped[Optional[str]] = mapped_column(String(100))

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    locations: Mapped[List["Location"]] = relationship(
        back_populates="site", cascade="all, delete-orphan"
    )
    assets: Mapped[List["Asset"]] = relationship(back_populates="site")
    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship(back_populates="site")
    sales_orders: Mapped[List["SalesOrder"]] = relationship(back_populates="site")

class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint("site_id", "location_code", name="uq_locations_site_code"),
    )

    location_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.site_id"), nullable=False)

    location_code: Mapped[str] = mapped_column(String(50), nullable=False)
    location_name: Mapped[str] = mapped_column(String(200), nullable=False)

    parent_location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("locations.location_id")
    )

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    site: Mapped["Site"] = relationship(back_populates="locations")

    parent: Mapped[Optional["Location"]] = relationship(
        remote_side="Location.location_id", back_populates="children"
    )
    children: Mapped[List["Location"]] = relationship(back_populates="parent")

    assets: Mapped[List["Asset"]] = relationship(back_populates="location")
    from_transactions: Mapped[List["AssetTransaction"]] = relationship(
        foreign_keys="AssetTransaction.from_location_id",
        back_populates="from_location",
    )
    to_transactions: Mapped[List["AssetTransaction"]] = relationship(
        foreign_keys="AssetTransaction.to_location_id",
        back_populates="to_location",
    )

class Item(Base):
    __tablename__ = "items"

    item_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    item_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)

    category: Mapped[Optional[str]] = mapped_column(String(100))
    unit_of_measure: Mapped[Optional[str]] = mapped_column(String(50))

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    po_lines: Mapped[List["PurchaseOrderLine"]] = relationship(back_populates="item")
    so_lines: Mapped[List["SalesOrderLine"]] = relationship(back_populates="item")

class Asset(Base):
    __tablename__ = "assets"

    asset_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    asset_tag: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    asset_name: Mapped[str] = mapped_column(String(200), nullable=False)

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.site_id"), nullable=False)
    location_id: Mapped[Optional[int]] = mapped_column(ForeignKey("locations.location_id"))
    vendor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vendors.vendor_id"))

    serial_number: Mapped[Optional[str]] = mapped_column(String(200))
    category: Mapped[Optional[str]] = mapped_column(String(100))

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'Active'")
    )

    cost: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    purchase_date: Mapped[Optional[date]] = mapped_column(Date)

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    site: Mapped["Site"] = relationship(back_populates="assets")
    location: Mapped[Optional["Location"]] = relationship(back_populates="assets")
    vendor: Mapped[Optional["Vendor"]] = relationship(back_populates="assets")

    transactions: Mapped[List["AssetTransaction"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )

class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = (
        UniqueConstraint("vendor_id", "bill_number", name="uq_bills_vendor_billnumber"),
    )

    bill_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)

    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.vendor_id"), nullable=False)

    bill_number: Mapped[str] = mapped_column(String(100), nullable=False)
    bill_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date)

    total_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)

    currency: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=text("'USD'")
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'Open'")
    )

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    vendor: Mapped["Vendor"] = relationship(back_populates="bills")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        UniqueConstraint("po_number", name="uq_purchaseorders_number"),
    )

    po_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)

    po_number: Mapped[str] = mapped_column(String(100), nullable=False)

    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.vendor_id"), nullable=False)
    po_date: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'Open'")
    )

    site_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sites.site_id"))

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    vendor: Mapped["Vendor"] = relationship(back_populates="purchase_orders")
    site: Mapped[Optional["Site"]] = relationship(back_populates="purchase_orders")

    lines: Mapped[List["PurchaseOrderLine"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan"
    )

class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"
    __table_args__ = (
        UniqueConstraint("po_id", "line_number", name="uq_purchaseorderlines"),
    )

    po_line_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)

    po_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.po_id"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)

    item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("items.item_id"))
    item_code: Mapped[str] = mapped_column(String(100), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(String(200))

    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="lines")
    item: Mapped[Optional["Item"]] = relationship(back_populates="po_lines")

class SalesOrder(Base):
    __tablename__ = "sales_orders"
    __table_args__ = (
        UniqueConstraint("so_number", name="uq_salesorders_number"),
    )

    so_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)

    so_number: Mapped[str] = mapped_column(String(100), nullable=False)

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.customer_id"), nullable=False
    )
    so_date: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'Open'")
    )

    site_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sites.site_id"))

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    customer: Mapped["Customer"] = relationship(back_populates="sales_orders")
    site: Mapped[Optional["Site"]] = relationship(back_populates="sales_orders")

    lines: Mapped[List["SalesOrderLine"]] = relationship(
        back_populates="sales_order", cascade="all, delete-orphan"
    )

class SalesOrderLine(Base):
    __tablename__ = "sales_order_lines"
    __table_args__ = (
        UniqueConstraint("so_id", "line_number", name="uq_salesorderlines"),
    )

    so_line_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)

    so_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.so_id"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)

    item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("items.item_id"))
    item_code: Mapped[str] = mapped_column(String(100), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(String(200))

    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)

    sales_order: Mapped["SalesOrder"] = relationship(back_populates="lines")
    item: Mapped[Optional["Item"]] = relationship(back_populates="so_lines")

class AssetTransaction(Base):
    __tablename__ = "asset_transactions"

    asset_txn_id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)

    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.asset_id"), nullable=False)

    from_location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("locations.location_id")
    )
    to_location_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("locations.location_id")
    )

    txn_type: Mapped[str] = mapped_column(String(30), nullable=False)

    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )

    txn_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=UTC_NOW
    )

    note: Mapped[Optional[str]] = mapped_column(String(500))

    asset: Mapped["Asset"] = relationship(back_populates="transactions")

    from_location: Mapped[Optional["Location"]] = relationship(
        foreign_keys=[from_location_id], back_populates="from_transactions"
    )
    to_location: Mapped[Optional["Location"]] = relationship(
        foreign_keys=[to_location_id], back_populates="to_transactions"
    )
