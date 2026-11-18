import os
import json
import glob

RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "results"))

def parse_l1():
    rates = [5, 20, 50]
    summary = {}
    for r in rates:
        runs = []
        for run_idx in [1, 2, 3]:
            path = os.path.join(RESULTS_DIR, f"l1_{r}rps_run{run_idx}.json")
            with open(path) as f:
                data = json.load(f)
            m = data["metrics"]
            http_reqs = m["http_reqs"]["count"]
            rate = m["http_reqs"]["rate"]
            fail_rate = m.get("http_req_failed", {}).get("value", 0.0) * 100
            dur = m["http_req_duration"]
            runs.append({
                "run": run_idx,
                "target_rate": r,
                "achieved_rate": round(rate, 2),
                "total_reqs": http_reqs,
                "error_pct": round(fail_rate, 2),
                "med_ms": round(dur["med"], 2),
                "avg_ms": round(dur["avg"], 2),
                "p90_ms": round(dur["p(90)"], 2),
                "p95_ms": round(dur["p(95)"], 2),
                "p99_ms": round(dur["p(99)"], 2),
                "min_ms": round(dur["min"], 2),
                "max_ms": round(dur["max"], 2),
            })
        runs.sort(key=lambda x: x["med_ms"])
        median_run = runs[1] # middle of 3
        summary[r] = {
            "runs": runs,
            "median": median_run
        }
    return summary

def parse_l2():
    workers = [1, 2, 3]
    summary = {}
    for w in workers:
        runs = []
        for run_idx in [1, 2, 3]:
            path = os.path.join(RESULTS_DIR, f"l2_w{w}_run{run_idx}.json")
            with open(path) as f:
                data = json.load(f)
            m = data["metrics"]
            # drain time is test duration in seconds
            # iteration_duration or data sent rate or duration from k6 root
            # Let's check testRunDurationMs or jobs_completed_total rate
            completed = m["jobs_completed_total"]["count"]
            completed_rate = m["jobs_completed_total"]["rate"]
            drain_time_s = completed / completed_rate if completed_rate > 0 else 0
            
            e2e = m["job_e2e_duration_ms"]
            runs.append({
                "run": run_idx,
                "workers": w,
                "jobs_completed": completed,
                "drain_time_s": round(drain_time_s, 2),
                "completed_per_s": round(completed_rate, 2),
                "e2e_med_s": round(e2e["med"] / 1000.0, 2),
                "e2e_p90_s": round(e2e["p(90)"] / 1000.0, 2),
                "e2e_p95_s": round(e2e["p(95)"] / 1000.0, 2),
                "e2e_min_s": round(e2e["min"] / 1000.0, 2),
                "e2e_max_s": round(e2e["max"] / 1000.0, 2),
            })
        runs.sort(key=lambda x: x["drain_time_s"])
        median_run = runs[1] # middle of 3
        summary[w] = {
            "runs": runs,
            "median": median_run
        }
    return summary

def main():
    l1 = parse_l1()
    l2 = parse_l2()
    
    print("=== L1 API Latency Summary (Median of 3 runs) ===")
    print("| Target Rate | Achieved Rate | Error % | p50 (med) | p90 | p95 | p99 |")
    print("|---|---|---|---|---|---|---|")
    for r in [5, 20, 50]:
        med = l1[r]["median"]
        print(f"| {r} req/s | {med['achieved_rate']} req/s | {med['error_pct']}% | {med['med_ms']} ms | {med['p90_ms']} ms | {med['p95_ms']} ms | {med['p99_ms']} ms |")
        
    print("\n=== L2 Worker Scaling Summary (Median of 3 runs) ===")
    base_tput = l2[1]["median"]["completed_per_s"]
    print("| Workers | Drain Time | Completed Jobs/s | Speed-up vs 1 Worker | e2e p50 | e2e p95 |")
    print("|---|---|---|---|---|---|")
    for w in [1, 2, 3]:
        med = l2[w]["median"]
        speedup = round(med["completed_per_s"] / base_tput, 2)
        print(f"| {w} | {med['drain_time_s']} s | {med['completed_per_s']} jobs/s | {speedup}x | {med['e2e_med_s']} s | {med['e2e_p95_s']} s |")

if __name__ == "__main__":
    main()
