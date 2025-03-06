#include <PID_v1.h>

// Flex pin attachments. CHANGE FOR ESP
const int FLEX_PIN1 = A0;
const int FLEX_PIN1 = A1;
const int FLEX_PIN1 = A2;

// Holds tuning values
struct params {
  kp;
  ki;
  kd;
}
params pidParams1;
params pidParams2;
params pidParams3;

// ADJUST USING THE MAP
double setpoint1;
double setpoint2;
double setpoint3;

// Input and output values
double flexADC1;
double motorPos1;
double flexADC2;
double motorPos2;
double flexADC3;
double motorPos3;

// PID tuning values
pidParams1.Kp = 5.884;
pidParams1.Ki = 27.125; 
pidParams1.Kd = 0;

pidParams2.Kp = 5.884;
pidParams2.Ki = 27.125; 
pidParams2.Kd = 0;

pidParams3.Kp = 5.884;
pidParams3.Ki = 27.125; 
pidParams3.Kd = 0;

// Create PID objects
PID loop1(&flexADC1, &motorPos1, &setpoint1, Kp, Ki, Kd, DIRECT);
PID loop2(&flexADC2, &motorPos2, &setpoint2, Kp, Ki, Kd, DIRECT);
PID loop3(&flexADC3, &motorPos3, &setpoint3, Kp, Ki, Kd, DIRECT);

void setup() {
    Serial.begin(9600);

    // Setting input pins
    pinMode(FLEX_PIN1, INPUT);
    pinMode(FLEX_PIN2, INPUT);
    pinMode(FLEX_PIN3, INPUT);

    // Enable PIDs
    loop1.SetMode(AUTOMATIC);
    loop2.SetMode(AUTOMATIC);
    loop3.SetMode(AUTOMATIC);
}

void loop() {
    flexADC1 = analogRead(FLEX_PIN1);
    Serial.println("Input: " + String(flexADC));

    loop1.compute();
    
    delay(250);
}
