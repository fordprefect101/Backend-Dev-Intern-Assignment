"""
SQLite storage layer for the job queue system.
"""
import sqlite3
import os
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class Storage:
    """
    Handles all database operations for the job queue.

    Uses SQLite for persistence with a simple schema:
    - jobs table: stores all job information
    - config table: stores system configuration
    """

    def __init__(self, db_path: str = "queue.db"):
        """
        Initialize storage with database path.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Create database and tables if they don't exist."""
        with self._get_connection() as conn:
            self._create_tables(conn)

    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections.

        This ensures connections are properly closed after use.
        Usage:
            with storage._get_connection() as conn:
                conn.execute(...)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
            conn.commit()  # Auto-commit on success
        except Exception:
            conn.rollback()  # Rollback on error
            raise
        finally:
            conn.close()  # Always close connection

    def _create_tables(self, conn: sqlite3.Connection):
        """
        Create database schema (tables).

        Creates two tables:
        1. jobs: stores job data
        2. config: stores configuration key-value pairs
        """
        # Create jobs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                command TEXT NOT NULL,
                state TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Create config table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Create index on state for faster queries
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_state
            ON jobs(state)
        """)

        conn.commit()

    def get_connection(self):
        """
        Public method to get a database connection.

        Returns a connection object that can be used for queries.
        Caller is responsible for closing the connection.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_job(self, job_data: Dict[str, Any]) -> None:
        """
        Save a new job to the database.

        Args:
            job_data: Dictionary containing job fields
                Required keys: id, command, state, created_at, updated_at
                Optional keys: attempts, max_retries

        Example:
            storage.create_job({
                'id': '123',
                'command': 'echo hello',
                'state': 'pending',
                'attempts': 0,
                'max_retries': 3,
                'created_at': '2024-01-01T00:00:00',
                'updated_at': '2024-01-01T00:00:00'
            })
        """
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO jobs (id, command, state, attempts, max_retries, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                job_data['id'],
                job_data['command'],
                job_data['state'],
                job_data.get('attempts', 0),
                job_data.get('max_retries', 3),
                job_data['created_at'],
                job_data['updated_at']
            ))

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a job from the database by its ID.

        Args:
            job_id: The unique identifier of the job

        Returns:
            Dictionary with job data if found, None if not found

        Example:
            job = storage.get_job('123')
            if job:
                print(f"Job command: {job['command']}")
            else:
                print("Job not found")
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, command, state, attempts, max_retries, created_at, updated_at
                FROM jobs
                WHERE id = ?
            """, (job_id,))

            row = cursor.fetchone()

            if row:
                # Convert sqlite3.Row to dictionary
                return dict(row)
            return None

    def update_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing job in the database.

        Args:
            job_id: The unique identifier of the job to update
            updates: Dictionary of fields to update (e.g., {'state': 'completed', 'attempts': 1})

        Returns:
            True if job was updated, False if job not found

        Example:
            # Update job state to completed
            storage.update_job('123', {'state': 'completed'})

            # Update multiple fields
            storage.update_job('123', {
                'state': 'failed',
                'attempts': 2
            })
        """
        if not updates:
            return False

        # Build the SET clause dynamically based on provided fields
        set_parts = []
        values = []

        for key, value in updates.items():
            set_parts.append(f"{key} = ?")
            values.append(value)

        # Always update the updated_at timestamp
        from datetime import datetime, timezone
        set_parts.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())

        # Add job_id as last parameter for WHERE clause
        values.append(job_id)

        sql = f"""
            UPDATE jobs
            SET {', '.join(set_parts)}
            WHERE id = ?
        """

        with self._get_connection() as conn:
            cursor = conn.execute(sql, values)
            return cursor.rowcount > 0  # Returns True if at least one row was updated

    def list_jobs(self, state: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List jobs from the database with optional filtering.

        Args:
            state: Optional filter by job state (e.g., 'pending', 'completed', 'failed')
            limit: Optional limit on number of jobs to return

        Returns:
            List of job dictionaries (empty list if no jobs found)

        Example:
            # Get all jobs
            all_jobs = storage.list_jobs()

            # Get only pending jobs
            pending_jobs = storage.list_jobs(state='pending')

            # Get first 10 completed jobs
            completed_jobs = storage.list_jobs(state='completed', limit=10)
        """
        sql = """
            SELECT id, command, state, attempts, max_retries, created_at, updated_at
            FROM jobs
        """
        params = []

        # Add WHERE clause if filtering by state
        if state:
            sql += " WHERE state = ?"
            params.append(state)

        # Add ORDER BY to get jobs in creation order
        sql += " ORDER BY created_at ASC"

        # Add LIMIT clause if specified
        if limit:
            sql += " LIMIT ?"
            params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

            # Convert all rows to dictionaries
            return [dict(row) for row in rows]
