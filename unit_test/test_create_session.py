import sys
sys.path.append('E:\\SQL-chatbot')

import pytest
from fastapi.testclient import TestClient
from main import app
import uuid

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_create_session_valid(client):
    response = client.post(
        "/create_session",
        json={
            "user_id": "50e99228-b9ed-4503-b3d0-745556157f43",
            "session_name": "New Chat Session"
        }
    )
    assert response.status_code == 200
    response_json = response.json()
    assert "session_id" in response_json
    assert response_json["session_name"] == "New Chat Session"
    assert "created_at" in response_json
    assert "last_modified" in response_json

def test_create_session_default_name(client):
    response = client.post(
        "/create_session",
        json={
            "user_id": "50e99228-b9ed-4503-b3d0-745556157f43"
        }
    )
    assert response.status_code == 200
    response_json = response.json()
    assert "session_id" in response_json
    assert response_json["session_name"] == "New Chat"
    assert "created_at" in response_json
    assert "last_modified" in response_json


def test_rename_session_valid(client):
    # First, create a session to rename
    create_response = client.post(
        "/create_session",
        json={
            "user_id": "50e99228-b9ed-4503-b3d0-745556157f43",
            "session_name": "Session to Rename"
        }
    )
    assert create_response.status_code == 200
    create_response_json = create_response.json()
    session_id = create_response_json["session_id"]

    # Now, rename the session
    rename_response = client.post(
        "/rename_session",
        json={
            "user_id": "50e99228-b9ed-4503-b3d0-745556157f43",
            "session_id": session_id,
            "new_session_name": "Renamed Session"
        }
    )
    assert rename_response.status_code == 200
    rename_response_json = rename_response.json()
    assert rename_response_json["session_id"] == session_id
    assert rename_response_json["new_session_name"] == "Renamed Session"


def test_rename_session_not_found(client):
    rename_response = client.post(
        "/rename_session",
        json={
            "user_id": "50e99228-b9ed-4503-b3d0-745556157f43",
            "session_id": "non-existent-session-id",
            "new_session_name": "New Name"
        }
    )
    assert rename_response.status_code == 400
    rename_response_json = rename_response.json()
    assert rename_response_json["detail"] == "Session not found."
