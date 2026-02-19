FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

RUN mkdir -p data

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

CMD ["python", "-m", "src.main"]
