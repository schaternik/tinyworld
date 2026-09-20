FROM python:3.12-slim

# sqlite3 CLI so you can poke at the world from inside the container
RUN apt-get update && apt-get install -y --no-install-recommends sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY tinyworld.py .

# State lives here; mounted out as a volume
RUN mkdir -p /data && useradd -m -u 1000 sim && chown -R sim /data /app
USER sim

ENV OLLAMA_HOST=http://host.docker.internal:11434 \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "tinyworld.py", "--db", "/data/world.db"]
CMD ["--ticks", "30", "--model", "mock"]
