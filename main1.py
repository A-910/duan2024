import json
import cv2
import requests
import gc
import time
from app.firebase_service import upload_image_to_firebase
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor


def fetch_registered_ips(file_path=None):
    """
    Đọc danh sách IP đã đăng ký từ tệp JSON hoặc API.
    """
    # Ưu tiên lấy danh sách IP từ API (nếu có)
    api_url = os.getenv("IP_REGISTER_API", None)
    if api_url:
        try:
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch IPs from API. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching IPs from API: {e}")

    # Nếu không có API, lấy từ file JSON
    file_path = file_path or os.getenv("IP_REGISTER_FILE", "05.ip-register/registered_ips.json")
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except json.JSONDecodeError:
        print(f"Error decoding JSON from file: {file_path}")
    return None


def process_frame(chunk):
    """
    Chuyển đổi chunk byte thành frame hình ảnh.
    """
    np_array = np.frombuffer(chunk, dtype=np.uint8)
    frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    return frame if frame is not None else None


def fetch_stream(ip_address, retries=3, timeout=10):
    """
    Lấy stream từ ESP32-CAM.
    """
    stream_url = f"http://{ip_address}:80/stream?resolution=640x480"  # Giảm độ phân giải
    attempt = 0
    frame_buffer = b""  # Dùng để tích lũy các chunk ảnh
    max_buffer_size = 1024 * 200  # Tăng kích thước bộ đệm (200 KB)

    while attempt < retries:
        try:
            print(f"Attempting to fetch stream from {stream_url} (Attempt {attempt + 1}/{retries})...")
            response = requests.get(stream_url, timeout=timeout, stream=True)
            if response.status_code == 200:
                for chunk in response.iter_content(1024):
                    frame_buffer += chunk

                    if len(frame_buffer) > max_buffer_size:
                        # Reset buffer khi vượt quá kích thước
                        frame_buffer = frame_buffer[-1024 * 10:]  # Giữ lại 10 KB cuối

                    start = frame_buffer.find(b'\xff\xd8')  # Tìm phần đầu của JPEG
                    end = frame_buffer.find(b'\xff\xd9')  # Tìm phần kết thúc của JPEG
                    if start != -1 and end != -1:
                        jpeg_data = frame_buffer[start:end + 2]
                        frame = process_frame(jpeg_data)
                        if frame is not None:
                            yield frame
                        frame_buffer = frame_buffer[end + 2:]
            else:
                print(f"Failed to fetch stream, status code: {response.status_code}")
                break
        except requests.exceptions.Timeout:
            print(f"Timeout error while fetching stream from {stream_url}. Retrying...")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching stream: {e}")
            break
        attempt += 1

    print("Max retries reached. Could not fetch stream.")
    return


def main():
    # Đọc đường dẫn file IP từ biến môi trường
    registered_ips = fetch_registered_ips()

    if not registered_ips:
        print("No registered IPs found or failed to load the file.")
        return

    print(f"Registered IPs: {registered_ips}")

    device_name = registered_ips.get("device_name", "Unknown Device")
    ip_address = registered_ips.get("ip_address")

    if not ip_address:
        print(f"Invalid or missing IP address for device {device_name}.")
        return

    print(f"Processing stream for {device_name} ({ip_address})...")

    frame_count = 0  # Khởi tạo frame_count
    last_upload_time = time.time()  # Thời gian bắt đầu

    # Sử dụng ThreadPoolExecutor để xử lý upload ảnh song song
    with ThreadPoolExecutor(max_workers=2) as executor:
        for frame in fetch_stream(ip_address):
            if frame is None:
                print("No frame received. Exiting stream processing.")
                break

            # Hiển thị frame nhanh (stream)
            cv2.imshow("Live Stream", frame)

            # Kiểm tra thời gian và upload ảnh mỗi 2 giây
            current_time = time.time()
            if current_time - last_upload_time >= 2:  # Nếu đã 2 giây trôi qua
                _, buffer = cv2.imencode(".jpg", frame)
                executor.submit(upload_image_to_firebase, buffer.tobytes())
                print("Uploaded to Firebase")
                last_upload_time = current_time  # Cập nhật thời gian lần upload gần nhất

            # Thu dọn bộ nhớ mỗi 50 frame
            if frame_count % 50 == 0:
                gc.collect()

            frame_count += 1  # Tăng frame_count

            # Thoát khi nhấn "q"
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
