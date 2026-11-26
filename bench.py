"""
bench.py
========
Headless benchmark for the Expectimax 2048 agent in App/Ai/ai_player.py.

Plays N full games with the same rules as the web game (a new tile is a 2 with
90% probability and a 4 with 10%), letting the agent pick every move, and
reports how often it reaches 2048, score statistics, the max-tile
distribution and the average time per move.

Usage
-----
    python bench.py --games 100 --depth 3 --workers 2
    python bench.py --games 5 --markdown >> "$GITHUB_STEP_SUMMARY"
"""

import argparse
import os
import platform
import random
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "App"))

from Ai.ai_player import get_best_move, is_game_over  # noqa: E402

Board = List[List[int]]
MAX_MOVES_PER_GAME = 50_000  # safety cap, never reached in practice


# ── Game rules with scoring (same rules as ai_player.apply_move) ─────────────

def _slide_row_left(row: List[int]) -> Tuple[List[int], int]:
    tiles = [t for t in row if t]
    out: List[int] = []
    gained = 0
    i = 0
    while i < len(tiles):
        if i + 1 < len(tiles) and tiles[i] == tiles[i + 1]:
            out.append(tiles[i] * 2)
            gained += tiles[i] * 2
            i += 2
        else:
            out.append(tiles[i])
            i += 1
    return out + [0] * (4 - len(out)), gained


def _transpose(board: Board) -> Board:
    return [list(row) for row in zip(*board)]


def move_with_score(board: Board, direction: str) -> Tuple[Board, int]:
    """Return (new_board, points_gained) for a move. Does not modify board."""
    if direction in ("UP", "DOWN"):
        board = _transpose(board)
    rows = board if direction in ("LEFT", "UP") else [r[::-1] for r in board]
    new_rows, gained = [], 0
    for row in rows:
        slid, g = _slide_row_left(row)
        new_rows.append(slid)
        gained += g
    if direction in ("RIGHT", "DOWN"):
        new_rows = [r[::-1] for r in new_rows]
    if direction in ("UP", "DOWN"):
        new_rows = _transpose(new_rows)
    return new_rows, gained


def _spawn(board: Board, rng: random.Random) -> None:
    empty = [(r, c) for r in range(4) for c in range(4) if board[r][c] == 0]
    r, c = rng.choice(empty)
    board[r][c] = 2 if rng.random() < 0.9 else 4


# ── One game ──────────────────────────────────────────────────────────────────

def play_game(args: Tuple[int, int]) -> Dict:
    seed, depth = args
    rng = random.Random(seed)
    board: Board = [[0] * 4 for _ in range(4)]
    _spawn(board, rng)
    _spawn(board, rng)

    score = moves = 0
    reached_2048_at = None
    think_time = 0.0

    while moves < MAX_MOVES_PER_GAME and not is_game_over(board):
        t0 = time.perf_counter()
        direction = get_best_move(board, depth=depth)
        think_time += time.perf_counter() - t0

        new_board, gained = move_with_score(board, direction)
        if new_board == board:  # agent returned a no-op move; stop safely
            break
        board, score, moves = new_board, score + gained, moves + 1
        if reached_2048_at is None and max(map(max, board)) >= 2048:
            reached_2048_at = moves
        _spawn(board, rng)

    return {
        "seed": seed,
        "score": score,
        "moves": moves,
        "max_tile": max(map(max, board)),
        "reached_2048_at": reached_2048_at,
        "ms_per_move": 1000 * think_time / max(moves, 1),
    }


# ── Report ────────────────────────────────────────────────────────────────────

def summarize(results: List[Dict], depth: int, wall: float) -> Dict:
    n = len(results)
    scores = [r["score"] for r in results]
    tiles = Counter(r["max_tile"] for r in results)
    return {
        "games": n,
        "depth": depth,
        "reached_2048_pct": 100 * sum(r["max_tile"] >= 2048 for r in results) / n,
        "reached_4096_pct": 100 * sum(r["max_tile"] >= 4096 for r in results) / n,
        "avg_score": statistics.mean(scores),
        "median_score": statistics.median(scores),
        "best_score": max(scores),
        "avg_moves": statistics.mean(r["moves"] for r in results),
        "ms_per_move": statistics.mean(r["ms_per_move"] for r in results),
        "tile_dist": dict(sorted(tiles.items(), reverse=True)),
        "wall_seconds": wall,
    }


def print_text(s: Dict) -> None:
    print(f"Games played        : {s['games']} (search depth {s['depth']})")
    print(f"Reached 2048        : {s['reached_2048_pct']:.0f}% of games")
    print(f"Reached 4096        : {s['reached_4096_pct']:.0f}% of games")
    print(f"Score (avg / median): {s['avg_score']:,.0f} / {s['median_score']:,.0f}")
    print(f"Best score          : {s['best_score']:,}")
    print(f"Moves per game (avg): {s['avg_moves']:,.0f}")
    print(f"Time per move (avg) : {s['ms_per_move']:.1f} ms")
    print("Max tile reached    : " + ", ".join(f"{t}: {c}" for t, c in s["tile_dist"].items()))
    print(f"Wall time           : {s['wall_seconds']:.0f} s on {platform.python_implementation()} {platform.python_version()}")


def print_markdown(s: Dict) -> None:
    print(f"### 2048 AI benchmark — {s['games']} games, depth {s['depth']}\n")
    print("| Metric | Value |")
    print("|---|---|")
    print(f"| Reached 2048 | {s['reached_2048_pct']:.0f}% of games |")
    print(f"| Reached 4096 | {s['reached_4096_pct']:.0f}% of games |")
    print(f"| Average score | {s['avg_score']:,.0f} |")
    print(f"| Median score | {s['median_score']:,.0f} |")
    print(f"| Best score | {s['best_score']:,} |")
    print(f"| Average moves per game | {s['avg_moves']:,.0f} |")
    print(f"| Average time per move | {s['ms_per_move']:.1f} ms |")
    print("\n| Max tile | Games |")
    print("|---|---|")
    for tile, count in s["tile_dist"].items():
        print(f"| {tile} | {count} |")


def main() -> None:
    p = argparse.ArgumentParser(description="Benchmark the Expectimax 2048 agent.")
    p.add_argument("--games", type=int, default=20)
    p.add_argument("--depth", type=int, default=3, help="search depth passed to get_best_move")
    p.add_argument("--seed", type=int, default=0, help="first random seed (game i uses seed+i)")
    p.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    p.add_argument("--markdown", action="store_true", help="print a Markdown table")
    a = p.parse_args()

    jobs = [(a.seed + i, a.depth) for i in range(a.games)]
    t0 = time.perf_counter()
    if a.workers > 1:
        with ProcessPoolExecutor(max_workers=a.workers) as pool:
            results = list(pool.map(play_game, jobs))
    else:
        results = [play_game(j) for j in jobs]
    summary = summarize(results, a.depth, time.perf_counter() - t0)

    (print_markdown if a.markdown else print_text)(summary)


if __name__ == "__main__":
    main()
