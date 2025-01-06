import firebase_admin
from firebase_admin import credentials, db, storage
from ultralytics import YOLO
import cv2
import numpy as np
import time
import threading  # Thư viện để xử lý song song

# Khởi tạo Firebase
cred = credentials.Certificate("./serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://atmega238p-70bdc-default-rtdb.firebaseio.com/',
    'storageBucket': 'atmega238p-70bdc.firebasestorage.app'  # Bucket name của bạn
})

# Load mô hình YOLO
model = YOLO("best.pt")
print("YOLOv8n model loaded successfully.")
print("Các nhãn trong mô hình:", model.names)

# Lưu cache ảnh đã tải về
cached_image = None
last_updated_time = 0  # Thời gian ảnh cuối cùng được tải về


def download_latest_image_from_firebase():
    """Tải ảnh mới nhất từ Firebase Storage và trả về dữ liệu nhị phân."""
    global cached_image, last_updated_time  # Sử dụng ảnh cache nếu đã tải
    try:
        bucket = firebase_admin.storage.bucket()
        blobs = list(bucket.list_blobs(prefix="images/"))

        if not blobs:
            print("Không tìm thấy hình ảnh trong Firebase Storage.")
            return None

        # Chỉ tải ảnh nếu nó mới hơn ảnh hiện tại
        latest_blob = max(blobs, key=lambda b: b.updated)

        # Kiểm tra xem ảnh có thay đổi không
        if latest_blob.updated.timestamp() <= last_updated_time:
            return cached_image  # Nếu ảnh chưa thay đổi, trả ảnh cache

        image_data = latest_blob.download_as_bytes()
        cached_image = image_data  # Cập nhật cache
        last_updated_time = latest_blob.updated.timestamp()  # Cập nhật thời gian
        print(f"Đã tải hình ảnh mới: {latest_blob.name}")
        return image_data

    except Exception as e:
        print(f"Lỗi khi truy cập Firebase Storage: {e}")
        return None


def predict_fire(frame):
    """Chạy ảnh qua mô hình ML để dự đoán có lửa hay không."""
    try:
        results = model.predict(frame, imgsz=320)  # Dự đoán với kích thước ảnh nhỏ hơn

        fire_detected = False
        for result in results:
            for box in result.boxes:
                conf = box.conf.item()
                cls = int(box.cls.item())
                label = model.names[cls]

                print(f"Nhãn phát hiện: {label}, Độ tin cậy: {conf:.2f}")

                if label == 'Cháy' and conf > 0.7:
                    print("Lửa được phát hiện!")
                    fire_detected = True
                    x1, y1, x2, y2 = map(int, box.xyxy[0])  # Lấy tọa độ của bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)  # Vẽ hình vuông đỏ

        return 0 if fire_detected else 1  # Trả về 0 nếu phát hiện lửa, 1 nếu không phát hiện

    except Exception as e:
        print(f"Lỗi trong quá trình dự đoán: {e}")
        return 1


def send_to_firebase(result):
    """Gửi kết quả dự đoán lửa đến Firebase Realtime Database."""
    try:
        ref = db.reference("fire_detection")
        ref.set({"result": result})
        print(f"Đã gửi kết quả '{result}' đến Firebase Database.")
    except Exception as e:
        print(f"Lỗi khi gửi kết quả đến Firebase Database: {e}")


def process_images():
    """Tải ảnh từ Firebase, dự đoán lửa và gửi kết quả liên tục."""
    retry_attempts = 5  # Số lần thử tải lại ảnh tối đa

    while retry_attempts > 0:
        print("Đang lấy ảnh mới nhất từ Firebase Storage...")
        image_data = download_latest_image_from_firebase()  # Lấy ảnh dưới dạng nhị phân

        if not image_data:
            print("Thử tải lại ảnh...")
            retry_attempts -= 1
            if retry_attempts <= 0:
                print("Đã hết số lần thử. Thoát.")
                break
            time.sleep(1)  # Giảm thời gian chờ giữa các lần thử
            continue

        # Giải mã dữ liệu ảnh
        np_array = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        if frame is not None:
            # Dự đoán trên ảnh và gửi kết quả về Firebase
            fire_result = predict_fire(frame)
            send_to_firebase(fire_result)

            # Đợi trước khi tải ảnh tiếp theo
            time.sleep(2)  # Giảm thời gian chờ giữa các lần tải ảnh

        else:
            print("Lỗi khi giải mã ảnh. Thử lại...")

    print("Hoàn tất.")


if __name__ == "__main__":
    process_images()
