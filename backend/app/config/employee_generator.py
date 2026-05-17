"""MEMBRA CompanyOS — Dynamic Employee Generator.

Generates all 60 employees from shared schemas, department configs,
role templates, and compact employee roster. No copy-paste sludge.
"""
from typing import List, Dict, Any
from app.config.employee_schema import EmployeeConfig, _w, BASE_PROMPT
from app.config.departments import DEPARTMENTS

# ── Data source registry ──
SOURCES = {
    "market": ["coingecko", "defillama", "x_social_sentiment"],
    "onchain_sol": ["solana_rpc", "birdeye", "jupiter_quote", "orca_pools", "raydium_pools"],
    "onchain_eth": ["ethereum_rpc", "uniswap_subgraphs", "chainlink_price_feeds"],
    "dex": ["dex_screener", "coingecko", "defillama"],
    "yield": ["solana_rpc", "ethereum_rpc", "dex_screener", "orca_pools", "raydium_pools", "uniswap_subgraphs", "defillama"],
    "mempool": ["mempool_space", "jito_bundle_feed", "whale_alert_feeds"],
    "social": ["x_social_sentiment", "github_activity"],
    "internal": ["internal_ledger", "treasury_balances", "governance_proposals", "proofbook_events"],
    "compliance": ["risk_blacklist", "sanctions_compliance_provider"],
    "all_market": ["solana_rpc", "ethereum_rpc", "dex_screener", "birdeye", "jupiter_quote", "orca_pools", "raydium_pools", "uniswap_subgraphs", "chainlink_price_feeds", "coingecko", "defillama", "mempool_space", "whale_alert_feeds"],
}

# ── Tool registry ──
TOOLS = {
    "opportunity_scanner": ["opportunity_scanner", "price_monitor", "liquidity_analyzer"],
    "arb": ["arbitrage_detector", "fee_estimator", "slippage_calculator", "route_optimizer"],
    "spread": ["spread_analyzer", "basis_tracker", "funding_rate_monitor"],
    "yield": ["yield_comparator", "protocol_risk_scorer", "liquidity_analyzer", "exit_planner"],
    "mempool": ["mempool_analyzer", "frontrunning_detector", "sandwich_defender"],
    "product": ["user_research_synthesizer", "feature_prioritizer", "revenue_modeler"],
    "eng": ["smart_contract_auditor", "bug_bounty_tracker", "security_reviewer"],
    "ops": ["node_health_monitor", "deployment_automator", "alert_router"],
    "sales": ["partner_evaluator", "revenue_forecaster", "proposal_generator"],
    "treasury": ["treasury_rebalancer", "tax_optimizer", "slippage_calculator"],
    "legal": ["strategy_prohibition_engine", "sanctions_screener", "jurisdiction_checker"],
    "governance": ["proposal_evaluator", "voting_tally", "policy_engine", "approval_workflow_manager"],
    "proof": ["proofbook_writer", "event_validator", "coverage_checker"],
    "concierge": ["stakeholder_router", "inquiry_classifier", "escalation_manager"],
    "marketing": ["brand_mention_tracker", "sentiment_analyzer", "reach_estimator"],
    "hr": ["performance_tracker", "workload_balancer", "training_coordinator"],
}

# ── Role templates ──
ROLE_TEMPLATES = {
    "opportunity_discovery": {
        "task": "Scan market data for on-chain profit opportunities. Evaluate expected return, risk, and feasibility. Report findings with confidence scores.",
        "sources": SOURCES["all_market"] + SOURCES["internal"],
        "tools": TOOLS["opportunity_scanner"],
        "profit": "Discover profitable on-chain opportunities with quantified risk-adjusted returns.",
        "compliance": ["All opportunities simulated before proposal", "No private key usage", "Max exposure per trade $100k"],
    },
    "arbitrage_detection": {
        "task": "Scan cross-exchange and cross-chain price differences. Calculate net profit after fees and slippage.",
        "sources": SOURCES["all_market"] + SOURCES["internal"],
        "tools": TOOLS["arb"],
        "profit": "Capture low-risk arbitrage profit by detecting price dislocations before they close.",
        "compliance": ["All arbitrage simulated before proposal", "No execution without multisig", "Max exposure per trade $100k"],
    },
    "mempool_analysis": {
        "task": "Analyze mempool for MEV and sandwich attack patterns. Identify safe transaction windows.",
        "sources": SOURCES["mempool"] + SOURCES["onchain_sol"] + SOURCES["internal"],
        "tools": TOOLS["mempool"],
        "profit": "Protect MEMBRA transactions from MEV extraction and identify safe execution windows.",
        "compliance": ["No frontrunning of user transactions", "All mempool analysis logged", "No private key usage"],
    },
    "product_discovery": {
        "task": "Analyze user behavior and market gaps to identify new product opportunities.",
        "sources": SOURCES["market"] + SOURCES["social"] + SOURCES["internal"],
        "tools": TOOLS["product"],
        "profit": "Launch products that capture underserved market demand with validated revenue models.",
        "compliance": ["All user data anonymized", "Revenue projections conservative", "No misleading claims"],
    },
    "security_audit": {
        "task": "Audit smart contracts and protocols for vulnerabilities. Track bug bounty programs.",
        "sources": SOURCES["onchain_sol"] + SOURCES["onchain_eth"] + SOURCES["social"] + SOURCES["compliance"],
        "tools": TOOLS["eng"],
        "profit": "Prevent catastrophic loss by identifying vulnerabilities before exploitation.",
        "compliance": ["No exploits without disclosure", "Responsible disclosure only", "All audits logged to ProofBook"],
    },
    "node_operations": {
        "task": "Monitor validator and node health. Optimize uptime and rewards.",
        "sources": SOURCES["onchain_sol"] + SOURCES["onchain_eth"] + SOURCES["internal"],
        "tools": TOOLS["ops"],
        "profit": "Maximize staking and validation rewards through optimal node performance.",
        "compliance": ["No slashing conditions violated", "Downtime alerts immediate", "All changes simulated"],
    },
    "partnership": {
        "task": "Evaluate and close revenue-sharing partnerships. Negotiate terms.",
        "sources": SOURCES["market"] + SOURCES["internal"],
        "tools": TOOLS["sales"],
        "profit": "Close revenue partnerships that add predictable, high-margin recurring income.",
        "compliance": ["All deals require governance for >$50k", "Revenue share terms require legal review", "Partner performance audited quarterly"],
    },
    "treasury_rebalancing": {
        "task": "Monitor treasury composition vs target allocations. Recommend rebalancing trades.",
        "sources": SOURCES["market"] + SOURCES["internal"],
        "tools": TOOLS["treasury"],
        "profit": "Maintain optimal treasury allocation balancing growth, liquidity, and risk.",
        "compliance": ["Rebalances require governance for >$50k", "Tax implications reviewed", "No rebalancing during black swan events"],
    },
    "legal_compliance": {
        "task": "Review all proposals for compliance with internal prohibition list.",
        "sources": SOURCES["compliance"] + SOURCES["internal"],
        "tools": TOOLS["legal"],
        "profit": "Prevent catastrophic legal and regulatory exposure by enforcing zero-tolerance prohibitions.",
        "compliance": ["Zero tolerance for sanctions violations", "All blocks require documented reason", "Prohibition list updated within 1h of regulatory change"],
    },
    "governance": {
        "task": "Review all opportunity proposals for alignment with strategy, risk limits, and compliance.",
        "sources": SOURCES["internal"] + SOURCES["compliance"] + SOURCES["market"],
        "tools": TOOLS["governance"],
        "profit": "Ensure only high-quality, compliant opportunities advance to execution.",
        "compliance": ["No unilateral approvals", "All decisions logged to ProofBook", "Quorum required for treasury actions"],
    },
    "proofbook": {
        "task": "Write every opportunity, decision, rejection, simulation, and approval into ProofBook.",
        "sources": SOURCES["internal"] + SOURCES["compliance"],
        "tools": TOOLS["proof"],
        "profit": "Create an immutable record that proves MEMBRA's integrity.",
        "compliance": ["100pct event coverage required", "No deletions or modifications", "All writes verified"],
    },
    "concierge": {
        "task": "Route all partner and high-value user inquiries to the correct department.",
        "sources": SOURCES["market"] + SOURCES["internal"],
        "tools": TOOLS["concierge"],
        "profit": "Maximize partner satisfaction and retention through flawless inquiry routing.",
        "compliance": ["All inquiries logged", "No inquiry lost", "Sensitive data access minimal"],
    },
    "marketing": {
        "task": "Track brand mentions and community growth across all channels.",
        "sources": SOURCES["market"] + SOURCES["social"],
        "tools": TOOLS["marketing"],
        "profit": "Grow MEMBRA community at lowest acquisition cost while maximizing engagement.",
        "compliance": ["No botting or fake engagement", "All campaigns require legal review", "Community guidelines enforced"],
    },
    "hr_ops": {
        "task": "Track performance metrics and balance workload across all employees.",
        "sources": SOURCES["internal"] + SOURCES["social"],
        "tools": TOOLS["hr"],
        "profit": "Optimize workforce productivity by aligning employee effort with highest-ROI initiatives.",
        "compliance": ["Performance data confidential", "No algorithmic bias", "All decisions auditable"],
    },
}

# ── Department defaults ──
DEPT_DEFAULTS = {
    "dept-strategy": {"wallet_type": "WATCH_ONLY", "risk_limit": 50000.0},
    "dept-product": {"wallet_type": "WATCH_ONLY", "risk_limit": 25000.0},
    "dept-engineering": {"wallet_type": "WATCH_ONLY", "risk_limit": 25000.0},
    "dept-operations": {"wallet_type": "WATCH_ONLY", "risk_limit": 25000.0},
    "dept-sales": {"wallet_type": "WATCH_ONLY", "risk_limit": 100000.0},
    "dept-finance": {"wallet_type": "PAPER", "risk_limit": 750000.0},
    "dept-legal": {"wallet_type": "WATCH_ONLY", "risk_limit": 0.0},
    "dept-governance": {"wallet_type": "TREASURY_GATED", "risk_limit": 1000000.0},
    "dept-proof": {"wallet_type": "WATCH_ONLY", "risk_limit": 0.0},
    "dept-concierge": {"wallet_type": "WATCH_ONLY", "risk_limit": 25000.0},
    "dept-marketing": {"wallet_type": "WATCH_ONLY", "risk_limit": 50000.0},
    "dept-hr": {"wallet_type": "WATCH_ONLY", "risk_limit": 10000.0},
}

# ── Employee roster: (employee_number, name, department_id, role_key, title, custom_sources=[], custom_tools=[]) ──
EMPLOYEE_ROSTER = [
    # Strategy (1-5)
    (1, "Alice Chen", "dept-strategy", "opportunity_discovery", "Strategy Analyst"),
    (2, "Bob Martinez", "dept-strategy", "opportunity_discovery", "Market Scout"),
    (3, "Chloe Nakamura", "dept-strategy", "opportunity_discovery", "Yield Hunter"),
    (4, "David Okafor", "dept-strategy", "opportunity_discovery", "Alpha Researcher"),
    (5, "Elena Petrova", "dept-strategy", "opportunity_discovery", "Risk-Adj Return Analyst"),
    # Product (6-10)
    (6, "Fatima Al-Rashid", "dept-product", "product_discovery", "Product Analyst"),
    (7, "George Banerjee", "dept-product", "product_discovery", "Feature Designer"),
    (8, "Hannah Correa", "dept-product", "product_discovery", "UX Researcher"),
    (9, "Ivan Draganov", "dept-product", "product_discovery", "Revenue Modeler"),
    (10, "Jasmine Ellis", "dept-product", "product_discovery", "Competitive Intel"),
    # Engineering (11-15)
    (11, "Khaled Farouk", "dept-engineering", "security_audit", "Smart Contract Auditor"),
    (12, "Lina Gomes", "dept-engineering", "security_audit", "Protocol Security Lead"),
    (13, "Mateo Hernandez", "dept-engineering", "security_audit", "Bug Bounty Coordinator"),
    (14, "Nadia Ibrahim", "dept-engineering", "security_audit", "Code Reviewer"),
    (15, "Oscar Johansson", "dept-engineering", "security_audit", "Integration Tester"),
    # Operations (16-20)
    (16, "Priya Kapoor", "dept-operations", "node_operations", "Node Operations Lead"),
    (17, "Quentin Lam", "dept-operations", "node_operations", "Validator Manager"),
    (18, "Rosa Mendez", "dept-operations", "node_operations", "Infrastructure Engineer"),
    (19, "Samir Nasser", "dept-operations", "node_operations", "DevOps Specialist"),
    (20, "Tanya Volkov", "dept-operations", "node_operations", "Monitoring Engineer"),
    # Sales (21-25)
    (21, "Ursula Park", "dept-sales", "partnership", "Partnership Scout"),
    (22, "Victor Nguyen", "dept-sales", "partnership", "Merchant Settlement Lead"),
    (23, "Wanda Kowalski", "dept-sales", "partnership", "Liquidity Partner Scout"),
    (24, "Xavier Laurent", "dept-sales", "partnership", "Ecosystem Grant Hunter"),
    (25, "Yuki Tanaka", "dept-sales", "partnership", "Revenue Partner Closer"),
    # Finance (26-30)
    (26, "Zara Abbasi", "dept-finance", "arbitrage_detection", "Arbitrage Detection Specialist"),
    (27, "Adam Bergstrom", "dept-finance", "arbitrage_detection", "Spread Analyst"),
    (28, "Bella Cortez", "dept-finance", "arbitrage_detection", "Stablecoin Yield Comparator"),
    (29, "Carlos Dumont", "dept-finance", "treasury_rebalancing", "Treasury Rebalancing Advisor"),
    (30, "Diana Eriksson", "dept-finance", "treasury_rebalancing", "Liquidity Efficiency Optimizer"),
    # Legal (31-35)
    (31, "Fatima Hassan", "dept-legal", "legal_compliance", "Strategy Prohibition Enforcer"),
    (32, "George Ivanov", "dept-legal", "legal_compliance", "Regulatory Risk Classifier"),
    (33, "Helena Jansen", "dept-legal", "legal_compliance", "Jurisdiction Enforcer"),
    (34, "Ibrahim Kaya", "dept-legal", "legal_compliance", "Token Security Reviewer"),
    (35, "Julia Lindqvist", "dept-legal", "legal_compliance", "Compliance Framework Maintainer"),
    # Governance (36-40)
    (36, "Kenji Mori", "dept-governance", "governance", "Opportunity Approval Coordinator"),
    (37, "Leila Nassar", "dept-governance", "governance", "Policy Engine Architect"),
    (38, "Marcus Osei", "dept-governance", "governance", "Risk Limit Enforcer"),
    (39, "Nina Patel", "dept-governance", "governance", "Audit Trail Coordinator"),
    (40, "Omar Rahman", "dept-governance", "governance", "Multisig Coordinator"),
    # Proof (41-45)
    (41, "Penelope Stone", "dept-proof", "proofbook", "ProofBook Chief Writer"),
    (42, "Quinn Brooks", "dept-proof", "proofbook", "Hash Generator"),
    (43, "Rafael Cruz", "dept-proof", "proofbook", "Audit Trail Builder"),
    (44, "Sofia Eriksson", "dept-proof", "proofbook", "Integrity Verifier"),
    (45, "Tariq Al-Rashid", "dept-proof", "proofbook", "IPFS Publisher"),
    # Concierge (46-50)
    (46, "Uma Delgado", "dept-concierge", "concierge", "Stakeholder Router"),
    (47, "Victor Ek", "dept-concierge", "concierge", "Cross-Department Coordinator"),
    (48, "Wendy Foster", "dept-concierge", "concierge", "Satisfaction Tracker"),
    (49, "Xander Gomez", "dept-concierge", "concierge", "Partner Portal Manager"),
    (50, "Yasmine Haddad", "dept-concierge", "concierge", "Ticket Resolver"),
    # Marketing (51-55)
    (51, "Zane Irving", "dept-marketing", "marketing", "Brand Mention Tracker"),
    (52, "Aisha Johnson", "dept-marketing", "marketing", "Community Growth Analyst"),
    (53, "Bjorn Karlsson", "dept-marketing", "marketing", "Content Performance Tracker"),
    (54, "Celine Laurent", "dept-marketing", "marketing", "Grant Opportunity Finder"),
    (55, "Darius Miller", "dept-marketing", "marketing", "Ecosystem Event Tracker"),
    # HR (56-60)
    (56, "Elena Novak", "dept-hr", "hr_ops", "Performance Tracker"),
    (57, "Felix Ortiz", "dept-hr", "hr_ops", "Workload Balancer"),
    (58, "Greta Petersson", "dept-hr", "hr_ops", "Training Coordinator"),
    (59, "Hiroshi Yamamoto", "dept-hr", "hr_ops", "Wellbeing Monitor"),
    (60, "Isabella Zhang", "dept-hr", "hr_ops", "Compliance Auditor"),
]


# ── Permission matrix ──
PERMISSIONS = {
    "WATCH_ONLY": ["read_market_data", "scan_opportunities", "write_proofbook"],
    "PAPER": ["read_all_market_data", "simulate_arbitrage", "propose_arbitrage", "write_proofbook"],
    "PROPOSAL_ONLY": ["read_treasury", "propose_rebalance", "write_proofbook", "read_governance"],
    "TREASURY_GATED": ["read_all_proposals", "approve_opportunity", "reject_opportunity", "update_policy", "write_proofbook"],
}


def generate_employees() -> List[EmployeeConfig]:
    """Dynamically generate all 60 employees from compact roster + templates."""
    employees = []
    for num, name, dept, role_key, title in EMPLOYEE_ROSTER:
        tpl = ROLE_TEMPLATES[role_key]
        defaults = DEPT_DEFAULTS[dept]
        emp_id = f"emp-{dept.replace('dept-', '')[:1]}-{num:02d}"

        # Build sources: template sources + internal sources for all employees
        sources = list(dict.fromkeys(tpl["sources"] + SOURCES["internal"]))

        # Build permissions from wallet type
        perms = PERMISSIONS.get(defaults["wallet_type"], PERMISSIONS["WATCH_ONLY"])

        # Finance has some PAPER, some PROPOSAL_ONLY
        if dept == "dept-finance" and role_key == "treasury_rebalancing":
            wallet_type = "PROPOSAL_ONLY"
            perms = PERMISSIONS["PROPOSAL_ONLY"]
        else:
            wallet_type = defaults["wallet_type"]

        emp = EmployeeConfig(
            employee_id=emp_id,
            employee_number=num,
            name=name,
            department_id=dept,
            title=title,
            role=role_key,
            system_prompt=BASE_PROMPT,
            task_prompt=tpl["task"],
            approved_data_sources=sources,
            tools=tpl["tools"],
            wallet_address=_w(name, dept.replace("dept-", ""), num),
            wallet_type=wallet_type,
            permissions=perms,
            risk_limit=defaults["risk_limit"],
            profit_mandate=tpl["profit"],
            compliance_constraints=tpl["compliance"],
            reporting_format="json_with_confidence",
        )
        employees.append(emp)
    return employees
