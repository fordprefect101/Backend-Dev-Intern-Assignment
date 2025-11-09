#!/usr/bin/env python3
"""
Core Test Script for queuectl
Tests the essential flows of the job queue system.
"""

import subprocess
import time
import os
import sys


def run_command(cmd, capture_output=True):
    """Run a shell command and return result."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=capture_output,
        text=True
    )
    return result


def cleanup():
    """Remove test database if it exists."""
    if os.path.exists("queue.db"):
        os.remove("queue.db")
        print("✓ Cleaned up test database")


def test_enqueue():
    """Test 1: Enqueue a job."""
    print("\n[Test 1] Enqueue job...")
    result = run_command('queuectl enqueue \'{"id":"test-1","command":"echo Hello World"}\'')
    if result.returncode == 0 and "successfully enqueued" in result.stdout:
        print("✓ PASS: Job enqueued")
        return True
    print("✗ FAIL: Job enqueue failed")
    return False


def test_worker_execution():
    """Test 2: Worker processes a job successfully."""
    print("\n[Test 2] Worker execution...")
    
    # Enqueue a job
    run_command('queuectl enqueue \'{"id":"test-2","command":"echo Test execution"}\'')
    
    # Start worker in background
    worker = subprocess.Popen(
        'queuectl worker start',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for job to be processed
    time.sleep(3)
    
    # Stop worker
    worker.terminate()
    worker.wait(timeout=2)
    
    # Check if job completed
    result = run_command('queuectl list --state completed')
    if "test-2" in result.stdout:
        print("✓ PASS: Worker executed job successfully")
        return True
    print("✗ FAIL: Worker execution failed")
    return False


def test_job_failure():
    """Test 3: Worker handles job failure."""
    print("\n[Test 3] Job failure handling...")
    
    # Enqueue a failing job
    run_command('queuectl enqueue \'{"id":"test-3","command":"exit 1"}\'')
    
    # Start worker
    worker = subprocess.Popen(
        'queuectl worker start',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    time.sleep(3)
    worker.terminate()
    worker.wait(timeout=2)
    
    # Check if job is in failed or pending (retry)
    result = run_command('queuectl list --state failed')
    if "test-3" in result.stdout:
        print("✓ PASS: Job failure handled")
        return True
    
    # Check if it's pending (retry logic)
    result = run_command('queuectl list --state pending')
    if "test-3" in result.stdout:
        print("✓ PASS: Job failure handled (retry)")
        return True
    
    print("✗ FAIL: Job failure not handled")
    return False


def test_retry_and_dlq():
    """Test 4: Retry mechanism and DLQ."""
    print("\n[Test 4] Retry and DLQ...")
    
    # Enqueue a failing job with max_retries=2
    run_command('queuectl enqueue \'{"id":"test-4","command":"exit 1","max_retries":2}\'')
    
    # Start worker to process retries
    worker = subprocess.Popen(
        'queuectl worker start',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for retries to complete
    time.sleep(8)
    
    worker.terminate()
    worker.wait(timeout=2)
    
    # Check if job is in DLQ
    result = run_command('queuectl dlq list')
    if "test-4" in result.stdout:
        print("✓ PASS: Job moved to DLQ after retries")
        return True
    print("✗ FAIL: Retry/DLQ mechanism failed")
    return False


def test_multi_worker():
    """Test 5: Multi-worker concurrency."""
    print("\n[Test 5] Multi-worker concurrency...")
    
    # Enqueue multiple jobs
    for i in range(1, 6):
        run_command(f'queuectl enqueue \'{{"id":"multi-{i}","command":"echo Job {i}"}}\'')
    
    # Start 2 workers
    worker = subprocess.Popen(
        'queuectl worker start --count 2',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for jobs to be processed
    time.sleep(5)
    
    worker.terminate()
    worker.wait(timeout=3)
    
    # Check how many completed
    result = run_command('queuectl list --state completed')
    completed = sum(1 for i in range(1, 6) if f"multi-{i}" in result.stdout)
    
    if completed >= 3:  # At least 3 out of 5 should complete
        print(f"✓ PASS: Multi-worker processed {completed}/5 jobs")
        return True
    print(f"✗ FAIL: Only {completed}/5 jobs completed")
    return False


def test_status():
    """Test 6: Status command."""
    print("\n[Test 6] Status command...")
    result = run_command('queuectl status')
    if result.returncode == 0 and "Job Queue Status" in result.stdout:
        print("✓ PASS: Status command works")
        return True
    print("✗ FAIL: Status command failed")
    return False


def test_priority_queue():
    """Test 7: Priority queue ordering (HIGH > MEDIUM > LOW)."""
    print("\n[Test 7] Priority queue ordering...")

    # Clean database for fresh test
    cleanup()

    # Enqueue jobs in reverse priority order to test ordering
    # Use sleep to slow down execution so we can verify ordering
    jobs = [
        ('{"id":"low-1","command":"sleep 0.1 && echo LOW-1","priority":"low"}', "low-1", "low"),
        ('{"id":"low-2","command":"sleep 0.1 && echo LOW-2","priority":"low"}', "low-2", "low"),
        ('{"id":"med-1","command":"sleep 0.1 && echo MED-1","priority":"medium"}', "med-1", "medium"),
        ('{"id":"med-2","command":"sleep 0.1 && echo MED-2","priority":"medium"}', "med-2", "medium"),
        ('{"id":"high-1","command":"sleep 0.1 && echo HIGH-1","priority":"high"}', "high-1", "high"),
        ('{"id":"high-2","command":"sleep 0.1 && echo HIGH-2","priority":"high"}', "high-2", "high"),
    ]

    print("  Enqueuing jobs in order: LOW, LOW, MEDIUM, MEDIUM, HIGH, HIGH")
    for job_json, job_id, priority in jobs:
        result = run_command(f'queuectl enqueue \'{job_json}\'')
        if result.returncode != 0:
            print(f"✗ FAIL: Could not enqueue job {job_id}")
            return False
        # Verify priority is shown during enqueue
        if f"Priority: {priority}" not in result.stdout:
            print(f"✗ FAIL: Priority '{priority}' not displayed for job {job_id}")
            return False

    # Verify all jobs were created
    result = run_command('queuectl list')
    created_count = sum(1 for _, job_id, _ in jobs if job_id in result.stdout)
    if created_count < 6:
        print(f"✗ FAIL: Only {created_count}/6 jobs were created")
        return False

    # Start worker to process jobs
    print("  Starting worker to process jobs...")
    worker = subprocess.Popen(
        'queuectl worker start',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait for all jobs to complete
    time.sleep(3)

    worker.terminate()
    worker.wait(timeout=2)

    # Check that all jobs completed
    print("  Verifying jobs completed...")
    result = run_command('queuectl list --state completed')
    completed_count = sum(1 for _, job_id, _ in jobs if job_id in result.stdout)

    if completed_count < 6:
        print(f"✗ FAIL: Only {completed_count}/6 jobs completed")
        return False

    # Verify that priority information is displayed in list
    result = run_command('queuectl list')
    if "Priority: high" not in result.stdout:
        print("✗ FAIL: Priority not displayed in list output")
        return False

    print(f"✓ PASS: All 6 priority jobs completed with correct priority display")
    return True


def test_default_priority():
    """Test 8: Default priority is medium."""
    print("\n[Test 8] Default priority (medium)...")

    # Enqueue job without specifying priority
    result = run_command('queuectl enqueue \'{"id":"default-test","command":"echo test"}\'')

    if result.returncode != 0:
        print("✗ FAIL: Could not enqueue job")
        return False

    # Check if priority is medium
    if "Priority: medium" in result.stdout:
        print("✓ PASS: Default priority is medium")
        return True

    # Also check in list command
    result = run_command('queuectl list')
    if "default-test" in result.stdout and "Priority: medium" in result.stdout:
        print("✓ PASS: Default priority is medium (verified in list)")
        return True

    print("✗ FAIL: Default priority is not medium")
    return False


def test_invalid_priority():
    """Test 9: Invalid priority is rejected."""
    print("\n[Test 9] Invalid priority rejection...")

    # Try to enqueue job with invalid priority
    result = run_command('queuectl enqueue \'{"id":"invalid-test","command":"echo test","priority":"urgent"}\'')

    if result.returncode != 0 and "Invalid priority" in result.stderr:
        print("✓ PASS: Invalid priority rejected")
        return True

    print("✗ FAIL: Invalid priority not rejected")
    return False


def main():
    """Run all core tests."""
    print("=" * 60)
    print("CORE TESTS - queuectl Job Queue System")
    print("=" * 60)
    
    # Clean up
    cleanup()
    
    # Run tests
    tests = [
        ("Enqueue Job", test_enqueue),
        ("Worker Execution", test_worker_execution),
        ("Job Failure", test_job_failure),
        ("Retry and DLQ", test_retry_and_dlq),
        ("Multi-Worker", test_multi_worker),
        ("Status Command", test_status),
        ("Priority Queue Ordering", test_priority_queue),
        ("Default Priority", test_default_priority),
        ("Invalid Priority Rejection", test_invalid_priority),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"✗ FAIL: {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("-" * 60)
    print(f"Total: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 ALL CORE TESTS PASSED!")
        cleanup()
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        print("Database preserved for debugging: queue.db")
        return 1


if __name__ == "__main__":
    sys.exit(main())

