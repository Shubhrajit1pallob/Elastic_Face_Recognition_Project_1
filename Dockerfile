FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY Classification_Results_on_Face_Dataset_\(1000_images\).csv .

EXPOSE 8000

CMD [ "gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "server:app" ]