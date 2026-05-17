"""MEMBRA CompanyOS — OnChainOpportunity and related models."""
from sqlalchemy import Column, String, Text, JSON, Float, DateTime, Integer, ForeignKey, Index, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.models.base import Base, ULIDMixin
import enum


class OpportunityType(str, enum.Enum):
    ARBITRAGE = "arbitrage"
    LIQUIDITY_PROVISION = "liquidity_provision"
    STAKING_YIELD = "staking_yield"
    TREASURY_REBALANCE = "treasury_rebalance"
    MERCHANT_SETTLEMENT_SPREAD = "merchant_settlement_spread"
    STABLECOIN_ROUTE_OPTIMIZATION = "stablecoin_route_optimization"
    LIQUIDATION_MONITORING = "liquidation_monitoring"
    FEE_CAPTURE = "fee_capture"
    BRIDGE_SPREAD_MONITORING = "bridge_spread_monitoring"
    GRANT_REWARD = "grant_reward"
    PARTNER_REVENUE = "partner_revenue"


class SimulationStatus(str, enum.Enum):
    NOT_SIMULATED = "not_simulated"
    PENDING = "pending"
    SIMULATED = "simulated"
    FAILED = "failed"


class ApprovalStatus(str, enum.Enum):
    NOT_REVIEWED = "not_reviewed"
    PENDING_RISK = "pending_risk"
    PENDING_COMPLIANCE = "pending_compliance"
    PENDING_FINANCE = "pending_finance"
    PENDING_GOVERNANCE = "pending_governance"
    APPROVED = "approved"
    REJECTED = "rejected"


class ExecutionStatus(str, enum.Enum):
    NOT_EXECUTED = "not_executed"
    PROPOSED = "proposed"
    PENDING_TREASURY = "pending_treasury"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OnChainOpportunity(Base, ULIDMixin):
    """An on-chain profit opportunity discovered by an employee."""

    discovered_by_employee_id = Column(String(64), nullable=False, index=True)
    chain = Column(String(32), nullable=False, index=True)
    protocol = Column(String(128), nullable=False, index=True)
    opportunity_type = Column(String(64), nullable=False, index=True)
    asset_in = Column(String(128), nullable=False)
    asset_out = Column(String(128), nullable=False)

    expected_profit = Column(Float, default=0.0)
    expected_profit_percent = Column(Float, default=0.0)
    required_capital = Column(Float, default=0.0)
    estimated_fees = Column(Float, default=0.0)
    slippage_estimate = Column(Float, default=0.0)
    liquidity_depth = Column(Float, default=0.0)
    execution_window_seconds = Column(Integer, default=0)

    confidence_score = Column(Float, default=0.0, index=True)
    risk_score = Column(Float, default=None, index=True)
    compliance_score = Column(Float, default=None, index=True)

    simulation_status = Column(String(32), default="not_simulated", index=True)
    approval_status = Column(String(32), default="not_reviewed", index=True)
    execution_status = Column(String(32), default="not_executed", index=True)

    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    evidence_json = Column(JSON, default=dict)
    recommended_action = Column(Text)

    simulation_result_json = Column(JSON, default=dict)
    risk_review_json = Column(JSON, default=dict)
    compliance_review_json = Column(JSON, default=dict)
    finance_review_json = Column(JSON, default=dict)
    governance_review_json = Column(JSON, default=dict)
    execution_result_json = Column(JSON, default=dict)

    rejection_reason = Column(Text)
    rejected_by = Column(String(64))

    __table_args__ = (
        Index("ix_opportunities_status_composite", "simulation_status", "approval_status", "execution_status"),
        Index("ix_opportunities_confidence_risk", "confidence_score", "risk_score"),
    )

    proofs = relationship("ProofBookEvent", primaryjoin="and_(ProofBookEvent.entity_type=='opportunity', ProofBookEvent.entity_id==OnChainOpportunity.id)", lazy="selectin", viewonly=True)


class WalletRegistry(Base, ULIDMixin):
    """Treasury and employee wallet registry. No private keys stored."""

    wallet_address = Column(String(128), nullable=False, unique=True, index=True)
    wallet_type = Column(String(32), nullable=False, index=True)  # WATCH_ONLY, PAPER, PROPOSAL_ONLY, TREASURY_GATED
    owner_type = Column(String(32), nullable=False)  # employee, treasury, multisig
    owner_id = Column(String(64), nullable=False, index=True)
    chain = Column(String(32), nullable=False, index=True)
    label = Column(String(128))
    purpose = Column(Text)
    balance_json = Column(JSON, default=dict)
    last_balance_update = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(String(16), default="true", index=True)
    policy_id = Column(String(26), ForeignKey("governancepolicies.id"), nullable=True, index=True)
    metadata_json = Column(JSON, default=dict)


class TreasuryPolicy(Base, ULIDMixin):
    """Treasury approval policy for fund movements."""

    policy_name = Column(String(128), nullable=False)
    policy_type = Column(String(64), nullable=False, index=True)
    description = Column(Text)
    max_amount = Column(Float, default=0.0)
    min_signers = Column(Integer, default=1)
    required_departments = Column(JSON, default=list)
    required_scores = Column(JSON, default=dict)  # risk, compliance thresholds
    auto_execute_below = Column(Float, default=0.0)
    cooldown_hours = Column(Integer, default=24)
    status = Column(String(32), default="active", index=True)
    rule_json = Column(JSON, nullable=False)
    metadata_json = Column(JSON, default=dict)
