
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import psutil

process = psutil.Process()
memory_before_mb = process.memory_info().rss / (1024 * 1024)

start = time.perf_counter()
from services.recommendation_service import recommendation_service
initialization_seconds = time.perf_counter() - start

memory_after_mb = process.memory_info().rss / (1024 * 1024)

queries = [
    "database management SQL",
    "python programming",
    "machine learning",
    "web development",
    "data science",
] * 4


def run_query(query):
    start_time = time.perf_counter()
    results = recommendation_service.recommend_courses(query, top_n=5)
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return elapsed_ms, len(results)


start = time.perf_counter()
latencies = []

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [
        executor.submit(run_query, query)
        for query in queries
    ]

    for future in as_completed(futures):
        latency_ms, result_count = future.result()
        latencies.append(latency_ms)

total_seconds = time.perf_counter() - start

print("\n--- Recommendation Profiling ---")
print(f"RSS before service initialization: {memory_before_mb:.2f} MB")
print(f"RSS after service initialization:  {memory_after_mb:.2f} MB")
print(f"RSS increase: {memory_after_mb - memory_before_mb:.2f} MB")
print(f"Service initialization time: {initialization_seconds:.3f} sec")
print(f"Concurrent requests: {len(queries)}")
print(f"Worker threads: 5")
print(f"Total elapsed time: {total_seconds:.3f} sec")
print(f"Mean request latency: {sum(latencies) / len(latencies):.2f} ms")
print(f"Max request latency: {max(latencies):.2f} ms")
