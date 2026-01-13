"""Fake Purple A2A-compatible server for testing.

Endpoints:
- POST /a2a : JSON-RPC entrypoint supporting methods `tasks/send` and `tasks/get`.

Behavior:
- tasks/send: accepts a JSON-RPC request with params.message.parts[*].text
  returns a task in 'working' state immediately and schedules completion shortly.
- tasks/get: returns the current task state and artifacts (when completed).

The server generates simple deterministic actions based on keywords in the input text
(e.g., "turn on living room light" -> {"action":"update","key":"living_room_light","value":"on"}).
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import uuid
import threading
import time
import json
from typing import Dict, Any

app = FastAPI()

# In-memory task store
TASKS: Dict[str, Dict[str, Any]] = {}


def _make_artifact_for_message(text: str) -> Dict[str, Any]:
    """Generate artifact parts based on simple heuristics in text."""
    parts = []

    # Echo text part
    parts.append({"text": f"I received: {text[:200]}"})

    # Simple pattern rules
    text_l = text.lower()

    actions = []
    if "turn on" in text_l and "living room" in text_l:
        actions.append({"action": "update", "key": "living_room_light", "value": "on"})
    if "turn off" in text_l and "living room" in text_l:
        actions.append({"action": "update", "key": "living_room_light", "value": "off"})
    if "ac" in text_l and "24" in text_l:
        actions.append({"action": "update", "key": "ac_temperature", "value": 24})
        actions.append({"action": "update", "key": "ac", "value": "on"})
    if "set the ac to" in text_l:
        # try to extract number
        import re
        m = re.search(r"set the ac to\s*(\d{2})", text_l)
        if m:
            val = int(m.group(1))
            actions.append({"action": "update", "key": "ac_temperature", "value": val})
            actions.append({"action": "update", "key": "ac", "value": "on"})

    # Add JSON lines for actions
    for act in actions:
        parts.append({"text": json.dumps(act, ensure_ascii=False)})

    # If no actions, we may return an empty actions array
    if not actions:
        parts.append({"text": json.dumps({"actions": []}, ensure_ascii=False)})

    return {"parts": parts}


@app.post("/a2a")
async def a2a_entry(request: Request):
    data = await request.json()
    method = data.get("method")
    params = data.get("params", {})
    req_id = data.get("id")

    if method == "tasks/send":
        message = params.get("message", {})
        # extract text from parts
        text = ""
        for p in message.get("parts", []):
            if isinstance(p, dict) and p.get("text"):
                text += p.get("text") + "\n"

        task_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        # initial working state
        TASKS[task_id] = {
            "id": task_id,
            "sessionId": session_id,
            "status": {"state": "working"},
            "artifacts": [],
            "message_text": text,
        }

        # schedule completion shortly
        def complete_task(tid=task_id, txt=text):
            time.sleep(0.6)
            TASKS[tid]["status"] = {"state": "completed"}
            TASKS[tid]["artifacts"] = [_make_artifact_for_message(txt)]

        threading.Thread(target=complete_task, daemon=True).start()

        result = TASKS[task_id].copy()
        # return a working status so client may poll
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": result})

    elif method == "tasks/get":
        params_id = params.get("id")
        task = TASKS.get(params_id)
        if not task:
            return JSONResponse({"jsonrpc": "2.0", "id": req_id, "error": "task not found"}, status_code=404)
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": task})

    else:
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "error": "unknown method"}, status_code=400)


if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=9010)
