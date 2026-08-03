FROM python:3.11-slim

WORKDIR /app

COPY ai_service/app /app/app
COPY backend/app/__init__.py /app/app/__init__.py
COPY backend/app/ml /app/app/ml

RUN pip install --no-cache-dir fastapi uvicorn scikit-learn joblib numpy

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
