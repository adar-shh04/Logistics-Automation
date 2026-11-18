import subprocess
import time
import json
import os
import sys
import glob
import urllib.request
import urllib.error

RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "results"))
FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures"))
EVAL_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "eval", "data", "synthetic"))

COMPOSE_FILES = [
    "-f", "docker-compose.yml",
    "-f", "docker-compose.observability.yml",
    "-f", "docker-compose.loadtest.yml"
]

def run_cmd(cmd, check=True):
    print(f"--> Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    res = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True)
    if check and res.returncode != 0:
        print(f"STDERR: {res.stderr}")
        raise RuntimeError(f"Command failed with code {res.returncode}: {res.stderr}")
    return res

def wait_for_api(timeout=60):
    start = time.time()
    url = "http://127.0.0.1:8000/health"
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    print("API is healthy!")
                    return True
        except Exception:
            pass
        time.sleep(1)
    raise TimeoutError(f"API did not become healthy within {timeout}s")

def reset_stack(scale_workers=1, stub_mode=True, stub_delay_ms=500):
    print(f"\n==========================================")
    print(f"RESETTING STACK: workers={scale_workers}, stub={stub_mode}, delay={stub_delay_ms}ms")
    print(f"==========================================")
    run_cmd(["docker", "compose"] + COMPOSE_FILES + ["down", "-v"])
    
    env = os.environ.copy()
    env["WORKER_STUB_MODE"] = "true" if stub_mode else "false"
    env["WORKER_STUB_DELAY_MS"] = str(stub_delay_ms)
    
    up_cmd = ["docker", "compose"] + COMPOSE_FILES + ["up", "-d", f"--scale", f"worker={scale_workers}"]
    subprocess.run(up_cmd, env=env, check=True)
    wait_for_api()
    try:
        run_cmd(["docker", "exec", "-u", "0", "logistics_api", "chmod", "-R", "777", "/data/uploads"], check=False)
    except Exception:
        pass
    time.sleep(3) # Give worker a moment to connect

def run_k6(script, env_vars, summary_file):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_rel = os.path.relpath(summary_file, RESULTS_DIR)
    container_summary_path = f"/loadtests/results/{out_rel}".replace("\\", "/")
    
    cmd = [
        "docker", "run", "--rm", "-i",
        "--network", "logistics-automation_default",
        "-v", f"{os.path.abspath(os.path.dirname(__file__))}:/loadtests",
        "grafana/k6:0.49.0", "run",
        "--summary-export", container_summary_path,
    ]
    for k, v in env_vars.items():
        cmd.extend(["-e", f"{k}={v}"])
    cmd.append(f"/loadtests/{script}")
    
    print(f"Running k6 {script} -> {summary_file}")
    res = run_cmd(cmd, check=True)
    print(res.stdout[-600:] if len(res.stdout) > 600 else res.stdout)
    return res

def verify_l2_db_and_ledger(expected_count=300):
    print(f"Verifying DB transactions count and ledger chain...")
    query = "SELECT count(*) AS total, count(DISTINCT document_id) AS distinct_docs FROM transactions;"
    res = run_cmd(["docker", "exec", "logistics_db", "psql", "-U", "postgres", "-d", "trade_db", "-t", "-A", "-c", query])
    parts = res.stdout.strip().split("|")
    total = int(parts[0])
    distinct = int(parts[1])
    print(f"DB check: total={total}, distinct_docs={distinct} (expected {expected_count})")
    assert total == expected_count, f"Expected {expected_count} transactions, got {total}"
    assert distinct == expected_count, f"Expected {expected_count} distinct documents, got {distinct}"
    
    # Verify audit ledger
    worker_res = run_cmd(["docker", "ps", "--filter", "name=worker", "--format", "{{.Names}}"])
    worker_names = [n.strip() for n in worker_res.stdout.strip().splitlines() if n.strip()]
    first_worker = worker_names[0]
    
    audit_res = run_cmd(["docker", "exec", first_worker, "python", "-m", "app.audit", "verify"])
    print(f"Audit verify: {audit_res.stdout.strip()}")
    assert "VERIFY SUCCESS" in audit_res.stdout, "Audit chain verification failed!"
    print("Verification PASSED!")

def run_l1():
    print("\n==========================================")
    print("STARTING L1: API Latency Tests (5, 20, 50 rps x 3 runs)")
    print("==========================================")
    reset_stack(scale_workers=1, stub_mode=True, stub_delay_ms=500)
    
    rates = [5, 20, 50]
    for rate in rates:
        for run_idx in [1, 2, 3]:
            summary_file = os.path.join(RESULTS_DIR, f"l1_{rate}rps_run{run_idx}.json")
            if os.path.exists(summary_file):
                print(f"Skipping existing {summary_file}")
                continue
            print(f"\n--- L1: {rate} rps, Run {run_idx}/3 ---")
            env_vars = {
                "RATE": str(rate),
                "DURATION": "60s",
                "BASE_URL": "http://api:8000"
            }
            run_k6("upload_api.js", env_vars, summary_file)
            time.sleep(2)

def run_l2():
    print("\n==========================================")
    print("STARTING L2: Worker Scaling Tests (1, 2, 3 workers x 3 runs)")
    print("==========================================")
    workers_list = [1, 2, 3]
    for w in workers_list:
        for run_idx in [1, 2, 3]:
            summary_file = os.path.join(RESULTS_DIR, f"l2_w{w}_run{run_idx}.json")
            if os.path.exists(summary_file):
                print(f"Skipping existing {summary_file}")
                continue
            print(f"\n--- L2: {w} worker(s), Run {run_idx}/3 ---")
            reset_stack(scale_workers=w, stub_mode=True, stub_delay_ms=500)
            env_vars = {
                "N": "300",
                "VUS": "50",
                "BASE_URL": "http://api:8000"
            }
            run_k6("end_to_end.js", env_vars, summary_file)
            verify_l2_db_and_ledger(expected_count=300)
            time.sleep(2)

def run_l3():
    print("\n==========================================")
    print("STARTING L3: Real Pipeline Sample (20 sequential jobs, 1 worker, real OCR)")
    print("==========================================")
    summary_file = os.path.join(RESULTS_DIR, "l3_real_ocr.json")
    if os.path.exists(summary_file):
        print(f"Skipping existing {summary_file}")
        return
    
    reset_stack(scale_workers=1, stub_mode=False)
    
    # Pick 20 synthetic invoices
    invoices = [f"inv_{i:03d}.png" for i in range(1, 21)]
    durations = []
    
    print("Uploading 20 synthetic invoices sequentially...")
    import requests # or urllib
    for idx, fname in enumerate(invoices, 1):
        fpath = os.path.join(EVAL_DATA_DIR, fname)
        t0 = time.time()
        
        # Upload using curl.exe or python multipart
        cmd = f'curl.exe -s -F "file=@{fpath}" http://127.0.0.1:8000/upload'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        assert res.returncode == 0, f"Upload failed: {res.stderr}"
        body = json.loads(res.stdout)
        uid = body["document_id"]
        
        # Poll until complete
        completed = False
        while not completed and time.time() - t0 < 60:
            time.sleep(0.5)
            status_cmd = f"curl.exe -s http://127.0.0.1:8000/status/{uid}"
            sres = subprocess.run(status_cmd, shell=True, capture_output=True, text=True)
            if sres.returncode == 0:
                sbody = json.loads(sres.stdout)
                if sbody.get("status") == "completed":
                    completed = True
                    break
                elif sbody.get("status") == "failed":
                    raise RuntimeError(f"Job {uid} failed!")
        
        duration = time.time() - t0
        durations.append(duration)
        print(f"[{idx}/20] {fname} ({uid}) finished in {duration:.2f}s")
    
    # Scrape worker metrics from container
    worker_res = run_cmd(["docker", "ps", "--filter", "name=worker", "--format", "{{.Names}}"])
    first_worker = worker_res.stdout.strip().splitlines()[0]
    metrics_res = run_cmd(["docker", "exec", first_worker, "curl", "-s", "http://127.0.0.1:9100/metrics"])
    
    durations.sort()
    n = len(durations)
    med = durations[n // 2] if n % 2 != 0 else (durations[n // 2 - 1] + durations[n // 2]) / 2.0
    p95_idx = int(n * 0.95)
    p95 = durations[min(p95_idx, n - 1)]
    
    # Extract stage durations
    stages = {}
    for line in metrics_res.stdout.splitlines():
        if line.startswith("logistics_stage_duration_seconds_sum"):
            # e.g. logistics_stage_duration_seconds_sum{stage="ocr"} 25.123
            parts = line.split()
            stage_name = line.split('stage="')[1].split('"')[0]
            val = float(parts[1])
            stages[stage_name] = val / n # average stage duration
            
    l3_result = {
        "job_count": n,
        "durations_seconds": durations,
        "median_seconds": round(med, 3),
        "p95_seconds": round(p95, 3),
        "min_seconds": round(min(durations), 3),
        "max_seconds": round(max(durations), 3),
        "avg_stage_durations_seconds": {k: round(v, 4) for k, v in stages.items()},
        "metrics_raw": metrics_res.stdout
    }
    
    with open(summary_file, "w") as f:
        json.dump(l3_result, f, indent=2)
    print(f"L3 complete: median={med:.2f}s, p95={p95:.2f}s. Saved to {summary_file}")

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "all"
    if action in ("l1", "all"):
        run_l1()
    if action in ("l2", "all"):
        run_l2()
    if action in ("l3", "all"):
        run_l3()
