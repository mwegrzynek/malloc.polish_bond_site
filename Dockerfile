FROM python:3.11 AS builder

WORKDIR /app

# Copy workspace root and all member packages needed at build time
COPY pyproject.toml /app/
COPY malloc.polish_bond/ /app/malloc.polish_bond/
COPY malloc.polish_bond_site/ /app/malloc.polish_bond_site/

RUN pip install uv
RUN uv sync --no-dev --package malloc-polish-bond-site

FROM python:3.11-slim
WORKDIR /app

COPY --from=builder /app /app

RUN addgroup --gid 1000 app
RUN useradd -d /app -u 1000 -g 1000 -M app
RUN mkdir -p /app/.cache
RUN chown 1000:1000 /app/.cache
USER 1000

CMD ["/app/.venv/bin/uvicorn", "--host", "0.0.0.0", "malloc.polish_bond_site.main:app"]
