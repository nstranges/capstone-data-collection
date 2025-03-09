#include <PID_v1.h>

// Flex pin attachments. CHANGE FOR ESP
const int FLEX_PIN1 = A0;
const int FLEX_PIN2 = A1;
const int FLEX_PIN3 = A2;

// Holds tuning values
struct params {
  double Kp;
  double Ki;
  double Kd;
};

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
params pidParams1 = {5.884, 27.125, 0.0};
params pidParams2 = {5.884, 27.125, 0.0};
params pidParams3 = {5.884, 27.125, 0.0};

// Create PID objects
PID loop1(&flexADC1, &motorPos1, &setpoint1, pidParams1.Kp, pidParams1.Ki, pidParams1.Kd, DIRECT);
PID loop2(&flexADC2, &motorPos2, &setpoint2, pidParams2.Kp, pidParams2.Ki, pidParams2.Kd, DIRECT);
PID loop3(&flexADC3, &motorPos3, &setpoint3, pidParams3.Kp, pidParams3.Ki, pidParams3.Kd, DIRECT);

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

    loop1.Compute();
    
    delay(250);
}
