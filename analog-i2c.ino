#include <Wire.h>
#include <util/atomic.h>

#define PIN_COUNT 5

int CHANNEL_PINS[PIN_COUNT] = {A0, A1, A2, A3, A4};
int CHANNEL_VALUES[PIN_COUNT] = {};
int WINDOW = 20;  // moving average

void setup() {
  Wire.begin(8);                // join i2c bus with address #8
  Wire.onRequest(requestEvent); // register event
  Serial.begin(9600);
}

void loop() {
  int temp_values[PIN_COUNT] = {};
  for (int i = 0; i < WINDOW; i++) {
    for (int j = 0; j < PIN_COUNT; j++) {
      // Add current val
      temp_values[j] = temp_values[j] + analogRead(CHANNEL_PINS[j]);

      // Average on last iteration
      if (i == WINDOW - 1) {
        temp_values[j] = temp_values[j] / WINDOW;
      }
    }
    delay (1);
  }

  // Blocking copy to output array
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    memcpy(CHANNEL_VALUES, temp_values, sizeof(int)*PIN_COUNT);
  }
}

// function that executes whenever data is requested by master
// this function is registered as an event, see setup()
void requestEvent() {
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    for (int i = 0; i < PIN_COUNT; i++) {
      Wire.write(CHANNEL_VALUES[i]);
    }
  }
}
