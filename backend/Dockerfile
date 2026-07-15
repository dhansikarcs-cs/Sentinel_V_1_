FROM python:3.12-slim

RUN addgroup --system --gid 1001 sentinel && adduser --system --uid 1001 --ingroup sentinel sentinel

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R sentinel:sentinel /app

USER sentinel

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
