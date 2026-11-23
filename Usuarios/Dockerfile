FROM python:3.12-slim

WORKDIR /app

# Instalar las dependencias necesarias
RUN pip install --no-cache-dir fastapi uvicorn pydantic httpx tzdata

# Copiar el microservicio de Usuarios
COPY Usuarios/ /app/Usuarios/

# Puerto del microservicio
EXPOSE 8001

# Arrancar la API
CMD ["python", "-m", "uvicorn", "Usuarios.main_usuario:app", "--host", "0.0.0.0", "--port", "8001"]