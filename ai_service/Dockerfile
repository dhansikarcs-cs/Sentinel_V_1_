FROM python:3.11-slim

WORKDIR /app

COPY ../backend/app/ml /app/app/ml
COPY ../backend/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir fastapi uvicorn scikit-learn joblib numpy

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
