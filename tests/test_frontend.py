"""Browser tests for App/static/game.js.

The AI picks moves with the rules in Ai/ai_player.py, but the page plays them
with applyMove() in game.js. If the two disagree about what a move does, the AI
is playing a different game from the one on screen. (game.js once had UP and
DOWN swapped, which made the in-browser AI play close to randomly.)

Needs Playwright and Chromium:
    pip install -r requirements-dev.txt
    python -m playwright install chromium
Set CHROME_PATH to use an installed Chrome instead. Skipped if Playwright is missing.
"""
import os
import random
import threading

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from werkzeug.serving import make_server  # noqa: E402

import app as flask_app  # noqa: E402
from Ai.ai_player import apply_move  # noqa: E402

MOVES = ["UP", "DOWN", "LEFT", "RIGHT"]


@pytest.fixture(scope="module")
def page():
    server = make_server("127.0.0.1", 0, flask_app.app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH"))
        pg = browser.new_page()
        pg.goto(f"http://127.0.0.1:{server.server_port}/")
        yield pg
        browser.close()
    server.shutdown()


def browser_move(page, board, direction):
    return page.evaluate(
        "([b, d]) => { board = b.map(r => [...r]); applyMove(d); return board; }",
        [board, direction],
    )


def test_browser_moves_match_the_ai(page):
    rng = random.Random(0)
    for _ in range(100):
        board = [[rng.choice([0, 0, 2, 2, 4, 8, 16]) for _ in range(4)] for _ in range(4)]
        for direction in MOVES:
            assert browser_move(page, board, direction) == apply_move(board, direction), direction


@pytest.mark.parametrize("key, cell", [
    ("ArrowUp", (0, 1)), ("ArrowDown", (3, 1)), ("ArrowLeft", (1, 0)), ("ArrowRight", (1, 3)),
    ("w", (0, 1)), ("s", (3, 1)), ("a", (1, 0)), ("d", (1, 3)),
])
def test_keys_move_tiles_that_way(page, key, cell):
    # Start from a lone 8, which can't be confused with the 2 or 4 that spawns after the move.
    page.evaluate("() => { board = [[0,0,0,0],[0,8,0,0],[0,0,0,0],[0,0,0,0]]; gameOver = false; }")
    page.keyboard.press(key)
    row, col = cell
    assert page.evaluate(f"board[{row}][{col}]") == 8


def test_ai_step_ends_the_game_when_no_moves_are_left(page):
    page.evaluate("() => { board = [[2,4,2,4],[4,2,4,2],[2,4,2,4],[4,2,4,2]]; gameOver = false; }")
    page.evaluate("aiStep()")  # async; evaluate waits for it to finish
    assert page.evaluate("gameOver") is True
    assert page.is_visible("#overlay")
