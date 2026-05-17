"""Tests for LLM Employee Service."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from app.services.llm_employee import LLMEmployeeService
from app.config.employees import get_employee


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def llm_service(mock_db):
    return LLMEmployeeService(mock_db)


@pytest.fixture
def sample_opportunity():
    """Mock opportunity object."""
    opp = MagicMock()
    opp.id = "test_opp_001"
    opp.protocol = "uniswap"
    opp.chain = "ethereum"
    opp.opportunity_type = "arbitrage"
    opp.expected_profit = 1000.0
    opp.expected_profit_percent = 5.0
    opp.required_capital = 20000.0
    opp.risk_score = 0.3
    opp.compliance_score = 0.9
    opp.confidence_score = 0.85
    opp.simulation_status = "passed"
    opp.approval_status = "pending"
    opp.created_at = datetime.now(timezone.utc)
    return opp


@pytest.mark.asyncio
async def test_analyze_opportunity_deterministic(llm_service, mock_db, sample_opportunity):
    """Test opportunity analysis with deterministic LLM."""
    employee_id = "emp-s-01"  # Alice Chen - Strategy Analyst
    opportunity_id = "test_opp_001"
    
    # Mock database queries - ensure scalar_one_or_none is not async
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_opportunity
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    # Mock memory layer - create a proper async function that returns mock
    async def mock_get_memory_layer():
        mock_store = MagicMock()
        async def mock_store_async(*args, **kwargs):
            pass
        mock_store.store = mock_store_async
        mock_mem = MagicMock()
        mock_mem.store = mock_store
        return mock_mem
    
    # Mock event bus - create a proper async function
    async def mock_get_event_bus():
        mock_bus = MagicMock()
        async def mock_publish(*args, **kwargs):
            pass
        mock_bus.publish = mock_publish
        return mock_bus
    
    # Mock policy engine
    mock_policy = AsyncMock()
    async def mock_get_policy_engine():
        return mock_policy
    
    # Patch the global service instances
    import app.services.llm_employee
    original_memory = app.services.llm_employee.get_memory_layer
    original_event_bus = app.services.llm_employee.get_event_bus
    original_policy = app.services.llm_employee.get_policy_engine
    
    app.services.llm_employee.get_memory_layer = mock_get_memory_layer
    app.services.llm_employee.get_event_bus = mock_get_event_bus
    app.services.llm_employee.get_policy_engine = mock_get_policy_engine
    
    try:
        result = await llm_service.analyze_opportunity(employee_id, opportunity_id)
        
        assert result["employee_id"] == employee_id
        assert result["opportunity_id"] == opportunity_id
        assert "analysis" in result
        assert "decision" in result["analysis"]
        assert "confidence" in result["analysis"]
        assert "reasoning" in result["analysis"]
        assert "suggested_actions" in result["analysis"]
        assert result["llm_provider"] == "deterministic"
        
        # Check that analysis is reasonable
        analysis = result["analysis"]
        assert analysis["decision"] in ["approve", "reject", "escalate"]
        assert 0 <= analysis["confidence"] <= 1
        assert len(analysis["reasoning"]) > 0
        assert isinstance(analysis["suggested_actions"], list)
        
    finally:
        # Restore original functions
        app.services.llm_employee.get_memory_layer = original_memory
        app.services.llm_employee.get_event_bus = original_event_bus
        app.services.llm_employee.get_policy_engine = original_policy


@pytest.mark.asyncio
async def test_analyze_opportunity_not_found(llm_service, mock_db):
    """Test analysis when opportunity is not found."""
    employee_id = "emp-s-01"
    opportunity_id = "nonexistent"
    
    # Mock database to return None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    result = await llm_service.analyze_opportunity(employee_id, opportunity_id)
    
    assert "error" in result
    assert result["error"] == "Opportunity not found"
    assert result["opportunity_id"] == opportunity_id


@pytest.mark.asyncio
async def test_analyze_opportunity_employee_not_found(llm_service, mock_db):
    """Test analysis when employee is not found."""
    employee_id = "nonexistent_emp"
    opportunity_id = "test_opp_001"
    
    result = await llm_service.analyze_opportunity(employee_id, opportunity_id)
    
    assert "error" in result
    assert result["error"] == "Employee not found"
    assert result["employee_id"] == employee_id


@pytest.mark.asyncio
async def test_execute_task_scan_opportunities(llm_service, mock_db):
    """Test executing scan opportunities task."""
    employee_id = "emp-s-01"  # Alice Chen
    task_type = "scan_opportunities"
    task_data = {}
    trace_id = "trace_001"
    
    # Mock opportunity scanner
    mock_scanner = AsyncMock()
    mock_scanner.scan_all.return_value = [
        MagicMock(id="opp_1"),
        MagicMock(id="opp_2"),
    ]
    
    # Mock event bus - use MagicMock that doesn't need to be awaited
    mock_event_bus = MagicMock()
    mock_event_bus.publish = AsyncMock()
    
    # Patch the imports
    import app.services.llm_employee
    from app.services.opportunity_scanner import OpportunityScannerService
    
    original_scanner = getattr(app.services.llm_employee, 'OpportunityScannerService', None)
    original_event_bus = app.services.llm_employee.get_event_bus
    
    app.services.llm_employee.OpportunityScannerService = lambda db: mock_scanner
    app.services.llm_employee.get_event_bus = lambda: mock_event_bus
    
    try:
        result = await llm_service.execute_employee_task(
            employee_id, task_type, task_data, trace_id
        )
        
        assert result["employee_id"] == employee_id
        assert result["opportunities_found"] == 2
        assert result["trace_id"] == trace_id
        assert "opportunity_ids" in result
        
    finally:
        if original_scanner:
            app.services.llm_employee.OpportunityScannerService = original_scanner
        elif hasattr(app.services.llm_employee, 'OpportunityScannerService'):
            delattr(app.services.llm_employee, 'OpportunityScannerService')
        app.services.llm_employee.get_event_bus = original_event_bus


@pytest.mark.asyncio
async def test_execute_task_generate_report(llm_service):
    """Test executing generate report task."""
    employee_id = "emp-s-01"  # Alice Chen
    task_type = "generate_report"
    task_data = {
        "report_type": "summary",
        "data": {"key": "value"}
    }
    trace_id = "trace_002"
    
    # Mock event bus
    mock_event_bus = MagicMock()
    mock_event_bus.publish = AsyncMock()
    
    import app.services.llm_employee
    original_event_bus = app.services.llm_employee.get_event_bus
    app.services.llm_employee.get_event_bus = lambda: mock_event_bus
    
    try:
        result = await llm_service.execute_employee_task(
            employee_id, task_type, task_data, trace_id
        )
        
        assert result["employee_id"] == employee_id
        assert result["content"]["report_type"] == "summary"
        assert "content" in result
        assert "summary" in result["content"]
        assert "details" in result["content"]
        assert "recommendations" in result["content"]
        
    finally:
        app.services.llm_employee.get_event_bus = original_event_bus


@pytest.mark.asyncio
async def test_execute_task_unknown_type(llm_service):
    """Test executing unknown task type."""
    employee_id = "emp-s-01"  # Alice Chen
    task_type = "unknown_task"
    task_data = {}
    
    result = await llm_service.execute_employee_task(employee_id, task_type, task_data)
    
    assert "error" in result
    assert "Unknown task type" in result["error"]


@pytest.mark.asyncio
async def test_get_employee_status(llm_service):
    """Test getting employee status."""
    employee_id = "emp-s-01"  # Alice Chen
    
    result = await llm_service.get_employee_status(employee_id)
    
    # Check if employee exists
    if "error" in result:
        pytest.skip(f"Employee {employee_id} not found in config")
    
    assert result["employee_id"] == employee_id
    assert "name" in result
    assert "title" in result
    assert "department" in result
    assert "status" in result
    assert "wallet_type" in result
    assert "risk_limit" in result
    assert "profit_mandate" in result
    assert "llm_enabled" in result
    assert "llm_provider" in result
    assert "last_heartbeat" in result


@pytest.mark.asyncio
async def test_get_employee_status_not_found(llm_service):
    """Test getting status for non-existent employee."""
    employee_id = "nonexistent_emp"
    
    result = await llm_service.get_employee_status(employee_id)
    
    assert "error" in result
    assert result["error"] == "Employee not found"
    assert result["employee_id"] == employee_id


@pytest.mark.asyncio
async def test_deterministic_analysis_risk_assessment(llm_service, mock_db):
    """Test deterministic analysis with high risk opportunity."""
    employee_id = "emp-s-01"  # Alice Chen
    opportunity_id = "test_opp_001"
    
    # Create high-risk opportunity
    high_risk_opp = MagicMock()
    high_risk_opp.id = "test_opp_001"
    high_risk_opp.protocol = "risky_protocol"
    high_risk_opp.chain = "ethereum"
    high_risk_opp.opportunity_type = "arbitrage"
    high_risk_opp.expected_profit = 5000.0
    high_risk_opp.expected_profit_percent = 15.0
    high_risk_opp.required_capital = 33333.0
    high_risk_opp.risk_score = 0.9  # High risk
    high_risk_opp.compliance_score = 0.5  # Low compliance
    high_risk_opp.confidence_score = 0.7
    high_risk_opp.simulation_status = "passed"
    high_risk_opp.approval_status = "pending"
    high_risk_opp.created_at = datetime.now(timezone.utc)
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = high_risk_opp
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    # Mock services - use proper async functions
    async def mock_get_memory_layer():
        mock_store = MagicMock()
        async def mock_store_async(*args, **kwargs):
            pass
        mock_store.store = mock_store_async
        mock_mem = MagicMock()
        mock_mem.store = mock_store
        return mock_mem
    
    async def mock_get_event_bus():
        mock_bus = MagicMock()
        async def mock_publish(*args, **kwargs):
            pass
        mock_bus.publish = mock_publish
        return mock_bus
    
    mock_policy = AsyncMock()
    async def mock_get_policy_engine():
        return mock_policy
    
    import app.services.llm_employee
    original_memory = app.services.llm_employee.get_memory_layer
    original_event_bus = app.services.llm_employee.get_event_bus
    original_policy = app.services.llm_employee.get_policy_engine
    
    app.services.llm_employee.get_memory_layer = mock_get_memory_layer
    app.services.llm_employee.get_event_bus = mock_get_event_bus
    app.services.llm_employee.get_policy_engine = mock_get_policy_engine
    
    try:
        result = await llm_service.analyze_opportunity(employee_id, opportunity_id)
        
        analysis = result["analysis"]
        # High risk should trigger escalation or rejection
        assert analysis["decision"] in ["reject", "escalate"]
        assert analysis["risk_assessment"] == "high"
        
    finally:
        app.services.llm_employee.get_memory_layer = original_memory
        app.services.llm_employee.get_event_bus = original_event_bus
        app.services.llm_employee.get_policy_engine = original_policy


@pytest.mark.asyncio
async def test_deterministic_analysis_compliance_check(llm_service, mock_db):
    """Test deterministic analysis with compliance issues."""
    employee_id = "emp-l-31"  # Legal/Compliance employee
    opportunity_id = "test_opp_001"
    
    # Create non-compliant opportunity
    non_compliant_opp = MagicMock()
    non_compliant_opp.id = "test_opp_001"
    non_compliant_opp.protocol = "uniswap"
    non_compliant_opp.chain = "ethereum"
    non_compliant_opp.opportunity_type = "arbitrage"
    non_compliant_opp.expected_profit = 1000.0
    non_compliant_opp.expected_profit_percent = 5.0
    non_compliant_opp.required_capital = 20000.0
    non_compliant_opp.risk_score = 0.3
    non_compliant_opp.compliance_score = 0.4  # Low compliance
    non_compliant_opp.confidence_score = 0.85
    non_compliant_opp.simulation_status = "passed"
    non_compliant_opp.approval_status = "pending"
    non_compliant_opp.created_at = datetime.now(timezone.utc)
    
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = non_compliant_opp
    mock_db.execute.return_value = mock_result
    
    # Mock services - use proper async functions
    async def mock_get_memory_layer():
        mock_store = MagicMock()
        async def mock_store_async(*args, **kwargs):
            pass
        mock_store.store = mock_store_async
        mock_mem = MagicMock()
        mock_mem.store = mock_store
        return mock_mem
    
    async def mock_get_event_bus():
        mock_bus = MagicMock()
        async def mock_publish(*args, **kwargs):
            pass
        mock_bus.publish = mock_publish
        return mock_bus
    
    mock_policy = AsyncMock()
    async def mock_get_policy_engine():
        return mock_policy
    
    import app.services.llm_employee
    original_memory = app.services.llm_employee.get_memory_layer
    original_event_bus = app.services.llm_employee.get_event_bus
    original_policy = app.services.llm_employee.get_policy_engine
    
    app.services.llm_employee.get_memory_layer = mock_get_memory_layer
    app.services.llm_employee.get_event_bus = mock_get_event_bus
    app.services.llm_employee.get_policy_engine = mock_get_policy_engine
    
    try:
        result = await llm_service.analyze_opportunity(employee_id, opportunity_id)
        
        analysis = result["analysis"]
        # Low compliance should trigger rejection
        assert analysis["decision"] == "reject"
        assert "compliance" in analysis["reasoning"].lower()
        
    finally:
        app.services.llm_employee.get_memory_layer = original_memory
        app.services.llm_employee.get_event_bus = original_event_bus
        app.services.llm_employee.get_policy_engine = original_policy
