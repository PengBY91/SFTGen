"""Quality checker for evaluation datasets"""

from typing import Dict, Any, List
from graphgen.bases.eval_datatypes import EvaluationItem, QualityScore


class EvalQualityChecker:
    """
    Check the quality of evaluation items and datasets.
    """
    
    def __init__(self):
        self.min_question_length = 5  # words
        self.min_answer_length = 3  # words
        self.max_question_length = 200  # words
        self.max_answer_length = 500  # words
    
    def check_item_quality(self, item: EvaluationItem) -> QualityScore:
        """
        Check the quality of a single evaluation item.
        
        :param item: EvaluationItem to check
        :return: QualityScore object
        """
        issues = []
        suggestions = []
        score = 1.0
        
        # Check question quality
        question_words = len(item.question.split())
        if question_words < self.min_question_length:
            issues.append(f"Question too short ({question_words} words)")
            score -= 0.2
            suggestions.append("Expand the question to be more specific")
        elif question_words > self.max_question_length:
            issues.append(f"Question too long ({question_words} words)")
            score -= 0.1
            suggestions.append("Simplify the question")
        
        # Check answer quality
        answer_words = len(item.reference_answer.split())
        if answer_words < self.min_answer_length:
            issues.append(f"Answer too short ({answer_words} words)")
            score -= 0.2
            suggestions.append("Provide a more detailed answer")
        elif answer_words > self.max_answer_length:
            issues.append(f"Answer too long ({answer_words} words)")
            score -= 0.1
            suggestions.append("Condense the answer")
        
        # Check if question ends with question mark
        if not item.question.strip().endswith("?") and not item.question.strip().endswith("？"):
            issues.append("Question doesn't end with a question mark")
            score -= 0.05
            suggestions.append("Add a question mark at the end")
        
        # Check if answer is not empty
        if not item.reference_answer.strip():
            issues.append("Answer is empty")
            score -= 0.5
            suggestions.append("Provide a reference answer")
        
        # Check evaluation criteria
        if not item.evaluation_criteria:
            issues.append("Missing evaluation criteria")
            score -= 0.1
            suggestions.append("Add evaluation criteria for scoring")
        
        # Check metadata
        if not item.metadata.get("knowledge_nodes"):
            issues.append("Missing knowledge node information")
            score -= 0.05
        
        # Ensure score is between 0 and 1
        score = max(0.0, min(1.0, score))
        
        # Determine if item is valid
        is_valid = score >= 0.5 and not any("empty" in issue.lower() for issue in issues)
        
        return QualityScore(
            score=score,
            issues=issues,
            suggestions=suggestions,
            is_valid=is_valid,
        )
    
    def check_dataset_quality(self, items: List[EvaluationItem]) -> Dict[str, Any]:
        """
        Check the quality of an entire evaluation dataset.
        
        :param items: list of EvaluationItem objects
        :return: dictionary with quality statistics and report
        """
        if not items:
            return {
                "total_items": 0,
                "valid_items": 0,
                "average_quality_score": 0.0,
                "issues_summary": {},
                "overall_quality": "poor",
            }
        
        quality_scores = []
        valid_count = 0
        all_issues = []
        
        for item in items:
            quality_score = self.check_item_quality(item)
            quality_scores.append(quality_score.score)
            if quality_score.is_valid:
                valid_count += 1
            all_issues.extend(quality_score.issues)
        
        # Calculate statistics
        avg_score = sum(quality_scores) / len(quality_scores)
        
        # Summarize issues
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        # Determine overall quality
        if avg_score >= 0.8:
            overall_quality = "excellent"
        elif avg_score >= 0.6:
            overall_quality = "good"
        elif avg_score >= 0.4:
            overall_quality = "fair"
        else:
            overall_quality = "poor"
        
        # Check diversity
        diversity_score = self._check_diversity(items)
        
        return {
            "total_items": len(items),
            "valid_items": valid_count,
            "invalid_items": len(items) - valid_count,
            "average_quality_score": avg_score,
            "quality_distribution": self._get_quality_distribution(quality_scores),
            "issues_summary": issue_counts,
            "top_issues": sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "overall_quality": overall_quality,
            "diversity_score": diversity_score,
        }
    
    def _get_quality_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Get distribution of quality scores"""
        distribution = {
            "excellent (0.8-1.0)": 0,
            "good (0.6-0.8)": 0,
            "fair (0.4-0.6)": 0,
            "poor (0.0-0.4)": 0,
        }
        
        for score in scores:
            if score >= 0.8:
                distribution["excellent (0.8-1.0)"] += 1
            elif score >= 0.6:
                distribution["good (0.6-0.8)"] += 1
            elif score >= 0.4:
                distribution["fair (0.4-0.6)"] += 1
            else:
                distribution["poor (0.0-0.4)"] += 1
        
        return distribution
    
    def _check_diversity(self, items: List[EvaluationItem]) -> float:
        """
        Check diversity of questions in the dataset.
        
        :param items: list of EvaluationItem objects
        :return: diversity score (0.0-1.0)
        """
        if not items:
            return 0.0
        
        # Check type diversity
        types = set(item.type for item in items)
        type_diversity = len(types) / 4.0  # Assuming 4 types max
        
        # Check difficulty diversity
        difficulties = set(item.difficulty for item in items)
        difficulty_diversity = len(difficulties) / 3.0  # Assuming 3 levels
        
        # Check question uniqueness (simple check based on first words)
        first_words = set(item.question.split()[0].lower() for item in items if item.question)
        uniqueness = min(len(first_words) / len(items), 1.0)
        
        # Combine scores
        diversity_score = (type_diversity + difficulty_diversity + uniqueness) / 3.0
        
        return diversity_score


def filter_low_quality_items(
    items: List[EvaluationItem],
    min_quality_score: float = 0.5
) -> List[EvaluationItem]:
    """
    Filter out low-quality evaluation items.
    
    :param items: list of EvaluationItem objects
    :param min_quality_score: minimum quality score threshold
    :return: filtered list of high-quality items
    """
    checker = EvalQualityChecker()
    filtered_items = []
    
    for item in items:
        quality_score = checker.check_item_quality(item)
        if quality_score.score >= min_quality_score and quality_score.is_valid:
            filtered_items.append(item)
    
    return filtered_items
