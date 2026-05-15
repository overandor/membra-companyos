"""MEMBRA CompanyOS — ProofBook models."""
from sqlalchemy import Column, String, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, ULIDMixin


class ProofBookEvent(Base, ULIDMixin):
    """Immutable event written into the ProofBook."""

    event_type = Column(String(64), nullable=False, index=True)
    # intent_created, task_created, task_completed, agent_action, approval_granted,
    # job_posted, job_completed, settlement_sent, kpi_recorded, policy_created
    entity_type = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(26), nullable=False, index=True)
    actor_wallet = Column(String(64), index=True)
    actor_agent_id = Column(String(26), index=True, nullable=True)
    event_data = Column(JSON, nullable=False)
    proof_hash = Column(String(128), nullable=False, index=True)
    parent_hash = Column(String(128), index=True)  # chain of hashes
    ipfs_cid = Column(String(128))
    approval_id = Column(String(26), ForeignKey("approvalrequests.id"), index=True, nullable=True)
    metadata_json = Column(JSON, default=dict)

    approval = relationship("ApprovalRequest", back_populates="proof_events")
