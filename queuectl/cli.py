"""CLI command definitions for queuectl."""
import click
import json
import uuid
from queuectl.models import Job
from queuectl.storage import Storage


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
            state='pending',
            attempts=0,
            max_retries=job_data.get('max_retries', 3)  # Allow optional max_retries
        )

        # Save to database
        storage.create_job(job.to_dict())

        click.echo(f"\n✓ Job successfully enqueued!")
        click.echo(f"  Job ID: {job.id}")
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


@worker.command()
@click.option('--count', default=1, type=int, help='Number of workers to start')
def start(count):
    """Start one or more worker processes."""
    click.echo(f"Starting {count} worker(s)")
    # TODO: Implement worker start logic in Phase 6


@worker.command()
def stop():
    """Stop running workers gracefully."""
    click.echo("Stopping workers...")
    # TODO: Implement worker stop logic in Phase 6


@main.command()
def status():
    """Show summary of all job states & active workers."""
    click.echo("Status:")
    click.echo("  Jobs: pending=0, processing=0, completed=0, failed=0, dead=0")
    click.echo("  Workers: active=0")
    # TODO: Implement status logic in Phase 7


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
    """List jobs in the Dead Letter Queue."""
    click.echo("Dead Letter Queue jobs:")
    # TODO: Implement DLQ list logic in Phase 7


@dlq.command()
@click.argument('job_id', required=True)
def retry(job_id):
    """Retry a job from the Dead Letter Queue.
    
    JOB_ID: The ID of the job to retry
    """
    click.echo(f"Retrying job: {job_id}")
    # TODO: Implement DLQ retry logic in Phase 7


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
    """
    click.echo(f"Setting config: {key} = {value}")
    # TODO: Implement config set logic in Phase 7


if __name__ == '__main__':
    main()

