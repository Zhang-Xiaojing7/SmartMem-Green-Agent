"""A2A Smoke Test - Test Green Agent evaluating Fake Purple Agent."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
import json
import uuid

GREEN_AGENT_URL = "http://127.0.0.1:9009"
# Note: BaselineAgent internally appends "/a2a" to the URL, so we just provide the base URL
FAKE_PURPLE_URL = "http://127.0.0.1:9010"


def main():
    print("=" * 60)
    print("A2A Smoke Test: Green Agent -> Fake Purple Agent")
    print("=" * 60)

    # Check if servers are up
    try:
        resp = requests.get(f"{GREEN_AGENT_URL}/.well-known/agent.json", timeout=3)
        print(f"[OK] Green Agent is up: {resp.status_code}")
    except Exception as e:
        print(f"[FAIL] Green Agent not reachable: {e}")
        print("请先启动 Green Agent: python src/server.py")
        return

    try:
        # Simple health check to fake purple (use /a2a endpoint)
        resp = requests.post(f"{FAKE_PURPLE_URL}/a2a", json={"method": "health"}, timeout=3)
        print(f"[OK] Fake Purple is up: {resp.status_code}")
    except Exception as e:
        print(f"[FAIL] Fake Purple not reachable: {e}")
        print("请先启动 Fake Purple: python scripts/fake_purple_server.py")
        return

    # Send eval request to Green Agent
    print("\n>>> Sending Smoke Eval Request to Green Agent...")

    # EvalRequest format expected by Agent.run():
    # { "participants": {"purple_agent": "<url>"}, "config": {"mode": "smoke", ...} }
    eval_payload = {
        "participants": {
            "purple_agent": FAKE_PURPLE_URL
        },
        "config": {
            "mode": "smoke",
            "agent_type": "a2a"
        }
    }

    # Use message/send method (A2A SDK standard) with required messageId
    eval_request = {
        "jsonrpc": "2.0",
        "id": "smoke-test-1",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": str(uuid.uuid4()),
                "role": "user",
                "parts": [
                    {
                        "text": json.dumps(eval_payload)
                    }
                ]
            }
        }
    }

    # POST to root "/" (A2A SDK convention, not "/a2a")
    resp = requests.post(f"{GREEN_AGENT_URL}/", json=eval_request, timeout=60)
    print(f"Response status: {resp.status_code}")
    print(f"Response text: {resp.text[:500] if resp.text else '(empty)'}")
    
    if not resp.text:
        print("[ERROR] Empty response from Green Agent!")
        return
        
    result = resp.json()

    print(f"\n>>> Initial Response:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Check for error response
    if "error" in result:
        print(f"\n[ERROR] {result['error']}")
        return

    # Poll for completion if working
    task = result.get("result", {})
    task_id = task.get("id")

    if task_id and task.get("status", {}).get("state") == "working":
        print("\n>>> Task is working, polling for completion...")
        import time
        for i in range(30):  # Poll for up to 30 seconds
            time.sleep(1)
            poll_req = {
                "jsonrpc": "2.0",
                "id": f"poll-{i}",
                "method": "tasks/get",
                "params": {"id": task_id}
            }
            resp = requests.post(f"{GREEN_AGENT_URL}/", json=poll_req, timeout=10)
            poll_result = resp.json()
            state = poll_result.get("result", {}).get("status", {}).get("state")
            print(f"  Poll {i+1}: state={state}")
            if state in ("completed", "failed", "canceled"):
                result = poll_result
                break

    # Print final result
    print("\n" + "=" * 60)
    print("Final Result:")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
