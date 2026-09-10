FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

# exec matters: without it the shell stays PID 1 and never forwards SIGTERM to
# python, so `docker stop` waits out its timeout and kills the bot instead of
# letting it shut down. Measured: 11s and no signal without exec, 0s and a
# clean SIGTERM with it.
#
# The migration runs here rather than in a separate service because there is
# exactly one replica. A failing migration will restart-loop, which is loud but
# correct - the bot must not start against a schema it does not expect.
CMD ["sh", "-c", "alembic upgrade head && exec python -m app.run"]