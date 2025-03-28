import pytest
from pydantic_core import ValidationError as PydanticCoreValidationError
from tests.exception_handlers import pydantic_core_validation_exception_handler
from httpx import AsyncClient
from httpx import ASGITransport
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend

# FastAPI TestClient with error handler
@pytest.fixture
async def test_client(test_session):
    from app.main import app
    from app.routes.localities import postgresql_client

    async def override_get_session():
        yield test_session

    # Dependencies will be the death of me
    app.dependency_overrides[postgresql_client.get_session] = override_get_session

    FastAPICache.init(InMemoryBackend())
    app.add_exception_handler(PydanticCoreValidationError, pydantic_core_validation_exception_handler)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()