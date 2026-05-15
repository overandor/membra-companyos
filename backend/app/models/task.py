"""MEMBRA CompanyOS — TaskOS models."""
from sqlalchemy import Column, String, Text, JSON, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, ULIDMixin


class Task(Base, ULIDMixin):
    """Executable task within an objective."""

    objective_id = Column(String(26), ForeignKey("objectives.id"), index=True, nullable=True)
    company_id = Column(String(26), ForeignKey("companies.id"), index=True, nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    task_type = Column(String(64), nullable=False, index=True)  # ai_action, human_work, api_call, governance_gate
    status = Column(String(32), default="pending", index=True)  # pending, assigned, in_progress, blocked, completed, failed
    priority = Column(Integer, default=3)  # 1-5
    owner_id = Column(String(64), index=True)  # human wallet or user ID
    owner_agent_id = Column(String(26), ForeignKey("agents.id"), index=True, nullable=True)
    estimated_hours = Column(String(16))
    deadline = Column(String(64))  # ISO datetime
    proof_requirement = Column(JSON, default=dict)
    output_schema = Column(JSON, default=dict)
    blocked_reason = Column(Text)
    metadata_json = Column(JSON, default=dict)

    objective = relationship("Objective", back_populates="tasks")
    agent = relationship("Agent", back_populates="tasks")
    dependencies = relationship("TaskDependency", foreign_keys="TaskDependency.task_id", lazy="selectin")
    proofs = relationship("TaskProof", back_populates="task", lazy="selectin")
    assignments = relationship("TaskAssignment", back_populates="task", lazy="selectin")


class TaskDependency(Base, ULIDMixin):
    """Task-to-task dependency graph."""

    task_id = Column(String(26), ForeignKey("tasks.id"), index=True)
    depends_on_task_id = Column(String(26), ForeignKey("tasks.id"), index=True)
    dependency_type = Column(String(32), default="blocks")  # blocks, requires, triggers


class TaskAssignment(Base, ULIDMixin):
    """Assignment of a task to an entity (human, agent, vendor)."""

    task_id = Column(String(26), ForeignKey("tasks.id"), index=True)
    assignee_type = Column(String(32), nullable=False)  # human, agent, vendor, system
    assignee_id = Column(String(64), nullable=False, index=True)
    notes = Column(Text)
    status = Column(String(32), default="assigned")  # assigned, accepted, declined, completed

    task = relationship("Task", back_populates="assignments")


class TaskProof(Base, ULIDMixin):
    """Proof submission for a task."""

    task_id = Column(String(26), ForeignKey("tasks.id"), index=True)
    proof_type = Column(String(64), nullable=False)  # photo, document, api_response, signature, hash
    proof_data = Column(JSON, default=dict)
    ipfs_cid = Column(String(128))
    proof_hash = Column(String(128), nullable=False, index=True)
    verified = Column(String(32), default="pending")  # pending, verified, rejected
    verifier_id = Column(String(64))
    metadata_json = Column(JSON, default=dict)

    task = relationship("Task", back_populates="proofs")
