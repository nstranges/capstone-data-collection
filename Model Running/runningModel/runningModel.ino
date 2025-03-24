#include <string.h>
#include "helpers.h"
#include <PID_v1.h>
#include "BluetoothSerial.h"

// The required setpoints for the positions
const int numMotors = 3;
const int numClasses = 8;
double setpoints[numClasses][numMotors] = {
    {0, 0, 0},  
    {350, 0, 0},  
    {0, 350, 0},  
    {0, 0, 350},  
    {350, 350, 0},  
    {350, 0, 350},  
    {0, 350, 350},  
    {350, 350, 350}
};

// This is for the simple control mode
// Fully closed is 1030deg. (4096/360)*1031 = 11,729 fully closed 
double motContPositions[numClasses][numMotors] = {
    {0, 0, 0},  
    {11729, 0, 0},  
    {0, 11729, 0},  
    {0, 0, 11729},  
    {11729, 11729, 0},  
    {11729, 0, 11729},  
    {0, 11729, 11729},  
    {11729, 11729, 11729}
};

// The bluetooth serial module
BluetoothSerial SerialBT;

// Flex pin attachments
const int FLEX_PIN1 = 25;
const int FLEX_PIN2 = 26;
const int FLEX_PIN3 = 27;

// Holds tuning values
struct PIDParams {
  double Kp;
  double Ki;
  double Kd;
};

// Torque hold mode for grabbing stuff
double setpoint1;
double setpoint2;
double setpoint3;
bool torqueHoldMode[numMotors] = {false, false, false};
bool pidMode = false;
bool modelInference = false;
int curModelTestOut = 1;
int modelTestOutCount = 0;
int secondsToHoldTest = 5;
bool backToHomePos = true;
int torqueThreshold = 0; // CHANGE THIS FROM TESTING

// Input and output values
double flexADC1;
double motorPos1;
double flexADC2;
double motorPos2;
double flexADC3;
double motorPos3;

// PID tuning values
PIDParams pidParams1 = {5.146, 17.4956, 0.0};
PIDParams pidParams2 = {5.146, 17.4956, 0.0};
PIDParams pidParams3 = {5.146, 17.4956, 0.0};

// Create PID objects
PID loop1(&flexADC1, &motorPos1, &setpoint1, pidParams1.Kp, pidParams1.Ki, pidParams1.Kd, DIRECT);
PID loop2(&flexADC2, &motorPos2, &setpoint2, pidParams2.Kp, pidParams2.Ki, pidParams2.Kd, DIRECT);
PID loop3(&flexADC3, &motorPos3, &setpoint3, pidParams3.Kp, pidParams3.Ki, pidParams3.Kd, DIRECT);

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

// Prediction params
double input[numClasses];
double output[numClasses];

// For sequential samples
int predVar = 0;
int predVarCount = 0;
const int MAX_PRED_VAR_COUNT = 10;

// Shared data queue
struct SharedData {
    int emg1;
    int emg2;
    int emg3;
    int pulse;
};

// Samples to collect
const int NUM_SAMPLES = 15;
SharedData samples[NUM_SAMPLES];
int curSampleCount = 0;

// Delay times in ms
const int AVG_SAMPLE_TIME = 18;
const int PID_CHANGE_TIME = 2;
const int MODEL_DELAY_TIME = 1000;

// Data for the feature engineering
// The array is avg, var
struct FeatEng {
    double emg1[2];
    double emg2[2];
    double emg3[2];
    double pulse[2];
};

// For the model results
volatile bool modelDone = false;
volatile bool dataDone = false;
volatile int modelOutput = 0;
volatile bool modelDelay = false;
volatile int pidCommand = 0;
FeatEng features;

// Data passing
SemaphoreHandle_t featuresMutex;
SemaphoreHandle_t modelFlagMutex;
SemaphoreHandle_t outputMutex;
SemaphoreHandle_t delayMutex;

// Task declaration
TaskHandle_t Task1;
TaskHandle_t Task2;
TaskHandle_t Task3;

void setup(void) {
    Serial.begin(115200);

    // Enable bluetooth in master mode
    SerialBT.begin("ESP32_Client", true);
    if (SerialBT.connect("ESP32_Server")) {
        Serial.println("Connected to ESP32_Server!");
    } else {
        Serial.println("Failed to connect. Check server Bluetooth.");
        while (true);
    }

    // Setting input pins
    pinMode(FLEX_PIN1, INPUT);
    pinMode(FLEX_PIN2, INPUT);
    pinMode(FLEX_PIN3, INPUT);

    // Enable PIDs
    loop1.SetMode(AUTOMATIC);
    loop2.SetMode(AUTOMATIC);
    loop3.SetMode(AUTOMATIC);

    // Create semaphores
    featuresMutex = xSemaphoreCreateMutex();
    if (featuresMutex == NULL) {
        Serial.println("Failed to create featuresMutex");
        while (1);  // Halt the program
    }

    modelFlagMutex = xSemaphoreCreateMutex();
    if (modelFlagMutex == NULL) {
        Serial.println("Failed to create modelFlagMutex");
        while (1);  // Halt the program
    }

    outputMutex = xSemaphoreCreateMutex();
    if (outputMutex == NULL) {
        Serial.println("Failed to create outputMutex");
        while (1);  // Halt the program
    }

    delayMutex = xSemaphoreCreateMutex();
    if (delayMutex == NULL) {
        Serial.println("Failed to create delayMutex");
        while (1);  // Halt the program
    }

    xTaskCreatePinnedToCore(
                    SensorCollection,       /* Task function. */
                    "Sensor Collection",    /* name of task. */
                    10000,                  /* Stack size of task */
                    NULL,                   /* parameter of the task */
                    1,                      /* priority of the task */
                    &Task1,                 /* Task handle to keep track of created task */
                    0);                     /* pin task to core 0 */                  
    delay(250); 

    xTaskCreatePinnedToCore(
                    RunPIDs,                /* Task function. */
                    "Running PIDs",         /* name of task. */
                    10000,                  /* Stack size of task */
                    NULL,                   /* parameter of the task */
                    2,                      /* priority of the task */
                    &Task3,                 /* Task handle to keep track of created task */
                    0);                     /* pin task to core 0 */                  
    delay(250);

    xTaskCreatePinnedToCore(
                    RunModel,               /* Task function. */
                    "Model Running",        /* name of task. */
                    10000,                  /* Stack size of task */
                    NULL,                   /* parameter of the task */
                    1,                      /* priority of the task */
                    &Task2,                 /* Task handle to keep track of created task */
                    1);                     /* pin task to core 1 */
    
    delay(250); 
}

// Task that collects sensor data
void SensorCollection(void * pvParameters) {
    // Timing
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(AVG_SAMPLE_TIME);

    while (true) {
        // Read sensors
        SharedData data;
        data.pulse = analogRead(pulsePin);
        data.emg1 = analogRead(emgPin1);
        data.emg2 = analogRead(emgPin2);
        data.emg3 = analogRead(emgPin3);

        // Add to the data queue
        if (curSampleCount >= NUM_SAMPLES) {
            for(int i=0; i<NUM_SAMPLES-1; i++){
                samples[i] = samples[i+1];
            }
            samples[NUM_SAMPLES - 1] = data;

        } else {
            samples[curSampleCount] = data;
            curSampleCount++;
        }

        // Calculate features
        if (xSemaphoreTake(featuresMutex, portMAX_DELAY)) {
            features = calculateFeatures();

            xSemaphoreGive(featuresMutex);
        }

        // Check for new data
        if (xSemaphoreTake(modelFlagMutex, portMAX_DELAY)) {
            if (modelDone == true) {
                modelDone = false;

                // Getting the model output
                if (xSemaphoreTake(outputMutex, portMAX_DELAY)) {
                    // Can transmit data here
                    if (modelOutput == predVar) {
                        predVarCount++;
                    }
                    else {
                        predVar = modelOutput;
                        predVarCount = 0;
                    }

                    if (predVarCount >= MAX_PRED_VAR_COUNT) {
                        predVarCount = 0;

                        // Sending the commanded values to the PID
                        pidCommand = modelOutput;

                        // Delaying to reduce jitters
                        if (xSemaphoreTake(delayMutex, portMAX_DELAY)) {
                            if (!modelDelay) {
                              modelDelay = true;
                              Serial.println("Delaying the model");
                            }

                            xSemaphoreGive(delayMutex);
                        }
                    }

                    xSemaphoreGive(outputMutex);
                }
            }
            xSemaphoreGive(modelFlagMutex);
        }
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}

// Calculating the extra features
FeatEng calculateFeatures() {
    FeatEng features;

    // Buffers for the calculations
    int emg1Buffer[15], emg2Buffer[15], emg3Buffer[15], pulseBuffer[15];
    for (int i = 0; i < 15; i++) {
        emg1Buffer[i] = samples[i].emg1;
        emg2Buffer[i] = samples[i].emg2;
        emg3Buffer[i] = samples[i].emg3;
        pulseBuffer[i] = samples[i].pulse;
    }

    // Each feature prep
    features.emg1[0] = calculateAverage(emg1Buffer, 15);
    features.emg1[1] = calculateVariance(emg1Buffer, 15, features.emg1[0]);

    features.emg2[0] = calculateAverage(emg2Buffer, 15);
    features.emg2[1] = calculateVariance(emg2Buffer, 15, features.emg2[0]);

    features.emg3[0] = calculateAverage(emg3Buffer, 15);
    features.emg3[1] = calculateVariance(emg3Buffer, 15, features.emg3[0]);

    features.pulse[0] = calculateAverage(pulseBuffer, 15);
    features.pulse[1] = calculateVariance(pulseBuffer, 15, features.pulse[0]);

    return features;
}

// Task for running all PID loops
void RunPIDs(void * pvParameters) {
    // Timing
    TickType_t xLastWakeTime = xTaskGetTickCount();
    TickType_t xFrequency = pdMS_TO_TICKS(AVG_SAMPLE_TIME);

    String sendData = "";
    String gotData = "";
    int overrideVals[numMotors] = {0, 0, 0};

    int lastIndex = 0, index = 0;
    int feedbackVals[numMotors*2];

    while (true) {
        // Check if we want PID or not
        if (pidMode) {
            // Clear the buffer of data
            while (SerialBT.available()) {
                gotData = SerialBT.readStringUntil('\n');
            }

            // Check for extracted data
            if (gotData != "") {
                // Extract position and torque feedback
                for (int i = 0; i < (numMotors*2); i++) {
                    int nextIndex = gotData.indexOf(',', lastIndex);
                    if (nextIndex == -1) nextIndex = gotData.length();
                    
                    feedbackVals[i] = gotData.substring(lastIndex, nextIndex).toInt();
                    lastIndex = nextIndex + 1;
                }

                // Torque feedback check
                // for (int i = 0; i < numMotors; i++) {
                //     // Torque too high
                //     if (abs(feedbackVals[i]) >= torqueThreshold) {
                //         torqueHoldMode[i] = true;
                //     }
                // }
            }
            else {
                for (int i = 0; i < numMotors; i++) {
                torqueHoldMode[i] = false;
                }
            }

            // Hold the current value if grabbing something
            if (torqueHoldMode[0]) {
                motorPos1 = feedbackVals[3];
            }
            else {
                // Compute PID 1
                setpoint1 = setpoints[pidCommand][0];
                flexADC1 = analogRead(FLEX_PIN1);
                loop1.Compute();
            }

            if (torqueHoldMode[1]) {
                motorPos2 = feedbackVals[4];
            }
            else {
                // Compute PID 2
                setpoint2 = setpoints[pidCommand][1];
                flexADC2 = analogRead(FLEX_PIN2);
                loop2.Compute();
            }

            if (torqueHoldMode[2]) {
                motorPos3 = feedbackVals[5];
            }
            else {
                // Compute PID 3
                setpoint3 = setpoints[pidCommand][2];
                flexADC3 = analogRead(FLEX_PIN3);
                loop3.Compute();
            }

            gotData = "";
            
        }
        else {
            // Setting the motors directly to the wanted positions
            motorPos1 = motContPositions[pidCommand][0];
            motorPos2 = motContPositions[pidCommand][1];
            motorPos3 = motContPositions[pidCommand][2];
        }

        // Sending the data over Bluetooth for motor command
        sendData = String(motorPos1) + "," + String(motorPos2) + "," + String(motorPos3);
        SerialBT.println(sendData);
        Serial.println(sendData);
        
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}

// Task that collects sensor data
void RunModel(void * pvParameters) {
    // Timing
    TickType_t xLastWakeTime = xTaskGetTickCount();
    TickType_t xFrequency = pdMS_TO_TICKS(AVG_SAMPLE_TIME); 
    bool delayTheModel = false;

    while (true) {
        // Check if the model should be delayed
        if (xSemaphoreTake(delayMutex, portMAX_DELAY)) {
            delayTheModel = modelDelay;
            modelDelay = false;

            xSemaphoreGive(delayMutex);
        }

        // Changing the delay time
        if (delayTheModel) {
            // Blocking but on its own core
            delay(MODEL_DELAY_TIME);

            // If not in model inference mode
            if (!modelInference) {
                // Counting seconds in this position
                if (modelTestOutCount < secondsToHoldTest) {
                    modelTestOutCount++;
                }
            }
        }
        else {
            // Format input
            if (xSemaphoreTake(featuresMutex, portMAX_DELAY)) {
                int sampleIndex = 0;
                for (int i = 0; i < 8; i += 4) {
                    input[i] = features.emg1[sampleIndex];
                    input[i+1] = features.emg2[sampleIndex];
                    input[i+2] = features.emg3[sampleIndex];
                    input[i+3] = features.pulse[sampleIndex];
                    sampleIndex++;
                }

                xSemaphoreGive(featuresMutex);
            }

            // Model output val
            int maxIndex = 0;

            // Running the model or not
            if (modelInference) {
                // Predict with the model
                predict(input, output);

                // Output the results
                float maxVal = 0;
                for (int i = 0; i < numClasses; i++) {
                    if (output[i] > maxVal) {
                        maxIndex = i;
                        maxVal = output[i];
                    }
                }
            }
            else {
                // Held then reset
                if (modelTestOutCount >= secondsToHoldTest) {

                    modelTestOutCount = 0;
    
                    if (!backToHomePos) {
                        curModelTestOut++;
                        if (curModelTestOut >= numClasses) curModelTestOut = 1;
                    }
             
                    backToHomePos = !backToHomePos;
                }

                // Home or other position
                if (!backToHomePos) {
                    maxIndex = curModelTestOut;
                }
                else {
                    maxIndex = 0;
                }
            }
            
            // Showing that the model is done
            if (xSemaphoreTake(modelFlagMutex, portMAX_DELAY)) {
                modelDone = true;

                // Getting the model output
                if (xSemaphoreTake(outputMutex, portMAX_DELAY)) {
                    modelOutput = maxIndex;

                    xSemaphoreGive(outputMutex);
                }
                xSemaphoreGive(modelFlagMutex);
            }
        }
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
  	}
}

float calculateAverage(int buffer[], int size) {
	float sum = 0;
	for (int i = 0; i < size; i++) {
		sum += buffer[i];
	}
	return sum / size;
}

float calculateVariance(int buffer[], int size, float avg) {
	float sumSq = 0;
	for (int i = 0; i < size; i++) {
		sumSq += pow(buffer[i] - avg, 2);
	}
	return sumSq / size;
}

void loop() {
    
}