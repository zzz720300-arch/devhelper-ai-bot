"""SQLAlchemy models for AIU-FREELANCE-HUB."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(Text, nullable=False)
    profile_name = Column(Text, nullable=False)
    specialty = Column(Text, nullable=False)
    tone = Column(JSON, nullable=False, default=dict)
    contact = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    orders = relationship("Order", back_populates="profile")


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_platform = Column(Text, nullable=False)
    source_link = Column(Text, nullable=True)
    customer_contact = Column(Text, nullable=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    matched_profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=True)
    task_type = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="found")
    price = Column(Numeric(10, 2), nullable=True)
    result_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    profile = relationship("Profile", back_populates="orders")
    payments = relationship("Payment", back_populates="order")
    complaints = relationship("Complaint", back_populates="order")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    provider = Column(Text, nullable=False, default="yookassa")
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(Text, nullable=False, default="pending")
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    order = relationship("Order", back_populates="payments")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    from_contact = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    order = relationship("Order", back_populates="complaints")
