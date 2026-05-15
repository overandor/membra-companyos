"""MEMBRA CompanyOS — GovernanceOS models."""
from sqlalchemy import Column, String, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, ULIDMixin


class GovernancePolicy(Base, ULIDMixin):
    """Policy rule for governance."""

    company_id = Column(String(26), ForeignKey("companies.id"), index=True, nullable=True)
    policy_name = Column(String(128), nullable=False)
    policy_type = Column(String(64), nullable=False, index=True)
    # approval_gate, risk_policy, consent_rule, escalation_rule, dispute_rule, abuse_detection
    description = Column(Text)
    rule_json = Column(JSON, nullable=False)  # structured rule definition
    version = Column(String(16), default="1.0.0")
    status = Column(String(32), default="active", index=True)
    owner_wallet = Column(String(64), index=True)
    metadata_json = Column(JSON, default=dict)

    company = relationship("Company", back_populates="governance_policies")
    approvals = relationship("ApprovalRequest", back_populates="policy", lazy="selectin")


class ApprovalRequest(Base, ULIDMixin):
    """A request waiting for governance approval."""

    policy_id = Column(String(26), ForeignKey("governancepolicies.id"), index=True)
    entity_type = Column(String(64), nullable=False)  # task, job, agent_action, listing, settlement
    entity_id = Column(String(26), nullable=False, index=True)
    requester_wallet = Column(String(64), index=True)
    status = Column(String(32), default="pending", index=True)  # pending, approved, rejected, escalated
    approver_wallet = Column(String(64), index=True)
    decision_reason = Column(Text)
    metadata_json = Column(JSON, default=dict)

    policy = relationship("GovernancePolicy", back_populates="approvals")
    proof_events = relationship("ProofBookEvent", back_populates="approval", lazy="selectin")
