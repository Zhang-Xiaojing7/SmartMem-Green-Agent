"""
Quick smoke test - just verify Green Agent receives EvalRequest correctly.
Short timeout to avoid long waits.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import json
import asyncio
import httpx

GREEN_AGENT_URL = "http://localhost:9010"
PURPLE_AGENT_URL = "http://localhost:9011"


async def quick_test():
    """Quick test with short timeout."""
    
    print("Quick smoke test...")
    
    # Check Green Agent
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{GREEN_AGENT_URL}/.well-known/agent.json")
            print(f"Green Agent: {resp.status_code}")
    except Exception as e:
        print(f"Green Agent error: {e}")
        return
    
    # Check Purple Agent
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{PURPLE_AGENT_URL}/.well-known/agent.json")
            print(f"Purple Agent: {resp.status_code}")
    except Exception as e:
        print(f"Purple Agent error: {e}")
        return
    
    print("\nBoth agents are running!")
    
    # Just send a simple message to Green Agent (not EvalRequest)
    from messenger import send_message
    
    try:
        outputs = await send_message(
            message="Hello, are you the Green Agent?",
            base_url=GREEN_AGENT_URL,
            timeout=30
        )
        print(f"\nGreen Agent response: {outputs.get('response', 'N/A')}")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    asyncio.run(quick_test())
