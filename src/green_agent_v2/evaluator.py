from typing import List, Dict, Any, Tuple, Optional, Set
from .base import TestResult, WeaknessProfile, DimensionStats

# --- Constants ---

DIMENSIONS = ["precision", "ambiguous", "conflict", "memory", "noise"]

DEVICE_CONSTRAINTS = {
    # Living Room
    "living_room_light": {"type": "enum", "values": ["on", "off"]},
    "living_room_color": {"type": "enum", "values": ["white", "red", "blue", "warm"]},
    # Bedroom
    "bedroom_light": {"type": "enum", "values": ["on", "off"]},
    "bedroom_color": {"type": "enum", "values": ["white", "warm", "blue", "red"]},
    # Climate Control
    "ac": {"type": "enum", "values": ["on", "off"]},
    "ac_temperature": {"type": "int", "min": 16, "max": 30},
    "fan_speed": {"type": "enum", "values": ["off", "low", "medium", "high"]},
    # Entertainment & Security
    "music_volume": {"type": "int", "min": 0, "max": 10},
    "front_door_lock": {"type": "enum", "values": ["locked", "unlocked"]},
    "kitchen_light": {"type": "enum", "values": ["on", "off"]},
}

# --- Evaluators ---

class TurnEvaluator:
    """
    Evaluates a single turn (instruction -> action -> state change).
    """
    
    def __init__(self, expected_actions: List[Dict[str, Any]], expected_final_state: Dict[str, Any]):
        """
        Args:
            expected_actions: List of expected API calls (e.g., [{"action": "update", ...}]).
            expected_final_state: Dict of expected state values (e.g., {"light": "on"}).
        """
        self.expected_actions = expected_actions
        self.expected_final_state = expected_final_state
    
    def evaluate(self, actual_actions: List[Dict[str, Any]], actual_final_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compares actual execution against expectations.
        
        Returns:
            Dict containing score (1 or 0), status boolean, and error list.
        """
        errors = []
        
        # 1. Sequence Verification
        if len(actual_actions) != len(self.expected_actions):
            errors.append(f"Action count mismatch: expected {len(self.expected_actions)}, got {len(actual_actions)}")
        else:
            for i, (exp, act) in enumerate(zip(self.expected_actions, actual_actions)):
                if exp != act:
                    errors.append(f"Action #{i} mismatch: expected {exp}, got {act}")

        # If sequence failed, we can return early or continue based on strictness. 
        # Here we treat sequence failure as score 0.
        sequence_match = len(errors) == 0
        if not sequence_match:
             return self._build_result(0, sequence_match, False, errors, "Sequence mismatch")

        # 2. State Verification
        # Only verify keys present in expected_final_state
        state_match = True
        for key, exp_val in self.expected_final_state.items():
            act_val = actual_final_state.get(key)
            if act_val != exp_val:
                errors.append(f"State mismatch [{key}]: expected '{exp_val}', got '{act_val}'")
                state_match = False
        
        score = 1 if state_match else 0
        message = "Perfect" if score == 1 else "State mismatch"
        
        return self._build_result(score, sequence_match, state_match, errors, message)

    def _build_result(self, score: int, seq_match: bool, state_match: bool, errors: List[str], msg: str) -> Dict[str, Any]:
        """Helper to construct the return dictionary."""
        return {
            "score": score,
            "details": {
                "sequence_match": seq_match,
                "state_match": state_match,
                "errors": errors
            },
            "message": msg
        }


class WeaknessAnalyzer:
    """
    Analyzes test results to identify weaknesses in dimensions or devices.
    Used by AdaptiveEvaluator to maintain the global profile.
    """
    
    def __init__(self):
        self.profile = WeaknessProfile()
        self._init_stats()
    
    def _init_stats(self):
        """Initialize stats containers."""
        for dim in DIMENSIONS:
            self.profile.by_dimension[dim] = DimensionStats()
        for diff in ['easy', 'medium', 'difficult']:
            self.profile.by_difficulty[diff] = DimensionStats()
        for device in DEVICE_CONSTRAINTS.keys():
            self.profile.by_device[device] = DimensionStats()

    def update(self, result: Dict[str, Any], metadata: Dict[str, Any]):
        """
        Incrementally updates the profile with a single turn/case result.
        
        Args:
            result: The output from TurnEvaluator.evaluate()
            metadata: Context info like {'dimension': '...', 'difficulty': '...', 'involved_devices': [...]}
        """
        passed = result['score'] == 1
        score = result['score']
        
        # Helper to update a single stats object
        def _update_single_stat(stats_obj):
            stats_obj.total += 1
            stats_obj.total_score += score
            stats_obj.max_possible_score += 1 # Assuming 1 per turn
            if passed:
                stats_obj.passed += 1
            else:
                stats_obj.failed += 1

        # 1. Update Dimension Stats
        dim = metadata.get('dimension')
        if dim and dim in self.profile.by_dimension:
            _update_single_stat(self.profile.by_dimension[dim])
            
        # 2. Update Difficulty Stats
        diff = metadata.get('difficulty')
        if diff and diff in self.profile.by_difficulty:
            _update_single_stat(self.profile.by_difficulty[diff])
            
        # 3. Update Device Stats
        for device in metadata.get('involved_devices', []):
            if device in self.profile.by_device:
                _update_single_stat(self.profile.by_device[device])

    def get_profile(self) -> WeaknessProfile:
        return self.profile


class AdaptiveEvaluator:
    """
    Acts as a dynamic score tracker.
    It receives turn results from the Examiner, evaluates them, 
    and synchronizes global performance metrics in real-time.
    """
    
    def __init__(self):
        # Internal analyzer to track global stats
        self.analyzer = WeaknessAnalyzer()
        self.history: List[Dict[str, Any]] = []
    
    def evaluate_turn(
        self, 
        actual_actions: List[Dict[str, Any]], 
        actual_state: Dict[str, Any],
        expected_actions: List[Dict[str, Any]],
        expected_state: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates a single turn and updates global stats.
        
        Args:
            actual_actions: Actions performed by the agent.
            actual_state: Final state after execution.
            expected_actions: Expected actions (ground truth).
            expected_state: Expected final state (ground truth).
            metadata: Context dict, must include 'dimension', 'difficulty'. 
                      Can optionally include 'involved_devices'.
        
        Returns:
            The evaluation result for this turn.
        """
        # 1. Evaluate the specific turn
        evaluator = TurnEvaluator(expected_actions, expected_state)
        result = evaluator.evaluate(actual_actions, actual_state)
        
        # 2. Enrich result with metadata for the record
        full_record = {
            **result,
            "metadata": metadata,
            "index": len(self.history)
        }
        self.history.append(full_record)
        
        # 3. Synchronize global performance (Update Weakness Analyzer)
        # Ensure metadata has involved devices if not provided
        if 'involved_devices' not in metadata:
            metadata['involved_devices'] = self._extract_devices(expected_actions, expected_state)
            
        self.analyzer.update(result, metadata)
        
        return result

    def get_global_profile(self) -> WeaknessProfile:
        """Returns the current global weakness profile."""
        return self.analyzer.get_profile()

    def _extract_devices(self, actions: List[Dict], state: Dict) -> Set[str]:
        """Helper to identify devices involved in this turn."""
        devices = set()
        for action in actions:
            if 'key' in action:
                devices.add(action['key'])
        for key in state.keys():
            devices.add(key)
        return devices