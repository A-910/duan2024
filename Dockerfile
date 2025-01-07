FROM python:3.12.6-slim

# Cài đặt các công cụ cần thiết cho ứng dụng
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    python3-distutils \
    python3-pip \
    wget

# Xóa cache sau khi cài đặt
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Tạo thư mục làm việc
WORKDIR /app

# Sao chép các file cần thiết vào container
COPY requirements.txt .
COPY firedetector.py .
COPY serviceAccountKey.json .
COPY best.pt .

# Cài đặt thư viện Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5050
EXPOSE 5050

# Chạy ứng dụng
CMD ["python", "firedetector.py"]
