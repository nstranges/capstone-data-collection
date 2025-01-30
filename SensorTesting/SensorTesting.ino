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

  delay(100);
}

void loop() {
  // Read pulse
  rawPulse = analogRead(pulsePin);

  // Read emgs
  rawEmg1 = analogRead(emgPin1);
  rawEmg2 = analogRead(emgPin2);
  rawEmg3 = analogRead(emgPin3);

  // Print values to be read by the Python script
  Serial.print("xaccel ");
  Serial.println(-1);
  Serial.print("yaccel ");
  Serial.println(-1);
  Serial.print("zaccel ");
  Serial.println(-1);
  Serial.print("xrot ");
  Serial.println(-1);
  Serial.print("yrot ");
  Serial.println(-1);
  Serial.print("zrot ");
  Serial.println(-1);
  Serial.print("emg1 ");
  Serial.println(rawEmg1);
  Serial.print("emg2 ");
  Serial.println(rawEmg2);
  Serial.print("emg3 ");
  Serial.println(rawEmg3);
  Serial.print("pulse ");
  Serial.println(rawPulse);
}
