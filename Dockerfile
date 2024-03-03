FROM python:3.11 as builder

WORKDIR /app
ADD pyproject.toml poetry.lock README.md /app/
ADD src /app/src

RUN pip install poetry
RUN poetry config virtualenvs.in-project true
RUN poetry install --no-ansi

FROM python:3.11-slim
WORKDIR /app

COPY --from=builder /app /app
ADD . /app

RUN addgroup --gid 1000 app
RUN useradd -d /app -u 1000 -g 1000 -M app 
USER 1000

CMD ["/app/.venv/bin/uvicorn", "--host", "0.0.0.0", "malloc.polish_bond_site.main:app"]