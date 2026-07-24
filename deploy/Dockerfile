# FileForge services image — runs either the Cloud API or the License Server
# from one build. Pick which via the SERVICE env var (default: cloud-api).
#
#   docker build -f deploy/Dockerfile -t fileforge .
#   docker run -p 8080:8080 -e SERVICE=cloud-api   fileforge
#   docker run -p 8080:8080 -e SERVICE=license     fileforge
FROM python:3.12-slim

# ffmpeg powers the Pro video presets; drop this line to slim the image if the
# deployment doesn't need server-side video.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the engine + server deps first (better layer caching).
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -e '.[cloud,server,images]'

# App code for both services.
COPY cloud-api ./cloud-api
COPY license-server ./license-server
COPY deploy/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

ENV SERVICE=cloud-api \
    PORT=8080 \
    PYTHONUNBUFFERED=1
EXPOSE 8080

# Non-root for safety.
RUN useradd -m appuser && chown -R appuser /app
USER appuser

ENTRYPOINT ["./entrypoint.sh"]
