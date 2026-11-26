import pytest

import app as flask_app


@pytest.fixture()
def client():
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


def test_home_page_loads(client):
    assert client.get("/").status_code == 200


def test_ai_move_endpoint_returns_a_move(client):
    board = [[2, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    res = client.post("/ai_move", json={"board": board})
    assert res.status_code == 200
    assert res.get_json()["move"] in {"UP", "DOWN", "LEFT", "RIGHT"}


def test_submit_score_rejects_bad_values(client):
    assert client.post("/submit_score", json={"player": "x", "score": -5}).status_code == 400
    assert client.post("/submit_score", json={"player": "x", "score": "100"}).status_code == 400


def test_submitted_score_shows_on_leaderboard(client):
    res = client.post("/submit_score", json={"player": "ci-bot", "score": 123456})
    assert res.status_code == 200
    top = client.get("/leaderboard").get_json()["leaderboard"]
    assert top[0]["player"] == "ci-bot"
    assert top[0]["score"] == 123456


def test_long_player_names_are_trimmed(client):
    client.post("/submit_score", json={"player": "n" * 50, "score": 999999})
    top = client.get("/leaderboard").get_json()["leaderboard"]
    assert len(top[0]["player"]) <= 20
