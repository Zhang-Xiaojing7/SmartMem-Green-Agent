import json
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from agent import Agent

if __name__ == "__main__":
    ag = Agent()
    res = ag._smoke_run(None, agent_type='mock')
    print("SUMMARY:\n", res.get('summary'))
    print("PASS RATE:", res.get('pass_rate'))
    print("CHARTS:", res.get('chart_paths'))
    print('\nDETAILED RESULTS:')
    for r in res.get('results', []):
        try:
            # dataclass EvalResult
            print(f"- instruction: {r.instruction[:80]} | passed: {r.passed} | score: {r.score}")
        except Exception:
            print(f"- {r}")
    
    print('\nReturn object keys:', list(res.keys()))
