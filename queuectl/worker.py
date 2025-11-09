"""
Worker process logic for executing jobs from the queue.
"""
import subprocess
import time
import signal
import sys
from typing import Optional, Dict, Any
from queuectl.storage import Storage


class Worker:
    """
    Worker that processes jobs from the queue.

    The worker continuously polls the database for pending jobs,
    executes their commands, and updates their state based on results.
    """

    def __init__(self, worker_id: str = "worker-1"):
        """
        Initialize the worker.

        Args:
            worker_id: Unique identifier for this worker
        """
        self.worker_id = worker_id
        self.storage = Storage()
        self.running = True  # Flag to control worker loop

        print(f"Worker {self.worker_id} initialized")

    def get_next_pending_job(self) -> Optional[Dict[str, Any]]:
        """
        Get the next pending job from the queue.

        PRODUCTION: Uses atomic locking to prevent race conditions.
        Multiple workers can safely call this simultaneously.

        Returns:
            Job dictionary if claimed, None if no pending jobs
        """
        # Use atomic claim_next_job for race-condition-free claiming
        # This ensures only ONE worker gets each job, even with multiple workers
        return self.storage.claim_next_job(self.worker_id)

    def mark_as_processing(self, job_id: str) -> None:
        """
        Mark a job as currently being processed.

        Args:
            job_id: The job ID to update
        """
        self.storage.update_job(job_id, {'state': 'processing'})

    def mark_as_completed(self, job_id: str) -> None:
        """
        Mark a job as successfully completed and release the lock.

        Args:
            job_id: The job ID to update
        """
        self.storage.update_job(job_id, {
            'state': 'completed',
            'locked_by': None,  # Clear lock
            'locked_at': None   # Clear lock timestamp
        })

    def should_retry(self, attempts: int, max_retries: int) -> bool:
        """
        Determine if a failed job should be retried.

        Args:
            attempts: Current number of attempts (already completed)
            max_retries: Maximum number of retry attempts allowed

        Returns:
            True if job should retry (attempts < max_retries)
            False if job should go to DLQ (attempts >= max_retries)

        Example:
            max_retries = 3
            attempts = 0 -> should_retry = True  (can retry 3 times)
            attempts = 1 -> should_retry = True  (can retry 2 more times)
            attempts = 2 -> should_retry = True  (can retry 1 more time)
            attempts = 3 -> should_retry = False (out of retries, go to DLQ)
        """
        return attempts < max_retries

    def mark_as_failed(self, job_id: str, attempts: int, max_retries: int) -> None:
        """
        Mark a job as failed and decide whether to retry or send to DLQ.

        Uses retry logic with exponential backoff:
        - If attempts < max_retries: Set state to 'pending' (retry) with delay
        - If attempts >= max_retries: Set state to 'dead' (DLQ)

        Exponential backoff formula: delay = backoff_base ^ attempts seconds

        Args:
            job_id: The job ID to update
            attempts: Current number of attempts (will be incremented)
            max_retries: Maximum retry attempts allowed
        """
        from datetime import datetime, timezone, timedelta

        new_attempts = attempts + 1

        # Decide: Retry or DLQ?
        if self.should_retry(new_attempts, max_retries):
            # Still have retries left - set back to pending for retry
            new_state = 'pending'

            # Calculate exponential backoff delay
            # Formula: delay = initial_delay * (base ^ attempts) seconds
            backoff_base = int(self.storage.get_config('backoff-base', '2'))
            initial_delay = int(self.storage.get_config('backoff-initial-delay', '1'))
            delay_seconds = initial_delay * (backoff_base ** new_attempts)

            # Calculate next retry time
            next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)

            print(f"  → Job will retry (attempt {new_attempts}/{max_retries})")
            print(f"  → Retry scheduled in {delay_seconds} seconds (at {next_retry_at.strftime('%H:%M:%S')})")

            # Update with retry scheduling
            self.storage.update_job(job_id, {
                'state': new_state,
                'attempts': new_attempts,
                'next_retry_at': next_retry_at.isoformat(),
                'locked_by': None,   # Release the lock
                'locked_at': None    # Clear lock timestamp
            })
        else:
            # Out of retries - send to Dead Letter Queue
            new_state = 'dead'
            print(f"  → Job sent to DLQ (max retries {max_retries} exceeded)")

            # Update to DLQ (no retry scheduling needed)
            self.storage.update_job(job_id, {
                'state': new_state,
                'attempts': new_attempts,
                'next_retry_at': None,
                'locked_by': None,   # Release the lock
                'locked_at': None    # Clear lock timestamp
            })

    def execute_command(self, command: str, job_id: str) -> int:
        """
        Execute a shell command and return its exit code.

        CRITICAL: This is the core assignment requirement!
        - Exit code 0 = success (job should be marked completed)
        - Exit code non-zero = failure (job should be marked failed)

        Args:
            command: The shell command to execute
            job_id: The job ID (for logging)

        Returns:
            Exit code (0 = success, non-zero = failure)
        """
        print(f"[{job_id}] Executing command: {command}")

        try:
            # Execute the command using subprocess.run()
            result = subprocess.run(
                command,
                shell=True,              # Allow shell syntax (pipes, redirects, etc.)
                capture_output=True,     # Capture stdout and stderr
                text=True,               # Return output as string (not bytes)
                timeout=300              # 5 minute timeout (can be configured later)
            )

            # Log the output
            if result.stdout:
                print(f"[{job_id}] STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"[{job_id}] STDERR:\n{result.stderr}")

            # CRITICAL: Return the exit code
            print(f"[{job_id}] Exit code: {result.returncode}")
            return result.returncode

        except subprocess.TimeoutExpired:
            print(f"[{job_id}] ERROR: Command timed out after 300 seconds")
            return 124  # Standard timeout exit code

        except Exception as e:
            print(f"[{job_id}] ERROR: Failed to execute command: {e}")
            return 1  # Generic failure exit code

    def run(self) -> None:
        """
        Main worker loop.

        Continuously processes jobs until stopped.
        Polls the database for pending jobs every second.
        """
        # Set up signal handlers for graceful shutdown
        self.setup_signal_handlers()

        print(f"Worker {self.worker_id} started. Waiting for jobs...")
        print("Press Ctrl+C to stop gracefully.\n")

        while self.running:
            try:
                # Step 1: Atomically claim next pending job
                # This uses database locking - safe with multiple workers!
                job = self.get_next_pending_job()

                if job:
                    # Job is now locked by us (state='processing', locked_by=worker_id)
                    print(f"→ [{self.worker_id}] Claimed job: {job['id']}")

                    # Step 2: Execute the command
                    exit_code = self.execute_command(job['command'], job['id'])

                    # Step 3: Update job state based on exit code
                    if exit_code == 0:
                        # Success!
                        self.mark_as_completed(job['id'])
                        print(f"✓ [{self.worker_id}] Job {job['id']} completed successfully\n")
                    else:
                        # Failed!
                        self.mark_as_failed(job['id'], job['attempts'], job['max_retries'])
                        print(f"✗ [{self.worker_id}] Job {job['id']} failed with exit code {exit_code}")
                        print()  # Blank line for readability

                else:
                    # No jobs available - wait before polling again
                    time.sleep(1)  # Poll every 1 second

            except KeyboardInterrupt:
                # User pressed Ctrl+C
                print("\n^C received, shutting down gracefully...")
                self.shutdown()
                break

            except Exception as e:
                # Handle unexpected errors without crashing
                print(f"ERROR: Unexpected error in worker loop: {e}")
                time.sleep(1)  # Wait before continuing

        print(f"Worker {self.worker_id} stopped.")

    def setup_signal_handlers(self) -> None:
        """
        Set up signal handlers for graceful shutdown.

        Handles SIGINT (Ctrl+C) and SIGTERM (kill command).
        """
        def signal_handler(signum, frame):
            """Handle shutdown signals gracefully."""
            signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
            print(f"\n{signal_name} received, shutting down gracefully...")
            self.shutdown()

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # kill command

    def shutdown(self) -> None:
        """
        Gracefully shutdown the worker.
        """
        print(f"\nShutting down worker {self.worker_id}...")
        self.running = False
