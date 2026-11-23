FROM python:3.12-slim

WORKDIR /app

# Instalar las dependencias del microservicio
RUN pip install --no-cache-dir fastapi uvicorn "pydantic>=2" httpx tzdata

# Copiar el código de Espacios
COPY Espacios/ /app/Espacios/

# Configurar la base de datos SQLite
ENV ESPACIOS_DB=/app/Espacios/data/espacios.sqlite3

# Puerto del microservicio
EXPOSE 8003

# Arrancar Espacios
CMD ["python", "-m", "uvicorn", "Espacios.main_espacios:app", "--host", "0.0.0.0", "--port", "8003"]
