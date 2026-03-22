/**
 * game.js — 2048 game engine + AI + Leaderboard integration
 */

"use strict";

/* ── State ───────────────────────────────────────── */

let board = [];
let score = 0;
let bestScore = parseInt(localStorage.getItem("best") || "0", 10);
let gameOver = false;
let aiRunning = false;
let aiTimer = null;

/* ── New Game ────────────────────────────────────── */

function newGame() {
  board = Array.from({ length: 4 }, () => [0, 0, 0, 0]);
  score = 0;
  gameOver = false;

  stopAI();

  spawnTile();
  spawnTile();

  render();
  hideOverlay();
  updateScoreDisplay();

  setAIStatus("idle", "AI idle");
}

/* ── Move Mechanics ───────────────────────────────── */

function slideLeft(row) {
  const tiles = row.filter(v => v !== 0);
  const merged = [];
  let gain = 0;
  let skip = false;

  for (let i = 0; i < tiles.length; i++) {
    if (skip) {
      skip = false;
      continue;
    }

    if (i + 1 < tiles.length && tiles[i] === tiles[i + 1]) {
      const val = tiles[i] * 2;
      merged.push(val);
      gain += val;
      skip = true;
    } else {
      merged.push(tiles[i]);
    }
  }

  while (merged.length < 4) merged.push(0);

  return { row: merged, gain };
}

function applyMove(dir) {
  let changed = false;
  let gain = 0;

  const rotate90 = m => m[0].map((_, c) => m.map(r => r[c]).reverse());
  const rotate180 = m => rotate90(rotate90(m));
  const rotate270 = m => rotate90(rotate180(m));

  let b = board.map(r => [...r]);

  if (dir === "RIGHT") b = b.map(r => r.reverse());
  if (dir === "UP") b = rotate90(b);
  if (dir === "DOWN") b = rotate270(b);

  b = b.map(row => {
    const { row: newRow, gain: g } = slideLeft(row);
    gain += g;
    if (newRow.some((v, i) => v !== row[i])) changed = true;
    return newRow;
  });

  if (dir === "RIGHT") b = b.map(r => r.reverse());
  if (dir === "UP") b = rotate270(b);
  if (dir === "DOWN") b = rotate90(b);

  if (!changed) return false;

  board = b;
  score += gain;

  if (score > bestScore) {
    bestScore = score;
    localStorage.setItem("best", bestScore);
  }

  return true;
}

/* ── Tile Spawn ───────────────────────────────────── */

function spawnTile() {
  const empty = [];

  for (let r = 0; r < 4; r++)
    for (let c = 0; c < 4; c++)
      if (board[r][c] === 0)
        empty.push([r, c]);

  if (!empty.length) return;

  const [r, c] = empty[Math.floor(Math.random() * empty.length)];

  board[r][c] = Math.random() < 0.9 ? 2 : 4;

  return [r, c];
}

/* ── Game Over Check ─────────────────────────────── */

function checkGameOver() {
  for (let r = 0; r < 4; r++)
    for (let c = 0; c < 4; c++) {

      if (board[r][c] === 0) return false;

      if (c < 3 && board[r][c] === board[r][c + 1]) return false;

      if (r < 3 && board[r][c] === board[r + 1][c]) return false;
    }

  return true;
}

/* ── Rendering ───────────────────────────────────── */

function render(spawnedCell = null) {

  const boardEl = document.getElementById("board");

  boardEl.innerHTML = "";

  for (let r = 0; r < 4; r++) {
    for (let c = 0; c < 4; c++) {

      const val = board[r][c];

      const cell = document.createElement("div");

      cell.className = `cell cell-${Math.min(val, 2048)}`;

      if (val) cell.textContent = val;

      if (spawnedCell && spawnedCell[0] === r && spawnedCell[1] === c)
        cell.classList.add("spawned");

      boardEl.appendChild(cell);
    }
  }

  updateScoreDisplay();
}

function updateScoreDisplay() {
  document.getElementById("score").textContent = score;
  document.getElementById("best-score").textContent = bestScore;
}

/* ── Overlay ─────────────────────────────────────── */

function showOverlay(title, text) {

  document.getElementById("overlay-title").textContent = title;

  document.getElementById("overlay-score-text").textContent = text;

  document.getElementById("overlay").style.display = "flex";
}

function hideOverlay() {

  document.getElementById("overlay").style.display = "none";

  document.getElementById("player-name").value = "";
}

/* ── Player Input ───────────────────────────────── */

const KEY_TO_DIR = {

  ArrowUp: "DOWN",
  ArrowDown: "UP",
  ArrowLeft: "LEFT",
  ArrowRight: "RIGHT",

  w: "DOWN",
  s: "UP",
  a: "LEFT",
  d: "RIGHT"
};

document.addEventListener("keydown", e => {

  if (gameOver || aiRunning) return;

  const dir = KEY_TO_DIR[e.key];

  if (!dir) return;

  e.preventDefault();

  handleMove(dir);
});

function handleMove(dir) {

  const moved = applyMove(dir);

  if (!moved) return;

  const spawned = spawnTile();

  render(spawned);

  if (checkGameOver()) {

    gameOver = true;

    stopAI();

    showOverlay("Game Over", `Final score: ${score}`);
  }
}

/* ── AI Integration (FIXED) ─────────────────────── */

function setAIStatus(state, text) {

  const dot = document.getElementById("ai-dot");

  const span = document.getElementById("ai-status-text");

  dot.className = `ai-dot ${state}`;

  span.textContent = text;
}

async function aiStep() {

  if (gameOver) return;

  setAIStatus("thinking", "AI thinking...");

  try {

    const res = await fetch("/ai_move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ board })
    });

    const data = await res.json();

    let dir = data.move;

    let moved = applyMove(dir);

    if (!moved) {

      const dirs = ["UP", "DOWN", "LEFT", "RIGHT"];

      for (let d of dirs) {

        if (applyMove(d)) {

          dir = d;

          moved = true;

          break;
        }
      }
    }

    if (moved) {

      const spawned = spawnTile();

      render(spawned);

      setAIStatus("active", `AI played: ${dir}`);
    }

  } catch (err) {

    console.error(err);

    setAIStatus("idle", "AI error");
  }
}

/* ── AI Loop ────────────────────────────────────── */

function startAI() {

  if (aiRunning) return;

  aiRunning = true;

  document.getElementById("btn-ai-run").textContent = "AI: Stop ■";

  scheduleAI();
}

function stopAI() {

  aiRunning = false;

  clearTimeout(aiTimer);

  document.getElementById("btn-ai-run").textContent = "AI: Auto ▶";

  if (!gameOver)
    setAIStatus("idle", "AI idle");
}

function scheduleAI() {

  if (!aiRunning || gameOver) {

    stopAI();

    return;
  }

  const delay = parseInt(document.getElementById("ai-speed").value, 10);

  const ms = 850 - delay;

  aiTimer = setTimeout(async () => {

    await aiStep();

    scheduleAI();

  }, ms);
}

/* ── Leaderboard ────────────────────────────────── */

async function fetchLeaderboard() {

  const tbody = document.getElementById("leaderboard-body");

  tbody.innerHTML = `<tr><td colspan="4">Loading...</td></tr>`;

  try {

    const res = await fetch("/leaderboard");

    const data = await res.json();

    tbody.innerHTML = data.leaderboard.map(row => `
      <tr>
        <td>${row.rank}</td>
        <td>${row.player}</td>
        <td>${row.score}</td>
        <td>${row.created_at.split(" ")[0]}</td>
      </tr>
    `).join("");

  } catch {

    tbody.innerHTML = `<tr><td colspan="4">Error loading leaderboard</td></tr>`;
  }
}

/* ── Event Wiring ───────────────────────────────── */

// ...existing code...

/* ── Event Wiring ───────────────────────────────── */

document.getElementById("btn-new").addEventListener("click", newGame);

document.getElementById("btn-ai-step").addEventListener("click", () => {
  stopAI();
  aiStep();
});

document.getElementById("btn-ai-run").addEventListener("click", () => {
  aiRunning ? stopAI() : startAI();
});

document.getElementById("btn-refresh").addEventListener("click", fetchLeaderboard);

// Add event listener for score submission
document.getElementById("btn-submit").addEventListener("click", async () => {
  const player = document.getElementById("player-name").value.trim() || "Anonymous";
  try {
    const res = await fetch("/submit_score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player, score })
    });
    const data = await res.json();
    if (res.ok) {
      hideOverlay();
      fetchLeaderboard();  // Refresh leaderboard after successful submission
    } else {
      alert(data.error || "Error submitting score");
    }
  } catch (err) {
    console.error(err);
    alert("Error submitting score");
  }
});

/* ── Boot ───────────────────────────────────────── */

// ...existing code...
/* ── Boot ───────────────────────────────────────── */

newGame();

fetchLeaderboard();