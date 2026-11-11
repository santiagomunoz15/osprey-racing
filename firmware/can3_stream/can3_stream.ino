// ESP32 / Arduino, same legacy TWAI API as the working two-channel sketch.
#include <Arduino.h>
#include "driver/twai.h"

#define CAN_TX_PIN GPIO_NUM_4
#define CAN_RX_PIN GPIO_NUM_5

struct Channel { uint32_t id; const char *name; };
const Channel channels[] = {
  {0x001, "Battery Volts"},
  {0x002, "Front Brake"},
  {0x003, "Rear Brake"},
  {0x004, "Coolant Pressure"},
  {0x005, "Coolant Temperature"},
  {0x006, "Oil Pressure"},
  {0x007, "Oil Temperature"},
  {0x008, "RPM"},
  {0x009, "Lambda"},
  {0x010, "Fuel Pressure"},
  {0x011, "Fuel Level"},
  {0x012, "G Force Lat"},
  {0x013, "G Force Long"},
  {0x014, "G Force Vert"},
  {0x015, "Gear"},
  {0x016, "Steering Wheel Angle"},
  {0x017, "Steered Angle"},
  {0x018, "Sus Pos FL"},
  {0x019, "Sus Pos FR"},
  {0x020, "Sus Pos RL"},
  {0x021, "Sus Pos RR"},
  {0x022, "Throttle"},
  {0x023, "Yaw Rate"},
  {0x024, "Wheel Speed FL"},
  {0x025, "Wheel Speed FR"},
  {0x026, "Wheel Speed RL"},
  {0x027, "Wheel Speed RR"}
};
constexpr size_t N = sizeof(channels) / sizeof(channels[0]);
struct Reading {
  uint32_t count = 0, badLength = 0, lastMs = 0;
  uint8_t bytes[2] = {0, 0};
};
Reading readings[N];
uint32_t unknownFrames = 0, ignoredFrames = 0;
portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
bool ready = false;

void receiveTask(void *) {
  twai_message_t msg;
  for (;;) {
    if (twai_receive(&msg, pdMS_TO_TICKS(100)) != ESP_OK) continue;
    int match = -1;
    if (!msg.rtr && !msg.extd) {
      for (size_t i = 0; i < N; ++i) {
        if (channels[i].id == msg.identifier) { match = i; break; }
      }
    }
    uint32_t now = millis();
    portENTER_CRITICAL(&mux);
    if (msg.rtr || msg.extd) ++ignoredFrames;
    else if (match < 0) ++unknownFrames;
    else if (msg.data_length_code != 2) ++readings[match].badLength;
    else {
      Reading &r = readings[match];
      ++r.count;
      r.lastMs = now;
      r.bytes[0] = msg.data[0]; r.bytes[1] = msg.data[1];
    }
    portEXIT_CRITICAL(&mux);
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  // Retain NORMAL mode from the working setup so the ESP32 acknowledges frames.
  twai_general_config_t general = TWAI_GENERAL_CONFIG_DEFAULT(CAN_TX_PIN, CAN_RX_PIN, TWAI_MODE_NORMAL);
  general.rx_queue_len = 128;
  twai_timing_config_t timing = TWAI_TIMING_CONFIG_1MBITS();
  twai_filter_config_t filter = TWAI_FILTER_CONFIG_ACCEPT_ALL();
  esp_err_t err = twai_driver_install(&general, &timing, &filter);
  if (err != ESP_OK) { Serial.printf("Install failed: %d\n", err); return; }
  err = twai_start();
  if (err != ESP_OK) { Serial.printf("Start failed: %d\n", err); return; }
  if (xTaskCreate(receiveTask, "can3-rx", 4096, nullptr, 2, nullptr) != pdPASS) {
    Serial.println("Cannot create CAN receive task"); twai_stop(); return;
  }
  ready = true;
  Serial.println("CAN3 stream ready: latest samples, up to 10 Hz per channel.");
}

void loop() {
  if (!ready) { delay(1000); return; }
  static uint32_t sentCount[N] = {};
  delay(100);
  Reading snapshot[N];
  portENTER_CRITICAL(&mux);
  for (size_t i = 0; i < N; ++i) snapshot[i] = readings[i];
  portEXIT_CRITICAL(&mux);
  uint32_t now = millis();
  for (size_t i = 0; i < N; ++i) {
    const Reading &r = snapshot[i];
    if (!r.count || r.count == sentCount[i] || now - r.lastMs > 2000) continue;
    sentCount[i] = r.count;
    Serial.printf("{\"can_id\":%lu,\"data\":\"%02X%02X\"}\n",
                  (unsigned long)channels[i].id, unsigned(r.bytes[0]), unsigned(r.bytes[1]));
  }
}
