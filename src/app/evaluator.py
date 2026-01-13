"""
方案1：序列验证评分器
支持对比Agent发送的API请求序列与期望序列，以及最终状态验证
"""
from typing import List, Dict, Any, Tuple


class TurnEvaluator:
    """单个Turn的评分器"""
    
    def __init__(self, expected_action: List[Dict[str, Any]], expected_final_state: Dict[str, Any]):
        """
        初始化评分器
        
        Args:
            expected_action: 期望的API请求序列，例如：
                [
                  {"action": "update", "key": "light", "value": "on"},
                  {"action": "read", "key": "light"}
                ]
            expected_final_state: 期望的最终状态，例如：
                {"living_room_light": "on", "living_room_color": "warm"}
        """
        self.expected_action = expected_action
        self.expected_final_state = expected_final_state
    
    def evaluate(self, actual_action_sequence: List[Dict[str, Any]], actual_final_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        完整的Turn评分逻辑（方案1）
        
        Args:
            actual_action_sequence: Agent实际发送的API请求序列
            actual_final_state: 执行后的实际环境状态
        
        Returns:
            {
              "score": int (-1, 0, 1),
              "details": {
                "sequence_match": bool,
                "state_match": bool,
                "errors": List[str]
              },
              "message": str
            }
        """
        errors = []
        sequence_match = False
        state_match = False
        
        # Step 1: 序列验证
        sequence_match, seq_errors = self._verify_sequence(actual_action_sequence)
        errors.extend(seq_errors)
        
        if not sequence_match:
            return {
                "score": 0,
                "details": {
                    "sequence_match": False,
                    "state_match": None,
                    "errors": errors
                },
                "message": "Sequence mismatch: Agent's action sequence does not match expected sequence"
            }
        
        # Step 2: 状态验证
        state_match, state_errors = self._verify_state(actual_final_state)
        errors.extend(state_errors)
        
        score = 1 if state_match else 0
        message = "Perfect: Sequence and state both match" if score == 1 else "State mismatch: Final state does not match expected state"
        
        return {
            "score": score,
            "details": {
                "sequence_match": True,
                "state_match": state_match,
                "errors": errors
            },
            "message": message
        }
    
    def _verify_sequence(self, actual_sequence: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        验证请求序列是否完全匹配（顺序+内容）
        
        Returns:
            (是否匹配, 错误列表)
        """
        errors = []
        
        # 检查长度
        if len(actual_sequence) != len(self.expected_action):
            errors.append(
                f"Length mismatch: expected {len(self.expected_action)} actions, "
                f"got {len(actual_sequence)} actions"
            )
            return False, errors
        
        # 逐个检查每个请求
        for i, (expected, actual) in enumerate(zip(self.expected_action, actual_sequence)):
            if expected != actual:
                errors.append(
                    f"Action {i} mismatch: expected {expected}, got {actual}"
                )
                return False, errors
        
        return True, []
    
    def _verify_state(self, actual_state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证最终状态是否匹配（只检查expected中定义的字段）
        
        Returns:
            (是否匹配, 错误列表)
        """
        errors = []
        
        for key, expected_value in self.expected_final_state.items():
            if key not in actual_state:
                errors.append(f"Missing key in final state: {key}")
                return False, errors
            
            actual_value = actual_state[key]
            if actual_value != expected_value:
                errors.append(
                    f"State mismatch for '{key}': expected {expected_value}, "
                    f"got {actual_value}"
                )
                return False, errors
        
        return True, []


class ScenarioEvaluator:
    """整个Scenario的评分器"""
    
    def __init__(self, scenario_data: Dict[str, Any]):
        """
        初始化Scenario评分器
        
        Args:
            scenario_data: Scenario的定义，包含turns列表
        """
        self.scenario_data = scenario_data
        self.turns = scenario_data.get("turns", [])
    
    def evaluate_all_turns(self, actual_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        评分所有Turn
        
        Args:
            actual_results: 每个Turn的实际结果列表，每个元素包含：
                {
                  "turn_id": int,
                  "action_sequence": List[Dict],
                  "final_state": Dict
                }
        
        Returns:
            {
              "scenario_id": str,
              "total_score": int,
              "turn_scores": List[int],
              "turn_details": List[Dict],
              "summary": str
            }
        """
        turn_scores = []
        turn_details = []
        
        for i, turn_def in enumerate(self.turns):
            if i >= len(actual_results):
                turn_scores.append(0)
                turn_details.append({
                    "turn_id": turn_def["turn_id"],
                    "score": 0,
                    "message": "Missing actual result for this turn"
                })
                continue
            
            actual = actual_results[i]
            evaluator = TurnEvaluator(
                turn_def.get("expected_action", []),
                turn_def.get("expected_final_state", {})
            )
            
            result = evaluator.evaluate(
                actual.get("action_sequence", []),
                actual.get("final_state", {})
            )
            
            turn_scores.append(result["score"])
            turn_details.append({
                "turn_id": turn_def["turn_id"],
                "score": result["score"],
                "message": result["message"],
                "details": result["details"]
            })
        
        total_score = sum(turn_scores)
        max_score = len(self.turns)
        
        return {
            "scenario_id": self.scenario_data.get("scenario_id"),
            "total_score": total_score,
            "max_score": max_score,
            "turn_scores": turn_scores,
            "turn_details": turn_details,
            "summary": f"Scenario {self.scenario_data.get('scenario_id')}: {total_score}/{max_score}"
        }
