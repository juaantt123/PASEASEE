FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir "fastapi>=0.115,<1" "uvicorn[standard]>=0.30,<1" "httpx>=0.27,<1" "pydantic>=2,<3"

COPY main_estadisticas.py /app/main_estadisticas.py

RUN useradd --no-log-init --uid 10001 --create-home app
USER app

EXPOSE 8005
CMD ["uvicorn", "main_estadisticas:app", "--host", "0.0.0.0", "--port", "8005"]
