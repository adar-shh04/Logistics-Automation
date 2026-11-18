import concurrent.futures
from app import audit
from app.db import SessionLocal
from app.models import AuditLog


def test_audit_single_append_and_verify():
    db = SessionLocal()
    try:
        initial_count = db.query(AuditLog).count()
        h1 = audit.append_audit("TEST_ACTION_1", {"msg": "first"})
        assert len(h1) == 64

        h2 = audit.append_audit("TEST_ACTION_2", {"msg": "second"})
        assert len(h2) == 64
        assert h1 != h2

        ok, msg = audit.verify_chain(db)
        assert ok is True
        assert "Successfully verified" in msg
        assert db.query(AuditLog).count() == initial_count + 2
    finally:
        db.close()


def test_audit_concurrency_3_workers():
    """
    Simulates 3 concurrent worker threads appending 50 records each (150 total).
    Verifies that postgres advisory locking prevents race conditions and produces
    a strictly valid, unbroken hash chain.
    """
    entries_per_thread = 50
    num_threads = 3

    def worker_append(thread_id):
        hashes = []
        for seq in range(entries_per_thread):
            h = audit.append_audit(
                f"CONCURRENT_EVENT_{thread_id}",
                {"worker": thread_id, "sequence": seq, "data": f"payload-{seq}"}
            )
            hashes.append(h)
        return hashes

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker_append, tid) for tid in range(num_threads)]
        all_results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Check that all 150 entries returned valid sha256 hashes
    total_appended = sum(len(res) for res in all_results)
    assert total_appended == num_threads * entries_per_thread

    # Verify that the complete chain in DB is cryptographically sound
    ok, msg = audit.verify_chain()
    assert ok is True, f"Audit chain broken after concurrency run: {msg}"


def test_audit_verify_detects_tampering():
    db = SessionLocal()
    try:
        # Add a record
        h = audit.append_audit("TAMPER_TEST", {"secret": 123})
        last_row = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        original_hash = last_row.hash

        # Tamper with the row's hash
        last_row.hash = "0000000000000000000000000000000000000000000000000000000000000000"
        db.commit()

        ok, msg = audit.verify_chain(db)
        assert ok is False
        assert "Broken chain" in msg

        # Restore original hash
        last_row.hash = original_hash
        db.commit()

        ok_restored, _ = audit.verify_chain(db)
        assert ok_restored is True
    finally:
        db.close()


if __name__ == "__main__":
    print("Running audit tests...")
    test_audit_single_append_and_verify()
    print("Single append test: PASSED")
    test_audit_verify_detects_tampering()
    print("Tamper detection test: PASSED")
    test_audit_concurrency_3_workers()
    print("3-worker concurrency test: PASSED")
    print("All audit tests completed successfully!")
