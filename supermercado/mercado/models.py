"""Modelos ORM. Valores monetários e quantidades usam Decimal/Numeric."""
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (Column, Integer, String, Boolean, DateTime, Numeric,
                        ForeignKey, CheckConstraint, Index, text)
from sqlalchemy.orm import relationship
from .db import Base

def now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(180), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default='operator')
    active = Column(Boolean, nullable=False, default=True)
    version = Column(Integer, nullable=False, default=1)
    failures = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("role IN ('admin','operator')"),)

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False)

class Supplier(Base):
    __tablename__ = 'suppliers'
    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False)
    contact = Column(String(180), nullable=False, default='')

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    sku = Column(String(40), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    category_id = Column(ForeignKey('categories.id', ondelete='RESTRICT'), nullable=False)
    category = relationship(Category)
    unit = Column(String(4), nullable=False, default='UN')
    price = Column(Numeric(12,2), nullable=False)
    cost = Column(Numeric(12,2), nullable=False, default=0)
    stock = Column(Numeric(12,3), nullable=False, default=0)
    minimum = Column(Numeric(12,3), nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    __table_args__ = (CheckConstraint('stock >= 0'), CheckConstraint('price > 0'),
                      CheckConstraint('cost >= 0'), CheckConstraint('minimum >= 0'),
                      CheckConstraint("unit IN ('UN','KG')"))

class CashSession(Base):
    __tablename__ = 'cash_sessions'
    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    user = relationship(User)
    opened_at = Column(DateTime(timezone=True), nullable=False, default=now)
    closed_at = Column(DateTime(timezone=True))
    opening = Column(Numeric(12,2), nullable=False)
    expected = Column(Numeric(12,2))
    counted = Column(Numeric(12,2))
    difference = Column(Numeric(12,2))
    __table_args__ = (CheckConstraint('opening >= 0'), Index('uq_open_cash_user', 'user_id', unique=True,
        postgresql_where=text('closed_at IS NULL'), sqlite_where=text('closed_at IS NULL')))

class CashMovement(Base):
    __tablename__ = 'cash_movements'
    id = Column(Integer, primary_key=True)
    cash_id = Column(ForeignKey('cash_sessions.id', ondelete='RESTRICT'), nullable=False)
    kind = Column(String(15), nullable=False)
    amount = Column(Numeric(12,2), nullable=False)
    reason = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (CheckConstraint("kind IN ('supply','withdrawal')"), CheckConstraint('amount > 0'))

class Sale(Base):
    __tablename__ = 'sales'
    id = Column(Integer, primary_key=True)
    key = Column(String(36), unique=True, nullable=False)
    user_id = Column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    user = relationship(User)
    cash_id = Column(ForeignKey('cash_sessions.id', ondelete='RESTRICT'), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now, index=True)
    total = Column(Numeric(12,2), nullable=False)
    cash_received = Column(Numeric(12,2), nullable=False, default=0)
    change = Column(Numeric(12,2), nullable=False, default=0)
    status = Column(String(15), nullable=False, default='completed')
    cancel_reason = Column(String(200))
    items = relationship('SaleItem', order_by='SaleItem.id')
    payments = relationship('Payment', order_by='Payment.id')
    __table_args__ = (CheckConstraint('total > 0'), CheckConstraint("status IN ('completed','cancelled')"))

class SaleItem(Base):
    __tablename__ = 'sale_items'
    id = Column(Integer, primary_key=True)
    sale_id = Column(ForeignKey('sales.id', ondelete='RESTRICT'), nullable=False)
    product_id = Column(ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    name = Column(String(120), nullable=False)
    sku = Column(String(40), nullable=False)
    unit = Column(String(4), nullable=False)
    quantity = Column(Numeric(12,3), nullable=False)
    price = Column(Numeric(12,2), nullable=False)
    cost = Column(Numeric(12,2), nullable=False)
    subtotal = Column(Numeric(12,2), nullable=False)
    __table_args__ = (CheckConstraint('quantity > 0'),)

class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True)
    sale_id = Column(ForeignKey('sales.id', ondelete='RESTRICT'), nullable=False)
    method = Column(String(12), nullable=False)
    amount = Column(Numeric(12,2), nullable=False)
    reference = Column(String(50), nullable=False)
    __table_args__ = (CheckConstraint("method IN ('cash','debit','credit','pix')"), CheckConstraint('amount > 0'))

class Purchase(Base):
    __tablename__ = 'purchases'
    id = Column(Integer, primary_key=True)
    key = Column(String(36), unique=True, nullable=False)
    supplier_id = Column(ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=False)
    supplier = relationship(Supplier)
    user_id = Column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    reference = Column(String(80), nullable=False)
    total = Column(Numeric(12,2), nullable=False)
    items = relationship('PurchaseItem')

class PurchaseItem(Base):
    __tablename__ = 'purchase_items'
    id = Column(Integer, primary_key=True)
    purchase_id = Column(ForeignKey('purchases.id', ondelete='RESTRICT'), nullable=False)
    product_id = Column(ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    product = relationship(Product)
    quantity = Column(Numeric(12,3), nullable=False)
    cost = Column(Numeric(12,2), nullable=False)
    subtotal = Column(Numeric(12,2), nullable=False)

class StockMovement(Base):
    __tablename__ = 'stock_movements'
    id = Column(Integer, primary_key=True)
    product_id = Column(ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    product = relationship(Product)
    user_id = Column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    quantity = Column(Numeric(12,3), nullable=False)
    balance = Column(Numeric(12,3), nullable=False)
    reason = Column(String(200), nullable=False)

class Ledger(Base):
    __tablename__ = 'ledger'
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now, index=True)
    user_id = Column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    sale_id = Column(ForeignKey('sales.id', ondelete='RESTRICT'))
    purchase_id = Column(ForeignKey('purchases.id', ondelete='RESTRICT'))
    description = Column(String(200), nullable=False)
    amount = Column(Numeric(12,2), nullable=False)

class Audit(Base):
    __tablename__ = 'audit'
    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('users.id', ondelete='RESTRICT'))
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    action = Column(String(200), nullable=False)

class ResetToken(Base):
    __tablename__ = 'reset_tokens'
    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    digest = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, default=False)
