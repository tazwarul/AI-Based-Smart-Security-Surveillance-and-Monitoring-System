import winsound  # Windows এর জন্য সাউন্ড প্লে করার জন্য
import cvzone
import cv2
import math
import os
from ultralytics import YOLO
import time  # সময়ের জন্য প্রয়োজন
import threading  # For background threading
import requests  # To send images to Telegram
from twilio.rest import Client  # Twilio for voice calls

# Your Telegram bot API token
API_TOKEN = '7759523827:AAGxoNH4wowcv83EEjdzXhEocM0RWJBMd8A'
# Your chat ID (can be found by messaging your bot and using getUpdates API or using @userinfobot on Telegram)
CHAT_ID = '1184192406'

# Twilio configuration
TWILIO_ACCOUNT_SID = 'AC2260d2dfcb6e1f1ef0dbecff9e28ee8b'
TWILIO_AUTH_TOKEN = '7678b0187d3ef1a3374e49b3b1c7e9c7'
TWILIO_PHONE_NUMBER = '+17087873133'  # Your Twilio phone number
TO_PHONE_NUMBER = '+8801974015696'  # The phone number you want to call

# Running real-time from webcam
cap = cv2.VideoCapture(0)  # লাইভ ক্যামেরা
model = YOLO('fire1.pt')  # প্রশিক্ষিত YOLO মডেল লোড

# Reading the classes
classnames = ['Fire']

# এলার্ট সাউন্ডের ফাইল (WAV ফাইল)
alert_sound_path = 'alert.wav'  # .wav ফাইল ব্যবহার করা হচ্ছে

# সনাক্তকৃত ফ্রেমের জন্য সেভ ফোল্ডার
output_folder = "detected_frames"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# সাউন্ড প্লে করার ফাংশন
last_played_time = 0  # সাউন্ড শেষ প্লে হওয়ার সময়

def play_sound():
    global last_played_time
    current_time = time.time()  # বর্তমান সময় নেয়া হচ্ছে
    if current_time - last_played_time >= 2:  # ২ সেকেন্ডের গ্যাপ চেক
        winsound.PlaySound(alert_sound_path, winsound.SND_ASYNC)  # নন-ব্লকিং সাউন্ড
        last_played_time = current_time  # সাউন্ড প্লে হওয়ার সময় আপডেট করা

# Function to send image to Telegram
def send_image_to_telegram(image_path):
    url = f'https://api.telegram.org/bot{API_TOKEN}/sendPhoto'
    with open(image_path, 'rb') as photo:
        response = requests.post(url, data={'chat_id': CHAT_ID}, files={'photo': photo})
    return response

# Function to make a voice call via Twilio
def make_voice_call():
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        call = client.calls.create(
            to=TO_PHONE_NUMBER,
            from_=TWILIO_PHONE_NUMBER,
            twiml='<Response><Say>Alert! Fire has been detected. Please take immediate action.</Say></Response>'
        )
        print("Voice call alert initiated successfully!")
    except Exception as e:
        print(f"Error making voice call: {e}")

# Function to run in background thread for sending images to Telegram
def send_image_in_background(image_path):
    threading.Thread(target=send_image_to_telegram, args=(image_path,)).start()

# Add a flag to track if the call has already been made
call_made = False  # Initial state: no call has been made

while True:
    ret, frame = cap.read()
    if not ret:
        print("ক্যামেরা থেকে ফ্রেম পড়তে সমস্যা হচ্ছে।")
        break

    frame = cv2.resize(frame, (640, 480))  # রেজোলিউশন সেট করা
    result = model(frame, stream=True)

    # Getting bbox, confidence, and class names
    for info in result:
        boxes = info.boxes
        for box in boxes:
            confidence = box.conf[0]
            confidence = math.ceil(confidence * 100)
            Class = int(box.cls[0])
            if confidence > 70:  # থ্রেশোল্ড ৭০% সেট করা
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 5)
                cvzone.putTextRect(frame, f'{classnames[Class]} {confidence}%', [x1 + 5, y1 + 25],
                                   scale=1.5, thickness=2)

                # এলার্ট মেসেজ
                print(f"Fire detected with {confidence}% confidence!")

                # সাউন্ড এলার্ট চালু
                if os.path.exists(alert_sound_path):
                    play_sound()  # সাউন্ড প্লে
                else:
                    print("অ্যালার্ট সাউন্ড ফাইল পাওয়া যায়নি।")

                # ফ্রেম সেভ করা, ফাইল নামের মধ্যে টাইমস্ট্যাম্প যুক্ত করা হবে যাতে আলাদা আলাদা ছবি সেভ হয়
                timestamp = time.strftime("%Y%m%d_%H%M%S")  # টাইমস্ট্যাম্প তৈরি
                output_path = os.path.join(output_folder, f'detected_fire_{timestamp}.jpg')
                cv2.imwrite(output_path, frame)
                print(f"সনাক্তকৃত ফ্রেম সেভ করা হয়েছে: {output_path}")

                # Send image to Telegram in a separate thread
                send_image_in_background(output_path)

                # Make a voice call only once
                if not call_made:
                    make_voice_call()
                    call_made = True  # Set the flag to True after making the call

    # Display the frame
    cv2.imshow('Fire Detection', frame)

    # Exit on pressing 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
