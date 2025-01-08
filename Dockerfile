# Sử dụng hình ảnh chính thức của Python
FROM python:3.11.0-slim

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
COPY requirements.txt .       # Sao chép tệp dependencies
COPY firedetector.py .        # Sao chép mã chính của ứng dụng
COPY serviceAccountKey.json . # Sao chép tệp Firebase credentials
COPY best.pt .                # Sao chép tệp model YOLOv5 (nếu cần)

# Cài đặt thư viện Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Expose cổng 5050 để ứng dụng chạy
EXPOSE 5050

# Chạy ứng dụng
CMD ["python", "firedetector.py"]
