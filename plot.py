import io
import subprocess
import cv2
import numpy as np
import os
import time
import speech_recognition as sr
import pandas as pd
import matplotlib.pyplot as plt
from gtts import gTTS
import wikipedia
from datetime import datetime
import pytz
from flask import Flask, Response, render_template
from deepface import DeepFace
from g4f.client import Client

app = Flask(__name__)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Файл для запису результатів експерименту
LOG_FILE = "experiment_results.csv"

# Функція для запису результатів у файл
def log_result(query_type, duration, additional_info=""):
    with open(LOG_FILE, "a") as f:
        f.write(f"{query_type},{duration},{additional_info}\n")

# Функція для аналізу тривалості відповіді ChatGPT
def ask_chatgpt(prompt):
    client = Client()
    start_time = time.time()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        web_search=False
    )
    duration = time.time() - start_time
    log_result("ChatGPT", duration, prompt)
    return response.choices[0].message.content

# Функція для аналізу тривалості розпізнавання облич
def analyze_face(image):
    start_time = time.time()
    analysis = DeepFace.analyze(image, actions=['age', 'gender', 'emotion'], enforce_detection=False)
    duration = time.time() - start_time
    age = analysis[0]['age']
    gender = analysis[0]['gender']
    emotion = analysis[0]['dominant_emotion']
    log_result("FaceRecognition", duration, f"Age: {age}, Gender: {gender}, Emotion: {emotion}")
    return age, gender, emotion

# Функція для отримання кадрів та аналізу
def gen():
    while True:
        cmd = ['libcamera-still', '--width', '640', '--height', '480', '--output', '/dev/stdout', '--quality', '10']
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        frame = process.stdout.read()

        if frame:
            np_array = np.frombuffer(frame, np.uint8)
            image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            for (x, y, w, h) in faces:
                face_image = image[y:y+h, x:x+w]

                try:
                    age, gender, emotion = analyze_face(face_image)
                    cv2.putText(image, f'Age: {age}', (x, y-30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    cv2.putText(image, f'Gender: {gender}', (x, y-50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    cv2.putText(image, f'Emotion: {emotion}', (x, y-70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                except Exception as e:
                    print(f"Error analyzing face: {e}")

                cv2.rectangle(image, (x, y), (x + w, y + h), (255, 0, 0), 2)

            ret, jpeg = cv2.imencode('.jpg', image)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

# Функція для побудови графіків
def plot_results():
    try:
        df = pd.read_csv(LOG_FILE, names=["QueryType", "Duration", "Info"])
        
        plt.figure(figsize=(10, 5))

        # Графік часу відповіді ChatGPT
        chatgpt_data = df[df["QueryType"] == "ChatGPT"]
        plt.subplot(1, 2, 1)
        plt.plot(chatgpt_data.index, chatgpt_data["Duration"], marker="o", linestyle="-", color="b", label="ChatGPT Time")
        plt.xlabel("Запит")
        plt.ylabel("Час (сек)")
        plt.title("Час відповіді ChatGPT")
        plt.legend()

        # Графік часу розпізнавання облич
        face_data = df[df["QueryType"] == "FaceRecognition"]
        plt.subplot(1, 2, 2)
        plt.plot(face_data.index, face_data["Duration"], marker="s", linestyle="--", color="r", label="FaceRecognition Time")
        plt.xlabel("Запит")
        plt.ylabel("Час (сек)")
        plt.title("Час розпізнавання облич")
        plt.legend()

        plt.tight_layout()
        plt.savefig("experiment_results.png")
        plt.show()

    except Exception as e:
        print(f"Помилка при побудові графіка: {e}")

@app.route('/video_feed')
def video_feed():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/plot')
def plot():
    plot_results()
    return "Графіки збережено у файлі experiment_results.png"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
