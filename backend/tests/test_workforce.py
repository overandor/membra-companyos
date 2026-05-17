"""MEMBRA CompanyOS - Workforce & Safety Tests."""
import pytest
from app.config.departments import list_departments
from app.config.employees import list_employees

class TestWorkforce:
    def test_60_employees(self):
        assert len(list_employees()) == 60

    def test_12_departments(self):
        assert len(list_departments()) == 12

    def test_no_private_keys(self):
        for e in list_employees():
            a = e.wallet_address.lower()
            assert "priv" not in a and "seed" not in a and "mnemonic" not in a

    def test_wallet_types_valid(self):
        valid = {"WATCH_ONLY", "PAPER", "PROPOSAL_ONLY", "TREASURY_GATED"}
        for e in list_employees():
            assert e.wallet_type in valid

    def test_unique_ids(self):
        ids = [e.employee_id for e in list_employees()]
        assert len(ids) == len(set(ids))

    def test_5_per_department(self):
        from collections import Counter
        c = Counter(e.department_id for e in list_employees())
        assert len(c) == 12
        assert all(v == 5 for v in c.values())
