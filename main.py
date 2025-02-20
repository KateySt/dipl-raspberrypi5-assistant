import io
import subprocess
import cv2
import numpy as np
import os
import speech_recognition as sr
from gtts import gTTS
import wikipedia
from datetime import datetime
import pytz
import threading
from flask import Flask, Response, render_template
from deepface import DeepFace 
from g4f.client import Client

app = Flask(__name__)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def ask_chatgpt(prompt):
    client = Client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        web_search=False
    )
    print(response.choices[0].message.content)
    return response.choices[0].message.content

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
                    analysis = DeepFace.analyze(face_image, actions=['age', 'gender', 'emotion'], enforce_detection=False)
                    age = analysis[0]['age']
                    gender = analysis[0]['gender']
                    emotion = analysis[0]['dominant_emotion']

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

def speak(text):
    if not text.strip():
        print("Empty text provided to speak()")
        return

    try:
        tts = gTTS(text=text, lang='en')
        tts.save("audio.mp3")
        os.system("mpg321 audio.mp3")
    except Exception as e:
        print(f"Error while speaking: {e}")

def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Listening...")
        audio = recognizer.listen(source, phrase_time_limit=4)

    try:
        print("You said: " + recognizer.recognize_google(audio))
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        print("Sorry, I didn't catch that.")
        return None
    except sr.RequestError as e:
        print(f"Error with the speech recognition service: {e}")
        return None

def search_wikipedia(query):
    try:
        if query.lower().startswith("who is") or query.lower().startswith("who are"):
            person = query[4:].strip()  
            summary = wikipedia.summary(person, sentences=2) 
            print(f"Information about {person}: {summary}")
            speak(summary)
        else:
            print("I can only search for 'Who is' or 'Who are' questions right now.")
            speak("Sorry, I can only search for 'Who is' or 'Who are' questions.")
    except wikipedia.exceptions.DisambiguationError as e:
        print(f"Disambiguation Error: {e}")
        speak("Sorry, there are multiple people or topics with that name. Please be more specific.")
    except wikipedia.exceptions.PageError:
        print("Sorry, I couldn't find any information on Wikipedia for that search.")
        speak("Sorry, I couldn't find any information on Wikipedia for that search.")

def get_current_date_time():
    local_time = datetime.now(pytz.timezone("Europe/Kyiv"))
    return local_time.strftime("%A, %d %B %Y, %I:%M %p")

def voice_command_loop():
    while True:
        speech = speech_to_text()
        if speech:
            print(f"You said: {speech}")
            speak(speech)

            if "repeat after me" in speech.lower():
                print("Repeating: " + speech[15:]) 
                speak(speech[15:])
            elif "who is" in speech.lower() or "who are" in speech.lower():
                search_wikipedia(speech)
            elif "what day is it" in speech.lower() or "what is the date" in speech.lower():
                current_date_time = get_current_date_time()
                print(f"The current date and time is: {current_date_time}")
                speak(f"The current date and time is: {current_date_time}")
            elif "chat" in speech.lower():
                print("Chat find : " + speech[9:])
                response = ask_chatgpt(speech[9:])
                print("Response ChatGPT:", response)
                speak(response)
            else:
                print("I didn't understand your request.")

@app.route('/')
def index():
    return '''\
        <html>
            <head>
                <title>Robot Control</title>
                <script>
                    let baseUrl1 = "";
                    let baseUrl2 = "";

                    function setBaseUrls() {
                        baseUrl1 = document.getElementById("baseUrl1").value;
                        baseUrl2 = document.getElementById("baseUrl2").value;
                        if (baseUrl1) {
                            document.getElementById("streamImg").src = baseUrl1 + "/stream";
                        } else {
                            alert("Enter URL to move!");
                        }
                    }

                    function sendCommand(command) {
                        if (baseUrl1) {
                            fetch(baseUrl1 + "/action?go=" + command)
                                .then(response => console.log("Command sent:", command))
                                .catch(error => console.error("Error:", error));
                        } else {
                            alert("Enter URL to move!");
                        }
                    }

                    function sendAngle(joint, value) {
                        if (baseUrl2) {
                            fetch(baseUrl2 + "/move?joint=" + joint + "&direction=" + value)
                                .then(response => console.log(`Angle sent: ${joint}=${value}`))
                                .catch(error => console.error("Error:", error));
                        } else {
                            alert("Enter URL to control corners!");
                        }
                    }
                </script>
            </head>
            <body>
                <h1>Robot Control Interface</h1>
                <img src="/video_feed" width="640" height="480"><br>
                <h1>ESP32-CAM Robot</h1>
                <img id="streamImg" src="/stream" width="640" height="480"><br>
                <label>Base URL for movement:</label>
                <input type="text" id="baseUrl1" value="http://192.168.0.100" placeholder="http://192.168.0.100/"><br>
                <label>Base URL for angles:</label>
                <input type="text" id="baseUrl2" value="http://192.168.0.101" placeholder="http://192.168.0.101/"><br>
                <button onclick="setBaseUrls()">Set URLs</button>
                
                <h2>Movement Controls</h2>
                <button onclick="sendCommand('forward')">Forward</button>
                <button onclick="sendCommand('backward')">Backward</button>
                <button onclick="sendCommand('left')">Left</button>
                <button onclick="sendCommand('right')">Right</button>
                <button onclick="sendCommand('stop')">Stop</button>

                <h2>Joint Control</h2>
                <label>P:</label>
                <input type="range" min="0" max="180" onchange="sendAngle('P', this.value)">
                <label>M:</label>
                <input type="range" min="0" max="180" onchange="sendAngle('M', this.value)">
                <label>LR:</label>
                <input type="range" min="0" max="180" onchange="sendAngle('LR', this.value)">
                <label>B:</label>
                <input type="range" min="0" max="180" onchange="sendAngle('B', this.value)">
            </body>
        </html>
    '''

@app.route('/video_feed')
def video_feed():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    voice_thread = threading.Thread(target=voice_command_loop)
    voice_thread.daemon = True
    voice_thread.start()

    app.run(host='0.0.0.0', port=8000, debug=True)
