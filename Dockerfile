FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY Requirements.txt .

RUN pip install --no-cache-dir -r Requirements.txt

COPY . .

EXPOSE 8000

CMD [ "gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "server:app" ]