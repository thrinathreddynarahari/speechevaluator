"""Repository for evaluation database operations."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from models.evaluation import EmployeeEvaluation, EmployeeEvaluationReports

logger = logging.getLogger(__name__)


class EvaluationRepository:
    """Data access layer for evaluation-related database operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    def get_evaluation_by_employee_id(self, employee_id: int) -> EmployeeEvaluation | None:
        """Get existing evaluation record for an employee.

        Args:
            employee_id: The employee's ID.

        Returns:
            EmployeeEvaluation record if exists, None otherwise.
        """
        return (
            self.db.query(EmployeeEvaluation)
            .filter(EmployeeEvaluation.employee_id == employee_id)
            .first()
        )

    def create_evaluation(
        self,
        employee_id: int,
        feedback: str,
        created_by: int | None = None,
    ) -> EmployeeEvaluation:
        """Create a new evaluation record.

        Args:
            employee_id: The employee's ID.
            feedback: Transcription text to store.
            created_by: ID of user creating the record.

        Returns:
            The created EmployeeEvaluation record.
        """
        evaluation = EmployeeEvaluation(
            employee_id=employee_id,
            feedback=feedback,
            created_by=created_by,
            updated_by=created_by,
        )
        self.db.add(evaluation)
        self.db.flush()
        logger.info(
            "Created new evaluation record: id=%s for employee_id=%s",
            evaluation.id,
            employee_id,
        )
        return evaluation

    def update_evaluation_feedback(
        self,
        evaluation: EmployeeEvaluation,
        feedback: str,
        updated_by: int | None = None,
    ) -> EmployeeEvaluation:
        """Update the feedback on an existing evaluation record.

        Args:
            evaluation: The evaluation record to update.
            feedback: New transcription text.
            updated_by: ID of user updating the record.

        Returns:
            The updated EmployeeEvaluation record.
        """
        evaluation.feedback = feedback
        if updated_by:
            evaluation.updated_by = updated_by
        self.db.flush()
        logger.info(
            "Updated evaluation record: id=%s with new feedback",
            evaluation.id,
        )
        return evaluation

    def get_or_create_evaluation(
        self,
        employee_id: int,
        feedback: str,
        user_id: int | None = None,
    ) -> tuple[EmployeeEvaluation, bool]:
        """Get existing evaluation or create new one (upsert pattern).

        Args:
            employee_id: The employee's ID.
            feedback: Transcription text to store.
            user_id: ID of the current user for audit fields.

        Returns:
            Tuple of (evaluation record, was_created bool).
        """
        existing = self.get_evaluation_by_employee_id(employee_id)

        if existing:
            self.update_evaluation_feedback(existing, feedback, updated_by=user_id)
            return existing, False

        new_evaluation = self.create_evaluation(
            employee_id=employee_id,
            feedback=feedback,
            created_by=user_id,
        )
        return new_evaluation, True

    def create_evaluation_report(
        self,
        evaluation_id: UUID,
        report: dict[str, Any],
        created_by: int | None = None,
    ) -> EmployeeEvaluationReports:
        """Create a new evaluation report record.

        Args:
            evaluation_id: ID of the parent EmployeeEvaluation.
            report: The validated JSON report data.
            created_by: ID of user creating the record.

        Returns:
            The created EmployeeEvaluationReports record.
        """
        report_record = EmployeeEvaluationReports(
            employee_evaluation_id=evaluation_id,
            report=report,
            created_by=created_by,
            updated_by=created_by,
        )
        self.db.add(report_record)
        self.db.flush()
        logger.info(
            "Created evaluation report: id=%s for evaluation_id=%s",
            report_record.id,
            evaluation_id,
        )
        return report_record

    def get_evaluation_report_by_id(self, report_id: UUID) -> EmployeeEvaluationReports | None:
        """Get an evaluation report by its ID.

        Args:
            report_id: The report's UUID.

        Returns:
            EmployeeEvaluationReports record if exists, None otherwise.
        """
        return (
            self.db.query(EmployeeEvaluationReports)
            .filter(EmployeeEvaluationReports.id == report_id)
            .first()
        )

    def get_reports_for_evaluation(
        self,
        evaluation_id: UUID,
    ) -> list[EmployeeEvaluationReports]:
        """Get all reports for a given evaluation.

        Args:
            evaluation_id: The parent evaluation's UUID.

        Returns:
            List of EmployeeEvaluationReports records.
        """
        return (
            self.db.query(EmployeeEvaluationReports)
            .filter(EmployeeEvaluationReports.employee_evaluation_id == evaluation_id)
            .order_by(EmployeeEvaluationReports.created_at.desc())
            .all()
        )
