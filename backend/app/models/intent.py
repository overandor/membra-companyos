"""MEMBRA CompanyOS — IntentOS models."""
from sqlalchemy import Column, String, Text, JSON, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, ULIDMixin


class Intent(Base, ULIDMixin):
    """Raw user intent captured from chat, voice, or API."""

    raw_text = Column(Text, nullable=False)
    parsed_json = Column(JSON, default=dict)
    structured_objective_json = Column(JSON, default=dict)
    user_wallet = Column(String(64), index=True)
    user_id = Column(String(64), index=True)
    status = Column(String(32), default="pending", index=True)  # pending, parsing, structured, failed
    confidence_score = Column(Float, default=0.0)
    llm_provider = Column(String(32))
    llm_model = Column(String(64))
    metadata_json = Column(JSON, default=dict)

    # Relationship
    objectives = relationship("Objective", back_populates="intent", lazy="selectin")


class Objective(Base, ULIDMixin):
    """Structured objective derived from an intent."""

    intent_id = Column(String(26), ForeignKey("intents.id"), index=True)
    company_id = Column(String(26), ForeignKey("companies.id"), index=True, nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(32), default="active", index=True)  # active, completed, cancelled, failed
    priority = Column(String(16), default="medium")  # critical, high, medium, low
    target_completion = Column(String(64))  # ISO datetime string
    success_criteria = Column(JSON, default=list)
    assigned_department = Column(String(64))
    metadata_json = Column(JSON, default=dict)

    intent = relationship("Intent", back_populates="objectives")
    tasks = relationship("Task", back_populates="objective", lazy="selectin")
    company = relationship("Company", back_populates="objectives")
