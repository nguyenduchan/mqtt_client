# Dùng bản python nhẹ
FROM python:3.10-slim

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Cài đặt thư viện
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code vào
COPY . .

# Biến môi trường để phân biệt môi trường (DEV/PROD)
ENV APP_ENV=DEV
ENV BOARD_ID=BBB-WSL-TEST

# Chạy script
CMD ["python", "bbb_emulator.py"]
