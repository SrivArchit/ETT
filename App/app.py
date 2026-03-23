from flask import Flask, request, jsonify, send_from_directory
from flask import render_template
import os

from Ai.ai_player import get_best_move
from Leaderboard.db import init_db, add_score, get_top_scores

app = Flask(__name__, static_folder="static", template_folder="templates")

init_db()

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    scores = get_top_scores(limit=10)
    return jsonify({"leaderboard": scores})


@app.route("/submit_score", methods=["POST"])
def submit_score():
    data = request.get_json(force=True)
    player = data.get("player", "Anonymous").strip() or "Anonymous"
    score = data.get("score", 0)

    if not isinstance(score, int) or score < 0:
        return jsonify({"error": "Invalid score value"}), 400

    add_score(player, score)
    return jsonify({"message": "Score submitted successfully"})


@app.route("/ai_move", methods=["POST"])
def ai_move():
    data = request.get_json(force=True)
    board = data.get("board")

    move = get_best_move(board)
    return jsonify({"move": move})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)