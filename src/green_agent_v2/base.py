from dataclasses import dataclass, field
from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field


@dataclass
class TestResult:
    """单个测试结果"""
    test_case: dict
    score: float  # 0.0 - 1.0
    max_score: float
    passed: bool
    errors: List[str] = field(default_factory=list)
    turn_details: List[dict] = field(default_factory=list)


@dataclass 
class DimensionStats:
    """维度统计"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    total_score: float = 0.0
    max_possible_score: float = 0.0
    
    @property
    def pass_rate(self) -> float:
        return self.passed / max(1, self.total)
    
    @property
    def avg_score(self) -> float:
        return self.total_score / max(1, self.max_possible_score)
    
    @property
    def weakness_score(self) -> float:
        """弱点分数：越高越弱 (0-1)"""
        return 1.0 - self.avg_score


@dataclass
class WeaknessProfile:
    """弱点画像"""
    # 按维度统计
    by_dimension: Dict[str, DimensionStats] = field(default_factory=dict)
    # 按难度统计
    by_difficulty: Dict[str, DimensionStats] = field(default_factory=dict)
    # 按设备统计
    by_device: Dict[str, DimensionStats] = field(default_factory=dict)
    # 失败用例列表
    failed_cases: List[TestResult] = field(default_factory=list)
    # 边界发现
    boundary_found: Dict[str, str] = field(default_factory=dict)  # dimension -> difficulty
    

class ExpectedAction(BaseModel):
    action: Literal["update"] = "update"
    key: str
    value: Any


class Turn(BaseModel):
    turn_id: int
    gm_instruction: str
    expected_agent_action: List[ExpectedAction] = Field(default_factory=list)
    expected_final_state: Dict[str, Any]


class TestCase(BaseModel):
    scenario_id: str
    difficulty: Literal["easy", "medium", "difficult"]
    dimension: str
    description: str
    initial_state: Dict[str, Any] = Field(default_factory=dict)
    turns: List[Turn]


class TestCaseDatabase(BaseModel):
    metadata: Dict[str, Any] = Field(default_factory=dict)
    test_cases: List[TestCase] = Field(default_factory=list)