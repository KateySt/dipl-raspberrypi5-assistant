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

#define MOTOR_1_PIN_1 14
#define MOTOR_1_PIN_2 32
#define MOTOR_2_PIN_1 34
#define MOTOR_2_PIN_2 35

int SERVO_P_POS = 0;
int SERVO_M_POS = 0;
int SERVO_LR_POS = 0;
int SERVO_B_POS = 0;

#define FORMAT_SPIFFS_IF_FAILED true

const char* ssid = "";
const char* password = "";

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

void servo_balance(Servo &SERVO_, int &CRNT_POS);
void servo_control(Servo &SERVO_, int CRNT_POS);

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
            width: 25vw;
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
            box-shadow: 0 4px 10px 0 rgb(0 0 0 / 20%), 0 4px 20px 0 rgb(0 0 0 / 19%);
            margin: 1em;
            padding: 1em;
        }
    </style>
</head>

<body>

    <div class="main">
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
    
    //int move_state = state.toInt();

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
  else if(!strcmp(variable, "stop")) {
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
