# Sử dụng hình ảnh chính thức của Python
FROM python:3.12.6-slim

# Thiết lập biến môi trường để tránh thông báo không cần thiết từ Debian
ENV DEBIAN_FRONTEND=noninteractive

# Cài đặt các công cụ cần thiết
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    python3-distutils \
    python3-pip \
    wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Thiết lập thư mục làm việc
WORKDIR /app

# Sao chép file yêu cầu
COPY requirements.txt .

# Cài đặt thư viện Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Sao chép các file khác vào container
COPY firedetector.py .
COPY serviceAccountKey.json .
COPY best.pt .

# Expose cổng 5050 để ứng dụng lắng nghe
EXPOSE 5050

# Chạy ứng dụng
CMD ["python", "firedetector.py"]
