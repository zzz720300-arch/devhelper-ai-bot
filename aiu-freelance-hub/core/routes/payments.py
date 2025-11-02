"""Payment routes for interacting with YooKassa."""
from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.models import Order, Payment
from db.session import session_scope

router = APIRouter()


class PaymentCreateRequest(BaseModel):
    order_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)
    provider: str = "yookassa"


class PaymentCreateResponse(BaseModel):
    payment_id: uuid.UUID
    confirmation_url: str


class PaymentWebhook(BaseModel):
    payment_id: uuid.UUID
    status: str


@router.post("/create", response_model=PaymentCreateResponse)
async def create_payment(payload: PaymentCreateRequest) -> PaymentCreateResponse:
    confirmation_url = f"https://pay.yookassa.ru/checkout/{payload.order_id}"
    async with session_scope() as session:
        order = await session.get(Order, payload.order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        payment = Payment(
            order_id=order.id,
            amount=payload.amount,
            provider=payload.provider,
            status="pending",
            payload={"confirmation_url": confirmation_url},
        )
        session.add(payment)
        await session.flush()
        payment_id = payment.id
    return PaymentCreateResponse(payment_id=payment_id, confirmation_url=confirmation_url)


@router.post("/webhook")
async def payment_webhook(payload: PaymentWebhook) -> dict:
    async with session_scope() as session:
        payment = await session.get(Payment, payload.payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        payment.status = payload.status
        order = await session.get(Order, payment.order_id)
        if order and payload.status == "succeeded":
            order.status = "paid"
        await session.flush()
    return {"status": "ok"}
