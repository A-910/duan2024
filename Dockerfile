FROM python:3.12.6-slim

# Cài đặt các công cụ cần thiết cho ứng dụng, bao gồm distutils và build-essential
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    python3-distutils \
    python3-pip \
    wget \
    git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Cài đặt pip, setuptools và wheel
RUN pip install --upgrade pip setuptools wheel

# Tạo thư mục làm việc
WORKDIR /app

# Sao chép file requirements.txt vào container
COPY requirements.txt .

# Cài đặt các thư viện trong requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép các file còn lại vào container
COPY firedetector.py . 
COPY serviceAccountKey.json . 
COPY best.pt . 

# Expose port 5050
EXPOSE 5050

# Chạy ứng dụng
CMD ["python", "firedetector.py"]
