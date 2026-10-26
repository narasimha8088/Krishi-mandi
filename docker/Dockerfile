FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements-optional.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt -r backend/requirements-optional.txt
COPY backend ./backend
COPY web ./web
WORKDIR /app/backend
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
