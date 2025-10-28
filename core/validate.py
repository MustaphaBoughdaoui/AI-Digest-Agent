from __future__ import annotations

import logging
from typing import Dict, List

from .types import (
    AnswerResponse,
    ValidationIssue,
    ValidationIssueSeverity,
    ValidationReport,
)

logger = logging.getLogger(__name__)


def validate_answer(answer: AnswerResponse) -> ValidationReport:
    issues: List[ValidationIssue] = []
    label_to_source: Dict[str, bool] = {citation.label: True for citation in answer.sources}
    covered_bullets = 0

    for idx, bullet in enumerate(answer.bullets):
        if not bullet.citations:
            issues.append(
                ValidationIssue(
                    message="Bullet missing citation.",
                    severity=ValidationIssueSeverity.ERROR,
                    bullet_index=idx,
                )
            )
            continue
        unknown = [label for label in bullet.citations if label not in label_to_source]
        if unknown:
            issues.append(
                ValidationIssue(
                    message=f"Bullet references unknown citations: {unknown}",
                    severity=ValidationIssueSeverity.ERROR,
                    bullet_index=idx,
                )
            )
        else:
            covered_bullets += 1

    coverage = covered_bullets / max(len(answer.bullets), 1)
    passed = coverage >= 0.95
    if not passed:
        logger.info("Validation coverage %.2f below threshold.", coverage)
    return ValidationReport(
        passed=passed,
        coverage=coverage,
        issues=issues,
    )
