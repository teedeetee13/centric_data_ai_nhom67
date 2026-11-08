FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EDUSUPPORT_ENV=production \
    EDUSUPPORT_DB_PATH=/data/edusupport.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY src ./src
COPY models ./models
COPY data/kb ./data/kb
COPY data/raw ./data/raw
COPY experiments/*.json ./experiments/
COPY .streamlit ./.streamlit

# Không chạy bằng root; chỉ /data là ghi được
RUN useradd --system --uid 10001 edusupport \
    && mkdir /data \
    && chown edusupport /data
USER edusupport
VOLUME /data

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"

CMD ["python", "-m", "streamlit", "run", "app/main.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
