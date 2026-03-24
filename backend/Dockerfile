FROM python:3.11-slim

WORKDIR /app

# Chỉ copy requirements của backend
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code backend vào
COPY . .

EXPOSE 8001

# Lệnh chạy FastAPI
CMD ["uvicorn", "fast_api:app", "--host", "0.0.0.0", "--port", "8000"]
