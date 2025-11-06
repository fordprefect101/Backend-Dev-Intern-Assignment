# Python Job Queue System Implementation Plan

## Overview

Build a **basic-to-production** CLI job queue system (`queuectl`) using Python. Start with a simple dev-grade implementation that meets all assignment requirements, then upgrade to production-grade features.

**🎯 Learning Approach**: Start simple → Add complexity gradually → Learn concepts step by step

## Technology Stack

- **Language**: Python 3.8+
- **CLI Framework**: `click` (simple, powerful)
- **Storage**: SQLite (better than JSON for locking/concurrency)
- **Process Management**: `multiprocessing` for workers
- **File Locking**: `fcntl` (Unix) / `msvcrt` (Windows) or SQLite locking

## Project Structure

```
queuectl/
├── queuectl/              # Main package
│   ├── __init__.py
│   ├── cli.py            # CLI command definitions
│   ├── models.py         # Job data model
│   ├── storage.py        # SQLite persistence layer
│   ├── queue.py          # Queue management logic
│   ├── worker.py         # Worker process logic
│   ├── retry.py          # Retry & exponential backoff
│   ├── dlq.py            # Dead Letter Queue management
│   └── config.py         # Configuration management
├── tests/
│   └── test_basic.py     # Basic validation scripts
├── README.md
├── requirements.txt
└── setup.py              # Package installation
```

## Implementation Phases

**📖 Implementation Strategy**: Each phase has **BASIC** (dev-grade) and **PRODUCTION** (advanced) versions. Start with BASIC to understand concepts, then upgrade to PRODUCTION.

### Phase 1: Project Setup & CLI Foundation (BASIC) ✅ COMPLETED

**Concepts & Methodologies:**

- **Python Package Structure**: Module organization, `__init__.py`, package imports
- **CLI Framework (click)**: Command decorators, argument parsing, help text generation
- **Command-Line Interface Design**: Subcommands, flags, options, user experience patterns
- **Dependency Management**: `requirements.txt`, virtual environments, package installation
- **Project Architecture**: Separation of concerns, modular design

**What You'll Learn:**

- How to structure a Python package
- Using `click` decorators (`@click.group()`, `@click.command()`, `@click.option()`)
- Creating nested commands (e.g., `queuectl worker start`)
- Writing helpful command descriptions and help text
- Managing Python dependencies

**Tasks:**

- Initialize project structure
- Set up `click` CLI framework
- Create basic command structure (enqueue, worker, status, list, dlq, config)
- Add help text for all commands
- Create `requirements.txt` with dependencies

### Phase 2: Data Model & Persistence (BASIC) 🚧 NEXT

**Concepts & Methodologies:**

- **Data Modeling**: Entity design, field types, relationships
- **SQLite Database**: SQL schema design, table creation, transactions
- **CRUD Operations**: Create, Read, Update, Delete patterns
- **Database Transactions**: ACID properties, commit/rollback
- **Row-Level Locking**: `SELECT ... FOR UPDATE`, pessimistic locking
- **Connection Pooling**: Database connection management
- **Context Managers**: `with` statements for resource management

**What You'll Learn:**

- SQLite basics (CREATE TABLE, INSERT, SELECT, UPDATE, DELETE)
- Database schema design for job queues
- Using Python's `sqlite3` module
- Implementing atomic operations with transactions
- Preventing race conditions with database locks
- Context managers for automatic resource cleanup

**Tasks (BASIC):**

- Define simple Job model (id, command, state, attempts, max_retries, timestamps)
- Implement basic SQLite storage layer
- Create database schema (jobs table, config table)
- Implement simple CRUD operations (create, read, update, delete)
- **Skip complex locking for now** - start with single worker

**Production Upgrade Later:**
- Add locking fields (locked_by, locked_at)
- Implement transaction-based concurrency control

### Phase 3: Job Enqueue & Input Validation (BASIC)

**Concepts & Methodologies:**

- **Comprehensive Input Validation**: JSON schema validation, required field checking, data sanitization
- **Data Serialization**: JSON encoding/decoding with error handling
- **Command Arguments**: Parsing JSON strings from CLI with validation
- **Database Queries**: Filtering by state, sorting, pagination concepts
- **Error Handling**: Try-except blocks, user-friendly error messages
- **Data Transformation**: Converting between JSON and database records
- **ID Management**: Automatic ID generation and uniqueness validation

**What You'll Learn:**

- Implementing robust JSON schema validation with required field checking
- Validating that required fields (id, command) are present and non-empty
- Handling malformed JSON gracefully with clear error messages
- Parsing command-line arguments with `click` and comprehensive validation
- Writing SQL queries with WHERE clauses
- Handling validation errors gracefully at the input stage
- Converting between data formats (dict ↔ database row)
- Preventing malformed requests from entering the worker system

**Tasks (BASIC):**

- Implement `queuectl enqueue` command with simple validation
- Check that JSON has required fields (id, command) and they're not empty
- Generate UUID for id if not provided
- Save jobs to database with `pending` state
- Implement `queuectl list` command with basic state filtering
- Add simple error messages for missing fields

**Production Upgrade Later:**
- Advanced JSON schema validation
- Input sanitization and security checks
- Comprehensive error handling

### Phase 4: Single Worker System (BASIC)

**Concepts & Methodologies:**

- **Process Execution**: `subprocess` module for running shell commands with comprehensive result handling
- **Critical Exit Code Processing**: Understanding and properly handling return codes (0 = success, non-zero = failure)
- **State Machine**: State transitions (pending → processing → completed/failed) based on exit codes
- **Process Management**: Long-running processes, polling patterns
- **Signal Handling**: SIGTERM, SIGINT, graceful shutdown patterns
- **Error Handling**: Catching exceptions, handling command failures, subprocess errors
- **Database Transactions**: Updating job state atomically based on execution results

**What You'll Learn:**

- Using `subprocess.run()` with comprehensive result checking and timeout handling
- **CRITICAL**: Interpreting exit codes from executed processes (assignment requirement)
- Implementing state machines in Python with exit code-driven transitions
- Creating long-running worker processes with robust error handling
- Handling Unix signals (signal module)
- Graceful shutdown patterns (finish current job before exit)
- Atomic database updates based on command execution results
- Logging subprocess output and exit codes for debugging

**Tasks (BASIC):**

- Implement simple worker loop: `while True: process_next_job()`
- Worker picks up first `pending` job (no locking yet - single worker only)
- Execute shell commands using basic `subprocess.run()`
- Handle exit codes: 0 = completed, non-zero = failed
- Update job state: pending → processing → completed/failed
- Add simple Ctrl+C handling to stop worker

**Production Upgrade Later:**
- Advanced subprocess handling (timeouts, logging)
- Database locking for multi-worker support
- Graceful shutdown with signal handling
- Comprehensive error handling

### Phase 5: Retry Mechanism (BASIC)

**Concepts & Methodologies:**

- **Exponential Backoff**: Mathematical formula `delay = base ^ attempts`
- **Retry Patterns**: Automatic retry logic, retry scheduling
- **Time Calculations**: `datetime` module, timestamp arithmetic
- **Scheduling**: When to retry jobs (next_retry_at field)
- **State Transitions**: failed → pending (for retry) → dead (after max retries)
- **Conditional Logic**: Checking retry limits, calculating delays
- **Dead Letter Queue Pattern**: Moving permanently failed jobs to DLQ

**What You'll Learn:**

- Implementing exponential backoff algorithm
- Calculating future timestamps for retry scheduling
- Managing job state transitions for retries
- Implementing retry limits and DLQ logic
- Using datetime for time calculations
- Conditional logic for retry decisions

**Tasks (BASIC):**

- When job fails: increment `attempts` counter
- If `attempts < max_retries`: change state back to `pending` (simple retry)
- If `attempts >= max_retries`: change state to `dead` (move to DLQ)
- **Skip complex scheduling for now** - retry immediately

**Production Upgrade Later:**
- Implement exponential backoff delays
- Add `next_retry_at` timestamp scheduling
- Advanced retry scheduling logic

### Phase 6: Multi-Worker Support (BASIC → PRODUCTION)

**Concepts & Methodologies:**

- **Multiprocessing**: `multiprocessing.Process`, process pools
- **Parallelism**: Multiple processes running simultaneously
- **CRITICAL: SQL Locking Strategy**: Atomic job claiming with SQLite transactions
- **Race Condition Prevention**: Ensuring only one worker processes a job using database locks
- **Transaction-Based Locking**: Using `BEGIN IMMEDIATE` for atomic operations
- **Alternative Locking**: `SELECT ... FOR UPDATE` vs `UPDATE ... RETURNING` approaches
- **Process Management**: Starting/stopping multiple processes
- **Process Communication**: Process IDs, signal handling across processes
- **Concurrency Control**: Coordinating multiple workers accessing shared data
- **Graceful Shutdown**: Coordinating shutdown of multiple processes

**What You'll Learn:**

- Creating multiple processes with `multiprocessing`
- **CRITICAL**: Implementing atomic job claiming with SQLite transactions
- Understanding the race condition problem in detail
- Using `locked_by` and `locked_at` fields for coordination
- Implementing transaction-based vs row-level locking strategies
- Managing multiple worker processes
- Coordinating processes to avoid job conflicts
- Handling signals across multiple processes
- Implementing process pools and worker management
- Understanding concurrency vs parallelism

**Tasks (BASIC - Start Here):**

- Implement `queuectl worker start --count N` with simple multiprocessing
- Start multiple worker processes using `multiprocessing.Process`
- **Accept that jobs might occasionally be processed twice** (race conditions)
- Add basic worker process management

**Tasks (PRODUCTION - Upgrade Later):**

- **CRITICAL**: Implement atomic job claiming using SQLite transactions
- Add `get_next_job(worker_id)` function with proper locking
- Add locking fields to database schema (locked_by, locked_at)
- Implement lock cleanup for crashed workers
- Add graceful shutdown for all workers
- Test concurrency with multiple workers on same queue

**📚 Learning Note**: Start with BASIC to understand multiprocessing, then upgrade to PRODUCTION for proper concurrency control.

### Phase 7: Configuration & Polish (BASIC)

**Concepts & Methodologies:**

- **Configuration Management**: Key-value storage, default values
- **CLI Subcommands**: Nested command structures (`config set`, `dlq list`)
- **Data Aggregation**: Counting jobs by state, generating summaries
- **Documentation**: README.md writing, usage examples
- **Testing**: Basic validation scripts, smoke tests
- **Error Handling**: Comprehensive error messages, user feedback
- **Code Organization**: Clean code principles, separation of concerns
- **User Experience**: Helpful error messages, clear output formatting

**What You'll Learn:**

- Storing and retrieving configuration values
- Implementing nested CLI commands
- Aggregating data for status reports
- Writing effective documentation
- Creating basic test scripts
- Error handling best practices
- Code organization and maintainability

**Tasks:**

- Implement `queuectl config set` commands (max-retries, backoff-base)
- Implement `queuectl dlq list` and `queuectl dlq retry`
- Implement `queuectl status` with job state summary
- Add comprehensive README.md
- Create basic test/validation script
- Add error handling and user-friendly messages

## Key Implementation Details

### Storage Schema (SQLite)

**BASIC Schema (Start with this):**
```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    command TEXT NOT NULL,
    state TEXT NOT NULL,        -- 'pending', 'processing', 'completed', 'failed', 'dead'
    attempts INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

**PRODUCTION Schema (Add later for multi-worker):**
```sql
-- Add these columns when implementing proper locking:
ALTER TABLE jobs ADD COLUMN next_retry_at TEXT;
ALTER TABLE jobs ADD COLUMN locked_by TEXT;
ALTER TABLE jobs ADD COLUMN locked_at TEXT;
```

### Job States Flow

`pending` → `processing` → `completed` (success)

↓

`failed` → `pending` (retry) → `dead` (after max retries)

### Exponential Backoff Formula

`delay = base ^ attempts` seconds

- Example: base=2, attempts=1 → 2s, attempts=2 → 4s, attempts=3 → 8s

### Worker Job Processing - BASIC vs PRODUCTION

#### BASIC Approach (Start Here)
```python
def get_next_job_basic():
    """Simple approach - good for single worker or learning"""
    with sqlite3.connect('queue.db') as conn:
        cursor = conn.execute("""
            SELECT * FROM jobs
            WHERE state='pending'
            LIMIT 1
        """)
        job = cursor.fetchone()

        if job:
            conn.execute("""
                UPDATE jobs
                SET state='processing'
                WHERE id=?
            """, (job['id'],))
        return job

# Simple worker loop
def worker_loop_basic():
    while True:
        job = get_next_job_basic()
        if job:
            result = subprocess.run(job['command'], shell=True)
            if result.returncode == 0:
                mark_completed(job['id'])
            else:
                handle_failed_job(job['id'])
        time.sleep(1)  # Poll every second
```

#### PRODUCTION Approach (Advanced - Race Condition Safe)

**The Problem with BASIC approach:**
```
Worker A gets job #123    →    Worker B gets job #123 (same job!)
Both process it simultaneously 💥
```

**PRODUCTION Solution:**
```python
def get_next_job_production(worker_id):
    """Race condition safe - only one worker gets each job"""
    with sqlite3.connect('queue.db') as conn:
        cursor = conn.execute("""
            UPDATE jobs
            SET state='processing',
                locked_by=?,
                locked_at=datetime('now')
            WHERE id = (
                SELECT id FROM jobs
                WHERE state='pending' AND locked_by IS NULL
                LIMIT 1
            )
            RETURNING *
        """, (worker_id,))
        return cursor.fetchone()
```

**📚 Learning Path**: Start with BASIC to understand concepts → Upgrade to PRODUCTION when you need multiple workers

### Worker Process Management

- Use `multiprocessing.Process` for each worker
- Store worker PIDs for graceful shutdown
- Use signal handlers (SIGTERM, SIGINT) for graceful shutdown
- Workers finish current job before exiting

## Testing Strategy

- Create validation script that tests:
  - Job enqueue
  - Worker execution
  - Retry mechanism
  - DLQ functionality
  - Multi-worker concurrency
  - Configuration management