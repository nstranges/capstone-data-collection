// WIFI_AP settings.
const char* AP_SSID = "ESP32_DEV";
const char* AP_PWD  = "12345678";

// WIFI_STA settings.
const char* STA_SSID = "OnePlus 8";
const char* STA_PWD  = "40963840";

// the MAC address of the device you want to ctrl.
uint8_t broadcastAddress[] = {0x08, 0x3A, 0xF2, 0x93, 0x5F, 0xA8};
// uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};


typedef struct struct_message {
  int ID_send;
  int POS_send;
  int Spd_send;
} struct_message;

// Create a struct_message called myData
struct_message myData;


// set the default role here.
// 0 as normal mode.
// 1 as leader, ctrl other device via ESP-NOW.
// 2 as follower, can be controled via ESP-NOW.
#define DEFAULT_ROLE 0


// set the default wifi mode here.
// 1 as [AP] mode, it will not connect other wifi.
// 2 as [STA] mode, it will connect to know wifi.
#define DEFAULT_WIFI_MODE 1

// the uart used to control servos.
// GPIO 18 - S_RXD, GPIO 19 - S_TXD, as default.
#define S_RXD 18
#define S_TXD 19

// the IIC used to control OLED screen.
// GPIO 21 - S_SDA, GPIO 22 - S_SCL, as default.
#define S_SCL 22
#define S_SDA 21

// the GPIO used to control RGB LEDs.
// GPIO 23, as default.
#define RGB_LED   23
#define NUMPIXELS 10

// set the max ID.
int MAX_ID = 20;

// modeSelected.
// set the SERIAL_FORWARDING as true to control the servos with USB.
bool SERIAL_FORWARDING = false;

// OLED Screen Dispaly.
// Row1: MAC address.
// Row2: VCC --- IP address.
// Row3: MODE:Leader/Follower  [AP]/[STA][RSSI]
//       DEFAULT_ROLE: 1-Leader(L)/ 2-Follower(F).
//       DEFAULT_WIFI_MODE: 1-[AP]/ 2-[STA][RSSI] / 3-[TRY:SSID].
//       (no matter what wifi mode you select, you can always ctrl it via ESP-NOW.)
// Row4: the position of servo 1, 2 and 3.
String MAC_ADDRESS;
IPAddress IP_ADDRESS;
byte   SERVO_NUMBER;
byte   DEV_ROLE;
byte   WIFI_MODE;
int    WIFI_RSSI;

// set the interval of the threading.
#define threadingInterval 600
#define clientInterval    10

#if CONFIG_FREERTOS_UNICORE
#define ARDUINO_RUNNING_CORE 0
#else
#define ARDUINO_RUNNING_CORE 1
#endif

#include "RGB_CTRL.h"
#include "STSCTRL.h"
#include "CONNECT.h"
#include "BOARD_DEV.h"
#include <SCServo.h>
#include "BluetoothSerial.h"

HardwareSerial MySerial(1);  // Create a new HardwareSerial instance
BluetoothSerial SerialBT; // bluetooth instance

// For tracking time
unsigned long previousMillis = 0;
const unsigned long interval = 10;
const int numMotors = 3;

// Converting position to wanted value
int convFactor = 1; //11; // Estimated 4096/360 (one for now to do this)
bool motorMode[numMotors] = {false, false, false};
int wantedPos = 0;
int maxPosVal = 4096;
int rotCount = 0;
bool pidMode = false;
int totalPosition[numMotors] = {0};
int lastRawPos[numMotors] = {0};
int turnCount[numMotors] = {0}; 
int contSpeed[numMotors] = {0}; 

// Control variables
byte ID[numMotors];
int16_t Position[numMotors];
uint16_t Speed[numMotors];
byte ACC[numMotors];
int loadFbk[numMotors];
int posFbk[numMotors];

void setup() {
  Serial.begin(115200);
  while(!Serial) {}

  SerialBT.begin("ESP32_Server");

  // For the motor communication
  MySerial.begin(1000000, SERIAL_8N1, S_RXD, S_TXD);
  st.pSerial = &MySerial;

  InitRGB();

  espNowInit();
  
  getMAC();
  
  boardDevInit();

  RGBcolor(0, 64, 255);

  servoInit();

  wifiInit();

  webServerSetup();

  RGBoff();

  delay(1000);
  pingAll(true);

  threadInit();

  // Setting all of the motor speed controls
  for (int i = 0; i < numMotors; i++) {
    ID[i] = i+1;   // Save the ID
    Speed[i] = 3400;  // Set the servo speed
    ACC[i] = 100;   // Set the start/stop acceleration. The smaller the value, the lower the acceleration. The maximum value that can be set is 150.

    st.unLockEprom(ID[i]);
    st.writeByte(ID[i], SMS_STS_MODE, 1);
    st.LockEprom(ID[i]);
  }
}


void loop() {
  unsigned long currentMillis = millis();
  String gotData = "";
  String sendData = "";
  int lastIndex = 0, index = 0;
  int feedbackVals[numMotors];

  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

    if (SerialBT.available()) {
      // Read values as a String
      gotData = SerialBT.readStringUntil('\n');

      if (gotData != "") {
        // Extract position and torque feedback
        for (int i = 0; i < numMotors; i++) {
          int nextIndex = gotData.indexOf(',', lastIndex);
          if (nextIndex == -1) nextIndex = gotData.length();
          
          // Negative to accomodate motor mount orientation
          feedbackVals[i] = -(gotData.substring(lastIndex, nextIndex).toInt());
          lastIndex = nextIndex + 1;
        }

        for (int i = 0; i < numMotors; i++) {
            int rawPos = st.ReadPos(ID[i]);
            int delta = rawPos - lastRawPos[i];
        
            // Handle wraparound
            if (delta > 3000) {
                turnCount[i]--;
            } else if (delta < -3000) {
                turnCount[i]++;
            }
        
            totalPosition[i] = turnCount[i] * 4096 + rawPos;
            lastRawPos[i] = rawPos;
        
            // Proportional speed control
            int error = feedbackVals[i] - totalPosition[i];
            contSpeed[i] = constrain(error * 2, -3400, 3400);
            if (abs(error) < 5) contSpeed[i] = 0;
        
            st.WriteSpe(ID[i], contSpeed[i]);
        }
        
        // If we want to give feedback to the PID loop
        if (pidMode) {
          // Reading the feedback of the servos
          for (int i = 0; i < numMotors; i++) {
            loadFbk[i] = st.ReadLoad(i+1);
            sendData = sendData + "," + String(loadFbk[i]);

            if (motorMode[i]) {
              posFbk[i] = totalPosition[i];
            }
            else {
              posFbk[i] = st.ReadPos(i+1);
            }
            
            sendData = sendData + "," + String(posFbk[i]);
          }

          // Sending the response back
          SerialBT.println(sendData);
        }
      }
      else {
        for (int i = 0; i < numMotors; i++) {
          Position[i] = 0;
        }
        st.SyncWritePosEx(ID, 3, Position, Speed, ACC);
      }
    }
  }
}


// > > > > > > > > > DOC < < < < < < < < <
// === Develop Board Ctrl ===
// get the MAC address and save it in MAC_ADDRESS;
// getMAC();

// Init GPIO.
// pinMode(PIN_NUM, OUTPUT);
// pinMode(PIN_NUM, INPUT_PULLUP);

// set the level of GPIO.
// digitalWrite(PIN_NUM, LOW);
// digitalWrite(PIN_NUM, HIGH);

// PWM output(GPIO).
// int freq = 50;
// resolution = 12;
// ledcSetup(PWM_NUM, frep, resolution);
// ledcAttachPin(PIN_NUM, PWM_NUM);
// ledcWrite(PWM_NUM, PWM);


// === Servo Ctrl ===
// GPIO 18 as RX, GPIO 19 as TX, init the serial and the servos.
// servoInit();

// set the position as middle pos.
// setMiddle(servoID);
// st.WritePosEx(ID, position, speed, acc);



// === Devices Ctrl ===
// ctrl the RGB.
// 0 < (R, G, B) <= 255
// setSingleLED(LED_ID, matrix.Color(R, G, B));

// init the OLED screen, RGB_LED.
// boardDevInit();

// dispaly the newest information on the screen.
// screenUpdate();
