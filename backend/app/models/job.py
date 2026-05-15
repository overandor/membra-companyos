"""MEMBRA CompanyOS — JobOS models."""
from sqlalchemy import Column, String, Text, JSON, Numeric, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, ULIDMixin


class Job(Base, ULIDMixin):
    """A paid job, bounty, work order, or marketplace action."""

    task_id = Column(String(26), ForeignKey("tasks.id"), index=True, nullable=True)
    company_id = Column(String(26), ForeignKey("companies.id"), index=True, nullable=True)
    job_type = Column(String(64), nullable=False, index=True)
    # apartment_task, car_ad_task, window_ad_task, wearable_task, kpi_task, fulfillment_task, bounty
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(32), default="open", index=True)  # open, assigned, in_progress, completed, cancelled, disputed
    payment_amount = Column(Numeric(24, 8), default=0)
    payment_currency = Column(String(16), default="USDC")
    payment_status = Column(String(32), default="pending")  # pending, held, released, refunded
    escrow_address = Column(String(128))
    assignee_wallet = Column(String(64), index=True)
    deadline = Column(String(64))
    proof_requirement = Column(JSON, default=dict)
    location_json = Column(JSON, default=dict)  # GPS, address, zone
    metadata_json = Column(JSON, default=dict)

    task = relationship("Task", back_populates="jobs")
    company = relationship("Company", back_populates="jobs")
    settlements = relationship("Settlement", back_populates="job", lazy="selectin")


class Settlement(Base, ULIDMixin):
    """Settlement record for a completed job."""

    job_id = Column(String(26), ForeignKey("jobs.id"), index=True)
    amount = Column(Numeric(24, 8), nullable=False)
    currency = Column(String(16), default="USDC")
    recipient_wallet = Column(String(64), nullable=False, index=True)
    settlement_type = Column(String(32), default="manual")  # manual, automated, batch
    status = Column(String(32), default="pending", index=True)  # pending, submitted, confirmed, failed
    tx_hash = Column(String(128), index=True)
    external_rail = Column(String(32))  # solana, ethereum, stripe, wise, paypal
    metadata_json = Column(JSON, default=dict)

    job = relationship("Job", back_populates="settlements")
