"""Evaluation-specific data types for LLM evaluation dataset generation"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class EvaluationItem:
    """
    A single evaluation item in the evaluation dataset.
    """
    id: str
    type: str  # knowledge_coverage, reasoning_ability, factual_accuracy, comprehensive
    difficulty: str  # easy, medium, hard
    question: str
    reference_answer: str
    evaluation_criteria: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    distractors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "id": self.id,
            "type": self.type,
            "difficulty": self.difficulty,
            "question": self.question,
            "reference_answer": self.reference_answer,
            "evaluation_criteria": self.evaluation_criteria,
            "metadata": self.metadata,
            "distractors": self.distractors,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "EvaluationItem":
        """Create from dictionary"""
        return EvaluationItem(
            id=data.get("id", ""),
            type=data.get("type", ""),
            difficulty=data.get("difficulty", "medium"),
            question=data.get("question", ""),
            reference_answer=data.get("reference_answer", ""),
            evaluation_criteria=data.get("evaluation_criteria", {}),
            metadata=data.get("metadata", {}),
            distractors=data.get("distractors", []),
        )


@dataclass
class DifficultyScore:
    """
    Difficulty score for an evaluation item.
    """
    level: str  # easy, medium, hard
    score: float  # 0.0 - 1.0
    reasoning: str
    factors: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "level": self.level,
            "score": self.score,
            "reasoning": self.reasoning,
            "factors": self.factors,
        }


@dataclass
class QualityScore:
    """
    Quality score for an evaluation item.
    """
    score: float  # 0.0 - 1.0
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    is_valid: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "score": self.score,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "is_valid": self.is_valid,
        }


@dataclass
class EvaluationDataset:
    """
    A complete evaluation dataset.
    """
    name: str
    description: str
    items: List[EvaluationItem] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_item(self, item: EvaluationItem) -> None:
        """Add an evaluation item"""
        self.items.append(item)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate statistics for the dataset"""
        if not self.items:
            return {}
        
        type_counts = {}
        difficulty_counts = {}
        
        for item in self.items:
            type_counts[item.type] = type_counts.get(item.type, 0) + 1
            difficulty_counts[item.difficulty] = difficulty_counts.get(item.difficulty, 0) + 1
        
        total = len(self.items)
        
        return {
            "total_items": total,
            "type_distribution": {k: v / total for k, v in type_counts.items()},
            "difficulty_distribution": {k: v / total for k, v in difficulty_counts.items()},
            "type_counts": type_counts,
            "difficulty_counts": difficulty_counts,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "name": self.name,
            "description": self.description,
            "items": [item.to_dict() for item in self.items],
            "statistics": self.get_statistics(),
            "metadata": self.metadata,
        }
