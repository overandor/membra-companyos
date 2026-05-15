"""MEMBRA CompanyOS — AgentOS models."""
from sqlalchemy import Column, String, Text, JSON, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, ULIDMixin


class Agent(Base, ULIDMixin):
    """AI or human agent registered in AgentOS."""

    agent_type = Column(String(64), nullable=False, index=True)
    # strategy, product, engineering, ops, sales, finance, legal_risk, governance, proof, concierge
    name = Column(String(128), nullable=False)
    description = Column(Text)
    status = Column(String(32), default="active", index=True)  # active, paused, retired
    llm_provider = Column(String(32))
    llm_model = Column(String(64))
    system_prompt = Column(Text)
    allowed_actions = Column(JSON, default=list)
    blocked_actions = Column(JSON, default=list)
    output_schema = Column(JSON, default=dict)
    permissions = Column(JSON, default=list)
    company_id = Column(String(26), ForeignKey("companies.id"), index=True, nullable=True)
    department_id = Column(String(26), ForeignKey("departments.id"), index=True, nullable=True)
    owner_wallet = Column(String(64), index=True)
    version = Column(String(16), default="1.0.0")
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    metadata_json = Column(JSON, default=dict)

    tasks = relationship("Task", back_populates="agent", lazy="selectin")
    tools = relationship("AgentTool", back_populates="agent", lazy="selectin")
    action_logs = relationship("AgentActionLog", back_populates="agent", lazy="selectin")
    company = relationship("Company", back_populates="agents")
    department = relationship("Department", back_populates="agents")


class AgentTool(Base, ULIDMixin):
    """Tool available to an agent."""

    agent_id = Column(String(26), ForeignKey("agents.id"), index=True)
    tool_name = Column(String(128), nullable=False)
    tool_description = Column(Text)
    tool_schema = Column(JSON, default=dict)
    requires_human_approval = Column(String(16), default="false")
    rate_limit_per_minute = Column(Integer, default=60)

    agent = relationship("Agent", back_populates="tools")


class AgentActionLog(Base, ULIDMixin):
    """Every action taken by an agent is logged."""

    agent_id = Column(String(26), ForeignKey("agents.id"), index=True)
    action_type = Column(String(128), nullable=False, index=True)
    task_id = Column(String(26), ForeignKey("tasks.id"), index=True, nullable=True)
    job_id = Column(String(26), ForeignKey("jobs.id"), index=True, nullable=True)
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    status = Column(String(32), default="success", index=True)  # success, failure, blocked
    error_message = Column(Text)
    execution_time_ms = Column(Integer)
    proof_hash = Column(String(128))
    governance_gate_passed = Column(String(16), default="false")
    metadata_json = Column(JSON, default=dict)

    agent = relationship("Agent", back_populates="action_logs")
