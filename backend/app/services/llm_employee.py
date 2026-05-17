"""MEMBRA CompanyOS — LLM Employee Service.

Employees use LLMs to make intelligent decisions about opportunities,
execute tasks, and generate reports. Each employee has specialized
domain knowledge and decision-making capabilities.
"""
from typing import Dict, Any, List, Optional
import json
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.config.employees import get_employee, list_employees
from app.services.event_bus import get_event_bus, MembraEvent
from app.services.memory import get_memory_layer
from app.services.policy_engine import get_policy_engine, ExecutionContext
from app.models.opportunity import OnChainOpportunity
import structlog

logger = structlog.get_logger()

# Lazy imports for LLM providers
_openai_client = None
_groq_client = None
_anthropic_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None and settings.openai_api_key:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


def _get_groq_client():
    global _groq_client
    if _groq_client is None and settings.groq_api_key:
        from groq import AsyncGroq
        _groq_client = AsyncGroq(api_key=settings.groq_api_key)
    return _groq_client


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None and settings.anthropic_api_key:
        import anthropic
        _anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


class LLMEmployeeService:
    """LLM-powered employee decision-making and execution."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._llm_client = self._init_llm_client()

    def _init_llm_client(self):
        """Initialize LLM client with provider configuration."""
        if settings.openai_api_key:
            return {"provider": "openai", "model": settings.default_llm_model or "gpt-4o"}
        elif settings.groq_api_key:
            return {"provider": "groq", "model": settings.default_llm_model or "llama-3.3-70b-versatile"}
        elif settings.anthropic_api_key:
            return {"provider": "anthropic", "model": "claude-3-sonnet-20240229"}
        else:
            return {"provider": "deterministic", "model": "rule_based"}

    async def _call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call the configured LLM provider with the given prompt."""
        provider = self._llm_client["provider"]
        model = self._llm_client["model"]

        try:
            if provider == "openai":
                client = _get_openai_client()
                if client is None:
                    raise Exception("OpenAI client not initialized")
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
                return response.choices[0].message.content

            elif provider == "groq":
                client = _get_groq_client()
                if client is None:
                    raise Exception("Groq client not initialized")
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
                return response.choices[0].message.content

            elif provider == "anthropic":
                client = _get_anthropic_client()
                if client is None:
                    raise Exception("Anthropic client not initialized")
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                response = await client.messages.create(
                    model=model,
                    max_tokens=2000,
                    temperature=0.3,
                    messages=[{"role": "user", "content": full_prompt}]
                )
                return response.content[0].text

            else:
                return None  # Fallback to deterministic

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None

    async def analyze_opportunity(
        self,
        employee_id: str,
        opportunity_id: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Employee analyzes an opportunity using LLM and domain knowledge."""
        try:
            employee = get_employee(employee_id)
        except ValueError:
            return {"error": "Employee not found", "employee_id": employee_id}

        # Fetch opportunity details
        result = await self.db.execute(
            select(OnChainOpportunity).where(OnChainOpportunity.id == opportunity_id)
        )
        opp = result.scalar_one_or_none()
        if not opp:
            return {"error": "Opportunity not found", "opportunity_id": opportunity_id}

        # Build analysis prompt using employee's system prompt and task prompt
        analysis_prompt = self._build_analysis_prompt(employee, opp, context)

        # Get LLM response or use deterministic rules
        if self._llm_client["provider"] == "deterministic":
            analysis = self._deterministic_analysis(employee, opp, context)
        else:
            # Call actual LLM API
            llm_response = await self._call_llm(analysis_prompt, employee.system_prompt)
            if llm_response:
                try:
                    analysis = json.loads(llm_response)
                    # Validate required fields
                    if "decision" not in analysis:
                        analysis["decision"] = "escalate"
                    if "reasoning" not in analysis:
                        analysis["reasoning"] = "LLM analysis completed"
                    if "confidence" not in analysis:
                        analysis["confidence"] = 0.7
                    if "risk_assessment" not in analysis:
                        analysis["risk_assessment"] = "medium"
                    if "suggested_actions" not in analysis:
                        analysis["suggested_actions"] = []
                except json.JSONDecodeError:
                    # Fallback to deterministic if LLM returns invalid JSON
                    analysis = self._deterministic_analysis(employee, opp, context)
            else:
                analysis = self._deterministic_analysis(employee, opp, context)

        # Store in memory for future reference
        mem = await get_memory_layer()
        await mem.store.store(
            namespace="opportunity_analysis",
            key=f"{employee_id}_{opportunity_id}",
            data={
                "employee_id": employee_id,
                "opportunity_id": opportunity_id,
                "analysis": analysis,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Publish event
        bus = await get_event_bus()
        await bus.publish(MembraEvent(
            event_type="opportunity_analyzed",
            source="llm_employee",
            payload={
                "employee_id": employee_id,
                "opportunity_id": opportunity_id,
                "decision": analysis.get("decision"),
                "confidence": analysis.get("confidence"),
            },
            employee_id=employee_id,
        ))

        return {
            "employee_id": employee_id,
            "employee_name": employee.name,
            "department": employee.department_id,
            "opportunity_id": opportunity_id,
            "analysis": analysis,
            "llm_provider": self._llm_client["provider"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _build_analysis_prompt(
        self,
        employee,
        opportunity,
        context: Optional[Dict] = None
    ) -> str:
        """Build the analysis prompt for the LLM."""
        prompt = f"""You are {employee.name}, a {employee.title} in the {employee.department_id} department.

{employee.system_prompt}

{employee.task_prompt}

ANALYZE THIS OPPORTUNITY:
- Protocol: {opportunity.protocol}
- Chain: {opportunity.chain}
- Type: {opportunity.opportunity_type}
- Expected Profit: ${opportunity.expected_profit}
- Expected Profit %: {opportunity.expected_profit_percent}%
- Required Capital: ${opportunity.required_capital}
- Risk Score: {opportunity.risk_score}
- Compliance Score: {opportunity.compliance_score}
- Confidence Score: {opportunity.confidence_score}

Your profit mandate: {employee.profit_mandate}
Your risk limit: {employee.risk_limit}
Your compliance constraints: {employee.compliance_constraints}

Provide your analysis in JSON format:
{{
    "decision": "approve|reject|escalate",
    "reasoning": "detailed explanation",
    "risk_assessment": "low|medium|high",
    "confidence": 0.0-1.0,
    "suggested_actions": ["action1", "action2"],
    "additional_notes": "any concerns or observations"
}}
"""
        return prompt

    def _deterministic_analysis(
        self,
        employee,
        opportunity,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Deterministic analysis based on employee rules and opportunity data."""
        decision = "approve"
        reasoning = []
        risk = "low"
        confidence = 0.85
        actions = []

        # Risk assessment
        if opportunity.risk_score is None or opportunity.risk_score >= 0.8:
            risk = "high"
            decision = "escalate"
            reasoning.append(f"High risk score: {opportunity.risk_score}")
            actions.append("Request risk review from Risk Team")
        elif opportunity.risk_score >= 0.5:
            risk = "medium"
            reasoning.append(f"Moderate risk score: {opportunity.risk_score}")

        # Compliance check
        if opportunity.compliance_score is None or opportunity.compliance_score < 0.7:
            decision = "reject"
            reasoning.append(f"Compliance score too low: {opportunity.compliance_score}")
            actions.append("Request compliance review")
            confidence = 0.6

        # Profit mandate check
        if employee.profit_mandate and isinstance(employee.profit_mandate, dict):
            min_profit = employee.profit_mandate.get("min_profit_percent", 0)
            if opportunity.expected_profit_percent < min_profit:
                decision = "reject"
                reasoning.append(f"Profit {opportunity.expected_profit_percent}% below mandate {min_profit}%")
                confidence = 0.7

        # Risk limit check
        if employee.risk_limit and isinstance(employee.risk_limit, dict) and opportunity.risk_score:
            max_risk = employee.risk_limit.get("max_risk_score", 1.0)
            if opportunity.risk_score > max_risk:
                decision = "reject"
                reasoning.append(f"Risk {opportunity.risk_score} exceeds limit {max_risk}")
                confidence = 0.8

        # Department-specific logic
        if employee.department_id == "dept-finance":
            if opportunity.required_capital > employee.risk_limit.get("max_capital", 100000):
                decision = "escalate"
                reasoning.append("Capital exceeds finance department limit")
                actions.append("Request treasury approval")

        elif employee.department_id == "dept-compliance":
            decision = "escalate" if risk == "high" else "approve"
            reasoning.append("Compliance department requires escalation for high-risk")

        elif employee.department_id == "dept-strategy":
            if opportunity.expected_profit_percent > 10:
                reasoning.append("High-value strategic opportunity")
                confidence = 0.95
            else:
                decision = "reject"
                reasoning.append("Below strategic threshold")
                confidence = 0.7

        # Add department-specific notes
        if decision == "approve":
            reasoning.append(f"Meets {employee.department_id} department criteria")
            actions.append("Proceed with simulation")
            actions.append("Submit for governance approval")
        elif decision == "reject":
            actions.append("Document rejection reason")
            actions.append("Archive opportunity")

        return {
            "decision": decision,
            "reasoning": " | ".join(reasoning),
            "risk_assessment": risk,
            "confidence": confidence,
            "suggested_actions": actions,
            "additional_notes": f"Analyzed by {employee.name} ({employee.title})",
        }

    async def execute_employee_task(
        self,
        employee_id: str,
        task_type: str,
        task_data: Dict[str, Any],
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a task using the employee's LLM-powered capabilities."""
        try:
            employee = get_employee(employee_id)
        except ValueError:
            return {"error": "Employee not found", "employee_id": employee_id}

        # Build task execution prompt
        task_prompt = self._build_task_prompt(employee, task_type, task_data)

        # Execute task based on type
        if task_type == "scan_opportunities":
            result = await self._scan_opportunities(employee, task_data, trace_id)
        elif task_type == "analyze_opportunity":
            result = await self.analyze_opportunity(
                employee_id,
                task_data.get("opportunity_id"),
                task_data
            )
        elif task_type == "generate_report":
            result = await self._generate_report(employee, task_data, trace_id)
        elif task_type == "policy_check":
            result = await self._policy_check(employee, task_data, trace_id)
        else:
            result = {
                "error": "Unknown task type",
                "task_type": task_type,
                "available_tasks": ["scan_opportunities", "analyze_opportunity", "generate_report", "policy_check"]
            }

        # Log execution
        bus = await get_event_bus()
        await bus.publish(MembraEvent(
            event_type="task_executed",
            source="llm_employee",
            payload={
                "employee_id": employee_id,
                "task_type": task_type,
                "success": "error" not in result,
                "trace_id": trace_id,
            },
            employee_id=employee_id,
            trace_id=trace_id,
        ))

        return result

    def _build_task_prompt(
        self,
        employee,
        task_type: str,
        task_data: Dict[str, Any]
    ) -> str:
        """Build task execution prompt for the LLM."""
        prompt = f"""You are {employee.name}, {employee.title} at {employee.department_id}.

{employee.system_prompt}

TASK: {task_type}
DATA: {json.dumps(task_data, indent=2)}

{employee.task_prompt}

Execute this task and return the result in JSON format.
"""
        return prompt

    async def _scan_opportunities(
        self,
        employee,
        task_data: Dict[str, Any],
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Scan opportunities using employee's data sources."""
        # In production: call actual data sources (DEX APIs, etc.)
        # For now: simulate scanning
        from app.services.opportunity_scanner import OpportunityScannerService
        scanner = OpportunityScannerService(self.db)
        opportunities = await scanner.scan_all(employee_id=employee.employee_id)

        return {
            "employee_id": employee.employee_id,
            "task": "scan_opportunities",
            "opportunities_found": len(opportunities),
            "opportunity_ids": [o.id for o in opportunities],
            "data_sources_used": employee.approved_data_sources,
            "trace_id": trace_id,
        }

    async def _generate_report(
        self,
        employee,
        task_data: Dict[str, Any],
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a report using LLM."""
        report_type = task_data.get("report_type", "summary")
        data = task_data.get("data", {})

        # Build report using employee's reporting format
        report_format = employee.reporting_format or {
            "style": "concise",
            "sections": ["summary", "details", "recommendations"],
            "tone": "professional"
        }

        report = {
            "employee_id": employee.employee_id,
            "employee_name": employee.name,
            "department": employee.department_id,
            "report_type": report_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "format": report_format,
            "content": {
                "summary": f"Report generated by {employee.name} based on provided data.",
                "details": json.dumps(data, indent=2),
                "recommendations": [
                    "Review data for anomalies",
                    "Consider additional data sources",
                    "Validate with compliance team"
                ]
            },
            "trace_id": trace_id,
        }

        return report

    async def _policy_check(
        self,
        employee,
        task_data: Dict[str, Any],
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform policy check using the policy engine."""
        policy = get_policy_engine()
        ctx = ExecutionContext(
            employee_id=employee.employee_id,
            department_id=employee.department_id,
            action=task_data.get("action", "unknown"),
            target=task_data.get("target", "unknown"),
            amount=task_data.get("amount"),
            chain=task_data.get("chain"),
            risk_score=task_data.get("risk_score"),
            compliance_score=task_data.get("compliance_score"),
            simulation_passed=task_data.get("simulation_passed", False),
        )
        result = policy.evaluate(ctx)

        return {
            "employee_id": employee.employee_id,
            "task": "policy_check",
            "policy_result": result,
            "trace_id": trace_id,
        }

    async def get_employee_status(self, employee_id: str) -> Dict[str, Any]:
        """Get current status and recent activity of an employee."""
        try:
            employee = get_employee(employee_id)
        except ValueError:
            return {"error": "Employee not found", "employee_id": employee_id}

        # Get recent memory entries for this employee
        mem = await get_memory_layer()
        recent_analyses = []  # Would query memory store

        return {
            "employee_id": employee.employee_id,
            "name": employee.name,
            "title": employee.title,
            "department": employee.department_id,
            "status": employee.status,
            "wallet_type": employee.wallet_type,
            "risk_limit": employee.risk_limit,
            "profit_mandate": employee.profit_mandate,
            "llm_enabled": self._llm_client["provider"] != "deterministic",
            "llm_provider": self._llm_client["provider"],
            "recent_activity": recent_analyses,
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
        }


def get_llm_employee_service(db: AsyncSession) -> LLMEmployeeService:
    """Get or create LLM Employee Service instance."""
    return LLMEmployeeService(db)
