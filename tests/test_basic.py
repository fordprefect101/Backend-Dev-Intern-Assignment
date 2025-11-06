#!/usr/bin/env python3
"""
Basic validation and test script for queuectl.

Tests all major functionality:
- Job enqueue
- Worker execution
- Retry mechanism
- DLQ functionality
- Multi-worker concurrency
- Configuration management
"""

import subprocess
import time
import json
import sys
import os


def run_command(cmd, capture_output=True):
    """Run a shell command and return result."""
    print(f"  Running: {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=capture_output,
        text=True
    )
    if capture_output and result.stdout:
        print(f"  Output: {result.stdout.strip()}")
    return result


def test_enqueue():
    """Test job enqueuing."""
    print("\n" + "="*60)
    print("TEST 1: Job Enqueue")
    print("="*60)

    # Test basic enqueue
    result = run_command(
        'queuectl enqueue \'{"id":"test-enqueue","command":"echo Test enqueue"}\''
    )

    if result.returncode == 0 and "successfully enqueued" in result.stdout:
        print("✓ PASS: Job enqueued successfully")
        return True
    else:
        print("✗ FAIL: Job enqueue failed")
        return False


def test_list_jobs():
    """Test listing jobs."""
    print("\n" + "="*60)
    print("TEST 2: List Jobs")
    print("="*60)

    result = run_command('queuectl list --state pending')

    if result.returncode == 0 and "test-enqueue" in result.stdout:
        print("✓ PASS: Job listing works")
        return True
    else:
        print("✗ FAIL: Job listing failed")
        return False


def test_status():
    """Test status command."""
    print("\n" + "="*60)
    print("TEST 3: Status Command")
    print("="*60)

    result = run_command('queuectl status')

    if result.returncode == 0 and "Job Queue Status" in result.stdout:
        print("✓ PASS: Status command works")
        return True
    else:
        print("✗ FAIL: Status command failed")
        return False


def test_worker_execution():
    """Test single worker execution."""
    print("\n" + "="*60)
    print("TEST 4: Worker Execution")
    print("="*60)

    # Enqueue a simple job
    run_command(
        'queuectl enqueue \'{"id":"test-worker","command":"echo Worker test"}\''
    )

    # Start worker in background (will process for 5 seconds)
    print("  Starting worker (will run for 5 seconds)...")
    worker_proc = subprocess.Popen(
        'queuectl worker start',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait a bit for job to be processed
    time.sleep(3)

    # Terminate worker
    worker_proc.terminate()
    worker_proc.wait(timeout=2)

    # Check if job was completed
    result = run_command('queuectl list --state completed')

    if "test-worker" in result.stdout:
        print("✓ PASS: Worker executed job successfully")
        return True
    else:
        print("✗ FAIL: Worker execution failed")
        return False


def test_retry_mechanism():
    """Test retry and DLQ functionality."""
    print("\n" + "="*60)
    print("TEST 5: Retry Mechanism & DLQ")
    print("="*60)

    # Enqueue a failing job with max_retries=2
    run_command(
        'queuectl enqueue \'{"id":"test-retry","command":"exit 1","max_retries":2}\''
    )

    # Start worker in background
    print("  Starting worker to process failing job...")
    worker_proc = subprocess.Popen(
        'queuectl worker start',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for retries to complete (should fail 2 times and go to DLQ)
    time.sleep(5)

    # Terminate worker
    worker_proc.terminate()
    worker_proc.wait(timeout=2)

    # Check if job is in DLQ
    result = run_command('queuectl dlq list')

    if "test-retry" in result.stdout:
        print("✓ PASS: Job moved to DLQ after retries")
        return True
    else:
        print("✗ FAIL: Retry mechanism failed")
        return False


def test_dlq_retry():
    """Test DLQ retry functionality."""
    print("\n" + "="*60)
    print("TEST 6: DLQ Retry")
    print("="*60)

    # Try to retry the job from DLQ (auto-confirm with echo)
    result = run_command('echo "y" | queuectl dlq retry test-retry')

    if result.returncode == 0 and "reset and moved back to the queue" in result.stdout:
        print("✓ PASS: DLQ retry works")
        return True
    else:
        print("✗ FAIL: DLQ retry failed")
        return False


def test_config():
    """Test configuration management."""
    print("\n" + "="*60)
    print("TEST 7: Configuration Management")
    print("="*60)

    # Set config
    result1 = run_command('queuectl config set max-retries 5')

    # Get config
    result2 = run_command('queuectl config get max-retries')

    # List config
    result3 = run_command('queuectl config list')

    if (result1.returncode == 0 and
        "5" in result2.stdout and
        result3.returncode == 0):
        print("✓ PASS: Configuration management works")
        return True
    else:
        print("✗ FAIL: Configuration management failed")
        return False


def test_multi_worker():
    """Test multi-worker concurrency."""
    print("\n" + "="*60)
    print("TEST 8: Multi-Worker Concurrency")
    print("="*60)

    # Enqueue multiple jobs
    print("  Enqueuing 10 test jobs...")
    for i in range(1, 11):
        run_command(
            f'queuectl enqueue \'{{"id":"multi-{i}","command":"sleep 1 && echo Job {i}"}}\''
        )

    # Start 3 workers in background
    print("  Starting 3 workers (will run for 8 seconds)...")
    worker_proc = subprocess.Popen(
        'queuectl worker start --count 3',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for jobs to be processed
    time.sleep(8)

    # Terminate workers
    worker_proc.terminate()
    worker_proc.wait(timeout=3)

    # Check how many completed
    result = run_command('queuectl list --state completed')

    completed_count = sum(1 for i in range(1, 11) if f"multi-{i}" in result.stdout)

    if completed_count >= 8:  # At least 8 out of 10 should complete
        print(f"✓ PASS: Multi-worker processed {completed_count}/10 jobs")
        return True
    else:
        print(f"✗ FAIL: Only {completed_count}/10 jobs completed")
        return False


def cleanup():
    """Clean up test database."""
    print("\n" + "="*60)
    print("CLEANUP")
    print("="*60)

    if os.path.exists("queue.db"):
        os.remove("queue.db")
        print("✓ Removed test database")
    else:
        print("  No database to clean up")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("QUEUECTL VALIDATION TESTS")
    print("="*60)
    print("This will test all major functionality of the job queue system.")
    print("Tests will take approximately 30-40 seconds to complete.")

    # Clean up any existing database
    cleanup()

    # Run tests
    tests = [
        ("Job Enqueue", test_enqueue),
        ("List Jobs", test_list_jobs),
        ("Status Command", test_status),
        ("Worker Execution", test_worker_execution),
        ("Retry Mechanism & DLQ", test_retry_mechanism),
        ("DLQ Retry", test_dlq_retry),
        ("Configuration", test_config),
        ("Multi-Worker Concurrency", test_multi_worker),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"✗ FAIL: Test crashed with error: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    print("-"*60)
    print(f"Total: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED!")
        cleanup()
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        print("Database preserved for debugging: queue.db")
        return 1


if __name__ == "__main__":
    sys.exit(main())
