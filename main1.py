import json
import cv2
import requests
import gc
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor


def fetch_registered_ips(file_path="05.ip-register/registered_ips.json"):
    """Đọc danh sách IP đã đăng ký từ tệp JSON"""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None


def process_frame(chunk):
    """Chuyển đổi chunk byte thành frame hình ảnh"""
    np_array = np.frombuffer(chunk, dtype=np.uint8)
    frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    return frame if frame is not None else None


def fetch_stream(ip_address, retries=3, timeout=15):
    """Lấy stream từ ESP32-CAM"""
    stream_url = f"http://{ip_address}:80/stream?resolution=640x480"
    attempt = 0
    frame_buffer = b""
    max_buffer_size = 1024 * 500  # Tăng kích thước buffer (500 KB)

    while attempt < retries:
        try:
            print(f"Connecting to stream: {stream_url} (Attempt {attempt + 1}/{retries})...")
            response = requests.get(stream_url, timeout=timeout, stream=True)
            response.raise_for_status()  # Raise lỗi nếu status không phải 200
            
            for chunk in response.iter_content(1024):
                frame_buffer += chunk

                # Giới hạn kích thước buffer để tránh tràn bộ nhớ
                if len(frame_buffer) > max_buffer_size:
                    frame_buffer = frame_buffer[-1024 * 10:]  # Giữ lại 10 KB cuối

                # Tìm và xử lý frame JPEG
                start = frame_buffer.find(b'\xff\xd8')
                end = frame_buffer.find(b'\xff\xd9')
                if start != -1 and end != -1:
                    jpeg_data = frame_buffer[start:end + 2]
                    frame = process_frame(jpeg_data)
                    if frame is not None:
                        yield frame
                    frame_buffer = frame_buffer[end + 2:]  # Cắt dữ liệu đã xử lý

        except requests.exceptions.Timeout:
            print(f"Timeout error while fetching stream from {stream_url}. Retrying...")
        except requests.exceptions.RequestException as e:
            print(f"Stream connection error: {e}")
            break

        attempt += 1
    print("Max retries reached. Could not fetch stream.")


def upload_image_to_firebase(image_data):
    """Giả lập upload ảnh lên Firebase"""
    print("Uploading image to Firebase...")
    # Đây là hàm giả lập, bạn có thể thêm logic thực tế để upload lên Firebase.
    time.sleep(1)  # Giả lập thời gian upload
    print("Upload complete.")


def main():
    file_path = "05.ip-register/registered_ips.json"
    registered_ips = fetch_registered_ips(file_path)

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

    # Sử dụng ThreadPoolExecutor để xử lý upload ảnh song song
    with ThreadPoolExecutor(max_workers=2) as executor:
        for frame in fetch_stream(ip_address):
            if frame is None:
                print("No frame received. Exiting stream processing.")
                break

            # Hiển thị frame trực tiếp (live stream)
            cv2.imshow("Live Stream", frame)

            # Upload ảnh mỗi 2 giây
            current_time = time.time()
            if current_time - last_upload_time >= 2:
                _, buffer = cv2.imencode(".jpg", frame)
                executor.submit(upload_image_to_firebase, buffer.tobytes())
                print("Uploaded to Firebase")
                last_upload_time = current_time

            # Thu dọn bộ nhớ mỗi 50 frame
            if frame_count % 50 == 0:
                gc.collect()

            frame_count += 1

            # Thoát khi nhấn "q"
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
