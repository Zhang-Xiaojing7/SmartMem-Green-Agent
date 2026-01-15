FROM ghcr.io/astral-sh/uv:python3.13-bookworm

# Create a non-interactive user and set up home directory
RUN adduser --disabled-password --gecos "" --home /home/agent agent \
    && chown -R agent:agent /home/agent
USER agent
WORKDIR /home/agent

# Copy project files and install pinned dependencies. We keep --locked to ensure reproducible builds.
COPY pyproject.toml uv.lock README.md ./
COPY src src

RUN \
    --mount=type=cache,target=/home/agent/.cache/uv,uid=1000 \
    uv sync --locked

ENTRYPOINT ["uv", "run", "src/server.py"]
CMD ["--host", "0.0.0.0"]
EXPOSE 9009