import subprocess
import cv2
import numpy as np
import os
import time
import pandas as pd
import matplotlib.pyplot as plt
from flask import Flask, Response, render_template
from datetime import datetime
from deepface import DeepFace
from g4f.client import Client

app = Flask(__name__)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# File to store results
LOG_FILE = "experiment_results.csv"

# Function to log results
def log_result(query_type, duration, additional_info=""):
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    additional_info = additional_info.replace(",", ";").replace("\n", " ")
    with open(LOG_FILE, "a") as f:
        f.write(f'"{current_time}","{query_type}",{duration},"{additional_info}"\n')

# Function to analyze face recognition duration
def analyze_face(image):
    start_time = time.time()
    analysis = DeepFace.analyze(image, actions=['age', 'gender', 'emotion'], enforce_detection=False)
    duration = time.time() - start_time
    age = analysis[0]['age']
    gender = analysis[0]['gender']
    emotion = analysis[0]['dominant_emotion']
    log_result("FaceRecognition", duration, f"Age: {age}, Gender: {gender}, Emotion: {emotion}")
    return age, gender, emotion

# Function to capture frames and analyze face
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

# Function to query ChatGPT and log response time
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

# Function to plot results
# Function to plot results separately for ChatGPT and Face Recognition
def plot_results():
    try:
        # Read data from log file
        df = pd.read_csv(LOG_FILE, names=["Time", "QueryType", "Duration", "Info"], on_bad_lines='skip')
        df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
        df = df.dropna(subset=['Time'])

        # Plot ChatGPT response time
        plt.figure(figsize=(10, 5))
        chatgpt_data = df[df["QueryType"] == "ChatGPT"]
        plt.plot(chatgpt_data['Time'], chatgpt_data['Duration'], label="ChatGPT Response Time", marker="o", color="b", linestyle="-")
        plt.xlabel("Time")
        plt.ylabel("Time (seconds)")
        plt.title("ChatGPT Response Time")
        plt.legend()
        plt.tight_layout()
        plt.savefig("static/chatgpt_response_time.png")
        plt.close()

        # Plot Face Recognition response time
        plt.figure(figsize=(10, 5))
        face_recognition_data = df[df["QueryType"] == "FaceRecognition"]
        plt.plot(face_recognition_data['Time'], face_recognition_data['Duration'], label="Face Recognition Response Time", marker="s", color="r", linestyle="--")
        plt.xlabel("Time")
        plt.ylabel("Time (seconds)")
        plt.title("Face Recognition Response Time")
        plt.legend()
        plt.tight_layout()
        plt.savefig("static/face_recognition_response_time.png")
        plt.close()

        return render_template('plot_results.html', df=df)

    except Exception as e:
        print(f"Error generating the plot: {e}")
        return "Error generating the plot."

# Endpoint to display plot
@app.route('/plot')
def plot():
    return plot_results()

# Route to stream video feed
@app.route('/video_feed')
def video_feed():
    query = "Hello, ChatGPT! How are you today?" 
    response = ask_chatgpt(query)
    print("ChatGPT Response:", response)
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Start the Flask app
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Results</title>
</head>
<body>
    <h1>Performance Results</h1>
    
    <h2>ChatGPT Response Time</h2>
    <img src="{{ url_for('static', filename='chatgpt_response_time.png') }}" alt="ChatGPT Response Time">
    
    <h2>Face Recognition Response Time</h2>
    <img src="{{ url_for('static', filename='face_recognition_response_time.png') }}" alt="Face Recognition Response Time">
    
    <h2>Log Data</h2>
    <table>
        <tr>
            <th>Time</th>
            <th>Query Type</th>
            <th>Duration</th>
            <th>Info</th>
        </tr>
        {% for index, row in df.iterrows() %}
        <tr>
            <td>{{ row['Time'] }}</td>
            <td>{{ row['QueryType'] }}</td>
            <td>{{ row['Duration'] }}</td>
            <td>{{ row['Info'] }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>

"""

