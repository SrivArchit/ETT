# ── Base image ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# ── System dependencies (minimal) ──────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ─────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application source ───────────────────────────────────────────────────────
COPY . .

# ── Data directory for SQLite ────────────────────────────────────────────────
# The leaderboard DB lives inside /app/leaderboard by default.
# Mount a volume here for persistence across container restarts:
#   docker run -v leaderboard_data:/app/leaderboard -p 5000:5000 docker-2048-ai
RUN mkdir -p /app/leaderboard

# ── Runtime ──────────────────────────────────────────────────────────────────
ENV PORT=5000
EXPOSE 5000

# Use gunicorn for a production-grade WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "30", "app:app"]
