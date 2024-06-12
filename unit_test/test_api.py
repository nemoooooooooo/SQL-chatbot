# -*- coding: utf-8 -*-
"""
Created on Wed Jun 12 23:03:35 2024

@author: Nimra Noor
"""

import sys
sys.path.append('E:\\SQL-chatbot')

from fastapi.testclient import TestClient
from main import app  
import uuid

client = TestClient(app)

def test_update_api_key_valid():
    # UUID generation for test
    test_user_id = uuid.uuid4()
    response = client.post(
        "/update_api_key",
        json={
            "openai_key": "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",
            "fireworks_key": "mlAl0TNbwKrKkzmGvnofa0kDWX0KwEi1lHT8rn3oCAxgOwoa",
            "user_id": str(test_user_id)
        }
    )
    assert response.status_code == 200
    assert response.json() == {"key_updated": True}

def test_update_api_key_invalid_openai_key():
    test_user_id = uuid.uuid4()
    response = client.post(
        "/update_api_key",
        json={
            "openai_key": "invalid_key_format",
            "user_id": str(test_user_id)
        }
    )
    assert response.status_code == 400
    assert "Invalid OpenAI key format" in response.text

def test_update_api_key_no_keys_provided():
    test_user_id = uuid.uuid4()
    response = client.post(
        "/update_api_key",
        json={
            "user_id": str(test_user_id)
        }
    )
    assert response.status_code == 400
    assert "No API key provided" in response.text
