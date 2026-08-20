import os
import sys
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from backend.api.auth import get_current_user
from backend.api.dependencies import get_db
from backend.main import app


# Override authentication dependency
def override_get_current_user():
    return {"sub": "test-user-id", "permissions": ["user"]}


app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)


@pytest.fixture
def mock_dependencies(mocker):
    # Mocking cache_service exact cache check
    mocker.patch(
        "backend.services.cache_service.cache_service.check_exact_cache",
        return_value=None,
    )
    mocker.patch(
        "backend.services.embedding_service.embedding_service.embed_query",
        return_value=None,
    )

    # Mock langfuse config
    mocker.patch(
        "backend.services.observability.langfuse.langfuse_service.langfuse", new=None
    )

    # Mock the workflow_router get_state
    mock_state_wrapper = mocker.MagicMock()
    mock_state_wrapper.values = {}
    mocker.patch(
        "backend.workflows.router.workflow_router.workflow.get_state",
        return_value=mock_state_wrapper,
    )

    # Mock the workflow_router invocation
    mock_workflow_output = {
        "final_response": "This is a mock response from the query endpoint.",
        "analysis": {},
        "shared": {"messages": [], "context": []},
        "workflow": {
            "execution_path": ["guardrail", "manager_agent"],
            "current_execution_start_indices": {
                "messages": 0,
                "context": 0,
                "execution_path": 0,
            },
        },
    }
    mocker.patch(
        "backend.workflows.router.workflow_router.invoke",
        return_value=mock_workflow_output,
    )

    # Mock database dependency
    mock_db = mocker.MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    yield mock_db

    # Cleanup
    app.dependency_overrides.pop(get_db, None)


def test_query_endpoint(mock_dependencies):
    session_id = str(uuid4())
    payload = {"session_id": session_id, "query": "How do I optimize this python code?"}

    response = client.post("/api/v1/query/", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert "response" in data
    assert data["response"] == "This is a mock response from the query endpoint."
    assert "metadata" in data
    assert data["metadata"]["execution_path"] == ["guardrail", "manager_agent"]


def test_query_endpoint_cache_hit(mocker):
    session_id = str(uuid4())

    mocker.patch(
        "backend.services.cache_service.cache_service.check_exact_cache",
        return_value={
            "response": "This is a fast cached response.",
            "citations": [],
            "metadata": {"cache_type": "exact_redis_sub_1ms"},
        },
    )

    payload = {"session_id": session_id, "query": "How do I optimize this python code?"}

    response = client.post("/api/v1/query/", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "This is a fast cached response."
    assert data["metadata"]["cache_type"] == "exact_redis_sub_1ms"
    assert data["metadata"]["cached"] is True


def test_query_stream_cache_hit(mocker):
    session_id = str(uuid4())

    mocker.patch(
        "backend.services.cache_service.cache_service.check_exact_cache",
        return_value={
            "response": "This is a fast cached stream response.",
            "citations": [],
            "metadata": {"cache_type": "exact_redis_sub_1ms"},
        },
    )

    payload = {"session_id": session_id, "query": "How do I optimize this python code?"}

    with client.stream("POST", "/api/v1/query/stream", json=payload) as response:
        assert response.status_code == 200
        text = response.read().decode("utf-8")
        assert "connected" in text
        assert "This is a fast cached stream response." in text
        assert "done" in text
