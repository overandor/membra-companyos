"""Tests for MEMBRA LLM Bridge — 6 Novel Patterns."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from app.services.llm_bridge import LLMBridgeService


@pytest.fixture
def mock_db():
    """Create a mock AsyncSession."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def bridge(mock_db):
    """Create LLMBridgeService with mock DB."""
    service = LLMBridgeService(mock_db)
    service._provider = {"name": "deterministic", "model": "rule_based"}
    return service


class TestIntentDrivenUI:
    """Pattern 1: IntentDrivenUI — Natural language mutates React state."""

    async def test_open_task_panel_intent(self, bridge):
        result = await bridge.intent_driven_ui("I want to create a task", "/")
        assert result["action"] == "ui_patch"
        mutations = {m["target"] for m in result["mutations"]}
        assert "task_panel" in mutations
        assert result["confidence"] >= 0.5

    async def test_open_agent_panel_intent(self, bridge):
        result = await bridge.intent_driven_ui("show me the AI agents", "/")
        mutations = {m["target"] for m in result["mutations"]}
        assert "agent_panel" in mutations

    async def test_governance_intent(self, bridge):
        result = await bridge.intent_driven_ui("I need to approve something", "/")
        mutations = {m["target"] for m in result["mutations"]}
        assert "governance_panel" in mutations
        assert result["toast_message"]["type"] == "warning"

    async def test_unknown_intent_fallback(self, bridge):
        result = await bridge.intent_driven_ui("random gibberish xyz", "/")
        assert result["action"] == "ui_patch"
        assert result["confidence"] >= 0.5


class TestSchemaToComponent:
    """Pattern 2: SchemaToComponent — SQLAlchemy → React TSX."""

    async def test_generates_component_name(self, bridge):
        fields = [
            {"name": "asset_type", "type": "string", "nullable": False},
            {"name": "price", "type": "float", "nullable": True},
        ]
        result = await bridge.schema_to_component("world_asset", fields)
        assert result["component_name"] == "WorldAssetCard"
        assert result["table"] == "world_asset"
        assert "generated_tsx" in result

    async def test_tsx_contains_interface(self, bridge):
        fields = [{"name": "name", "type": "string", "nullable": False}]
        result = await bridge.schema_to_component("test_table", fields)
        tsx = result["generated_tsx"]
        assert "interface TestTableCardProps" in tsx
        assert "export function TestTableCard" in tsx
        assert "useState" in tsx

    async def test_field_type_mapping(self, bridge):
        fields = [
            {"name": "count", "type": "integer", "nullable": True},
            {"name": "active", "type": "boolean", "nullable": False},
        ]
        result = await bridge.schema_to_component("config", fields)
        form_types = [f["type"] for f in result["form_fields"]]
        assert "number" in form_types
        assert "checkbox" in form_types


class TestPredictiveOrchestration:
    """Pattern 3: PredictiveOrchestration — Predict next user needs."""

    async def test_new_session_prediction(self, bridge):
        result = await bridge.predictive_orchestrate("user_001", [])
        assert result["pattern"] == "predictive_orchestration"
        assert len(result["predicted_next_actions"]) == 3
        assert result["predicted_next_actions"][0]["action"] == "ingest_intent"
        assert result["confidence"] >= 0.5

    async def test_post_intent_prediction(self, bridge):
        actions = [{"action_type": "intent_created", "entity_id": "int_123"}]
        result = await bridge.predictive_orchestrate("user_001", actions)
        actions_list = result["predicted_next_actions"]
        assert any(a["action"] == "parse_intent" for a in actions_list)

    async def test_post_task_prediction(self, bridge):
        actions = [{"action_type": "task_created", "entity_id": "tsk_456"}]
        result = await bridge.predictive_orchestrate("user_001", actions)
        actions_list = result["predicted_next_actions"]
        assert any(a["action"] == "assign_task" for a in actions_list)

    async def test_preload_instructions(self, bridge):
        result = await bridge.predictive_orchestrate("user_001", [])
        assert "pre_fetched_data" in result
        assert "ui_preload" in result


class TestChatGovernance:
    """Pattern 4: ChatGovernance — Conversational approvals."""

    async def test_approve_intent_no_pending(self, bridge, mock_db):
        mock_db.execute.return_value = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        result = await bridge.chat_governance("yes approve it", "0xabc")
        assert result["pattern"] == "chat_governance"
        assert "No pending approvals" in result["reply"]
        assert result["action_taken"] == "none"

    async def test_reject_intent_no_pending(self, bridge, mock_db):
        mock_db.execute.return_value = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        result = await bridge.chat_governance("no reject it", "0xabc")
        assert "No pending approvals" in result["reply"]

    async def test_show_pending(self, bridge, mock_db):
        mock_db.execute.return_value = MagicMock()
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        result = await bridge.chat_governance("what needs approval", "0xabc")
        assert "Zero pending approvals" in result["reply"]

    async def test_ambiguous_message(self, bridge):
        result = await bridge.chat_governance("hello what is this", "0xabc")
        assert result["action_taken"] == "none"
        assert "governance assistant" in result["reply"]


class TestMultimodalProof:
    """Pattern 5: MultimodalProof — Vision LLM verifies media."""

    async def test_missing_task(self, bridge, mock_db):
        mock_db.execute.return_value = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        result = await bridge.multimodal_proof_verify("bad_id", "base64data", "image/png", "0xabc")
        assert result["error"] == "Task not found"
        assert not result["verified"]

    async def test_media_type_check(self, bridge, mock_db):
        task = MagicMock()
        task.proof_requirement = {"evidence_types": ["image"]}
        task.title = "Test Task"
        task.description = "Do something"
        task.status = "assigned"
        mock_db.execute.return_value = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = task

        result = await bridge.multimodal_proof_verify("task_1", "a" * 5000, "image/png", "0xabc")
        assert result["pattern"] == "multimodal_proof"
        assert "checks" in result
        assert "vision_analysis" in result

    async def test_small_media_rejected(self, bridge, mock_db):
        task = MagicMock()
        task.proof_requirement = {"evidence_types": ["image"]}
        task.title = "Test"
        task.description = ""
        task.status = "assigned"
        mock_db.execute.return_value = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = task

        result = await bridge.multimodal_proof_verify("task_1", "ab", "image/png", "0xabc")
        assert not result["verified"]


class TestAgentSwarmProxy:
    """Pattern 6: AgentSwarmProxy — Single proxy routes to multiple agents."""

    async def test_finance_routing(self, bridge):
        result = await bridge.agent_swarm_proxy("What is the budget for this", "0xabc")
        assert result["pattern"] == "agent_swarm_proxy"
        agents = [r["agent"] for r in result["agent_responses"]]
        assert "finance" in agents

    async def test_strategy_routing(self, bridge):
        result = await bridge.agent_swarm_proxy("How do we plan this objective", "0xabc")
        agents = [r["agent"] for r in result["agent_responses"]]
        assert "strategy" in agents

    async def test_compliance_routing(self, bridge):
        result = await bridge.agent_swarm_proxy("Is this policy compliant", "0xabc")
        agents = [r["agent"] for r in result["agent_responses"]]
        assert "compliance" in agents

    async def test_fallback_routing(self, bridge):
        result = await bridge.agent_swarm_proxy("hello", "0xabc")
        primary = result["routing_decision"]["primary_agent"]
        assert primary == "strategy"
        assert len(result["agent_responses"]) >= 2

    async def test_unified_reply_present(self, bridge):
        result = await bridge.agent_swarm_proxy("anything", "0xabc")
        assert "unified_reply" in result
        assert len(result["unified_reply"]) > 0
