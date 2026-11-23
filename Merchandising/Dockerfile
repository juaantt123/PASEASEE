FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MERCHANDISING_DB=/data/merchandising.sqlite3

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY main_tienda.py persistencia_merch.py ./Merchandising/

EXPOSE 8004

CMD ["python", "-m", "uvicorn", "Merchandising.main_tienda:app", "--host", "0.0.0.0", "--port", "8004"]