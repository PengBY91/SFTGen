"""Difficulty scorer for evaluation items"""

from typing import Dict, Any
from graphgen.bases.eval_datatypes import EvaluationItem, DifficultyScore


class EvalDifficultyScorer:
    """
    Score the difficulty of evaluation items based on various factors.
    """
    
    def __init__(self):
        self.difficulty_thresholds = {
            "easy": (0.0, 0.4),
            "medium": (0.4, 0.7),
            "hard": (0.7, 1.0),
        }
    
    def score_difficulty(self, item: EvaluationItem) -> DifficultyScore:
        """
        Score the difficulty of an evaluation item.
        
        :param item: EvaluationItem to score
        :return: DifficultyScore object
        """
        factors = {}
        total_score = 0.0
        weight_sum = 0.0
        
        # Factor 1: Reasoning hops (for reasoning-based questions)
        reasoning_hops = item.metadata.get("reasoning_hops", 0)
        if reasoning_hops > 0:
            hop_score = min(reasoning_hops / 5.0, 1.0)  # Normalize to 0-1
            factors["reasoning_hops"] = hop_score
            total_score += hop_score * 0.3
            weight_sum += 0.3
        
        # Factor 2: Number of knowledge points
        knowledge_points = len(item.metadata.get("knowledge_nodes", []))
        if knowledge_points > 0:
            kp_score = min(knowledge_points / 10.0, 1.0)  # Normalize to 0-1
            factors["knowledge_points"] = kp_score
            total_score += kp_score * 0.2
            weight_sum += 0.2
        
        # Factor 3: Question length (longer questions tend to be more complex)
        question_length = len(item.question.split())
        length_score = min(question_length / 50.0, 1.0)  # Normalize to 0-1
        factors["question_length"] = length_score
        total_score += length_score * 0.15
        weight_sum += 0.15
        
        # Factor 4: Answer length (longer answers indicate more complex topics)
        answer_length = len(item.reference_answer.split())
        answer_score = min(answer_length / 100.0, 1.0)  # Normalize to 0-1
        factors["answer_length"] = answer_score
        total_score += answer_score * 0.15
        weight_sum += 0.15
        
        # Factor 5: Number of distractors (more distractors = harder to distinguish)
        distractor_count = len(item.distractors)
        if distractor_count > 0:
            distractor_score = min(distractor_count / 5.0, 1.0)
            factors["distractor_count"] = distractor_score
            total_score += distractor_score * 0.2
            weight_sum += 0.2
        
        # Normalize score
        if weight_sum > 0:
            final_score = total_score / weight_sum
        else:
            final_score = 0.5  # Default to medium if no factors
        
        # Determine difficulty level
        difficulty_level = self._score_to_level(final_score)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(factors, final_score, difficulty_level)
        
        return DifficultyScore(
            level=difficulty_level,
            score=final_score,
            reasoning=reasoning,
            factors=factors,
        )
    
    def _score_to_level(self, score: float) -> str:
        """Convert numeric score to difficulty level"""
        for level, (low, high) in self.difficulty_thresholds.items():
            if low <= score < high:
                return level
        return "hard"  # Default to hard if score >= 0.7
    
    def _generate_reasoning(
        self,
        factors: Dict[str, float],
        score: float,
        level: str
    ) -> str:
        """Generate human-readable reasoning for the difficulty score"""
        reasoning_parts = [f"Difficulty level: {level} (score: {score:.2f})"]
        
        if "reasoning_hops" in factors:
            reasoning_parts.append(
                f"Requires {int(factors['reasoning_hops'] * 5)} reasoning hops"
            )
        
        if "knowledge_points" in factors:
            reasoning_parts.append(
                f"Involves {int(factors['knowledge_points'] * 10)} knowledge points"
            )
        
        if "distractor_count" in factors:
            reasoning_parts.append(
                f"Has {int(factors['distractor_count'] * 5)} distractors"
            )
        
        return ". ".join(reasoning_parts)


def score_dataset_difficulty(items: list[EvaluationItem]) -> Dict[str, Any]:
    """
    Score difficulty for all items in a dataset and return statistics.
    
    :param items: list of EvaluationItem objects
    :return: dictionary with difficulty statistics
    """
    scorer = EvalDifficultyScorer()
    
    difficulty_counts = {"easy": 0, "medium": 0, "hard": 0}
    scores = []
    
    for item in items:
        difficulty_score = scorer.score_difficulty(item)
        item.difficulty = difficulty_score.level  # Update item difficulty
        difficulty_counts[difficulty_score.level] += 1
        scores.append(difficulty_score.score)
    
    total = len(items)
    avg_score = sum(scores) / total if total > 0 else 0
    
    return {
        "total_items": total,
        "average_difficulty_score": avg_score,
        "difficulty_distribution": {
            level: count / total for level, count in difficulty_counts.items()
        },
        "difficulty_counts": difficulty_counts,
    }
