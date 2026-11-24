FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY Merchandising ./Merchandising
EXPOSE 8004
CMD ["uvicorn", "Merchandising.main_tienda:app", "--host", "0.0.0.0", "--port", "8004"]