"""MEMBRA CompanyOS — LLM Bridge API Routes.

Exposes all 6 novel LLM integration patterns as REST endpoints.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.llm_bridge import LLMBridgeService

router = APIRouter(prefix="/api/v1/llm")


# ═══════════════════════════════════════════════════════════════════════
# PATTERN 1 — IntentDrivenUI
# ═══════════════════════════════════════════════════════════════════════

@router.post("/intent-ui", tags=["llm — intent driven ui"])
async def intent_driven_ui(
    user_text: str,
    current_route: str = "/",
    context: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
):
    """Convert natural language into a UI state mutation payload.

    The frontend receives a JSON patch that it applies directly to React state:
    component visibility, form pre-fill, route hints, and data-fetch triggers.
    """
    bridge = LLMBridgeService(db)
    patch = await bridge.intent_driven_ui(user_text, current_route, context)
    return patch


# ═══════════════════════════════════════════════════════════════════════
# PATTERN 2 — SchemaToComponent
# ═══════════════════════════════════════════════════════════════════════

@router.post("/schema-component", tags=["llm — schema to component"])
async def schema_to_component(
    table_name: str,
    schema_fields: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db),
):
    """Auto-generate React component code from backend SQLAlchemy schema.

    Returns a complete TSX component string that the frontend can render
    dynamically or use as a codegen template.
    """
    bridge = LLMBridgeService(db)
    spec = await bridge.schema_to_component(table_name, schema_fields)
    return spec


# ═══════════════════════════════════════════════════════════════════════
# PATTERN 3 — PredictiveOrchestration
# ═══════════════════════════════════════════════════════════════════════

@router.post("/predict", tags=["llm — predictive orchestration"])
async def predictive_orchestrate(
    user_id: str,
    recent_actions: Optional[List[Dict[str, Any]]] = None,
    db: AsyncSession = Depends(get_db),
):
    """Predict next user needs and pre-compute data + UI states.

    Frontend calls this on mount or after each action. It receives:
    - predicted next actions with probabilities
    - pre-fetch endpoints to warm cache
    - UI preload instructions (which components to render ahead of time)
    """
    bridge = LLMBridgeService(db)
    prediction = await bridge.predictive_orchestrate(user_id, recent_actions or [])
    return prediction


# ═══════════════════════════════════════════════════════════════════════
# PATTERN 4 — ChatGovernance
# ═══════════════════════════════════════════════════════════════════════

@router.post("/governance-chat", tags=["llm — chat governance"])
async def chat_governance(
    message: str,
    user_wallet: str,
    thread_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Conversational governance — approve, reject, or query via natural chat.

    The LLM interprets intent from chat messages, validates against policies,
    mutates ApprovalRequest records, and returns a human-friendly reply.
    """
    bridge = LLMBridgeService(db)
    result = await bridge.chat_governance(message, user_wallet, thread_id)
    return result


# ═══════════════════════════════════════════════════════════════════════
# PATTERN 5 — MultimodalProof
# ═══════════════════════════════════════════════════════════════════════

@router.post("/verify-proof", tags=["llm — multimodal proof"])
async def multimodal_proof_verify(
    task_id: str,
    media_b64: str,
    mime_type: str = "image/png",
    submitter_wallet: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Verify uploaded media as task completion proof using vision LLM.

    Accepts base64-encoded image/document. Backend vision model analyzes content,
    checks against task requirements, writes ProofBook entry if verified.
    """
    bridge = LLMBridgeService(db)
    result = await bridge.multimodal_proof_verify(task_id, media_b64, mime_type, submitter_wallet or "")
    return result


# ═══════════════════════════════════════════════════════════════════════
# PATTERN 6 — AgentSwarmProxy
# ═══════════════════════════════════════════════════════════════════════

@router.post("/swarm", tags=["llm — agent swarm proxy"])
async def agent_swarm_proxy(
    user_message: str,
    user_wallet: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
):
    """Single LLM proxy routes frontend requests to multiple specialist agents.

    The proxy analyzes user intent, selects relevant backend agents,
    dispatches them in parallel, and synthesizes a unified response.
    """
    bridge = LLMBridgeService(db)
    result = await bridge.agent_swarm_proxy(user_message, user_wallet, context)
    return result
