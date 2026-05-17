"""MEMBRA CompanyOS - Opportunity & Safety Tests."""
import pytest
from app.config.employees import list_employees
from app.config.datasources import list_datasources

class TestSafetyRules:
    def test_no_guaranteed_profit_in_mandate(self):
        for e in list_employees():
            p = e.profit_mandate.lower()
            assert "guaranteed profit" not in p

    def test_no_private_keys_in_addresses(self):
        for e in list_employees():
            addr = e.wallet_address.lower()
            assert "priv" not in addr
            assert "seed" not in addr
            assert "mnemonic" not in addr
            assert len(addr) > 20

    def test_governance_gated(self):
        for e in list_employees():
            if e.department_id == "dept-governance":
                assert e.wallet_type == "TREASURY_GATED"

    def test_compliance_constraints_exist(self):
        for e in list_employees():
            assert e.compliance_constraints
            assert len(e.compliance_constraints) > 0

class TestDataSources:
    def test_22_sources(self):
        assert len(list_datasources()) == 22

    def test_all_sources_have_ids(self):
        for s in list_datasources():
            assert s.source_id
            assert s.name
