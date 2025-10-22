"""bench_latency.py

Simple warm + latency measurement script for the FastLane RAG app.
Run this after starting the server (uvicorn backend.main:app).
"""

import requests
import time
import statistics

BASE = "http://127.0.0.1:8000"

def warm():
    print("Warming retrieval endpoints...")
    try:
        r = requests.get(f"{BASE}/test-retrieval?query=Where%20can%20I%20park?")
        print("/test-retrieval:", r.status_code)
        r = requests.get(f"{BASE}/test-compose?query=Where%20can%20I%20park?")
        print("/test-compose:", r.status_code)
    except Exception as e:
        print("Warm failed:", e)


def measure_chat(n=5, session_id='bench-session'):
    payload = {"session_id": session_id, "message": "Where can I park?"}
    latencies = []

    for i in range(n):
        start = time.time()
        try:
            r = requests.post(f"{BASE}/chat", json=payload, timeout=10)
            elapsed = (time.time() - start) * 1000
            latencies.append(elapsed)
            print(f"Run {i+1}: {elapsed:.2f} ms, status: {r.status_code}")
        except Exception as e:
            print(f"Run {i+1} failed:", e)

    if latencies:
        print("\nResults (ms):")
        print("p50:", statistics.median(latencies))
        print("min:", min(latencies))
        print("max:", max(latencies))
        print("mean:", statistics.mean(latencies))


if __name__ == '__main__':
    warm()
    time.sleep(0.5)
    measure_chat(n=5)
