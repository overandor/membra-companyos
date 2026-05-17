"""MEMBRA CompanyOS — Execution Layer Tests."""
import pytest
from app.services.policy_engine import PolicyEngine, ExecutionContext, PolicyResult
from app.services.approval_workflow import ApprovalWorkflow, ApprovalStage
from app.services.chain_adapters import SolanaAdapter, EthereumAdapter, ChainTransaction
from app.services.tool_sandbox import ToolSandbox, ToolCall
from app.services.memory import MemoryStore, _cosine_similarity


class TestPolicyEngine:
    def test_allows_safe_opportunity(self):
        engine = PolicyEngine()
        ctx = ExecutionContext(
            employee_id="emp-f-01",
            department_id="dept-finance",
            action="propose_arbitrage",
            target="opp-123",
            amount=1000.0,
            chain="solana",
            risk_score=0.5,
            compliance_score=0.85,
            simulation_passed=True,
        )
        result = engine.evaluate(ctx)
        assert result["result"] == "allow"
        assert len(result["violations"]) == 0

    def test_blocks_high_risk(self):
        engine = PolicyEngine()
        ctx = ExecutionContext(
            employee_id="emp-f-01",
            department_id="dept-finance",
            action="propose_arbitrage",
            target="opp-123",
            risk_score=0.95,
            compliance_score=0.85,
            simulation_passed=True,
        )
        result = engine.evaluate(ctx)
        assert result["result"] == "deny"
        assert any(v["rule"] == "risk_threshold" for v in result["violations"])

    def test_blocks_low_compliance(self):
        engine = PolicyEngine()
        ctx = ExecutionContext(
            employee_id="emp-f-01",
            department_id="dept-finance",
            action="propose_arbitrage",
            target="opp-123",
            risk_score=0.5,
            compliance_score=0.5,
            simulation_passed=True,
        )
        result = engine.evaluate(ctx)
        assert result["result"] == "deny"
        assert any(v["rule"] == "compliance_minimum" for v in result["violations"])

    def test_blocks_without_simulation(self):
        engine = PolicyEngine()
        ctx = ExecutionContext(
            employee_id="emp-f-01",
            department_id="dept-finance",
            action="execute_arbitrage",
            target="opp-123",
            simulation_passed=False,
        )
        result = engine.evaluate(ctx)
        assert result["result"] == "simulate_only"
        assert any(v["rule"] == "no_execution_without_simulation" for v in result["violations"])

    def test_escalates_treasury_amount(self):
        engine = PolicyEngine()
        ctx = ExecutionContext(
            employee_id="emp-f-01",
            department_id="dept-finance",
            action="approve_opportunity",
            target="opp-123",
            amount=100000.0,
            simulation_passed=True,
            risk_score=0.5,
            compliance_score=0.85,
        )
        result = engine.evaluate(ctx)
        assert result["result"] == "escalate"
        assert any(v["rule"] == "treasury_amount_limit" for v in result["violations"])


class TestApprovalWorkflow:
    @pytest.mark.asyncio
    async def test_create_and_advance_request(self):
        wf = ApprovalWorkflow()
        req = await wf.create_request(
            request_id="req-001",
            opportunity_id="opp-001",
            employee_id="emp-g-01",
            department_id="dept-governance",
        )
        assert req.request_id == "req-001"
        assert req.current_stage == ApprovalStage.SIMULATION_REVIEW

        req = await wf.advance(req.request_id, "signer-1", "approve")
        assert req.current_stage == ApprovalStage.RISK_REVIEW
        assert len(req.signatures) == 1

    @pytest.mark.asyncio
    async def test_reject_request(self):
        wf = ApprovalWorkflow()
        req = await wf.create_request(
            request_id="req-002",
            opportunity_id="opp-002",
            employee_id="emp-g-01",
            department_id="dept-governance",
        )
        req = await wf.advance(req.request_id, "signer-1", "reject", "too risky")
        assert req.current_stage == ApprovalStage.REJECTED
        assert req.signatures[0]["decision"] == "reject"

    @pytest.mark.asyncio
    async def test_escalate_request(self):
        wf = ApprovalWorkflow()
        req = await wf.create_request(
            request_id="req-003",
            opportunity_id="opp-003",
            employee_id="emp-g-01",
            department_id="dept-governance",
        )
        req = await wf.advance(req.request_id, "signer-1", "escalate", "needs board review")
        assert req.current_stage == ApprovalStage.ESCALATED

    def test_get_request(self):
        wf = ApprovalWorkflow()
        # Non-existent request
        assert wf.get_request("req-missing") is None


class TestChainAdapters:
    @pytest.mark.asyncio
    async def test_solana_simulate(self):
        adapter = SolanaAdapter()
        tx = ChainTransaction(
            tx_id="tx-1",
            chain="solana",
            from_address="addr1",
            to_address="addr2",
            amount=10.0,
            token="USDC",
        )
        result = await adapter.simulate(tx)
        assert result["success"] is True
        assert result["chain"] == "solana"
        assert "gas_cost" in result

    @pytest.mark.asyncio
    async def test_ethereum_simulate(self):
        adapter = EthereumAdapter()
        tx = ChainTransaction(
            tx_id="tx-2",
            chain="ethereum",
            from_address="addr1",
            to_address="addr2",
            amount=10.0,
            token="USDC",
        )
        result = await adapter.simulate(tx)
        assert result["success"] is True
        assert result["chain"] == "ethereum"
        assert "gas_cost" in result


class TestToolSandbox:
    def test_register_and_list_tools(self):
        sandbox = ToolSandbox()
        sandbox.register_tool("test_tool", lambda args: {"result": args.get("x", 0) * 2})
        assert "test_tool" in sandbox.list_tools()

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        sandbox = ToolSandbox()
        sandbox.register_tool("double", lambda args: args.get("x", 0) * 2)
        call = ToolCall(tool_name="double", employee_id="emp-1", department_id="dept-test", args={"x": 5})
        result = await sandbox.execute(call)
        assert result.success is True
        assert result.output == 10
        assert result.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        sandbox = ToolSandbox()
        call = ToolCall(tool_name="missing", employee_id="emp-1", department_id="dept-test", args={})
        result = await sandbox.execute(call)
        assert result.success is False
        assert "Unknown tool" in result.error

    @pytest.mark.asyncio
    async def test_policy_blocked(self):
        sandbox = ToolSandbox()
        sandbox.register_tool("blocked", lambda args: "ok")
        sandbox.set_policy_check(lambda call: False)
        call = ToolCall(tool_name="blocked", employee_id="emp-1", department_id="dept-test", args={})
        result = await sandbox.execute(call)
        assert result.success is False
        assert result.blocked_by_policy is True


class TestMemoryStore:
    @pytest.mark.asyncio
    async def test_cosine_similarity(self):
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert _cosine_similarity(a, b) == pytest.approx(1.0)

        c = [0.0, 1.0, 0.0]
        assert _cosine_similarity(a, c) == pytest.approx(0.0)

        d = [0.707, 0.707, 0.0]
        assert _cosine_similarity(a, d) == pytest.approx(0.707, abs=0.01)
