#!/usr/bin/env python3
"""
Data-locality prototype: array-backed Python list versus linked list.

The benchmark measures sequential traversal and summation. Both structures
contain the same integer objects. Construction is outside the timed region,
so the experiment focuses on traversal rather than allocation cost.

Run:
    python locality_benchmark.py
    python locality_benchmark.py --sizes 100000 250000 500000 1000000 --repeats 9

The script uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import timeit
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Node:
    """One linked-list node; slots reduce per-node dictionary overhead."""
    value: int
    next: "Node | None" = None


def build_linked_list(values: list[int]) -> Node | None:
    """Build a singly linked list while preserving the input value objects."""
    head: Node | None = None
    tail: Node | None = None

    for value in values:
        node = Node(value=value)
        if head is None:
            head = node
        else:
            assert tail is not None
            tail.next = node
        tail = node

    return head


def sum_array_backed(values: list[int]) -> int:
    """Sequentially traverse an array-backed Python list."""
    total = 0
    for value in values:
        total += value
    return total


def sum_linked(head: Node | None) -> int:
    """Sequentially traverse a linked list by following next pointers."""
    total = 0
    current = head
    while current is not None:
        total += current.value
        current = current.next
    return total


def median_runtime(function, repeats: int) -> float:
    """Return the median of repeated one-run measurements."""
    function()  # warm-up; excluded from recorded samples
    samples = timeit.repeat(function, repeat=repeats, number=1)
    return statistics.median(samples)


def run_benchmark(sizes: list[int], repeats: int, output_csv: Path) -> list[dict]:
    """Benchmark each size and write reproducible results to CSV."""
    rows: list[dict] = []

    for size in sizes:
        # Create the common data once; both structures hold the same values.
        values = list(range(size))
        linked_head = build_linked_list(values)

        # Verify correctness before measuring performance.
        array_checksum = sum_array_backed(values)
        linked_checksum = sum_linked(linked_head)
        if array_checksum != linked_checksum:
            raise AssertionError("The two data structures produced different sums.")

        array_seconds = median_runtime(
            lambda: sum_array_backed(values), repeats
        )
        linked_seconds = median_runtime(
            lambda: sum_linked(linked_head), repeats
        )

        speedup = linked_seconds / array_seconds
        time_reduction_pct = (
            (linked_seconds - array_seconds) / linked_seconds
        ) * 100.0

        rows.append({
            "elements": size,
            "array_seconds_median": array_seconds,
            "linked_list_seconds_median": linked_seconds,
            "speedup_array_vs_linked": speedup,
            "array_time_reduction_percent": time_reduction_pct,
            "checksum": array_checksum,
        })

    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare sequential traversal of an array-backed list and linked list."
    )
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[100_000, 250_000, 500_000, 1_000_000],
        help="Dataset sizes (default: 100000 250000 500000 1000000).",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=9,
        help="Number of timing repetitions per structure and size (default: 9).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark_results.csv"),
        help="CSV output path (default: benchmark_results.csv).",
    )
    args = parser.parse_args()

    if args.repeats < 3:
        parser.error("--repeats must be at least 3 for a useful median.")
    if any(size <= 0 for size in args.sizes):
        parser.error("All dataset sizes must be positive.")

    rows = run_benchmark(args.sizes, args.repeats, args.output)

    print("DATA-LOCALITY BENCHMARK")
    print(f"Python: {__import__('sys').version.split()[0]}")
    print(f"Platform: {__import__('platform').platform()}")
    print(f"Repeats per measurement: {args.repeats}; statistic: median")
    print()
    print(
        f"{'Elements':>12} {'Array (s)':>12} {'Linked (s)':>12} "
        f"{'Speedup':>10} {'Time saved':>12}"
    )
    print("-" * 64)
    for row in rows:
        print(
            f"{row['elements']:>12,} "
            f"{row['array_seconds_median']:>12.6f} "
            f"{row['linked_list_seconds_median']:>12.6f} "
            f"{row['speedup_array_vs_linked']:>9.2f}x "
            f"{row['array_time_reduction_percent']:>11.1f}%"
        )
    print()
    print("Correctness: all array and linked-list checksums matched.")
    print(f"Results saved to: {args.output}")


if __name__ == "__main__":
    main()
