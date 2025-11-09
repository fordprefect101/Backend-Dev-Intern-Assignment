"""CLI command definitions for queuectl."""
import click
import json
import uuid
import multiprocessing
import time
from queuectl.models import Job
from queuectl.storage import Storage
from queuectl.worker import Worker


@click.group()
@click.version_option(version="0.1.0")
def main():
    """queuectl - CLI-based background job queue system."""
    pass


@main.command()
@click.argument('job_json', required=True)
def enqueue(job_json):
    """Add a new job to the queue.

    JOB_JSON: JSON string containing job data (e.g., '{"id":"job1","command":"sleep 2"}')
    """
    # Step 1: Parse JSON with error handling
    try:
        job_data = json.loads(job_json)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON - {e.msg}", err=True)
        click.echo(f"Position: line {e.lineno}, column {e.colno}", err=True)
        click.echo("\nExample of valid JSON:", err=True)
        click.echo('  {"command": "echo hello"}', err=True)
        raise click.Abort()

    # Check that we got a dictionary (not a list, string, etc.)
    if not isinstance(job_data, dict):
        click.echo("Error: JSON must be an object (dictionary), not a list or primitive value", err=True)
        click.echo("\nExample of valid JSON:", err=True)
        click.echo('  {"command": "echo hello"}', err=True)
        raise click.Abort()

    click.echo(f"✓ Successfully parsed JSON with {len(job_data)} field(s)")

    # Step 2: Validate required fields
    # Check if 'command' field exists
    if 'command' not in job_data:
        click.echo("Error: Missing required field 'command'", err=True)
        click.echo("\nThe 'command' field is required and must contain the shell command to execute.", err=True)
        click.echo("\nExample:", err=True)
        click.echo('  {"command": "echo hello"}', err=True)
        raise click.Abort()

    # Check if 'command' is not empty
    if not job_data['command'] or not str(job_data['command']).strip():
        click.echo("Error: Field 'command' cannot be empty", err=True)
        click.echo("\nThe 'command' field must contain a valid shell command.", err=True)
        click.echo("\nExample:", err=True)
        click.echo('  {"command": "echo hello"}', err=True)
        raise click.Abort()

    # Validate 'id' field if provided (must not be empty)
    if 'id' in job_data and (not job_data['id'] or not str(job_data['id']).strip()):
        click.echo("Error: Field 'id' cannot be empty", err=True)
        click.echo("\nIf you provide an 'id' field, it must not be empty.", err=True)
        click.echo("Tip: You can omit the 'id' field and one will be auto-generated.", err=True)
        raise click.Abort()

    # Validate 'priority' field if provided (must be 'high', 'medium', or 'low')
    valid_priorities = ['high', 'medium', 'low']
    if 'priority' in job_data:
        priority = str(job_data['priority']).lower()
        if priority not in valid_priorities:
            click.echo(f"Error: Invalid priority '{job_data['priority']}'", err=True)
            click.echo(f"\nPriority must be one of: {', '.join(valid_priorities)}", err=True)
            click.echo("\nExample:", err=True)
            click.echo('  {"command": "echo hello", "priority": "high"}', err=True)
            raise click.Abort()
        job_data['priority'] = priority  # Normalize to lowercase
    else:
        job_data['priority'] = 'medium'  # Default priority

    click.echo(f"✓ Validation passed")

    # Step 3: Generate UUID if 'id' not provided
    if 'id' not in job_data or not job_data['id']:
        job_data['id'] = str(uuid.uuid4())
        click.echo(f"✓ Generated job ID: {job_data['id']}")
    else:
        click.echo(f"✓ Using provided job ID: {job_data['id']}")

    click.echo(f"  Command: {job_data['command']}")

    # Step 4: Save job to database
    try:
        # Create Storage instance
        storage = Storage()

        # Create Job object with validated data
        job = Job(
            id=job_data['id'],
            command=job_data['command'],
            priority=job_data['priority'],
            state='pending',
            attempts=0,
            max_retries=job_data.get('max_retries', 3)  # Allow optional max_retries
        )

        # Save to database
        storage.create_job(job.to_dict())

        click.echo(f"\n✓ Job successfully enqueued!")
        click.echo(f"  Job ID: {job.id}")
        click.echo(f"  Priority: {job.priority}")
        click.echo(f"  State: {job.state}")
        click.echo(f"  Max Retries: {job.max_retries}")

    except Exception as e:
        click.echo(f"\nError: Failed to save job to database", err=True)
        click.echo(f"  {str(e)}", err=True)
        raise click.Abort()


@main.group()
def worker():
    """Manage worker processes."""
    pass


def worker_process_runner(worker_id: str):
    """
    Function to run a worker in a separate process.

    This is called by multiprocessing.Process() for each worker.

    Args:
        worker_id: Unique identifier for this worker
    """
    worker_instance = Worker(worker_id=worker_id)
    worker_instance.run()


@worker.command()
@click.option('--count', default=1, type=int, help='Number of workers to start')
def start(count):
    """Start one or more worker processes."""
    if count < 1:
        click.echo("Error: Count must be at least 1", err=True)
        raise click.Abort()

    if count > 10:
        click.echo("Warning: Starting more than 10 workers may cause performance issues.")
        if not click.confirm("Continue anyway?"):
            raise click.Abort()

    try:
        click.echo(f"Starting {count} worker(s)...\n")

        # Create a list to hold worker processes
        processes = []

        # Start worker processes
        for i in range(count):
            worker_id = f"worker-{i+1}"

            # Create a new process for this worker
            process = multiprocessing.Process(
                target=worker_process_runner,
                args=(worker_id,),
                name=worker_id
            )

            # Start the process
            process.start()
            processes.append(process)

            click.echo(f"✓ Started {worker_id} (PID: {process.pid})")

        click.echo(f"\n{count} worker(s) running. Press Ctrl+C to stop all workers.\n")

        # Wait for all processes to complete
        # This blocks until user presses Ctrl+C or workers exit
        try:
            for process in processes:
                process.join()  # Wait for process to finish
        except KeyboardInterrupt:
            click.echo("\n\nShutting down all workers...")

            # Terminate all worker processes
            for process in processes:
                if process.is_alive():
                    click.echo(f"  Stopping {process.name}...")
                    process.terminate()

            # Wait for all processes to terminate
            for process in processes:
                process.join(timeout=5)  # Wait up to 5 seconds

            click.echo("All workers stopped.")

    except Exception as e:
        click.echo(f"Error: Failed to start workers", err=True)
        click.echo(f"  {str(e)}", err=True)
        raise click.Abort()


@worker.command()
def stop():
    """Stop running workers gracefully."""
    click.echo("Stopping workers...")
    # TODO: Implement worker stop logic in Phase 6


@main.command()
def status():
    """Show summary of all job states & active workers."""
    try:
        storage = Storage()
        counts = storage.get_job_counts()

        # Calculate total
        total = sum(counts.values())

        click.echo("Job Queue Status")
        click.echo("=" * 50)
        click.echo("\nJobs by State:")
        click.echo(f"  Pending:     {counts['pending']:>6}")
        click.echo(f"  Processing:  {counts['processing']:>6}")
        click.echo(f"  Completed:   {counts['completed']:>6}")
        click.echo(f"  Failed:      {counts['failed']:>6}")
        click.echo(f"  Dead (DLQ):  {counts['dead']:>6}")
        click.echo("-" * 50)
        click.echo(f"  Total:       {total:>6}")

        # Show percentage if there are jobs
        if total > 0:
            click.echo("\nCompletion Rate:")
            completion_rate = (counts['completed'] / total) * 100
            click.echo(f"  {completion_rate:.1f}% ({counts['completed']}/{total})")

            if counts['dead'] > 0:
                failure_rate = (counts['dead'] / total) * 100
                click.echo(f"\nPermanent Failures:")
                click.echo(f"  {failure_rate:.1f}% ({counts['dead']}/{total})")

        # Show active work
        active_jobs = counts['pending'] + counts['processing']
        if active_jobs > 0:
            click.echo(f"\nActive/Pending Work: {active_jobs} job(s)")

            # Show priority breakdown for active jobs
            priority_counts = storage.get_priority_counts()
            priority_total = sum(priority_counts.values())
            if priority_total > 0:
                click.echo("\nActive Jobs by Priority:")
                click.echo(f"  High:        {priority_counts['high']:>6}")
                click.echo(f"  Medium:      {priority_counts['medium']:>6}")
                click.echo(f"  Low:         {priority_counts['low']:>6}")

        click.echo("=" * 50)

    except Exception as e:
        click.echo(f"Error: Failed to get status", err=True)
        click.echo(f"  {str(e)}", err=True)
        raise click.Abort()


@main.command()
@click.option('--state', type=click.Choice(['pending', 'processing', 'completed', 'failed', 'dead']),
              help='Filter jobs by state')
def list(state):
    """List jobs by state."""
    try:
        # Create Storage instance
        storage = Storage()

        # Query jobs with optional state filter
        jobs = storage.list_jobs(state=state)

        # Display header
        if state:
            click.echo(f"Jobs with state: {state}")
        else:
            click.echo("All jobs")
        click.echo("-" * 80)

        # Check if any jobs found
        if not jobs:
            click.echo("No jobs found.")
            return

        # Display each job
        for job in jobs:
            click.echo(f"\nJob ID: {job['id']}")
            click.echo(f"  Command: {job['command']}")
            click.echo(f"  Priority: {job.get('priority', 'medium')}")
            click.echo(f"  State: {job['state']}")
            click.echo(f"  Attempts: {job['attempts']}/{job['max_retries']}")
            click.echo(f"  Created: {job['created_at']}")
            click.echo(f"  Updated: {job['updated_at']}")

        # Show total count
        click.echo("-" * 80)
        click.echo(f"Total: {len(jobs)} job(s)")

    except Exception as e:
        click.echo(f"Error: Failed to list jobs", err=True)
        click.echo(f"  {str(e)}", err=True)
        raise click.Abort()


@main.group()
def dlq():
    """Manage Dead Letter Queue."""
    pass


@dlq.command(name='list')
def dlq_list():
    """List jobs in the Dead Letter Queue (permanently failed jobs)."""
    try:
        # Create Storage instance
        storage = Storage()

        # Query for dead jobs
        dead_jobs = storage.list_jobs(state='dead')

        # Display header
        click.echo("Dead Letter Queue (DLQ)")
        click.echo("=" * 80)
        click.echo("These jobs have failed permanently after exhausting all retries.\n")

        # Check if any jobs found
        if not dead_jobs:
            click.echo("No jobs in DLQ.")
            click.echo("\nTip: Jobs are sent to DLQ after failing max_retries times.")
            return

        # Display each dead job
        for job in dead_jobs:
            click.echo(f"\nJob ID: {job['id']}")
            click.echo(f"  Command: {job['command']}")
            click.echo(f"  Priority: {job.get('priority', 'medium')}")
            click.echo(f"  State: {job['state']}")
            click.echo(f"  Failed Attempts: {job['attempts']}/{job['max_retries']}")
            click.echo(f"  Created: {job['created_at']}")
            click.echo(f"  Last Updated: {job['updated_at']}")

        # Show total count
        click.echo("=" * 80)
        click.echo(f"Total jobs in DLQ: {len(dead_jobs)}")
        click.echo("\nTo retry a job: queuectl dlq retry <JOB_ID>")

    except Exception as e:
        click.echo(f"Error: Failed to list DLQ jobs", err=True)
        click.echo(f"  {str(e)}", err=True)
        raise click.Abort()


@dlq.command()
@click.argument('job_id', required=True)
def retry(job_id):
    """Retry a job from the Dead Letter Queue.

    Resets a dead job back to pending state so it can be retried by a worker.
    The job's attempt counter is reset to 0, giving it full retries again.

    JOB_ID: The ID of the job to retry

    Example:
      queuectl dlq retry abc-123
    """
    try:
        storage = Storage()

        # Check if job exists
        job = storage.get_job(job_id)

        if not job:
            click.echo(f"Error: Job '{job_id}' not found", err=True)
            raise click.Abort()

        # Check if job is in DLQ (dead state)
        if job['state'] != 'dead':
            click.echo(f"Error: Job '{job_id}' is not in Dead Letter Queue", err=True)
            click.echo(f"  Current state: {job['state']}", err=True)
            click.echo(f"\nOnly jobs in 'dead' state can be retried from DLQ.", err=True)
            click.echo(f"Use 'queuectl dlq list' to see jobs in DLQ.", err=True)
            raise click.Abort()

        # Show job info before retry
        click.echo(f"Job '{job_id}':")
        click.echo(f"  Command: {job['command']}")
        click.echo(f"  Previous attempts: {job['attempts']}/{job['max_retries']}")

        # Confirm retry
        if not click.confirm("\nRetry this job?"):
            click.echo("Cancelled.")
            raise click.Abort()

        # Reset job to pending state with attempts back to 0
        storage.update_job(job_id, {
            'state': 'pending',
            'attempts': 0,
            'locked_by': None,
            'locked_at': None
        })

        click.echo(f"\n✓ Job '{job_id}' has been reset and moved back to the queue")
        click.echo(f"  New state: pending")
        click.echo(f"  Attempts reset to: 0/{job['max_retries']}")
        click.echo(f"\nThe job will be picked up by the next available worker.")

    except Exception as e:
        click.echo(f"Error: Failed to retry job", err=True)
        click.echo(f"  {str(e)}", err=True)
        raise click.Abort()


@main.group()
def config():
    """Manage configuration."""
    pass


@config.command()
@click.argument('key', required=True)
@click.argument('value', required=True)
def set(key, value):
    """Set a configuration value.

    KEY: Configuration key (e.g., max-retries, backoff-base)
    VALUE: Configuration value

    Examples:
      queuectl config set max-retries 5
      queuectl config set backoff-base 2
    """
    try:
        storage = Storage()

        # Validate known config keys (optional - warn if unknown)
        known_keys = ['max-retries', 'backoff-base', 'backoff-initial-delay']
        if key not in known_keys:
            click.echo(f"Warning: '{key}' is not a standard config key.", err=True)
            click.echo(f"Known keys: {', '.join(known_keys)}", err=True)
            if not click.confirm("Set it anyway?"):
                raise click.Abort()

        # Store the config
        storage.set_config(key, value)

        click.echo(f"✓ Configuration updated:")
        click.echo(f"  {key} = {value}")

    except Exception as e:
        click.echo(f"Error: Failed to set configuration", err=True)
        click.echo(f"  {str(e)}", err=True)
        raise click.Abort()


@config.command()
@click.argument('key', required=True)
def get(key):
    """Get a configuration value.

    KEY: Configuration key to retrieve

    Examples:
      queuectl config get max-retries
      queuectl config get backoff-base
    """
    try:
        storage = Storage()

        # Define defaults for known keys
        defaults = {
            'max-retries': '3',
            'backoff-base': '2',
            'backoff-initial-delay': '1'
        }

        default = defaults.get(key)
        value = storage.get_config(key, default)

        if value:
            click.echo(f"{key} = {value}")

            # Show if it's the default
            if value == default and default:
                click.echo(f"  (default value)")
        else:
            click.echo(f"{key} is not set")
            if default:
                click.echo(f"  Default would be: {default}")

    except Exception as e:
        click.echo(f"Error: Failed to get configuration", err=True)
        click.echo(f"  {str(e)}", err=True)
        raise click.Abort()


@config.command(name='list')
def list_config():
    """List all configuration values."""
    try:
        storage = Storage()
        config = storage.list_config()

        if not config:
            click.echo("No configuration values set.")
            click.echo("\nDefaults:")
            click.echo("  max-retries = 3")
            click.echo("  backoff-base = 2")
            click.echo("  backoff-initial-delay = 1")
            return

        click.echo("Configuration:")
        click.echo("-" * 40)
        for key, value in config.items():
            click.echo(f"  {key} = {value}")
        click.echo("-" * 40)
        click.echo(f"Total: {len(config)} value(s)")

    except Exception as e:
        click.echo(f"Error: Failed to list configuration", err=True)
        click.echo(f"  {str(e)}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    main()

