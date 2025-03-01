#include <WiFi.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include "SPIFFS.h"
#include <ESP32Servo.h>

Servo SERVO_P;
Servo SERVO_M;
Servo SERVO_LR;
Servo SERVO_B;

#define SERVO_P_PIN 27
#define SERVO_M_PIN 26
#define SERVO_LR_PIN 33
#define SERVO_B_PIN 25

#define MOTOR_1_PIN_1 18
#define MOTOR_1_PIN_2 19
#define MOTOR_2_PIN_1 21
#define MOTOR_2_PIN_2 22

int TRIG_1 = 4;
int ECHO_1 = 2;

int TRIG_2 = 16;
int ECHO_2 = 35;

int TRIG_3 = 17;
int ECHO_3 = 36;

int TRIG_4 = 32;
int ECHO_4 = 39;

int SERVO_P_POS = 0;
int SERVO_M_POS = 0;
int SERVO_LR_POS = 0;
int SERVO_B_POS = 0;

#define FORMAT_SPIFFS_IF_FAILED true

// Replace with your network credentials
const char* ssid = "";
const char* password = "";

// Define minimum distance threshold (in cm)
int MIN_DISTANCE = 10;  // Minimum distance (can be modified)

void servo_balance(Servo &SERVO_, int &CRNT_POS) {
  Serial.println("Balance");
  SERVO_.write(0);
  CRNT_POS = 0;
  delay(10);
}

void servo_control(Servo &SERVO_, int CRNT_POS) {
    SERVO_.write(CRNT_POS);
}

AsyncWebServer server(80);

// Function to measure distance using ultrasonic sensor
long measureDistance(int trigPin, int echoPin) {
    Serial.print("Measuring with TrigPin: ");
    Serial.print(trigPin);
    Serial.print(", EchoPin: ");
    Serial.println(echoPin);

    
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long duration = pulseIn(echoPin, HIGH);
  Serial.print("Pulse duration: ");
    Serial.println(duration);
  long distance = duration* 0.034/2; // Convert to cm
    Serial.print("Distance (cm): ");
    Serial.println(distance);
  return distance;
}

const char index_html[] PROGMEM = R"rawliteral(
<html lang="en">
<head>
   <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Robotic hand</title>
    <style>
            body {
            display: flex;
            flex-direction: column;
            text-align: center;
            justify-content: center;
        }

        .main {
            display: flex;
            flex-direction: column;
            align-self: center;
            justify-content: center;
            align-items: center;
            min-height: 100%;
            width: 100%;
        }
      table { margin-left: auto; margin-right: auto; }
      td { padding: 8 px; }
      .button {
        background-color: #2f4468;
        border: none;
        color: white;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 18px;
        margin: 6px 3px;
        cursor: pointer;
        -webkit-touch-callout: none;
        -webkit-user-select: none;
        -khtml-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
        user-select: none;
        -webkit-tap-highlight-color: rgba(0,0,0,0);
      }
        button,
        input {
            width: 100%;
        }

        label {
            display: block;
            color: #9c8d9d;
        }

        h3 {
            color: #adadad;
            text-align: center;
            margin: 0;
        }

        .row {
            text-align: left;
            width: 100%;
            margin: 1em;
            padding: 1em;
        }

        .alert {
            color: red;
            font-size: 20px;
        }
    </style>
</head>
<body>
    <div class="main">
        <h3 id="obstacle-alert"></h3>
        <div class="row">
            <label for="">PALM</label>
            <input type="range" min="0" max="180" class="slider" onchange="movement('P',this.value)" />
        </div>
        <div class="row">
            <label for="">MIDDLE</label>
            <input type="range" min="0" max="180" class="slider" onchange="movement('M',this.value)" />
        </div>
        <div class="row">
            <label for="">SHOULDER</label>
            <input type="range" min="0" max="180" class="slider" onchange="movement('LR',this.value)" />
        </div>
        <div class="row">
            <label for="">BASE</label>
            <input type="range" min="0" max="180" class="slider" onchange="movement('B',this.value)" />
        </div>
        <table>
          <tr><td colspan="3" align="center"><button class="button" onmousedown="toggleCheckbox('forward');" ontouchstart="toggleCheckbox('forward');" onmouseup="toggleCheckbox('stop');" ontouchend="toggleCheckbox('stop');">Forward</button></td></tr>
          <tr><td align="center"><button class="button" onmousedown="toggleCheckbox('left');" ontouchstart="toggleCheckbox('left');" onmouseup="toggleCheckbox('stop');" ontouchend="toggleCheckbox('stop');">Left</button></td><td align="center"><button class="button" onmousedown="toggleCheckbox('stop');" ontouchstart="toggleCheckbox('stop');">Stop</button></td><td align="center"><button class="button" onmousedown="toggleCheckbox('right');" ontouchstart="toggleCheckbox('right');" onmouseup="toggleCheckbox('stop');" ontouchend="toggleCheckbox('stop');">Right</button></td></tr>
          <tr><td colspan="3" align="center"><button class="button" onmousedown="toggleCheckbox('backward');" ontouchstart="toggleCheckbox('backward');" onmouseup="toggleCheckbox('stop');" ontouchend="toggleCheckbox('stop');">Backward</button></td></tr>                   
        </table>
    </div>

    <script>
        function toggleCheckbox(x) {
fetch('/check_obstacle')
    .then(response => response.json())
    .then(data => {
        const alertElement = document.getElementById('obstacle-alert');
        
        if (data.obstacleDetected) {
            let message = 'Obstacle Detected! Stopping movement. ';

            let directions = [];
            if (data.right) directions.push("Right");
            if (data.front) directions.push("Front");
            if (data.left) directions.push("Left");
            if (data.back) directions.push("Back");

            message += "Location: " + directions.join(", ");
            alertElement.innerText = message;
        } else {
            alertElement.innerText = '';
        }
    })
    .catch(error => console.error('Error fetching obstacle data:', error));

            var xhr = new XMLHttpRequest();
            xhr.open("GET", "/action?go=" + x, true);
            xhr.send();
        }
        function movement(joint,directions) {
            var xhttp = new XMLHttpRequest();
            xhttp.onreadystatechange = function () {
                if (this.readyState == 4 && this.status == 200) {
                    //console.log(this.responseText);
                }
            };
            xhttp.open("GET", "/move?joint=" + joint + "&directions=" + directions, true);
            xhttp.send();
        }
    </script>
</body>
</html>
)rawliteral";

void setup(){
  SERVO_P.attach(SERVO_P_PIN);
  SERVO_M.attach(SERVO_M_PIN);
  SERVO_LR.attach(SERVO_LR_PIN);
  SERVO_B.attach(SERVO_B_PIN);

  pinMode(MOTOR_1_PIN_1, OUTPUT);
  pinMode(MOTOR_1_PIN_2, OUTPUT);
  pinMode(MOTOR_2_PIN_1, OUTPUT);
  pinMode(MOTOR_2_PIN_2, OUTPUT);
  
  pinMode(TRIG_1, OUTPUT); 
  pinMode(ECHO_1, INPUT);
  pinMode(TRIG_2, OUTPUT);
  pinMode(ECHO_2, INPUT);
  pinMode(TRIG_3, OUTPUT); 
  pinMode(ECHO_3, INPUT);
  pinMode(TRIG_4, OUTPUT);
  pinMode(ECHO_4, INPUT);
  
  Serial.begin(115200);

  servo_balance(SERVO_P, SERVO_P_POS);
  servo_balance(SERVO_M, SERVO_M_POS);
  servo_balance(SERVO_LR, SERVO_LR_POS);
  servo_balance(SERVO_B, SERVO_B_POS);
  
  if (!SPIFFS.begin(FORMAT_SPIFFS_IF_FAILED)) {
    Serial.println("SPIFFS Mount Failed");
    return;
  }

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi..");
  }
  
  Serial.println(WiFi.localIP());

server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
  request->send_P(200, "text/html", index_html);
});

server.on("/check_obstacle", HTTP_GET, [](AsyncWebServerRequest *request) {
    long distance1 = measureDistance(TRIG_1, ECHO_1);  
    long distance2 = measureDistance(TRIG_2, ECHO_2);  
    long distance3 = measureDistance(TRIG_3, ECHO_3);  
    long distance4 = measureDistance(TRIG_4, ECHO_4);  

    bool obstacleRight  = (distance1 < MIN_DISTANCE);
    bool obstacleFront  = (distance2 < MIN_DISTANCE);
    bool obstacleLeft   = (distance3 < MIN_DISTANCE);
    bool obstacleBack   = (distance4 < MIN_DISTANCE);

   
    String jsonResponse = "{";
    jsonResponse += "\"obstacleDetected\": " + String(obstacleRight || obstacleFront || obstacleLeft || obstacleBack ? "true" : "false") + ",";
    jsonResponse += "\"right\": " + String(obstacleRight ? "true" : "false") + ",";
    jsonResponse += "\"front\": " + String(obstacleFront ? "true" : "false") + ",";
    jsonResponse += "\"left\": " + String(obstacleLeft ? "true" : "false") + ",";
    jsonResponse += "\"back\": " + String(obstacleBack ? "true" : "false");
    jsonResponse += "}";

    request->send(200, "application/json", jsonResponse);
});

server.on("/move", HTTP_GET, [] (AsyncWebServerRequest *request) {
  String joint;
  String directions;
  int directions_;
  if (request->hasParam("joint")) {
    joint = request->getParam("joint")->value();
    directions = request->getParam("directions")->value();
    directions_ = directions.toInt();

    Serial.print(joint);
    Serial.print(" & ");
    Serial.println(directions);

    if(joint.equals("P")) { servo_control(SERVO_P, directions_); }
    if(joint.equals("M")) { servo_control(SERVO_M, directions_); }
    if(joint.equals("B")) { servo_control(SERVO_B, directions_); }
    if(joint.equals("LR")) { servo_control(SERVO_LR, directions_); }
    
  }
  request->send(200, "text/plain", "OK");
  
});

server.on("/action", HTTP_GET, [] (AsyncWebServerRequest *request) {
  String go;
  if (request->hasParam("go")) {
    go = request->getParam("go")->value();
Serial.print(go);

    // Measure the distances from all four sensors
    long distance1 = measureDistance(TRIG_1, ECHO_1);  // Right
    long distance2 = measureDistance(TRIG_2, ECHO_2);  // Front
    long distance3 = measureDistance(TRIG_3, ECHO_3);  // Left
    long distance4 = measureDistance(TRIG_4, ECHO_4);  // Back

    // Check if any direction has an obstacle within the minimum distance
    bool obstacleRight = (distance1 < MIN_DISTANCE);
    bool obstacleFront = (distance2 < MIN_DISTANCE);
    bool obstacleLeft = (distance3 < MIN_DISTANCE);
    bool obstacleBack = (distance4 < MIN_DISTANCE);

    // If there is an obstacle, prevent movement in the corresponding direction
    if (go.equals("forward") && obstacleFront) {
      Serial.println("Obstacle detected in front! Stopping forward movement.");
      return;
    }
    else if (go.equals("backward") && obstacleBack) {
      Serial.println("Obstacle detected behind! Stopping backward movement.");
      return;
    }
    else if (go.equals("left") && obstacleLeft) {
      Serial.println("Obstacle detected on the left! Stopping left movement.");
      return;
    }
    else if (go.equals("right") && obstacleRight) {
      Serial.println("Obstacle detected on the right! Stopping right movement.");
      return;
    }
    
  if(go.equals("forward")) {
    Serial.println("Forward");
    digitalWrite(MOTOR_1_PIN_1, 1);
    digitalWrite(MOTOR_1_PIN_2, 0);
    digitalWrite(MOTOR_2_PIN_1, 1);
    digitalWrite(MOTOR_2_PIN_2, 0);
  }
  else if(go.equals("left")) {
    Serial.println("Left");
    digitalWrite(MOTOR_1_PIN_1, 0);
    digitalWrite(MOTOR_1_PIN_2, 1);
    digitalWrite(MOTOR_2_PIN_1, 1);
    digitalWrite(MOTOR_2_PIN_2, 0);
  }
  else if(go.equals("right")) {
    Serial.println("Right");
    digitalWrite(MOTOR_1_PIN_1, 1);
    digitalWrite(MOTOR_1_PIN_2, 0);
    digitalWrite(MOTOR_2_PIN_1, 0);
    digitalWrite(MOTOR_2_PIN_2, 1);
  }
  else if(go.equals("backward")) {
    Serial.println("Backward");
    digitalWrite(MOTOR_1_PIN_1, 0);
    digitalWrite(MOTOR_1_PIN_2, 1);
    digitalWrite(MOTOR_2_PIN_1, 0);
    digitalWrite(MOTOR_2_PIN_2, 1);
  }
  else if(go.equals("stop")) {
    Serial.println("Stop");
    digitalWrite(MOTOR_1_PIN_1, 0);
    digitalWrite(MOTOR_1_PIN_2, 0);
    digitalWrite(MOTOR_2_PIN_1, 0);
    digitalWrite(MOTOR_2_PIN_2, 0);
  }
    
  }
  request->send(200, "text/plain", "OK");
  
});

server.begin();
}

void loop() {
}
