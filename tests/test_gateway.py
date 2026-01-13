#!/usr/bin/env python3
"""Simple test script for the SRE Inference Gateway."""

import asyncio
import time

import httpx


async def test_health_endpoints() -> None:
    """Test health and readiness endpoints."""
    async with httpx.AsyncClient() as client:
        print("Testing health endpoints...")
        
        # Health check
        response = await client.get("http://localhost:8000/v1/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        health_data = response.json()
        assert isinstance(health_data, dict), "Health response should be a dict"
        assert "status" in health_data, "Health response should contain 'status' key"
        print(f"Health: {response.status_code} - {health_data}")
        
        # Readiness check
        response = await client.get("http://localhost:8000/v1/ready")
        assert response.status_code == 200, f"Readiness check failed: {response.text}"
        ready_data = response.json()
        assert isinstance(ready_data, dict), "Ready response should be a dict"
        print(f"Ready: {response.status_code} - {ready_data}")


async def test_chat_completion() -> None:
    """Test chat completion endpoint."""
    async with httpx.AsyncClient() as client:
        print("\nTesting chat completion...")
        
        request_data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        start_time = time.time()
        response = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json=request_data,
            timeout=30.0
        )
        duration = time.time() - start_time
        
        print(f"Chat completion: {response.status_code}")
        print(f"Duration: {duration:.2f}s")
        
        assert response.status_code == 200, f"Chat completion failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, dict), "Response should be a dict"
        assert "id" in data, "Response should contain 'id' key"
        assert "model" in data, "Response should contain 'model' key"
        assert "choices" in data, "Response should contain 'choices' key"
        assert isinstance(data["choices"], list), "Choices should be a list"
        assert len(data["choices"]) > 0, "Choices should not be empty"
        assert isinstance(data["choices"][0], dict), "First choice should be a dict"
        assert "message" in data["choices"][0], "Choice should contain 'message' key"
        assert "content" in data["choices"][0]["message"], "Message should contain 'content' key"
        
        print(f"Response ID: {data['id']}")
        print(f"Model: {data['model']}")
        print(f"Content: {data['choices'][0]['message']['content']}")
        print(f"Usage: {data['usage']}")


async def test_provider_routing() -> None:
    """Test provider routing with headers."""
    async with httpx.AsyncClient() as client:
        print("\nTesting provider routing...")
        
        request_data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "Test provider routing"}
            ]
        }
        
        # Test with specific provider
        headers = {"X-Provider-Priority": "mock_openai"}
        response = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json=request_data,
            headers=headers,
            timeout=30.0
        )
        
        assert response.status_code == 200, f"OpenAI provider routing failed: {response.text}"
        data = response.json()
        assert "choices" in data and len(data["choices"]) > 0, "Response should contain choices"
        assert "message" in data["choices"][0], "Choice should contain message"
        assert "content" in data["choices"][0]["message"], "Message should contain content"
        print(f"OpenAI provider response: {data['choices'][0]['message']['content']}")
        
        # Test with different provider
        headers = {"X-Provider-Priority": "mock_vllm"}
        response = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json=request_data,
            headers=headers,
            timeout=30.0
        )
        
        assert response.status_code == 200, f"vLLM provider routing failed: {response.text}"
        data = response.json()
        assert "choices" in data and len(data["choices"]) > 0, "Response should contain choices"
        assert "message" in data["choices"][0], "Choice should contain message"
        assert "content" in data["choices"][0]["message"], "Message should contain content"
        print(f"vLLM provider response: {data['choices'][0]['message']['content']}")


async def test_request_id_propagation() -> None:
    """Test request ID propagation."""
    async with httpx.AsyncClient() as client:
        print("\nTesting request ID propagation...")
        
        request_data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "Test request ID"}
            ]
        }
        
        # Test with custom request ID
        custom_request_id = "test-req-12345"
        headers = {"X-Request-ID": custom_request_id}
        
        response = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json=request_data,
            headers=headers,
            timeout=30.0
        )
        
        assert response.status_code == 200, f"Request ID propagation test failed: {response.text}"
        
        # Assert that the request ID was propagated in the response header
        assert response.headers.get('X-Request-ID') == custom_request_id, f"Request ID not propagated in header. Expected: {custom_request_id}, Got: {response.headers.get('X-Request-ID')}"
        
        data = response.json()
        print(f"Custom request ID preserved: {custom_request_id}")
        print(f"Response ID: {data['id']}")


async def main() -> int:
    """Run all tests."""
    print("SRE Inference Gateway Test Suite")
    print("=" * 40)
    
    try:
        await test_health_endpoints()
        await test_chat_completion()
        await test_provider_routing()
        await test_request_id_propagation()
        
        print("\n" + "=" * 40)
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"\nTest failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)