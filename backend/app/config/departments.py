"""MEMBRA CompanyOS — Department Configuration (12 Departments).

Each department has:
- department_id, name, mission
- risk_limit, approved_data_sources, allowed_tools
- wallet_policy, reporting_schedule, escalation_rules
"""
from typing import List, Dict, Any
from pydantic import BaseModel


class DepartmentConfig(BaseModel):
    department_id: str
    name: str
    mission: str
    risk_limit: float  # max USD exposure per opportunity
    approved_data_sources: List[str]
    allowed_tools: List[str]
    wallet_policy: str  # WATCH_ONLY, PAPER, PROPOSAL_ONLY, TREASURY_GATED
    reporting_schedule: str  # cron-like or interval
    escalation_rules: Dict[str, Any]
    risk_tolerance: str  # conservative, moderate, aggressive
    profit_mandate: str
    compliance_constraints: List[str]


DEPARTMENTS: List[DepartmentConfig] = [
    DepartmentConfig(
        department_id="dept-strategy",
        name="Strategy",
        mission="Identify market regimes, allocate capital across ecosystems, rank opportunities, and monitor competitors to guide MEMBRA's treasury and growth strategy.",
        risk_limit=500000.0,
        approved_data_sources=[
            "solana_rpc", "ethereum_rpc", "bitcoin_node",
            "dex_screener", "birdeye", "jupiter_quote",
            "uniswap_subgraphs", "chainlink_price_feeds",
            "coingecko", "defillama", "internal_ledger",
            "treasury_balances", "governance_proposals",
        ],
        allowed_tools=[
            "market_regime_analyzer", "capital_allocator",
            "ecosystem_ranker", "competitor_monitor",
            "yield_strategy_builder", "macro_signal_aggregator",
        ],
        wallet_policy="WATCH_ONLY",
        reporting_schedule="0 */6 * * *",  # every 6 hours
        escalation_rules={
            "high_risk_opportunity": {"threshold": 100000, "escalate_to": "Governance"},
            "market_regime_shift": {"threshold": 0.7, "escalate_to": "Strategy Head"},
            "competitor_threat": {"threshold": 0.8, "escalate_to": "Product"},
        },
        risk_tolerance="moderate",
        profit_mandate="Maximize risk-adjusted treasury yield and ecosystem opportunity capture through systematic macro analysis and capital allocation recommendations.",
        compliance_constraints=[
            "No sanctioned jurisdiction exposure",
            "No unregistered security recommendations",
            "All proposals must include downside scenario",
        ],
    ),
    DepartmentConfig(
        department_id="dept-product",
        name="Product",
        mission="Design and evaluate MEMBRA product offerings, feature roadmaps, user experience, and integration opportunities with on-chain protocols and partners.",
        risk_limit=250000.0,
        approved_data_sources=[
            "solana_rpc", "ethereum_rpc",
            "dex_screener", "jupiter_quote",
            "coingecko", "defillama",
            "github_activity", "x_social_sentiment",
            "internal_ledger", "governance_proposals",
        ],
        allowed_tools=[
            "protocol_integrator", "feature_roadmap_planner",
            "user_feedback_aggregator", "partner_evaluator",
            "competitor_feature_tracker", "integration_tester",
        ],
        wallet_policy="WATCH_ONLY",
        reporting_schedule="0 */12 * * *",  # every 12 hours
        escalation_rules={
            "critical_bug": {"threshold": 1.0, "escalate_to": "Engineering"},
            "partner_opportunity": {"threshold": 50000, "escalate_to": "Sales"},
            "user_churn_spike": {"threshold": 0.15, "escalate_to": "Marketing"},
        },
        risk_tolerance="moderate",
        profit_mandate="Identify product-led revenue opportunities, partner integrations, and feature gaps that drive user acquisition and retention revenue.",
        compliance_constraints=[
            "No integration with un-audited protocols",
            "All partner evaluations must include legal review",
            "User data must remain private",
        ],
    ),
    DepartmentConfig(
        department_id="dept-engineering",
        name="Engineering",
        mission="Build and maintain scanners, backtesters, route optimizers, wallet monitors, alert systems, and all core infrastructure for on-chain intelligence.",
        risk_limit=100000.0,
        approved_data_sources=[
            "solana_rpc", "ethereum_rpc", "bitcoin_node",
            "dex_screener", "birdeye", "jupiter_quote",
            "orca_pools", "raydium_pools", "uniswap_subgraphs",
            "chainlink_price_feeds", "mempool_space",
            "github_activity", "internal_ledger",
        ],
        allowed_tools=[
            "opportunity_scanner", "backtest_engine",
            "route_optimizer", "wallet_monitor",
            "alert_system", "infrastructure_deployer",
            "code_reviewer", "security_scanner",
            "performance_profiler", "log_aggregator",
        ],
        wallet_policy="WATCH_ONLY",
        reporting_schedule="0 */4 * * *",  # every 4 hours
        escalation_rules={
            "infrastructure_outage": {"threshold": 1.0, "escalate_to": "Operations"},
            "security_vulnerability": {"threshold": 1.0, "escalate_to": "Legal + Governance"},
            "performance_degradation": {"threshold": 0.9, "escalate_to": "Engineering Lead"},
        },
        risk_tolerance="conservative",
        profit_mandate="Build tools that discover, simulate, and route on-chain opportunities with sub-second latency and maximum uptime reliability.",
        compliance_constraints=[
            "No production secrets in code",
            "All deployments require security review",
            "No direct key access in infrastructure",
        ],
    ),
    DepartmentConfig(
        department_id="dept-operations",
        name="Operations",
        mission="Monitor system uptime, execution queues, stuck transactions, data freshness, and treasury workflow health across all MEMBRA infrastructure.",
        risk_limit=50000.0,
        approved_data_sources=[
            "solana_rpc", "ethereum_rpc", "bitcoin_node",
            "mempool_space", "whale_alert_feeds",
            "internal_ledger", "treasury_balances",
            "proofbook_events", "governance_proposals",
            "risk_blacklist",
        ],
        allowed_tools=[
            "uptime_monitor", "execution_queue_monitor",
            "transaction_tracker", "data_freshness_checker",
            "treasury_workflow_monitor", "incident_responder",
            "capacity_planner", "cost_optimizer",
        ],
        wallet_policy="WATCH_ONLY",
        reporting_schedule="*/15 * * * *",  # every 15 minutes
        escalation_rules={
            "system_down": {"threshold": 1.0, "escalate_to": "Engineering + Governance"},
            "treasury_anomaly": {"threshold": 1.0, "escalate_to": "Finance + Governance"},
            "data_stale": {"threshold": 300, "escalate_to": "Engineering"},
        },
        risk_tolerance="conservative",
        profit_mandate="Minimize operational downtime cost, optimize infrastructure spend, and ensure all profit-seeking systems are healthy and auditable.",
        compliance_constraints=[
            "All incidents logged to ProofBook",
            "No manual fund movements",
            "24/7 monitoring coverage required",
        ],
    ),
    DepartmentConfig(
        department_id="dept-sales",
        name="Sales",
        mission="Find and cultivate merchant settlement leads, liquidity partners, ecosystem grant opportunities, and revenue-generating partnerships.",
        risk_limit=100000.0,
        approved_data_sources=[
            "solana_rpc", "ethereum_rpc",
            "dex_screener", "defillama",
            "coingecko", "x_social_sentiment",
            "github_activity", "internal_ledger",
            "governance_proposals",
        ],
        allowed_tools=[
            "lead_finder", "partner_scorer",
            "grant_opportunity_tracker", "merchant_settlement_analyzer",
            "liquidity_partner_evaluator", "proposal_generator",
        ],
        wallet_policy="WATCH_ONLY",
        reporting_schedule="0 */8 * * *",  # every 8 hours
        escalation_rules={
            "enterprise_deal": {"threshold": 100000, "escalate_to": "Strategy"},
            "grant_deadline": {"threshold": 72, "escalate_to": "Governance"},
            "partner_risk": {"threshold": 0.6, "escalate_to": "Legal"},
        },
        risk_tolerance="moderate",
        profit_mandate="Generate partner revenue, merchant settlement volume, and grant funding through systematic opportunity identification and outreach.",
        compliance_constraints=[
            "All partners KYC-reviewed",
            "No sanctioned entity engagement",
            "Revenue share terms require legal approval",
        ],
    ),
    DepartmentConfig(
        department_id="dept-finance",
        name="Finance",
        mission="Detect arbitrage, analyze spreads, compare stablecoin yields, recommend treasury rebalancing, optimize liquidity, and project fee revenue.",
        risk_limit=750000.0,
        approved_data_sources=[
            "solana_rpc", "ethereum_rpc", "bitcoin_node",
            "dex_screener", "birdeye", "jupiter_quote",
            "orca_pools", "raydium_pools", "uniswap_subgraphs",
            "chainlink_price_feeds", "coingecko", "defillama",
            "mempool_space", "whale_alert_feeds",
            "internal_ledger", "treasury_balances",
        ],
        allowed_tools=[
            "arbitrage_detector", "spread_analyzer",
            "yield_comparator", "treasury_rebalancer",
            "liquidity_efficiency_optimizer", "fee_revenue_projector",
            "pnl_tracker", "var_calculator",
        ],
        wallet_policy="PAPER",  # paper trading only for simulations
        reporting_schedule="0 */3 * * *",  # every 3 hours
        escalation_rules={
            "arbitrage_opportunity": {"threshold": 50000, "escalate_to": "Governance"},
            "yield_drop": {"threshold": 0.05, "escalate_to": "Strategy"},
            "treasury_imbalance": {"threshold": 0.2, "escalate_to": "Governance"},
        },
        risk_tolerance="moderate",
        profit_mandate="Maximize treasury returns through systematic arbitrage detection, yield optimization, spread analysis, and liquidity efficiency recommendations.",
        compliance_constraints=[
            "All trades simulated before proposal",
            "No direct execution without multisig",
            "VaR limits enforced per strategy",
        ],
    ),
    DepartmentConfig(
        department_id="dept-legal",
        name="Legal",
        mission="Block prohibited strategies, classify regulatory risk, enforce jurisdiction restrictions, review token/security classifications, and maintain compliance frameworks.",
        risk_limit=0.0,
        approved_data_sources=[
            "coingecko", "defillama",
            "risk_blacklist", "sanctions_compliance_provider",
            "governance_proposals", "internal_ledger",
            "github_activity",
        ],
        allowed_tools=[
            "strategy_prohibition_engine", "regulatory_risk_classifier",
            "jurisdiction_enforcer", "token_security_reviewer",
            "compliance_framework_maintainer", "audit_trail_validator",
        ],
        wallet_policy="WATCH_ONLY",
        reporting_schedule="0 */12 * * *",  # every 12 hours
        escalation_rules={
            "prohibited_strategy_detected": {"threshold": 1.0, "escalate_to": "Governance + Proof"},
            "regulatory_alert": {"threshold": 0.5, "escalate_to": "Governance"},
            "sanctions_match": {"threshold": 1.0, "escalate_to": "Governance + Block immediately"},
        },
        risk_tolerance="conservative",
        profit_mandate="Protect MEMBRA from legal, regulatory, and reputational risk by enforcing compliance boundaries while enabling maximum permissible profit opportunities.",
        compliance_constraints=[
            "Zero tolerance for sanctions violations",
            "All tokens classified before strategy approval",
            "Jurisdiction rules updated within 24h of regulatory change",
        ],
    ),
    DepartmentConfig(
        department_id="dept-governance",
        name="Governance",
        mission="Approve or reject opportunity proposals, maintain the policy engine, enforce risk limits, create immutable audit trails, and coordinate cross-department decisions.",
        risk_limit=1000000.0,
        approved_data_sources=[
            "internal_ledger", "treasury_balances",
            "proofbook_events", "governance_proposals",
            "risk_blacklist", "sanctions_compliance_provider",
            "coingecko", "defillama",
        ],
        allowed_tools=[
            "policy_engine", "approval_workflow_manager",
            "risk_limit_enforcer", "audit_trail_generator",
            "multisig_coordinator", "voting_tally",
            "proposal_evaluator", "escalation_router",
        ],
        wallet_policy="TREASURY_GATED",  # multisig/MPC required
        reporting_schedule="0 */2 * * *",  # every 2 hours
        escalation_rules={
            "policy_violation": {"threshold": 1.0, "escalate_to": "Legal + Proof"},
            "approval_deadline": {"threshold": 24, "escalate_to": "Strategy Head"},
            "multisig_threshold": {"threshold": 0.66, "escalate_to": "All signers"},
        },
        risk_tolerance="conservative",
        profit_mandate="Ensure all profit-seeking activities are policy-compliant, risk-bounded, and auditable. Govern treasury actions through structured multisig approval.",
        compliance_constraints=[
            "No unilateral approvals",
            "All decisions logged to ProofBook",
            "Quorum required for all treasury actions",
        ],
    ),
    DepartmentConfig(
        department_id="dept-proof",
        name="Proof",
        mission="Write every opportunity, decision, rejection, simulation, and approval into ProofBook. Hash reports. Produce immutable audit trails. Verify data integrity.",
        risk_limit=0.0,
        approved_data_sources=[
            "internal_ledger", "proofbook_events",
            "treasury_balances", "governance_proposals",
            "risk_blacklist", "sanctions_compliance_provider",
        ],
        allowed_tools=[
            "proofbook_writer", "hash_generator",
            "audit_trail_builder", "integrity_verifier",
            "event_chain_validator", "report_formatter",
            "ipfs_publisher", "timestamp_anchor",
        ],
        wallet_policy="WATCH_ONLY",
        reporting_schedule="*/5 * * * *",  # every 5 minutes
        escalation_rules={
            "hash_mismatch": {"threshold": 1.0, "escalate_to": "Engineering + Governance"},
            "missing_event": {"threshold": 1.0, "escalate_to": "Governance"},
            "integrity_failure": {"threshold": 1.0, "escalate_to": "All Departments"},
        },
        risk_tolerance="conservative",
        profit_mandate="Ensure every profit opportunity, simulation, approval, and execution is immutably recorded. Prove MEMBRA's operational integrity to partners and auditors.",
        compliance_constraints=[
            "100% event coverage required",
            "No deletions or modifications",
            "Chain of custody must be verifiable",
        ],
    ),
    DepartmentConfig(
        department_id="dept-concierge",
        name="Concierge",
        mission="Deliver white-glove support to MEMBRA partners and high-value users. Coordinate cross-department requests, route inquiries, and ensure stakeholder satisfaction.",
        risk_limit=25000.0,
        approved_data_sources=[
            "internal_ledger", "treasury_balances",
            "governance_proposals", "x_social_sentiment",
            "coingecko",
        ],
        allowed_tools=[
            "stakeffect_router", "inquiry_classifier",
            "escalation_manager", "satisfaction_tracker",
            "partner_portal_manager", "ticket_resolver",
        ],
        wallet_policy="WATCH_ONLY",
        reporting_schedule="0 */6 * * *",  # every 6 hours
        escalation_rules={
            "high_value_request": {"threshold": 50000, "escalate_to": "Sales + Strategy"},
            "complaint": {"threshold": 1.0, "escalate_to": "Legal"},
            "partner_churn_risk": {"threshold": 0.7, "escalate_to": "Sales + Marketing"},
        },
        risk_tolerance="moderate",
        profit_mandate="Maximize partner lifetime value and user retention through exceptional coordination, rapid issue resolution, and proactive stakeholder engagement.",
        compliance_constraints=[
            "All communications logged",
            "No financial advice to users",
            "Partner data confidentiality required",
        ],
    ),
    DepartmentConfig(
        department_id="dept-marketing",
        name="Marketing",
        mission="Find partner opportunities, merchant settlement leads, liquidity partners, ecosystem grants, and build MEMBRA's brand visibility in the on-chain economy.",
        risk_limit=50000.0,
        approved_data_sources=[
            "coingecko", "defillama",
            "x_social_sentiment", "github_activity",
            "internal_ledger", "governance_proposals",
            "dex_screener",
        ],
        allowed_tools=[
            "brand_mention_tracker", "community_growth_analyzer",
            "content_performance_tracker", "grant_opportunity_finder",
            "partner_visibility_scorer", "ecosystem_event_tracker",
        ],
        wallet_policy="WATCH_ONLY",
        reporting_schedule="0 */8 * * *",  # every 8 hours
        escalation_rules={
            "viral_opportunity": {"threshold": 0.9, "escalate_to": "Strategy"},
            "brand_risk": {"threshold": 0.6, "escalate_to": "Legal"},
            "grant_deadline": {"threshold": 48, "escalate_to": "Sales"},
        },
        risk_tolerance="moderate",
        profit_mandate="Drive user acquisition, partner engagement, and grant revenue through data-driven brand positioning and ecosystem visibility strategies.",
        compliance_constraints=[
            "No misleading claims",
            "All promotions require legal review",
            "Influencer partnerships require disclosure compliance",
        ],
    ),
    DepartmentConfig(
        department_id="dept-hr",
        name="HR",
        mission="Manage the 60-employee workforce, track performance, ensure employee wellbeing, coordinate training, and maintain workforce compliance and allocation.",
        risk_limit=10000.0,
        approved_data_sources=[
            "internal_ledger", "proofbook_events",
            "governance_proposals", "github_activity",
        ],
        allowed_tools=[
            "performance_tracker", "workload_balancer",
            "training_coordinator", "employee_wellbeing_monitor",
            "compliance_auditor", "allocation_optimizer",
        ],
        wallet_policy="WATCH_ONLY",
        reporting_schedule="0 0 * * *",  # daily
        escalation_rules={
            "employee_overload": {"threshold": 0.85, "escalate_to": "Department Head"},
            "performance_anomaly": {"threshold": 0.5, "escalate_to": "Governance"},
            "compliance_gap": {"threshold": 1.0, "escalate_to": "Legal + Governance"},
        },
        risk_tolerance="conservative",
        profit_mandate="Optimize workforce productivity, ensure 100% compliance coverage, and allocate talent to highest-ROI profit-seeking initiatives.",
        compliance_constraints=[
            "All employee actions auditable",
            "No bias in allocation algorithms",
            "Wellbeing metrics tracked weekly",
        ],
    ),
]


DEPARTMENT_MAP: Dict[str, DepartmentConfig] = {d.department_id: d for d in DEPARTMENTS}


def get_department(department_id: str) -> DepartmentConfig:
    if department_id not in DEPARTMENT_MAP:
        raise ValueError(f"Department {department_id} not found")
    return DEPARTMENT_MAP[department_id]


def list_departments() -> List[DepartmentConfig]:
    return DEPARTMENTS
