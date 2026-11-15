import cv2
import winsound
import time
import os
import openpyxl
import requests
import threading
import face_recognition  # Face recognition এর জন্য লাইব্রেরি যুক্ত করা

# Telegram Bot API Token এবং Chat ID
TOKEN = '7759523827:AAGxoNH4wowcv83EEjdzXhEocM0RWJBMd8A'
CHAT_ID = '1184192406'

# ক্যামেরা শুরু করা
cam = cv2.VideoCapture('vid.mp4')

# ফেস ডিটেকশন লোড করা
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# নির্দিষ্ট rectangular box এর স্থান ও আকার
box_x, box_y, box_w, box_h = 10, 10, 200, 350
last_sound_time = 0
alert_interval = 2

# লগ ফোল্ডার এবং ফাইল তৈরি
log_folder = "movement_logs"
video_folder = "movement_videos"
if not os.path.exists(log_folder):
    os.makedirs(log_folder)
if not os.path.exists(video_folder):
    os.makedirs(video_folder)

log_file_path = os.path.join(log_folder, "log.txt")

# ভিডিও রাইটার সেটআপ
timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
video_path = os.path.join(video_folder, f"movement_{timestamp}.avi")
fourcc = cv2.VideoWriter_fourcc(*'XVID')
video_writer = cv2.VideoWriter(video_path, fourcc, 20.0, (int(cam.get(3)), int(cam.get(4))))

# এক্সেল ফাইল তৈরি এবং শিরোনাম সংযোজন
excel_file_path = "movement_log.xlsx"
if not os.path.exists(excel_file_path):
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "Movement Logs"
    sheet.append(["Name", "Detection Time", "Date"])
    wb.save(excel_file_path)

# পরিচিত মুখের ডাটাবেস লোড করা
known_faces = []
known_names = []

known_faces_folder = "known_faces"
for filename in os.listdir(known_faces_folder):
    if filename.endswith(".jpg") or filename.endswith(".png"):
        filepath = os.path.join(known_faces_folder, filename)
        image = face_recognition.load_image_file(filepath)
        encoding = face_recognition.face_encodings(image)[0]
        known_faces.append(encoding)
        known_names.append(os.path.splitext(filename)[0])

# Telegram এ মেসেজ এবং ছবি পাঠানোর ফাংশন
def send_telegram_message_with_photo(message, image_path):
    def task():
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        with open(image_path, 'rb') as photo:
            files = {'photo': photo}
            data = {
                "chat_id": CHAT_ID,
                "caption": message
            }
            requests.post(url, data=data, files=files)

    threading.Thread(target=task).start()

# রিয়েল টাইম ডিসপ্লে এবং প্রসেসিং
while cam.isOpened():
    ret, frame1 = cam.read()
    ret, frame2 = cam.read()

    if not ret:
        print("Error: Unable to read from camera.")
        break

    diff = cv2.absdiff(frame1, frame2)
    grey = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(grey, (5, 5), 0)

    _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
    dilate = cv2.dilate(thresh, None, iterations=3)
    contours, _ = cv2.findContours(dilate, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame1, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.rectangle(frame1, (box_x, box_y), (box_x + box_w, box_y + box_h), (0, 0, 255), 2)

    # Face Recognition
    rgb_frame = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        matches = face_recognition.compare_faces(known_faces, face_encoding)
        name = "Unknown"

        if True in matches:
            match_index = matches.index(True)
            name = known_names[match_index]

        cv2.rectangle(frame1, (left, top), (right, bottom), (255, 0, 0), 2)
        cv2.putText(frame1, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        if (box_x <= left <= box_x + box_w and 
            box_y <= top <= box_y + box_h and 
            box_x <= right <= box_x + box_w and 
            box_y <= bottom <= box_y + box_h):

            current_time = time.time()
            if current_time - last_sound_time > alert_interval:
                winsound.PlaySound('alert.wav', winsound.SND_ASYNC)
                last_sound_time = current_time

                image_path = os.path.join(log_folder, f"face_{timestamp.replace(':', '-')}.jpg")
                cv2.imwrite(image_path, frame1)

                wb = openpyxl.load_workbook(excel_file_path)
                sheet = wb.active
                sheet.append([name, timestamp, time.strftime("%Y-%m-%d")])
                wb.save(excel_file_path)

                with open(log_file_path, "a") as log_file:
                    log_file.write(f"Face detected: {name} at {timestamp}, saved image: {image_path}\n")

                send_telegram_message_with_photo(f"Face detected: {name} at {timestamp}", image_path)

    for c in contours:
        if cv2.contourArea(c) < 2000:
            continue

        x, y, w, h = cv2.boundingRect(c)
        cv2.rectangle(frame1, (x, y), (x + w, y + h), (0, 255, 0), 2)

        if (box_x <= x <= box_x + box_w and 
            box_y <= y <= box_y + box_h and 
            box_x <= x + w <= box_x + box_w and 
            box_y <= y + h <= box_y + box_h):

            current_time = time.time()
            if current_time - last_sound_time > alert_interval:
                winsound.PlaySound('alert.wav', winsound.SND_ASYNC)
                last_sound_time = current_time

                image_path = os.path.join(log_folder, f"movement_{timestamp.replace(':', '-')}.jpg")
                cv2.imwrite(image_path, frame1)

                wb = openpyxl.load_workbook(excel_file_path)
                sheet = wb.active
                sheet.append(["Movement", timestamp, time.strftime("%Y-%m-%d")])
                wb.save(excel_file_path)

                with open(log_file_path, "a") as log_file:
                    log_file.write(f"Movement detected at {timestamp}, saved image: {image_path}\n")

                send_telegram_message_with_photo(f"Movement detected at {timestamp}", image_path)

    video_writer.write(frame1)

    cv2.imshow("Camera", frame1)

    if cv2.waitKey(10) == ord('q'):
        break

cam.release()
video_writer.release()
cv2.destroyAllWindows()
