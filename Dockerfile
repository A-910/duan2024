
FROM python:3.12.6-slim

# Cài đặt các công cụ cần thiết
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 libsm6 libxext6 libxrender-dev && \
    apt-get clean

# Tạo thư mục làm việc
WORKDIR /app

# Sao chép các file cần thiết vào container
COPY requirements.txt ./requirements.txt
COPY main1.py ./main1.py
COPY serviceAccountKey.json ./serviceAccountKey.json


# Cài đặt thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000
EXPOSE 5050


# Chạy ứng dụng
CMD ["python", "main1.py"]
