# queuectl - CLI Job Queue System

A production-grade CLI-based background job queue system built with Python. Features include worker process management, priority queue support, automatic retry with exponential backoff, Dead Letter Queue (DLQ) support, and race-condition-free multi-worker concurrency.

## Features

- **Job Queue Management**: Enqueue shell commands as jobs with automatic state tracking
- **Priority Queue**: Jobs processed by priority (high > medium > low) then FIFO within same priority
- **Multi-Worker Support**: Run multiple worker processes concurrently with atomic job claiming
- **Race Condition Prevention**: Production-grade SQLite locking ensures each job is processed exactly once
- **Automatic Retry**: Failed jobs automatically retry with configurable max retries
- **Dead Letter Queue (DLQ)**: Permanently failed jobs are moved to DLQ for manual review and retry
- **Exit Code Processing**: Jobs succeed (exit code 0) or fail (non-zero) based on command execution
- **Configuration Management**: Persistent configuration storage for system settings
- **Status Reporting**: Real-time job queue statistics and completion rates with priority breakdown
- **Graceful Shutdown**: Workers finish current jobs before stopping (Ctrl+C safe)
- **SQLite Persistence**: All data persisted to database with ACID guarantees

## 1. Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Local Setup

**Step 1: Clone the repository**
```bash
git clone https://github.com/fordprefect101/Backend-Dev-Intern-Assignment.git
cd Backend-Dev-Intern-Assignment
```

**Step 2: Create and activate virtual environment (recommended)**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

**Step 3: Install the package**
```bash
pip install -e .
```

This installs the `queuectl` command with all dependencies in an isolated environment.

**Step 4: Verify installation**
```bash
queuectl --help
```

You should see the CLI help menu with all available commands.

**Step 5: Run the test script**
```bash
python3 test_core.py
```

This runs the core test suite to verify everything is working correctly.

## 2. Usage Examples

### Enqueuing Jobs

**Example 1: Basic job**
```bash
$ queuectl enqueue '{"command":"echo Hello World"}'
✓ Successfully parsed JSON with 1 field(s)
✓ Validation passed
✓ Generated job ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
  Command: echo Hello World

✓ Job successfully enqueued!
  Job ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
  State: pending
  Max Retries: 3
```

**Example 2: Job with custom ID**
```bash
$ queuectl enqueue '{"id":"my-job-1","command":"python script.py"}'
✓ Successfully parsed JSON with 2 field(s)
✓ Validation passed
✓ Using provided job ID: my-job-1
  Command: python script.py

✓ Job successfully enqueued!
  Job ID: my-job-1
  State: pending
  Max Retries: 3
```

**Example 3: Job with custom max retries**
```bash
$ queuectl enqueue '{"command":"curl api.example.com","max_retries":5}'
✓ Job successfully enqueued!
  Job ID: f7g8h9i0-j1k2-3456-lmno-pq7890123456
  State: pending
  Max Retries: 5
```

**Example 4: Job with priority**
```bash
# High priority job
$ queuectl enqueue '{"command":"critical-task.sh","priority":"high"}'
✓ Job successfully enqueued!
  Job ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
  Command: critical-task.sh
  Priority: high
  State: pending
  Max Retries: 3

# Medium priority (default)
$ queuectl enqueue '{"command":"normal-task.sh","priority":"medium"}'

# Low priority
$ queuectl enqueue '{"command":"background-task.sh","priority":"low"}'
```

**Note**: Priority values are `high`, `medium`, or `low`. Default is `medium`. Jobs are processed in priority order (high > medium > low), then FIFO within the same priority.

**Example 5: Complex commands**
```bash
# Pipes and redirects work
$ queuectl enqueue '{"command":"cat file.txt | grep error > errors.log"}'

# Multiple commands with &&
$ queuectl enqueue '{"command":"cd /tmp && ls -la && pwd"}'
```

### Worker Management

**Example 1: Start a single worker**
```bash
$ queuectl worker start
Starting 1 worker(s)...

✓ Started worker-1 (PID: 12345)

1 worker(s) running. Press Ctrl+C to stop all workers.

Worker worker-1 initialized
Worker worker-1 started. Waiting for jobs...
Press Ctrl+C to stop gracefully.

→ [worker-1] Claimed job: a1b2c3d4-e5f6-7890-abcd-ef1234567890
[a1b2c3d4-e5f6-7890-abcd-ef1234567890] Executing command: echo Hello World
[a1b2c3d4-e5f6-7890-abcd-ef1234567890] STDOUT:
Hello World
[a1b2c3d4-e5f6-7890-abcd-ef1234567890] Exit code: 0
✓ [worker-1] Job a1b2c3d4-e5f6-7890-abcd-ef1234567890 completed successfully
```

**Example 2: Start multiple workers**
```bash
$ queuectl worker start --count 3
Starting 3 worker(s)...

✓ Started worker-1 (PID: 12345)
✓ Started worker-2 (PID: 12346)
✓ Started worker-3 (PID: 12347)

3 worker(s) running. Press Ctrl+C to stop all workers.
```

**Example 3: Stop workers gracefully**
Press `Ctrl+C` in the worker terminal. Workers will finish their current job before exiting:
```
^C received, shutting down gracefully...

Shutting down worker worker-1...
Worker worker-1 stopped.
```

### Monitoring

**Example 1: Check queue status**
```bash
$ queuectl status
Job Queue Status
==================================================

Jobs by State:
  Pending:          3
  Processing:       2
  Completed:       45
  Failed:           1
  Dead (DLQ):       2
--------------------------------------------------
  Total:           53

Completion Rate:
  84.9% (45/53)

Permanent Failures:
  3.8% (2/53)

Active/Pending Work: 5 job(s)

Active Jobs by Priority:
  High:       2
  Medium:     2
  Low:        1
==================================================
```

**Example 2: List all jobs**
```bash
$ queuectl list
All jobs
--------------------------------------------------------------------------------

Job ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
  Command: echo Hello World
  State: completed
  Priority: medium
  Attempts: 1/3
  Created: 2025-01-07T10:30:00+00:00
  Updated: 2025-01-07T10:30:05+00:00

Job ID: my-job-1
  Command: python script.py
  State: pending
  Priority: high
  Attempts: 0/3
  Created: 2025-01-07T10:31:00+00:00
  Updated: 2025-01-07T10:31:00+00:00

--------------------------------------------------------------------------------
Total: 2 job(s)
```

**Example 3: Filter by state**
```bash
$ queuectl list --state pending
Jobs with state: pending
--------------------------------------------------------------------------------

Job ID: my-job-1
  Command: python script.py
  State: pending
  Attempts: 0/3
  Created: 2025-01-07T10:31:00+00:00
  Updated: 2025-01-07T10:31:00+00:00

--------------------------------------------------------------------------------
Total: 1 job(s)
```

### Dead Letter Queue (DLQ)

**Example 1: View failed jobs**
```bash
$ queuectl dlq list
Dead Letter Queue (DLQ)
================================================================================
These jobs have failed permanently after exhausting all retries.

Job ID: failed-job-1
  Command: exit 1
  State: dead
  Failed Attempts: 3/3
  Created: 2025-01-07T10:00:00+00:00
  Last Updated: 2025-01-07T10:00:15+00:00

================================================================================
Total jobs in DLQ: 1

To retry a job: queuectl dlq retry <JOB_ID>
```

**Example 2: Retry a failed job**
```bash
$ queuectl dlq retry failed-job-1
Job 'failed-job-1':
  Command: exit 1
  Previous attempts: 3/3

Retry this job? [y/N]: y

✓ Job 'failed-job-1' has been reset and moved back to the queue
  New state: pending
  Attempts reset to: 0/3

The job will be picked up by the next available worker.
```

### Configuration

**Example 1: Set configuration**
```bash
$ queuectl config set max-retries 5
✓ Configuration updated:
  max-retries = 5

$ queuectl config set backoff-base 2
✓ Configuration updated:
  backoff-base = 2
```

**Example 2: Get configuration**
```bash
$ queuectl config get max-retries
max-retries = 5
  (default value)

$ queuectl config get backoff-base
backoff-base = 2
```

**Example 3: List all configuration**
```bash
$ queuectl config list
Configuration:
----------------------------------------
  backoff-base = 2
  max-retries = 5
----------------------------------------
Total: 2 value(s)
```

## 3. Architecture Overview

### System Components

```
┌─────────────┐
│   CLI       │ ─── User interface (click framework)
└──────┬──────┘
       │
┌──────▼──────┐
│  Storage    │ ─── SQLite database layer (ACID transactions)
└──────┬──────┘
       │
┌──────▼──────────────────┐
│  Jobs Table             │
│  ┌─────────────────┐    │
│  │ pending         │    │
│  │ processing      │    │
│  │ completed       │    │
│  │ failed          │    │
│  │ dead (DLQ)      │    │
│  └─────────────────┘    │
└─────────────────────────┘
       │
       │  (Atomic claiming with BEGIN IMMEDIATE)
       │
┌──────▼───────┐  ┌─────────────┐  ┌─────────────┐
│  Worker-1    │  │  Worker-2   │  │  Worker-N   │
│              │  │             │  │             │
│ subprocess   │  │ subprocess  │  │ subprocess  │
│ execution    │  │ execution   │  │ execution   │
└──────────────┘  └─────────────┘  └─────────────┘
```

### Job Lifecycle

**State Machine:**
```
pending ──────> processing ──────> completed ✓
   ▲                │
   │                │ (exit code ≠ 0)
   │                ▼
   │             failed
   │                │
   │ (retry)        │ (attempts < max_retries)
   └────────────────┘
                    │
                    │ (attempts ≥ max_retries)
                    ▼
                  dead (DLQ)
```

**Lifecycle Flow:**
1. **Enqueue**: Job created with `state='pending'`
2. **Claim**: Worker atomically claims job (`state='processing'`)
3. **Execute**: Worker runs the shell command
4. **Success**: Exit code 0 → `state='completed'`
5. **Failure**: Exit code ≠ 0 → `state='failed'`
6. **Retry**: If `attempts < max_retries` → back to `pending` with delay
7. **DLQ**: If `attempts >= max_retries` → `state='dead'`

### Data Persistence

**Database: SQLite (`queue.db`)**

**jobs table schema:**
- `id` (TEXT PRIMARY KEY) - Unique job identifier
- `command` (TEXT NOT NULL) - Shell command to execute
- `priority` (TEXT DEFAULT 'medium') - Job priority (high/medium/low)
- `state` (TEXT NOT NULL) - Job state (pending/processing/completed/failed/dead)
- `attempts` (INTEGER) - Number of execution attempts
- `max_retries` (INTEGER) - Maximum retry attempts before DLQ
- `created_at` (TEXT) - Job creation timestamp
- `updated_at` (TEXT) - Last update timestamp
- `locked_by` (TEXT) - Worker ID that claimed the job
- `locked_at` (TEXT) - Lock acquisition timestamp
- `next_retry_at` (TEXT) - Scheduled retry timestamp (for exponential backoff)

**config table schema:**
- `key` (TEXT PRIMARY KEY) - Configuration key
- `value` (TEXT NOT NULL) - Configuration value

**Persistence guarantees:**
- ACID transactions ensure data consistency
- All job state changes are immediately persisted
- Database survives worker crashes
- Jobs can be recovered after system restart

### Worker Logic

**Worker Process Flow:**

1. **Startup**: Worker initializes and connects to database
2. **Poll Loop**: Continuously polls for pending jobs (every 1 second)
3. **Claim Job**: Atomically claims next pending job using `BEGIN IMMEDIATE`
   - Jobs are selected by priority (high > medium > low), then FIFO within same priority
4. **Execute**: Runs shell command via `subprocess.run()`
5. **Update State**: Updates job state based on exit code
6. **Repeat**: Returns to polling loop

**Key Worker Behaviors:**
- **Atomic Claiming**: Uses database transactions to prevent race conditions
- **Exit Code Processing**: 0 = success, non-zero = failure
- **Retry Logic**: Automatically retries failed jobs with exponential backoff
- **Graceful Shutdown**: Finishes current job before exiting (Ctrl+C safe)
- **Multi-Worker Safe**: Multiple workers can run concurrently without conflicts

**Worker Coordination:**
- All workers share the same SQLite database
- Database locking ensures only one worker claims each job
- Lock is held only during claiming (~3ms), not during execution
- Workers execute jobs in parallel after claiming

### Race Condition Prevention

The system uses SQLite's `BEGIN IMMEDIATE` transactions for atomic job claiming:

```python
# Pseudo-code of atomic claiming
BEGIN IMMEDIATE;  # Locks database
SELECT job WHERE state='pending' AND locked_by IS NULL 
  ORDER BY priority (high > medium > low), created_at ASC 
  LIMIT 1;
UPDATE job SET state='processing', locked_by='worker-1', locked_at=NOW();
COMMIT;  # Releases lock
```

This ensures that even with 100 workers, each job is claimed by exactly one worker.

### Retry Mechanism with Exponential Backoff

When a job fails (exit code ≠ 0):

1. **Increment attempts counter**
2. **Check if attempts < max_retries**
   - YES → Set state back to `pending` with scheduled retry time
   - NO → Set state to `dead` (sent to DLQ)

**Exponential Backoff Formula:**
```
delay = initial_delay * (base ^ attempts) seconds
```

**Default Configuration:**
- `backoff-base` = 2
- `backoff-initial-delay` = 1

**Example with max_retries=3, base=2, initial_delay=1:**
- Attempt 1 fails → Retry in **2 seconds** (1 × 2¹ = 2s)
- Attempt 2 fails → Retry in **4 seconds** (1 × 2² = 4s)
- Attempt 3 fails → **Sent to DLQ** (max retries exceeded)

**Configuring Backoff:**
```bash
# Set longer initial delay (30 seconds)
queuectl config set backoff-initial-delay 30

# Use base 3 for faster growth
queuectl config set backoff-base 3
# Now: 30s, 90s, 270s, 810s...
```

### Exit Code Processing

The system evaluates command exit codes:

- **Exit code 0**: Success → Job marked as `completed`
- **Exit code ≠ 0**: Failure → Job marked as `failed`, retry logic kicks in

Examples:
```bash
# These succeed (exit 0)
queuectl enqueue '{"command":"echo hello"}'
queuectl enqueue '{"command":"true"}'

# These fail (exit 1)
queuectl enqueue '{"command":"exit 1"}'
queuectl enqueue '{"command":"false"}'

# Command not found (exit 127)
queuectl enqueue '{"command":"nonexistent-command"}'
```

### Subprocess Execution

Commands are executed with:
- **shell=True**: Supports pipes, redirects, and shell syntax
- **capture_output=True**: Stdout/stderr are captured and logged
- **timeout=300**: 5-minute timeout per job (configurable)

## 4. Assumptions & Trade-offs

### Design Decisions

**1. SQLite for Persistence**
- **Assumption**: Single-machine deployment with moderate throughput (<1000 jobs/sec)
- **Trade-off**: Simple, zero-configuration database vs. distributed scalability
- **Why**: ACID guarantees, built-in Python support, perfect for local/single-server use

**2. Atomic Job Claiming with Database Locking**
- **Approach**: `BEGIN IMMEDIATE` transactions lock entire database during claim
- **Trade-off**: Simple correctness vs. maximum concurrency
- **Why**: Zero race conditions, easy to reason about
- **Limitation**: ~10-50 concurrent workers max (SQLite write lock)

**3. Exponential Backoff Formula**
- **Formula**: `delay = initial_delay × (base ^ attempts)`
- **Assumption**: Network/external service failures are transient
- **Why**: Industry-standard pattern, prevents thundering herd
- **Configurable**: Users can tune `backoff-base` and `backoff-initial-delay`

**4. In-Database State Management**
- **Approach**: All state in SQLite (no external state store)
- **Trade-off**: Simplicity vs. distributed coordination
- **Why**: Single source of truth, crash recovery is automatic
- **Limitation**: Can't scale across machines without shared filesystem

**5. Shell Command Execution**
- **Approach**: Commands run with `shell=True` in subprocess
- **Security Trade-off**: Flexibility vs. injection risk
- **Assumption**: Trusted job sources only (not public-facing)
- **Mitigation**: Jobs must be explicitly enqueued (no external API)

**6. Polling-Based Worker**
- **Approach**: Workers poll database every 1 second for pending jobs
- **Trade-off**: Simple implementation vs. instant job pickup
- **Why**: No complex pub/sub infrastructure needed

**7. No Distributed Lock Recovery**
- **Limitation**: Crashed workers leave jobs in "processing" state
- **Assumption**: Workers are reliable, crashes are rare
- **Workaround**: Manual database reset for stuck jobs

**8. Synchronous Job Execution**
- **Approach**: One job per worker at a time
- **Trade-off**: Simple, predictable resource usage vs. throughput
- **Why**: Easy debugging, clear resource limits

### Simplifications Made

1. **No job dependencies**: Jobs are independent (no DAG/workflow support)
2. **No job timeouts per-job**: Global 300s timeout for all jobs
3. **No distributed workers**: All workers must share same filesystem
4. **No audit log**: Job history not preserved after deletion
5. **No resource limits**: No CPU/memory constraints per job
6. **No authentication**: No user/permission system

## 5. Testing Instructions

### Running the Core Test Suite

The project includes a single test script that verifies core functionality:

```bash
python3 test_core.py
```

**What it tests:**
1. **Enqueue Job** - Basic job enqueueing
2. **Worker Execution** - Worker processes a job successfully
3. **Job Failure** - Worker handles job failure correctly
4. **Retry and DLQ** - Retry mechanism and Dead Letter Queue
5. **Multi-Worker** - Multiple workers processing jobs concurrently
6. **Status Command** - Status command functionality

**Expected output:**
```
============================================================
CORE TESTS - queuectl Job Queue System
============================================================
✓ Cleaned up test database

[Test 1] Enqueue job...
✓ PASS: Job enqueued

[Test 2] Worker execution...
✓ PASS: Worker executed job successfully

[Test 3] Job failure handling...
✓ PASS: Job failure handled

[Test 4] Retry and DLQ...
✓ PASS: Job moved to DLQ after retries

[Test 5] Multi-worker concurrency...
✓ PASS: Multi-worker processed 5/5 jobs

[Test 6] Status command...
✓ PASS: Status command works

============================================================
TEST SUMMARY
============================================================
✓ PASS: Enqueue Job
✓ PASS: Worker Execution
✓ PASS: Job Failure
✓ PASS: Retry and DLQ
✓ PASS: Multi-Worker
✓ PASS: Status Command
------------------------------------------------------------
Total: 6/6 tests passed

🎉 ALL CORE TESTS PASSED!
```

**If tests fail:**
- The database (`queue.db`) is preserved for debugging
- Check worker output for error messages
- Verify `queuectl` command is installed: `queuectl --help`

### Manual Testing

**Test 1: Basic job execution**
```bash
# Terminal 1: Start worker
queuectl worker start

# Terminal 2: Enqueue and check
queuectl enqueue '{"id":"test-1","command":"echo Test 1"}'
queuectl list --state completed
```

**Test 2: Retry mechanism**
```bash
# Enqueue failing job
queuectl enqueue '{"id":"retry-test","command":"exit 1","max_retries":2}'

# Start worker - watch it retry and eventually move to DLQ
queuectl worker start

# Check DLQ
queuectl dlq list
```

**Test 3: Multi-worker concurrency**
```bash
# Enqueue many jobs
for i in {1..10}; do
  queuectl enqueue "{\"id\":\"job-$i\",\"command\":\"echo Job $i\"}"
done

# Start multiple workers
queuectl worker start --count 3

# Watch them process jobs concurrently
queuectl status
```

## Troubleshooting

### Issue: Jobs stuck in "processing" state

**Cause**: Worker crashed while processing a job

**Solution**: Jobs remain locked. Manual reset required:
```bash
# Manually reset stuck job (requires DB access)
sqlite3 queue.db "UPDATE jobs SET state='pending', locked_by=NULL WHERE state='processing'"
```

### Issue: "Database is locked" errors

**Cause**: Multiple processes accessing database with high contention

**Solution**: This is normal and handled by SQLite retry logic. If persistent:
- Reduce number of workers
- Check for long-running queries

### Issue: Worker not finding jobs

**Check job state:**
```bash
queuectl list --state pending
```

**Check worker output** for error messages

**Verify database exists:**
```bash
ls -la queue.db
```

### Issue: Command execution fails with "command not found"

**Cause**: Command not in PATH or typo

**Solution**: Use full path or verify command exists:
```bash
queuectl enqueue '{"command":"/usr/bin/python3 script.py"}'
```

## Configuration Reference

| Key | Default | Description |
|-----|---------|-------------|
| max-retries | 3 | Maximum retry attempts before DLQ |
| backoff-base | 2 | Base for exponential backoff (not yet implemented) |

## Project Structure

```
queuectl/
├── queuectl/
│   ├── __init__.py          # Package initialization
│   ├── cli.py               # CLI commands (enqueue, worker, status, list, dlq, config)
│   ├── models.py            # Job data model
│   ├── storage.py           # SQLite database layer
│   └── worker.py            # Worker process logic
├── test_core.py             # Core test script
├── README.md                # This file
├── IMPLEMENTATION_SUMMARY.md # Detailed implementation guide
├── requirements.txt         # Python dependencies
├── setup.py                 # Package installation
└── queue.db                 # SQLite database (created on first run)
```

## Development

### Running in development mode

```bash
# Install in editable mode
pip install -e .

# Make changes to code
# Changes take effect immediately without reinstalling
```

### Adding new commands

Edit `queuectl/cli.py` and add new click commands:

```python
@main.command()
def mycommand():
    """My custom command."""
    click.echo("Hello from custom command!")
```

### Extending storage

Add new methods to `queuectl/storage.py`:

```python
def my_query(self):
    with self._get_connection() as conn:
        cursor = conn.execute("SELECT * FROM jobs WHERE ...")
        return cursor.fetchall()
```

## Implementation Status

- ✅ Phase 1: CLI Foundation
- ✅ Phase 2: Data Model & Persistence
- ✅ Phase 3: Job Enqueue & Input Validation
- ✅ Phase 4: Single Worker System
- ✅ Phase 5: Retry Mechanism
- ✅ Phase 6: Multi-Worker Support & Race Condition Prevention
- ✅ Phase 7: Configuration & Polish


Video Demo: https://drive.google.com/file/d/15sYdHIAw30pxto_TnDfIfLdpdkwpGzfa/view?usp=sharing
