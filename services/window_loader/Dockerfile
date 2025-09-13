FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -U pip && pip install -r requirements.txt
COPY . .
ENV HOST=0.0.0.0 PORT=8081
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081"]
