FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY nexus_workspace ./nexus_workspace
RUN pip install --no-cache-dir .
COPY sources.lock.json ./sources.lock.json
RUN mkdir -p /app/state /app/artifacts
EXPOSE 8787
CMD ["nexus", "serve"]
