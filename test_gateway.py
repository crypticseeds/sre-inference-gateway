#!/usr/bin/env python3
"""Simple test script for the SRE Inference Gateway."""

import asyncio
import json
import time
from typing import Dict, Any

import httpx


async def test_health_endpoints() -> None:
    """Test health and readiness endpoints."""
    async with httpx.AsyncClient() as client:
        print("Testing health endpoints...")
        
        # Health check
        response = await client.get("http://localhost:8000/v1/health")
        print(f"Health: {response.status_code} - {response.json()}")
        
        # Readiness check
        response = await client.get("http://localhost:8000/v1/ready")
        print(f"Ready: {response.status_code} - {response.json()}")


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
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response ID: {data['id']}")
            print(f"Model: {data['model']}")
            print(f"Content: {data['choices'][0]['message']['content']}")
            print(f"Usage: {data['usage']}")
        else:
            print(f"Error: {response.text}")


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
        
        if response.status_code == 200:
            data = response.json()
            print(f"OpenAI provider response: {data['choices'][0]['message']['content']}")
        
        # Test with different provider
        headers = {"X-Provider-Priority": "mock_vllm"}
        response = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json=request_data,
            headers=headers,
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
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
        
        if response.status_code == 200:
            data = response.json()
            print(f"Custom request ID preserved: {custom_request_id}")
            print(f"Response ID: {data['id']}")


async def main() -> None:
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