*Objective*

Build a **CLI-based background job queue system** called `queuectl`.

This system should manage background jobs with worker processes, handle retries using exponential backoff, and maintain a **Dead Letter Queue (DLQ)** for permanently failed jobs.



## 🧩 **Problem Overview**



You need to implement a minimal, production-grade job queue system that supports:

- Enqueuing and managing background jobs

- Running multiple worker processes

- Retrying failed jobs automatically with exponential backoff

- Moving jobs to a **Dead Letter Queue** after exhausting retries

- Persistent job storage across restarts

- All operations accessible through a **CLI interface**



📦 Job Specification



Each job must contain at least the following fields:

{

  "id": "unique-job-id",

  "command": "echo 'Hello World'",

  "state": "pending",

  "attempts": 0,

  "max_retries": 3,

  "created_at": "2025-11-04T10:30:00Z",

  "updated_at": "2025-11-04T10:30:00Z"

}



Job Lifecycle:

## 🔄 **Job Lifecycle**



| **State** | **Description** |

| --- | --- |

| `pending` | Waiting to be picked up by a worker |

| `processing` | Currently being executed |

| `completed` | Successfully executed |

| `failed` | Failed, but retryable |

| `dead` | Permanently failed (moved to DLQ) |



CLI commands:

your tool must support the following commands:

| **Category** | **Command Example** | **Description** |



| --- | --- | --- |

| **Enqueue** | `queuectl enqueue '{"id":"job1","command":"sleep 2"}'` | Add a new job to the queue |

| **Workers** | `queuectl worker start --count 3` | Start one or more workers |

|  | `queuectl worker stop` | Stop running workers gracefully |

| **Status** | `queuectl status` | Show summary of all job states & active workers |

| **List Jobs** | `queuectl list --state pending` | List jobs by state |

| **DLQ** | `queuectl dlq list` / `queuectl dlq retry job1` | View or retry DLQ jobs |

| **Config** | `queuectl config set max-retries 3` | Manage configuration (retry, backoff, etc.) |

## ⚙️ **System Requirements**



1. **Job Execution**

    - Each worker must execute the specified command (e.g. `sleep 2`, `echo hello`, etc.)

    - Exit codes should determine success or failure.

    - Commands that fail or are not found should trigger retries.

2. **Retry & Backoff**

    - Failed jobs retry automatically.

    - Implement exponential backoff:

        

        `delay = base ^ attempts` seconds

        

    - Move to DLQ after `max_retries`.

3. **Persistence**

    - Job data must persist across restarts.

    - Use file storage (JSON) or SQLite/embedded DB or anything which you think is best for this usecase.

4. **Worker Management**

    - Multiple workers can process jobs in parallel.

    - Prevent duplicate processing (locking required).

    - Implement graceful shutdown (finish current job before exit).

5. **Configuration**

    - Allow configurable retry count and backoff base via CLI.

Deliverables:

- ✅ Working CLI application (`queuectl`)

- ✅ Persistent job storage

- ✅ Multiple worker support

- ✅ Retry mechanism with exponential backoff

- ✅ Dead Letter Queue

- ✅ Configuration management

- ✅ Clean CLI interface (commands & help texts)

- ✅ Comprehensive `README.md`

- ✅ Code structured with clear separation of concerns

- ✅ At least minimal testing or script to validate core flows
