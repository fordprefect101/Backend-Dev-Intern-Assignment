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
        # Create jobs table with locking fields for multi-worker support
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                command TEXT NOT NULL,
                state TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                locked_by TEXT,
                locked_at TEXT
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

        # Migrate existing database: Add locking columns if they don't exist
        self._migrate_add_locking_fields(conn)

        conn.commit()

    def _migrate_add_locking_fields(self, conn: sqlite3.Connection):
        """
        Migration: Add locking fields to existing jobs table.

        This handles databases created before Phase 6.
        Safely adds locked_by and locked_at columns if they don't exist.
        """
        # Check if locked_by column exists
        cursor = conn.execute("PRAGMA table_info(jobs)")
        columns = [row[1] for row in cursor.fetchall()]

        # Add locked_by if missing
        if 'locked_by' not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN locked_by TEXT")

        # Add locked_at if missing
        if 'locked_at' not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN locked_at TEXT")

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
                SELECT id, command, state, attempts, max_retries, created_at, updated_at, locked_by, locked_at
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
            SELECT id, command, state, attempts, max_retries, created_at, updated_at, locked_by, locked_at
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

    def claim_next_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Atomically claim the next pending job for a worker.

        PRODUCTION-GRADE: Race condition safe!
        Uses database transactions to ensure only ONE worker claims each job.

        Args:
            worker_id: Unique identifier for the worker claiming the job

        Returns:
            Job dictionary if claimed, None if no jobs available

        How it works:
            1. Start a transaction with BEGIN IMMEDIATE (locks database)
            2. Find first pending job that is NOT locked
            3. Atomically update it with worker_id and lock timestamp
            4. Return the job to the worker
            5. If another worker already claimed it, this returns None

        Example:
            job = storage.claim_next_job('worker-1')
            if job:
                print(f"Claimed job {job['id']}")
            else:
                print("No jobs available")
        """
        from datetime import datetime, timezone

        with self._get_connection() as conn:
            # Start an immediate transaction - locks the database
            conn.execute("BEGIN IMMEDIATE")

            try:
                # Find first pending job that isn't locked
                cursor = conn.execute("""
                    SELECT id, command, state, attempts, max_retries, created_at, updated_at, locked_by, locked_at
                    FROM jobs
                    WHERE state = 'pending' AND locked_by IS NULL
                    ORDER BY created_at ASC
                    LIMIT 1
                """)

                row = cursor.fetchone()

                if not row:
                    # No jobs available
                    conn.commit()
                    return None

                job = dict(row)

                # Atomically claim the job by updating lock fields
                now = datetime.now(timezone.utc).isoformat()
                conn.execute("""
                    UPDATE jobs
                    SET state = 'processing',
                        locked_by = ?,
                        locked_at = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (worker_id, now, now, job['id']))

                conn.commit()

                # Update the job dict with new values
                job['state'] = 'processing'
                job['locked_by'] = worker_id
                job['locked_at'] = now
                job['updated_at'] = now

                return job

            except Exception:
                conn.rollback()
                raise

    def set_config(self, key: str, value: str) -> None:
        """
        Store a configuration value.

        Args:
            key: Configuration key (e.g., 'max-retries', 'backoff-base')
            value: Configuration value (stored as string)

        Example:
            storage.set_config('max-retries', '5')
            storage.set_config('backoff-base', '2')
        """
        with self._get_connection() as conn:
            # Use INSERT OR REPLACE to update existing or insert new
            conn.execute("""
                INSERT OR REPLACE INTO config (key, value)
                VALUES (?, ?)
            """, (key, value))

    def get_config(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a configuration value.

        Args:
            key: Configuration key to retrieve
            default: Default value if key not found

        Returns:
            Configuration value if found, default otherwise

        Example:
            max_retries = storage.get_config('max-retries', '3')
            backoff_base = storage.get_config('backoff-base', '2')
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT value FROM config
                WHERE key = ?
            """, (key,))

            row = cursor.fetchone()

            if row:
                return row['value']
            return default

    def list_config(self) -> Dict[str, str]:
        """
        List all configuration key-value pairs.

        Returns:
            Dictionary of all config keys and values

        Example:
            config = storage.list_config()
            for key, value in config.items():
                print(f"{key} = {value}")
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT key, value FROM config ORDER BY key")
            rows = cursor.fetchall()

            return {row['key']: row['value'] for row in rows}

    def get_job_counts(self) -> Dict[str, int]:
        """
        Get count of jobs by state.

        Returns:
            Dictionary mapping state to count
            Example: {'pending': 5, 'processing': 2, 'completed': 100, 'failed': 3, 'dead': 1}
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT state, COUNT(*) as count
                FROM jobs
                GROUP BY state
                ORDER BY state
            """)
            rows = cursor.fetchall()

            # Create dict with all states initialized to 0
            counts = {
                'pending': 0,
                'processing': 0,
                'completed': 0,
                'failed': 0,
                'dead': 0
            }

            # Update with actual counts
            for row in rows:
                counts[row['state']] = row['count']

            return counts
