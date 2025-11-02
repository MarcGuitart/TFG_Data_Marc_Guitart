FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -U pip && pip install -r requirements.txt
RUN pip uninstall -y kafka || true \
 && pip install --no-cache-dir kafka-python==2.0.2
COPY . .
CMD ["python", "main.py"]