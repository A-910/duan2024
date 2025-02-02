# Sử dụng hình ảnh chính thức của Python
FROM python:3.12.6-slim

# Cài đặt các công cụ và thư viện cần thiết
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1 \
    python3-distutils && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Tạo thư mục làm việc
WORKDIR /app

# Sao chép các file cần thiết vào container
COPY requirements.txt .
COPY firedetector.py .
COPY serviceAccountKey.json .
# Sao chép best.pt chỉ khi cần thiết
COPY best.pt .

# Cài đặt thư viện Python
RUN pip install --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5050
EXPOSE 5050

# Chạy ứng dụng
CMD ["python", "firedetector.py"]
