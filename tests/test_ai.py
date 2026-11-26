import random

import pytest

from Ai.ai_player import MOVES, apply_move, boards_equal, get_best_move, is_game_over
from bench import move_with_score


def row_board(row):
    return [row[:], [0] * 4, [0] * 4, [0] * 4]


@pytest.mark.parametrize(
    "row, expected",
    [
        ([2, 2, 2, 2], [4, 4, 0, 0]),
        ([2, 0, 2, 4], [4, 4, 0, 0]),
        ([4, 4, 8, 8], [8, 16, 0, 0]),
        ([2, 4, 8, 16], [2, 4, 8, 16]),
        ([0, 0, 0, 2], [2, 0, 0, 0]),
    ],
)
def test_left_slide_and_merge(row, expected):
    assert apply_move(row_board(row), "LEFT")[0] == expected


def test_right_up_down():
    assert apply_move(row_board([2, 2, 4, 0]), "RIGHT")[0] == [0, 0, 4, 4]
    column = [[2, 0, 0, 0], [2, 0, 0, 0], [4, 0, 0, 0], [0, 0, 0, 0]]
    assert [r[0] for r in apply_move(column, "UP")] == [4, 4, 0, 0]
    assert [r[0] for r in apply_move(column, "DOWN")] == [0, 0, 4, 4]


def test_apply_move_does_not_mutate_input():
    board = row_board([2, 2, 0, 0])
    apply_move(board, "LEFT")
    assert board[0] == [2, 2, 0, 0]


def test_game_over_detection():
    stuck = [[2, 4, 2, 4], [4, 2, 4, 2], [2, 4, 2, 4], [4, 2, 4, 2]]
    assert is_game_over(stuck)
    one_merge_left = [row[:] for row in stuck]
    one_merge_left[0][1] = 2
    assert not is_game_over(one_merge_left)


def random_board(rng, fill=0.6):
    return [
        [rng.choice([2, 4, 8, 16, 32, 64, 128]) if rng.random() < fill else 0 for _ in range(4)]
        for _ in range(4)
    ]


def test_best_move_is_always_a_legal_move():
    rng = random.Random(42)
    checked = 0
    while checked < 25:
        board = random_board(rng)
        if is_game_over(board):
            continue
        move = get_best_move(board)
        assert move in MOVES
        assert not boards_equal(apply_move(board, move), board), "agent picked a move that changes nothing"
        checked += 1


def test_benchmark_rules_match_the_agent():
    """bench.py scores games with its own move function; it must match the agent's rules."""
    rng = random.Random(7)
    for _ in range(200):
        board = random_board(rng, fill=0.7)
        for move in MOVES:
            new_board, gained = move_with_score(board, move)
            assert new_board == apply_move(board, move)
            assert gained >= 0
