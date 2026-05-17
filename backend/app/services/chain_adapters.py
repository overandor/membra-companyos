"""MEMBRA CompanyOS — Chain Adapters.

Solana, Ethereum, Base, Arbitrum, Hyperliquid.
Simulation-only execution first. No real fund moves without
explicit treasury approval and multisig.
"""
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone
import structlog

from app.services.event_bus import get_event_bus
from app.core.events import MembraEvent

logger = structlog.get_logger()


class Chain(Enum):
    SOLANA = "solana"
    ETHEREUM = "ethereum"
    BASE = "base"
    ARBITRUM = "arbitrum"
    HYPERLIQUID = "hyperliquid"


class ExecutionMode(Enum):
    SIMULATION = "simulation"
    DRY_RUN = "dry_run"
    PRODUCTION = "production"


@dataclass
class ChainTransaction:
    tx_id: str
    chain: str
    from_address: str
    to_address: str
    amount: float
    token: str
    data: Optional[str] = None
    gas_estimate: Optional[float] = None
    simulation_result: Optional[Dict[str, Any]] = None


class ChainAdapter:
    """Base class for chain adapters."""

    def __init__(self, chain: Chain, mode: ExecutionMode = ExecutionMode.SIMULATION):
        self.chain = chain
        self.mode = mode
        self.simulation_only = mode == ExecutionMode.SIMULATION

    async def simulate(self, tx: ChainTransaction) -> Dict[str, Any]:
        """Simulate a transaction and return outcome without broadcasting."""
        raise NotImplementedError

    async def execute(self, tx: ChainTransaction) -> Dict[str, Any]:
        """Execute or simulate a transaction based on mode."""
        if self.simulation_only:
            result = await self.simulate(tx)
            result["mode"] = "simulation"
            result["broadcast"] = False
            return result
        # Production path would go here with proper signing
        raise NotImplementedError("Production execution requires treasury approval and multisig")

    async def get_balance(self, address: str, token: str) -> Dict[str, Any]:
        """Get balance for an address."""
        raise NotImplementedError


class SolanaAdapter(ChainAdapter):
    """Solana chain adapter — simulation first."""

    def __init__(self, mode: ExecutionMode = ExecutionMode.SIMULATION):
        super().__init__(Chain.SOLANA, mode)

    async def simulate(self, tx: ChainTransaction) -> Dict[str, Any]:
        logger.info("solana_simulate", tx_id=tx.tx_id, amount=tx.amount, token=tx.token)
        # Realistic simulation logic
        gas = 0.000005
        slippage = 0.001
        net = tx.amount - gas - (tx.amount * slippage)
        return {
            "success": net > 0,
            "gas_cost": gas,
            "slippage": slippage,
            "net_amount": max(0, net),
            "estimated_time_ms": 400,
            "chain": "solana",
        }

    async def get_balance(self, address: str, token: str) -> Dict[str, Any]:
        return {"address": address, "token": token, "balance": 0.0, "chain": "solana"}


class EthereumAdapter(ChainAdapter):
    """Ethereum chain adapter — simulation first."""

    def __init__(self, mode: ExecutionMode = ExecutionMode.SIMULATION):
        super().__init__(Chain.ETHEREUM, mode)

    async def simulate(self, tx: ChainTransaction) -> Dict[str, Any]:
        logger.info("ethereum_simulate", tx_id=tx.tx_id, amount=tx.amount, token=tx.token)
        gas = 0.002
        slippage = 0.003
        net = tx.amount - gas - (tx.amount * slippage)
        return {
            "success": net > 0,
            "gas_cost": gas,
            "slippage": slippage,
            "net_amount": max(0, net),
            "estimated_time_ms": 12000,
            "chain": "ethereum",
        }

    async def get_balance(self, address: str, token: str) -> Dict[str, Any]:
        return {"address": address, "token": token, "balance": 0.0, "chain": "ethereum"}


class BaseAdapter(ChainAdapter):
    """Base (Coinbase L2) adapter."""

    def __init__(self, mode: ExecutionMode = ExecutionMode.SIMULATION):
        super().__init__(Chain.BASE, mode)

    async def simulate(self, tx: ChainTransaction) -> Dict[str, Any]:
        gas = 0.0001
        slippage = 0.002
        net = tx.amount - gas - (tx.amount * slippage)
        return {
            "success": net > 0,
            "gas_cost": gas,
            "slippage": slippage,
            "net_amount": max(0, net),
            "estimated_time_ms": 3000,
            "chain": "base",
        }

    async def get_balance(self, address: str, token: str) -> Dict[str, Any]:
        return {"address": address, "token": token, "balance": 0.0, "chain": "base"}


class ArbitrumAdapter(ChainAdapter):
    """Arbitrum adapter."""

    def __init__(self, mode: ExecutionMode = ExecutionMode.SIMULATION):
        super().__init__(Chain.ARBITRUM, mode)

    async def simulate(self, tx: ChainTransaction) -> Dict[str, Any]:
        gas = 0.0002
        slippage = 0.002
        net = tx.amount - gas - (tx.amount * slippage)
        return {
            "success": net > 0,
            "gas_cost": gas,
            "slippage": slippage,
            "net_amount": max(0, net),
            "estimated_time_ms": 4000,
            "chain": "arbitrum",
        }

    async def get_balance(self, address: str, token: str) -> Dict[str, Any]:
        return {"address": address, "token": token, "balance": 0.0, "chain": "arbitrum"}


class HyperliquidAdapter(ChainAdapter):
    """Hyperliquid perp/DEX adapter."""

    def __init__(self, mode: ExecutionMode = ExecutionMode.SIMULATION):
        super().__init__(Chain.HYPERLIQUID, mode)

    async def simulate(self, tx: ChainTransaction) -> Dict[str, Any]:
        gas = 0.0
        fee = tx.amount * 0.00035
        net = tx.amount - gas - fee
        return {
            "success": net > 0,
            "gas_cost": gas,
            "fee": fee,
            "net_amount": max(0, net),
            "estimated_time_ms": 500,
            "chain": "hyperliquid",
        }

    async def get_balance(self, address: str, token: str) -> Dict[str, Any]:
        return {"address": address, "token": token, "balance": 0.0, "chain": "hyperliquid"}


class ChainRouter:
    """Router that dispatches to the correct chain adapter."""

    def __init__(self, mode: ExecutionMode = ExecutionMode.SIMULATION):
        self.mode = mode
        self.adapters = {
            Chain.SOLANA.value: SolanaAdapter(mode),
            Chain.ETHEREUM.value: EthereumAdapter(mode),
            Chain.BASE.value: BaseAdapter(mode),
            Chain.ARBITRUM.value: ArbitrumAdapter(mode),
            Chain.HYPERLIQUID.value: HyperliquidAdapter(mode),
        }

    async def route(self, tx: ChainTransaction) -> Dict[str, Any]:
        adapter = self.adapters.get(tx.chain)
        if adapter is None:
            return {"success": False, "error": f"Unsupported chain: {tx.chain}"}
        result = await adapter.execute(tx)
        bus = await get_event_bus()
        await bus.publish(MembraEvent(
            event_type="system.health_check",
            source="chain_router",
            payload={"tx_id": tx.tx_id, "chain": tx.chain, "mode": self.mode.value, "result": result},
        ))
        return result

    async def simulate(self, tx: ChainTransaction) -> Dict[str, Any]:
        adapter = self.adapters.get(tx.chain)
        if adapter is None:
            return {"success": False, "error": f"Unsupported chain: {tx.chain}"}
        return await adapter.simulate(tx)


# Singleton
_router: Optional[ChainRouter] = None


def get_chain_router() -> ChainRouter:
    global _router
    if _router is None:
        _router = ChainRouter()
    return _router
