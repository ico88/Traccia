FROM python:3.11-slim AS native
RUN apt-get update && apt-get install -y --no-install-recommends build-essential git ca-certificates libgomp1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir cmake==4.4.4
WORKDIR /build
COPY scripts/setup_runtimes.py scripts/setup_runtimes.py
RUN python scripts/setup_runtimes.py --jobs 2

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libstdc++6 ca-certificates && rm -rf /var/lib/apt/lists/* && useradd --create-home --uid 10001 aula
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=native /build/runtimes /app/runtimes
COPY aulalocale /app/aulalocale
RUN mkdir /data && chown aula:aula /data
ENV AULALOCALE_DATA_DIR=/data
USER aula
EXPOSE 8765
CMD ["python", "-m", "uvicorn", "aulalocale.app:app", "--host", "0.0.0.0", "--port", "8765"]
