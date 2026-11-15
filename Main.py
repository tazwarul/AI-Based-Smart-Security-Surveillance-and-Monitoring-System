import cv2
import winsound
import time
import os
import openpyxl
import requests
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import subprocess
import numpy as np  # উজ্জ্বলতা ফিচারের জন্য প্রয়োজন

# Telegram Bot API Token এবং Chat ID
TOKEN = '7759523827:AAGxoNH4wowcv83EEjdzXhEocM0RWJBMd8A'
CHAT_ID = '1184192406'

# ক্যামেরা শুরু করা
cam = cv2.VideoCapture(0)

# Night mode state
night_mode = False  # নাইট মোড শুরু অবস্থায় বন্ধ

# ফেস ডিটেকশন লোড করা
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# নির্দিষ্ট rectangular box এর স্থান ও আকার (x, y, width, height)
box_x, box_y, box_w, box_h = 10, 60, 200, 350
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
    sheet.append(["Name", "Detection Time", "Date"])  # শিরোনাম যোগ করা
    wb.save(excel_file_path)

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

# GUI কোড শুরু
def start_detection():
    global running
    running = True
    detection_thread()

def stop_detection():
    global running
    running = False
    cam.release()
    video_writer.release()
    cv2.destroyAllWindows()
    messagebox.showinfo("Info", "Detection Stopped.")

def next_program():
    stop_detection()
    subprocess.Popen(['python', 'next_program.py'])  # 'next_program.py' এর পরিবর্তে আপনার পরবর্তী প্রোগ্রামের নাম বসান

def another_program():
    stop_detection()
    subprocess.Popen(['python', 'p1.py'])  # 'another_program.py' এর পরিবর্তে আপনার নতুন প্রোগ্রামের নাম দিন


def detection_thread():
    global last_sound_time, night_mode
    ret, frame1 = cam.read()
    ret, frame2 = cam.read()

    if not ret:
        print("Error: Unable to read from camera.")
        return

    # উজ্জ্বলতা নির্ধারণ
    gray_frame = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    brightness = np.mean(gray_frame)
    light_condition = "Normal Light"

    if brightness < 50:
        light_condition = "Low Light"
        if night_mode:  # নাইট মোড চালু থাকলে ব্রাইটনেস বাড়ানো
            frame1 = cv2.convertScaleAbs(frame1, alpha=2, beta=50)
            cv2.putText(frame1, "Night Mode ON", (450, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    elif brightness > 200:
        light_condition = "Bright Light"

    # ফ্রেমে উজ্জ্বলতা এবং আলো নির্দেশ করা
    cv2.putText(frame1, f"Brightness: {int(brightness)}", (450, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.putText(frame1, light_condition, (450, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # দুটি ফ্রেমের পার্থক্য বের করা
    diff = cv2.absdiff(frame1, frame2)
    grey = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)
    blur = cv2.GaussianBlur(grey, (5, 5), 0)

    # থ্রেশহোল্ড এবং ডাইলেশন
    _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
    dilate = cv2.dilate(thresh, None, iterations=3)
    contours, _ = cv2.findContours(dilate, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # ফ্রেমে টাইমস্ট্যাম্প যোগ করা
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame1, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # স্ক্রিনে rectangular box আঁকা
    cv2.rectangle(frame1, (box_x, box_y), (box_x + box_w, box_y + box_h), (0, 0, 255), 2)

    # ফেস ডিটেকশন
    faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))

    for (x, y, w, h) in faces:
        cv2.rectangle(frame1, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cv2.putText(frame1, "Unknown", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        if (box_x <= x <= box_x + box_w and 
            box_y <= y <= box_y + box_h and 
            box_x <= x + w <= box_x + box_w and 
            box_y <= y + h <= box_y + box_h):

            current_time = time.time()
            if current_time - last_sound_time > alert_interval:
                winsound.PlaySound('alert.wav', winsound.SND_ASYNC)
                last_sound_time = current_time

                image_path = os.path.join(log_folder, f"face_{timestamp.replace(':', '-')}.jpg")
                cv2.imwrite(image_path, frame1)

                wb = openpyxl.load_workbook(excel_file_path)
                sheet = wb.active
                sheet.append(["Unknown", timestamp, time.strftime("%Y-%m-%d")])
                wb.save(excel_file_path)

                with open(log_file_path, "a") as log_file:
                    log_file.write(f"Face detected at {timestamp}, saved image: {image_path}\n")

                send_telegram_message_with_photo(f"Face detected at {timestamp}", image_path)

    for c in contours:
        if cv2.contourArea(c) < 2000:  # ছোট মুভমেন্ট ইগনোর করুন
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

    # পুনরায় detection শুরু করার জন্য after() ব্যবহার
    if running:
        root.after(10, detection_thread)

# GUI তৈরি করা
root = tk.Tk()
root.title("Face and Movement Detection")

# GUI কোড আগের মতোই রাখা হয়েছে
root.geometry("700x500")
logo_image = Image.open("logo.png")
logo_image = logo_image.resize((150, 150), Image.Resampling.LANCZOS)
logo_photo = ImageTk.PhotoImage(logo_image)

logo_label = tk.Label(root, image=logo_photo)
logo_label.pack(pady=10)

heading_label1 = tk.Label(root, text="Information and Communication Engineering", font=("Times New Roman", 15, "bold"))
heading_label1.pack(pady=10)

heading_label2 = tk.Label(root, text="IoT-Integrated Smart Security Surveillance System", font=("Helvetica", 18, "bold"))
heading_label2.pack(pady=5)

blank_line = tk.Label(root, text="", font=("Helvetica", 14))
blank_line.pack(pady=2)

start_button = tk.Button(root, text="Start Detection", font=("Helvetica", 14), command=start_detection)
start_button.place(x=50, y=300)

next_button = tk.Button(root, text="Face Recognition", font=("Helvetica", 14), command=next_program)
next_button.place(x=500, y=300)

stop_button = tk.Button(root, text="       Stop       ", font=("Helvetica", 14), command=stop_detection)
stop_button.place(x=280, y=440)

another_button = tk.Button(root, text="       Fire       ", font=("Helvetica", 14), command=another_program)
another_button.place(x=280, y=380)  # বোতামের অবস্থান (x, y) অনুযায়ী পরিবর্তন করতে পারেন


def toggle_night_mode(event=None):
   global night_mode
   night_mode = not night_mode
   mode_status = "ON" if night_mode else "OFF"
   print(f"Night Mode is now {mode_status}")
   messagebox.showinfo("Night Mode", f"Night Mode is now {mode_status}")

# নাইট মোড টগল করার জন্য `N` কী বোর্ড শর্টকাট যুক্ত করা
root.bind('n', toggle_night_mode)


root.mainloop()
