# queuectl

CLI-based background job queue system with worker processes, retry mechanism with exponential backoff, and Dead Letter Queue (DLQ) support.

## Installation

```bash
pip install -e .
```

## Usage

### Enqueue a job
```bash
queuectl enqueue '{"id":"job1","command":"sleep 2"}'
```

### Start workers
```bash
queuectl worker start --count 3
```

### Stop workers
```bash
queuectl worker stop
```

### Check status
```bash
queuectl status
```

### List jobs
```bash
queuectl list --state pending
```

### Manage Dead Letter Queue
```bash
queuectl dlq list
queuectl dlq retry job1
```

### Configuration
```bash
queuectl config set max-retries 3
queuectl config set backoff-base 2
```

## Development Status

- ✅ Phase 1: CLI Foundation (Complete)
- ⏳ Phase 2: Data Model & Persistence (Pending)
- ⏳ Phase 3: Job Enqueue & Basic Retrieval (Pending)
- ⏳ Phase 4: Single Worker System (Pending)
- ⏳ Phase 5: Retry Mechanism & Exponential Backoff (Pending)
- ⏳ Phase 6: Multi-Worker & Concurrency (Pending)
- ⏳ Phase 7: Configuration & Polish (Pending)

