# Lightweight image for the Order Tracker backend.
#
# Build and run from this directory (the one containing backend/ and frontend/):
#   docker build -t udatracker .
#   docker run --rm -p 5000:5000 udatracker
#
# Storage is in-memory, so orders are lost when the container stops.

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_DEBUG=0 \
    PORT=5000

WORKDIR /app

# Dependencies first, so edits to the source do not invalidate the pip layer.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/

# Run as an unprivileged user rather than root.
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 5000

# app.py binds 0.0.0.0 so the port is reachable from outside the container.
CMD ["python", "-m", "backend.app"]
