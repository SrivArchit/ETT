""

import copy
import math
from typing import List, Optional

Board = List[List[int]]
MOVES = ["UP", "DOWN", "LEFT", "RIGHT"]


# ── Board mechanics ──────────────────────────────────────────────────────────

def _slide_row_left(row: List[int]) -> List[int]:
    """Slide and merge a single row to the left."""
    # Remove zeros
    tiles = [t for t in row if t != 0]
    merged: List[int] = []
    skip = False
    for i in range(len(tiles)):
        if skip:
            skip = False
            continue
        if i + 1 < len(tiles) and tiles[i] == tiles[i + 1]:
            merged.append(tiles[i] * 2)
            skip = True
        else:
            merged.append(tiles[i])
    # Pad with zeros
    return merged + [0] * (4 - len(merged))


def _move_left(board: Board) -> Board:
    return [_slide_row_left(row) for row in board]


def _move_right(board: Board) -> Board:
    return [_slide_row_left(row[::-1])[::-1] for row in board]


def _transpose(board: Board) -> Board:
    return [list(row) for row in zip(*board)]


def _move_up(board: Board) -> Board:
    return _transpose(_move_left(_transpose(board)))


def _move_down(board: Board) -> Board:
    return _transpose(_move_right(_transpose(board)))


_MOVE_FN = {
    "UP": _move_up,
    "DOWN": _move_down,
    "LEFT": _move_left,
    "RIGHT": _move_right,
}


def apply_move(board: Board, direction: str) -> Board:
    """Return new board after applying direction (does not modify original)."""
    return _MOVE_FN[direction](copy.deepcopy(board))


def boards_equal(a: Board, b: Board) -> bool:
    return all(a[r][c] == b[r][c] for r in range(4) for c in range(4))


def get_empty_cells(board: Board):
    return [(r, c) for r in range(4) for c in range(4) if board[r][c] == 0]


def is_game_over(board: Board) -> bool:
    """True if no move changes the board."""
    for move in MOVES:
        if not boards_equal(board, apply_move(board, move)):
            return False
    return True


# ── Heuristic evaluation ─────────────────────────────────────────────────────

def _max_tile(board: Board) -> int:
    return max(board[r][c] for r in range(4) for c in range(4))


def _empty_count(board: Board) -> int:
    return sum(1 for r in range(4) for c in range(4) if board[r][c] == 0)


def _monotonicity(board: Board) -> float:
    """
    Reward boards where tile values decrease monotonically along rows/cols.
    Returns a score in [0, large positive float].
    """
    score = 0.0
    # Rows (left-to-right and right-to-left)
    for row in board:
        vals = [math.log2(t) if t > 0 else 0 for t in row]
        left = sum(max(0, vals[i] - vals[i + 1]) for i in range(3))
        right = sum(max(0, vals[i + 1] - vals[i]) for i in range(3))
        score -= min(left, right)
    # Columns (top-to-bottom and bottom-to-top)
    for c in range(4):
        col = [board[r][c] for r in range(4)]
        vals = [math.log2(t) if t > 0 else 0 for t in col]
        up = sum(max(0, vals[i] - vals[i + 1]) for i in range(3))
        down = sum(max(0, vals[i + 1] - vals[i]) for i in range(3))
        score -= min(up, down)
    return score


def _smoothness(board: Board) -> float:
    """Penalise large differences between adjacent tiles."""
    penalty = 0.0
    for r in range(4):
        for c in range(4):
            if board[r][c] == 0:
                continue
            val = math.log2(board[r][c])
            for dr, dc in [(0, 1), (1, 0)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 4 and 0 <= nc < 4 and board[nr][nc] != 0:
                    penalty -= abs(val - math.log2(board[nr][nc]))
    return penalty


def _merge_score(board: Board) -> float:
    """Reward pairs that can be merged."""
    score = 0.0
    for r in range(4):
        for c in range(4):
            if board[r][c] == 0:
                continue
            for dr, dc in [(0, 1), (1, 0)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < 4 and 0 <= nc < 4 and board[r][c] == board[nr][nc]:
                    score += math.log2(board[r][c])
    return score


def evaluate(board: Board) -> float:
    """
    Combined heuristic.  Weights tuned empirically for reasonable 2048 play.
    """
    empty = _empty_count(board)
    if empty == 0 and is_game_over(board):
        return float("-inf")

    return (
        27.0  * empty
        + 1.0   * math.log2(_max_tile(board) or 1)
        + 1.5   * _monotonicity(board)
        + 0.1   * _smoothness(board)
        + 1.0   * _merge_score(board)
    )


# ── Expectimax search ────────────────────────────────────────────────────────

# Tile spawn probabilities: 90 % → 2, 10 % → 4
_SPAWN_PROBS = [(2, 0.9), (4, 0.1)]


def _expectimax(board: Board, depth: int, is_player: bool) -> float:
    """Recursive expectimax."""
    if depth == 0 or is_game_over(board):
        return evaluate(board)

    if is_player:
        best = float("-inf")
        for move in MOVES:
            new_board = apply_move(board, move)
            if boards_equal(new_board, board):
                continue  # invalid move
            val = _expectimax(new_board, depth - 1, False)
            if val > best:
                best = val
        return best if best != float("-inf") else evaluate(board)
    else:
        # Chance node: average over all empty-cell × tile-value combinations
        empty = get_empty_cells(board)
        if not empty:
            return evaluate(board)
        total = 0.0
        for r, c in empty:
            for tile, prob in _SPAWN_PROBS:
                board[r][c] = tile
                total += prob * _expectimax(board, depth - 1, True)
                board[r][c] = 0
        return total / len(empty)


def get_best_move(board: Board, depth: int = 3) -> str:
    """
    Given a 4×4 board (nested list of ints), return the best move string.
    Depth-3 expectimax provides a good balance of quality vs. response time.
    Falls back to the first valid move if all scores are equal.
    """
    best_move: Optional[str] = None
    best_score = float("-inf")

    for move in MOVES:
        new_board = apply_move(board, move)
        if boards_equal(new_board, board):
            continue  # move has no effect
        score = _expectimax(new_board, depth - 1, False)
        if score > best_score:
            best_score = score
            best_move = move

    # Fallback: first valid move
    if best_move is None:
        for move in MOVES:
            if not boards_equal(apply_move(board, move), board):
                return move
        return "UP"  # game over, doesn't matter

    return best_move
