#include <string.h>
#include "helpers.h"

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
double input[8];
double output[8];

int predVar = 0;
int predVarCount = 0;
int maxPredVarCount = 3;

// Shared data queue
struct SharedData {
    int emg1;
    int emg2;
    int emg3;
    int pulse;
};

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
FeatEng features;

// Data passing
QueueHandle_t sharedDataQueue;
SemaphoreHandle_t featEngMutex;
SemaphoreHandle_t modelFlagMutex;
SemaphoreHandle_t dataFlagMutex;
SemaphoreHandle_t outputMutex;

// Task declaration
TaskHandle_t Task1;
TaskHandle_t Task2;

void setup(void) {
    Serial.begin(115200);

    // Q 15 long
    sharedDataQueue = xQueueCreate(15, sizeof(SharedData));

        // Create semaphores
    featEngMutex = xSemaphoreCreateMutex();
    if (featEngMutex == NULL) {
        Serial.println("Failed to create featEngMutex");
        while (1);  // Halt the program
    }

    modelFlagMutex = xSemaphoreCreateMutex();
    if (modelFlagMutex == NULL) {
        Serial.println("Failed to create modelFlagMutex");
        while (1);  // Halt the program
    }

    dataFlagMutex = xSemaphoreCreateMutex();
    if (dataFlagMutex == NULL) {
        Serial.println("Failed to create dataFlagMutex");
        while (1);  // Halt the program
    }

    outputMutex = xSemaphoreCreateMutex();
    if (outputMutex == NULL) {
        Serial.println("Failed to create outputMutex");
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
    delay(500); 

    xTaskCreatePinnedToCore(
                    RunModel,               /* Task function. */
                    "Model Running",        /* name of task. */
                    10000,                  /* Stack size of task */
                    NULL,                   /* parameter of the task */
                    2,                      /* priority of the task */
                    &Task2,                 /* Task handle to keep track of created task */
                    1);                     /* pin task to core 1 */
    
    delay(500); 
}

// Task that collects sensor data
void SensorCollection(void * pvParameters) {
    // Timing
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(17);

    while (true) {
        // Read sensors
        SharedData data;
        data.pulse = analogRead(pulsePin);
        data.emg1 = analogRead(emgPin1);
        data.emg2 = analogRead(emgPin2);
        data.emg3 = analogRead(emgPin3);

        // Add data to the queue
        if (xQueueSend(sharedDataQueue, &data, portMAX_DELAY) != pdTRUE) {
            Serial.println("Failed to add data to the queue");
        }

        // If the queue is full, calculate feature engineering
        int availableSamples = uxQueueMessagesWaiting(sharedDataQueue);
        if (availableSamples >= 15) {
            if (xSemaphoreTake(featEngMutex, portMAX_DELAY)) {
                features = calculateFeatures();

                xSemaphoreGive(featEngMutex);
            }
        }

        // Check for new data
        if (xSemaphoreTake(modelFlagMutex, portMAX_DELAY)) {
            modelDone = false;

            xSemaphoreGive(modelFlagMutex);

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

                if (predVarCount >= maxPredVarCount) {
                  predVarCount = 0;
                  Serial.println(modelOutput);
                }

                xSemaphoreGive(outputMutex);
            }
        }
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}

// Calculating the extra features
FeatEng calculateFeatures() {
    SharedData dataArray[15];
    FeatEng features;

    // Collect data samples from the queue
    for (int i = 0; i < 15; i++) {
        if (xQueueReceive(sharedDataQueue, &dataArray[i], portMAX_DELAY) != pdTRUE) {
            Serial.println("Failed to retrieve data from the queue");
        }
    }

    // Buffers for the calculations
    int emg1Buffer[15], emg2Buffer[15], emg3Buffer[15], pulseBuffer[15];
    for (int i = 0; i < 15; i++) {
        emg1Buffer[i] = dataArray[i].emg1;
        emg2Buffer[i] = dataArray[i].emg2;
        emg3Buffer[i] = dataArray[i].emg3;
        pulseBuffer[i] = dataArray[i].pulse;
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

// Task that collects sensor data
void RunModel(void * pvParameters) {
    // Timing
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(18); 
    while (true) {
      	int availableSamples = uxQueueMessagesWaiting(sharedDataQueue);
      	if (availableSamples >= 15) {
			int sampleIndex = 0;

			// Feature engineering
			if (xSemaphoreTake(featEngMutex, portMAX_DELAY)) {
				sampleIndex = 0;
				for (int i = 0; i < 8; i += 4) {
					input[i] = features.emg1[sampleIndex];
					input[i+1] = features.emg2[sampleIndex];
					input[i+2] = features.emg3[sampleIndex];
					input[i+3] = features.pulse[sampleIndex];
          sampleIndex++;
				}

        Serial.println("Start");
        for (int i = 0; i < 8; i++) {
          Serial.println(input[i]);
        }
        Serial.println("Finish");

				xSemaphoreGive(featEngMutex);
			}

			// Predict with the model
			predict(input, output);

			// Output the results
			int maxIndex = 0;
			float maxVal = 0;
			for (int i = 0; i < 8; i++) {
				if (output[i] > maxVal) {
				    maxIndex = i;
				    maxVal = output[i];
				}
			}

			if (xSemaphoreTake(modelFlagMutex, portMAX_DELAY)) {
            	modelDone = true;

            	// Getting the model output
            	if (xSemaphoreTake(outputMutex, portMAX_DELAY)) {
					modelOutput = maxIndex;

					xSemaphoreGive(modelFlagMutex);
					xSemaphoreGive(outputMutex);
				}
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
