#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

// MPU
Adafruit_MPU6050 mpu;

// Pulse sensor
int pulsePin = 4;
int rawPulse;

// Emg sensors
int emgPin1 = 2;
int rawEmg1;
int emgPin2 = 12;
int rawEmg2;
int emgPin3 = 13;
int rawEmg3;

void setup(void) {
  Serial.begin(115200);
  while (!Serial)
    delay(10);

  // Try to initialize!
  if (!mpu.begin()) {
    while (1) {
      delay(10);
    }
  }

  // Setting mpu params
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  delay(100);
}

void loop() {
  // Read pulse
  rawPulse = analogRead(pulsePin);

  // Read emgs
  rawEmg1 = analogRead(emgPin1);
  rawEmg2 = analogRead(emgPin2);
  rawEmg3 = analogRead(emgPin3);

  // Read mpu
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  // Print values to be read by the Python script
  Serial.print("xaccel ");
  Serial.println(a.acceleration.x);
  Serial.print("yaccel ");
  Serial.println(a.acceleration.y);
  Serial.print("zaccel ");
  Serial.println(a.acceleration.z);
  Serial.print("xrot ");
  Serial.println(a.gyro.x);
  Serial.print("yrot ");
  Serial.println(a.gyro.y);
  Serial.print("zrot ");
  Serial.println(a.gyro.z);
  Serial.print("emg1 ");
  Serial.println(rawEmg1);
  Serial.print("emg2 ");
  Serial.println(rawEmg2);
  Serial.print("emg3 ");
  Serial.println(rawEmg3);
  Serial.print("pulse ");
  Serial.println(rawPulse);
}
