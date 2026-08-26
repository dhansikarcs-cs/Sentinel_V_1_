FROM python:3.11-slim

RUN addgroup --system --gid 1001 sentinel && adduser --system --uid 1001 --ingroup sentinel sentinel

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data && chown -R sentinel:sentinel /app

USER sentinel

EXPOSE 10000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
