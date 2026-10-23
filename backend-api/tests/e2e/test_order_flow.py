"""E2E tests for API quote request flow."""
import pytest
import httpx


@pytest.mark.e2e
@pytest.mark.order_flow
async def test_quote_request_flow(api_base_url, test_customer_data, test_order_lines):
    """Test quote request API flow: POST /orcamentos with real data."""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        payload = {
            "nome": test_customer_data["name"],
            "email": test_customer_data["email"],
            "contacto": test_customer_data["phone"],
            "observacoes": "E2E test order",
            "linhas": test_order_lines,
            "cf_turnstile_response": None,
        }

        response = await client.post("/orcamentos", json=payload)
        assert response.status_code in (200, 201), f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("id"), "Quote should have ID"


@pytest.mark.e2e
async def test_contact_message_flow(api_base_url, test_customer_data):
    """Test contact message API flow: POST /contacto with real data."""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        payload = {
            "nome": test_customer_data["name"],
            "email": test_customer_data["email"],
            "contacto": test_customer_data["phone"],
            "assunto": "E2E Test",
            "mensagem": "Test contact message",
            "website": "",
            "cf_turnstile_response": None,
        }

        response = await client.post("/contacto", json=payload)
        assert response.status_code in (200, 201), f"Expected 200/201, got {response.status_code}: {response.text}"


@pytest.mark.e2e
async def test_catalogue_fetch(api_base_url):
    """Test catalogue API fetch: GET /catalogo (public read)."""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        response = await client.get("/catalogo")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict), "Catalogue should return list or dict"
