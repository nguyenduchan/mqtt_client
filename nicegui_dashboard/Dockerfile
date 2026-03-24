# Sử dụng Python phiên bản nhẹ
FROM python:3.11-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Cài đặt các thư viện cần thiết
# NiceGUI yêu cầu pandas nếu bạn dùng bảng dữ liệu
RUN pip install --no-cache-dir nicegui pandas

# Copy code và config vào container
COPY dashboard.py .
COPY config.json .

# Mở port 8504 (Trùng với port trong ui.run)
EXPOSE 8080

# Chạy ứng dụng
CMD ["python", "dashboard.py"]
