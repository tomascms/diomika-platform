"""E2E test configuration — real test database, not mocks."""
import asyncio
import os
import pytest
from datetime import datetime
from decimal import Decimal


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async E2E tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def api_base_url():
    """API de staging/local para E2E. Nunca API_BASE_URL: no .env da raiz é produção."""
    url = os.getenv("E2E_API_URL")
    if not url:
        pytest.skip("E2E_API_URL não definida (aponta para staging ou local)")
    return url


@pytest.fixture
def test_user_id():
    """Test user ID for E2E tests."""
    return "test-user-123"


@pytest.fixture
def test_customer_data():
    """Test customer data for E2E order flow."""
    return {
        "name": "E2E Test Customer",
        "email": f"e2e-test-{datetime.utcnow().timestamp()}@diomika.pt",
        "phone": "+351 912345678",
    }


@pytest.fixture
def test_order_lines():
    """Test order lines for E2E order flow."""
    return [
        {
            "ean": "5901234123457",
            "quantity": 1,
            "color_code": "BLACK",
        },
    ]


def pytest_configure(config):
    """Configure E2E test markers."""
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "order_flow: mark test as order flow test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
