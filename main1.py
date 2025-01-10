import os
import json
import cv2
import requests
import gc
import time
from app.firebase_service import upload_image_to_firebase
import numpy as np
from concurrent.futures import ThreadPoolExecutor

def fetch_registered_ips(file_path, is_url=False):
    """Đọc danh sách IP đã đăng ký từ tệp JSON, từ URL hoặc từ thư mục cục bộ."""
    try:
        if is_url:
            response = requests.get(file_path, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch file from URL, status code: {response.status_code}")
                return None
        else:
            with open(file_path, "r") as f:
                return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching file from URL: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON.")
        return None

def process_frame(chunk):
    """Chuyển đổi chunk byte thành frame hình ảnh."""
    np_array = np.frombuffer(chunk, dtype=np.uint8)
    frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    return frame if frame is not None else None

def fetch_stream(ip_address, retries=3, timeout=10):
    """Lấy stream từ ESP32-CAM."""
    stream_url = f"http://{ip_address}:80/stream?resolution=640x480"
    attempt = 0
    frame_buffer = b""
    max_buffer_size = 1024 * 200

    while attempt < retries:
        try:
            print(f"Attempting to fetch stream from {stream_url} (Attempt {attempt + 1}/{retries})...")
            response = requests.get(stream_url, timeout=timeout, stream=True)
            if response.status_code == 200:
                for chunk in response.iter_content(1024):
                    frame_buffer += chunk
                    if len(frame_buffer) > max_buffer_size:
                        frame_buffer = frame_buffer[-1024 * 10:]
                    start = frame_buffer.find(b'\xff\xd8')
                    end = frame_buffer.find(b'\xff\xd9')
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
    # Xác định thư mục hiện tại của script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Tạo đường dẫn tới file JSON
    file_path = os.path.join(current_dir, "05.ip-register", "registered_ips.json")
    is_url = False  # Đặt True nếu muốn sử dụng URL
    
    # Kiểm tra xem file có tồn tại không
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    # Lấy danh sách IP đã đăng ký
    registered_ips = fetch_registered_ips(file_path, is_url=is_url)

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

    frame_count = 0
    last_upload_time = time.time()

    with ThreadPoolExecutor(max_workers=2) as executor:
        for frame in fetch_stream(ip_address):
            if frame is None:
                print("No frame received. Exiting stream processing.")
                break

            cv2.imshow("Live Stream", frame)

            current_time = time.time()
            if current_time - last_upload_time >= 2:
                _, buffer = cv2.imencode(".jpg", frame)
                executor.submit(upload_image_to_firebase, buffer.tobytes())
                print("Uploaded to Firebase")
                last_upload_time = current_time

            if frame_count % 50 == 0:
                gc.collect()

            frame_count += 1

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
