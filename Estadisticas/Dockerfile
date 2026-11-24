FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY Estadisticas ./Estadisticas
EXPOSE 8005
CMD ["uvicorn", "Estadisticas.main_estadisticas:app", "--host", "0.0.0.0", "--port", "8005"]