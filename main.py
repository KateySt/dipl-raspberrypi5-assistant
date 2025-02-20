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

app = Flask(__name__)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

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
            else:
                print("I didn't understand your request.")

@app.route('/')
def index():
    return '''\
        <html>
            <head>
                <title>Raspberry Pi Camera</title>
            </head>
            <body>
                <h1>Raspberry Pi - Surveillance Camera</h1>
                <img src="/video_feed" width="640" height="480">
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
