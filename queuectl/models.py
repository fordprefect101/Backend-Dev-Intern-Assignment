"""
Data models for the job queue system.
"""
from datetime import datetime
from typing import Optional


class Job:
    """
    Represents a job in the queue system.

    Attributes:
        id: Unique identifier for the job
        command: Shell command to execute
        state: Current state (pending, processing, completed, failed, dead)
        attempts: Number of times job has been attempted
        max_retries: Maximum number of retry attempts allowed
        created_at: When the job was created
        updated_at: When the job was last updated
    """

    def __init__(
        self,
        id: str,
        command: str,
        state: str = "pending",
        attempts: int = 0,
        max_retries: int = 3,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None
    ):
        self.id = id
        self.command = command
        self.state = state
        self.attempts = attempts
        self.max_retries = max_retries
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()

    def to_dict(self):
        """Convert Job to dictionary for storage."""
        return {
            'id': self.id,
            'command': self.command,
            'state': self.state,
            'attempts': self.attempts,
            'max_retries': self.max_retries,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create Job from dictionary (from database)."""
        return cls(
            id=data['id'],
            command=data['command'],
            state=data['state'],
            attempts=data['attempts'],
            max_retries=data['max_retries'],
            created_at=data['created_at'],
            updated_at=data['updated_at']
        )

    def __repr__(self):
        return f"Job(id={self.id}, command={self.command}, state={self.state})"
