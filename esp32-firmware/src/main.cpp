/*
 * PDS-32: Système IoT Intelligent de Gestion Énergétique
 * ESP32 Firmware - Version Complète
 *
 * Fonctionnalités:
 * - Lecture capteurs (DHT22, ACS712, PIR, LDR)
 * - Communication MQTT
 * - Contrôle actionneurs (2 Relays)
 * - Automatisation intelligente
 * - Calcul consommation énergétique temps réel
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ArduinoJson.h>

// ==================== FORWARD DECLARATIONS ====================

// WiFi / MQTT
void connectWiFi();
void reconnectMQTT();
void mqttCallback(char *topic, byte *payload, unsigned int length);

// Sensors & Data
void readSensors();
void publishData();
void publishActuatorStatus();

// Automation & Actuators
void runAutomation();
void setRelay1(bool state);
void setRelay2(bool state);

// Utils
void blinkLED(int times);

// ==================== CONFIGURATION ====================

// Wi-Fi Credentials (Wokwi)
const char *ssid = "Wokwi-GUEST";
const char *password = "";

// MQTT Broker
const char *mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;
const char *mqtt_user = "";
const char *mqtt_password = "";

// Device ID
const char *device_id = "esp32_001";

// MQTT Topics
const char *topic_energy = "home/energy/power";
const char *topic_sensors = "home/sensors/environment";
const char *topic_presence = "home/sensors/presence";
const char *topic_actuators = "home/actuators/status";
const char *topic_control = "home/control/command";

#define LED_BUILTIN 2 // ESP32 onboard LED (Wokwi compatible)
#define DHT_PIN 4     // DHT22 Temperature & Humidity
#define DHT_TYPE DHT22
#define CURRENT_SENSOR_PIN 34 // ACS712 Analog Input
#define LDR_PIN 35            // Light Sensor Analog
#define PIR_PIN 13            // Motion Sensor Digital
#define RELAY1_PIN 26         // Relay 1 (AC/Heater)
#define RELAY2_PIN 27         // Relay 2 (Lights)
#define LED_STATUS_PIN 5      // Status LED

// Constants
#define VOLTAGE 220.0            // Voltage réseau (V)
#define ACS712_SENSITIVITY 0.185 // 5A model (V/A)
#define PUBLISH_INTERVAL 5000    // Publish every 5 seconds
#define SENSOR_READ_INTERVAL 100 // Read sensors every 100ms
#define ACS712_OFFSET 1.65       // Midpoint voltage (0A)
#define PRESENCE_TIMEOUT 3000    // 5 minutes (ms)
// ==================== OBJECTS ====================
WiFiClient espClient;
PubSubClient mqtt(espClient);
DHT dht(DHT_PIN, DHT_TYPE);

// ==================== VARIABLES ====================
// Sensor Data
float temperature = 0.0;
float humidity = 0.0;
float power = 0.0;
float current = 0.0;
float energyTotal = 0.0;
int lightLevel = 0;
bool presenceDetected = false;

// Actuator States
bool relay1State = false;
bool relay2State = false;

// Timing
unsigned long lastPublish = 0;
unsigned long lastSensorRead = 0;
unsigned long energyLastUpdate = 0;

// Automation
bool autoMode = true;
unsigned long presenceTimeout = 300000; // 5 minutes
unsigned long lastPresenceTime = 0;

bool autoModeTemporarilyDisabled = false;
unsigned long autoModeDisabledTime = 0;
const unsigned long AUTO_MODE_TIMEOUT = 30000; // 30 seconds
void setup()
{
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n\n=================================");
  Serial.println("\n=== PDS-32: Energy Management v1.0");
  Serial.println("  ESP32 Firmware");
  Serial.println("=================================\n");
  // Initialize Pins
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);
  pinMode(RELAY1_PIN, OUTPUT);
  pinMode(RELAY2_PIN, OUTPUT);
  pinMode(LED_STATUS_PIN, OUTPUT);

  digitalWrite(RELAY1_PIN, LOW);
  digitalWrite(RELAY2_PIN, LOW);
  digitalWrite(LED_STATUS_PIN, LOW);
  digitalWrite(LED_BUILTIN, LOW);

  Serial.println("✓ Pins initialized");

  // Initialize DHT22
  dht.begin();
  Serial.println("✓ DHT22 initialized");

  // Connect to Wi-Fi
  connectWiFi();

  // Setup MQTT
  mqtt.setServer(mqtt_server, mqtt_port);
  mqtt.setCallback(mqttCallback);

  Serial.println("✓ MQTT configured");
  Serial.println("\nSetup complete! Starting main loop...\n");

  blinkLED(3);
}

// ==================== CHECK AUTO MODE TIMER ====================
void checkAutoModeTimer()
{
  if (autoModeTemporarilyDisabled && !autoMode)
  {
    unsigned long elapsed = millis() - autoModeDisabledTime;

    // Afficher le temps restant toutes les 10 secondes
    static unsigned long lastPrint = 0;
    if (elapsed - lastPrint >= 10000)
    {
      unsigned long remaining = (AUTO_MODE_TIMEOUT - elapsed) / 1000;
      Serial.printf("⏳ Auto mode re-enables in %lu seconds...\n", remaining);
      lastPrint = elapsed;
    }

    // Check if 30 seconds have passed
    if (elapsed >= AUTO_MODE_TIMEOUT)
    {
      autoMode = true;
      autoModeTemporarilyDisabled = false;
      Serial.println("✓ Auto mode re-enabled automatically (30s timeout)");
      publishActuatorStatus();
    }
  }
}
// ==================== MAIN LOOP ====================
void loop()
{
  // Ensure MQTT connection
  if (!mqtt.connected())
  {
    reconnectMQTT();
  }
  mqtt.loop();

  // Read sensors periodically
  if (millis() - lastSensorRead >= SENSOR_READ_INTERVAL)
  {
    readSensors();
    lastSensorRead = millis();
  }

  // Publish data periodically
  if (millis() - lastPublish >= PUBLISH_INTERVAL)
  {
    publishData();
    lastPublish = millis();
  }

  // Check auto mode timer (NEW!)
  checkAutoModeTimer();

  // Automation logic
  if (autoMode)
  {
    runAutomation();
  }
}
// ==================== Wi-Fi CONNECTION ====================
void connectWiFi()
{
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20)
  {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED)
  {
    Serial.println("\n✓ Wi-Fi connected!");
    Serial.print("  IP Address: ");
    Serial.println(WiFi.localIP());
    blinkLED(2);
  }
  else
  {
    Serial.println("\n✗ Wi-Fi connection failed!");
  }
}

// ==================== MQTT CONNECTION ====================
void reconnectMQTT()
{
  int attempts = 0;

  while (!mqtt.connected() && attempts < 5)
  {
    Serial.print("Connecting to MQTT broker...");

    String clientId = "ESP32_" + String(device_id) + "_" + String(random(0xffff), HEX);

    if (mqtt.connect(clientId.c_str(), mqtt_user, mqtt_password))
    {
      Serial.println(" ✓ Connected!");

      // Subscribe to control topic
      mqtt.subscribe(topic_control);
      Serial.print("  Subscribed to: ");
      Serial.println(topic_control);

      blinkLED(2);
      return;
    }
    else
    {
      Serial.print(" ✗ Failed, rc=");
      Serial.println(mqtt.state());
      attempts++;
      delay(2000);
    }
  }

  if (!mqtt.connected())
  {
    Serial.println("✗ MQTT connection failed after 5 attempts");
  }
}

// ==================== MQTT CALLBACK ====================
// ==================== MQTT CALLBACK ====================
void mqttCallback(char *topic, byte *payload, unsigned int length)
{
  Serial.printf("📨 Message received [%s]: ", topic);

  // ==================== PARSE JSON ====================
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, payload, length);

  if (error)
  {
    Serial.printf("✗ JSON parse error: %s\n", error.c_str());
    return;
  }

  const char *command = doc["command"];
  if (!command)
  {
    Serial.println("✗ Missing 'command' field");
    return;
  }

  Serial.println(command);

  // ==================== HELPER LAMBDA ====================
  auto manualRelayControl = [&](void (*relayFunc)(bool), bool state)
  {
    relayFunc(state);
    autoMode = false;
    autoModeTemporarilyDisabled = true;
    autoModeDisabledTime = millis();
    Serial.println("⚠ Auto mode disabled for 30s (manual control)");
  };

  // ==================== COMMAND HANDLING ====================
  // Manual relay controls
  if (strcmp(command, "relay1_on") == 0)
  {
    manualRelayControl(setRelay1, true);
  }
  else if (strcmp(command, "relay1_off") == 0)
  {
    manualRelayControl(setRelay1, false);
  }
  else if (strcmp(command, "relay2_on") == 0)
  {
    manualRelayControl(setRelay2, true);
  }
  else if (strcmp(command, "relay2_off") == 0)
  {
    manualRelayControl(setRelay2, false);
  }
  // Auto mode controls
  else if (strcmp(command, "auto_on") == 0)
  {
    autoMode = true;
    autoModeTemporarilyDisabled = false;
    Serial.println("✓ Auto mode: ON (manually enabled)");
  }
  else if (strcmp(command, "auto_off") == 0)
  {
    autoMode = false;
    autoModeTemporarilyDisabled = false;
    Serial.println("✓ Auto mode: OFF (manually disabled)");
  }
  // Utility commands
  else if (strcmp(command, "reset_energy") == 0)
  {
    energyTotal = 0.0;
    Serial.println("✓ Energy counter reset");
  }
  // Unknown command
  else
  {
    Serial.printf("✗ Unknown command: %s\n", command);
    return; // Early return, no need to publish status
  }

  // ==================== STATUS UPDATE ====================
  publishActuatorStatus();
}

// ==================== READ SENSORS ====================
void readSensors()
{
  // Read DHT22 (Temperature & Humidity)
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  if (!isnan(h) && !isnan(t))
  {
    humidity = h;
    temperature = t;
  }

  // Read Current Sensor (ACS712)
  int sensorValue = analogRead(CURRENT_SENSOR_PIN);
  float voltage = (sensorValue / 4095.0) * 3.3; // ESP32 ADC 12-bit

  // Calculate current (offset = 1.65V for 0A)
  current = abs((voltage - ACS712_OFFSET) / ACS712_SENSITIVITY);

  // Apply noise filter (threshold 0.1A)
  if (current < 0.1)
  {
    current = 0.0;
  }

  // Calculate power (P = V × I)
  power = VOLTAGE * current;

  // Calculate cumulative energy (kWh)
  unsigned long timeDiff = millis() - energyLastUpdate;
  if (energyLastUpdate > 0 && timeDiff > 0)
  {
    float hours = timeDiff / 3600000.0;
    energyTotal += (power * hours) / 1000.0; // Wh to kWh
  }
  energyLastUpdate = millis();

  // Read Light Sensor (LDR)
  int rawLight = analogRead(LDR_PIN);
  lightLevel = map(rawLight, 0, 4095, 0, 100); // Convert to percentage

  // Read PIR Motion Sensor
  bool currentPresence = digitalRead(PIR_PIN);
  if (currentPresence)
  {
    presenceDetected = true;
    lastPresenceTime = millis();
  }
  else
  {
    // Check timeout (5 minutes)
    if (millis() - lastPresenceTime > PRESENCE_TIMEOUT)
    {
      presenceDetected = false;
    }
  }
}

// ==================== PUBLISH DATA ====================
void publishData()
{
  if (!mqtt.connected())
  {
    Serial.println("⚠ MQTT not connected, skipping publish");
    return;
  }

  // --- Publish Energy Data ---
  StaticJsonDocument<256> energyDoc;
  energyDoc["timestamp"] = millis();
  energyDoc["device_id"] = device_id;
  energyDoc["power"] = round(power * 100) / 100.0;
  energyDoc["voltage"] = VOLTAGE;
  energyDoc["current"] = round(current * 100) / 100.0;
  energyDoc["energy_total"] = round(energyTotal * 1000) / 1000.0;

  char energyBuffer[256];
  serializeJson(energyDoc, energyBuffer);
  mqtt.publish(topic_energy, energyBuffer);

  // --- Publish Sensor Data ---
  StaticJsonDocument<256> sensorDoc;
  sensorDoc["timestamp"] = millis();
  sensorDoc["device_id"] = device_id;
  sensorDoc["temperature"] = round(temperature * 10) / 10.0;
  sensorDoc["humidity"] = round(humidity * 10) / 10.0;
  sensorDoc["light_level"] = lightLevel;

  char sensorBuffer[256];
  serializeJson(sensorDoc, sensorBuffer);
  mqtt.publish(topic_sensors, sensorBuffer);

  // --- Publish Presence Data ---
  StaticJsonDocument<128> presenceDoc;
  presenceDoc["timestamp"] = millis();
  presenceDoc["device_id"] = device_id;
  presenceDoc["presence"] = presenceDetected;

  char presenceBuffer[128];
  serializeJson(presenceDoc, presenceBuffer);
  mqtt.publish(topic_presence, presenceBuffer);

  // --- Publish Actuator Status ---
  publishActuatorStatus();

  // --- Debug Print ---
  Serial.println("\n--- Sensor Data Published ---");
  Serial.printf("Temperature: %.1f°C | Humidity: %.1f%%\n", temperature, humidity);
  Serial.printf("Power: %.2fW | Current: %.2fA\n", power, current);
  Serial.printf("Energy Total: %.3f kWh\n", energyTotal);
  Serial.printf("Light: %d%% | Presence: %s\n", lightLevel, presenceDetected ? "Yes" : "No");
  Serial.printf("Relay1: %s | Relay2: %s | Auto: %s\n",
                relay1State ? "ON" : "OFF",
                relay2State ? "ON" : "OFF",
                autoMode ? "ON" : "OFF");
  Serial.println("-----------------------------\n");

  // Status LED blink
  digitalWrite(LED_BUILTIN, HIGH);
  delay(500);
  digitalWrite(LED_BUILTIN, LOW);
}

// ==================== PUBLISH ACTUATOR STATUS ====================
void publishActuatorStatus()
{
  if (!mqtt.connected())
    return;

  StaticJsonDocument<128> actuatorDoc;
  actuatorDoc["timestamp"] = millis();
  actuatorDoc["device_id"] = device_id;
  actuatorDoc["relay1"] = relay1State;
  actuatorDoc["relay2"] = relay2State;
  actuatorDoc["auto_mode"] = autoMode;

  char actuatorBuffer[128];
  serializeJson(actuatorDoc, actuatorBuffer);
  mqtt.publish(topic_actuators, actuatorBuffer);
}

// ==================== AUTOMATION LOGIC ====================
void runAutomation()
{
  // Rule 1: Turn off lights when no presence
  if (!presenceDetected && relay2State)
  {
    Serial.println("🤖 AUTO: No presence → Lights OFF");
    setRelay2(false);
  }

  // Rule 2: Turn on lights when presence + low light
  if (presenceDetected && lightLevel < 30 && !relay2State)
  {
    Serial.println("🤖 AUTO: Presence + Low light → Lights ON");
    setRelay2(true);
  }

  // Rule 3: Turn off lights when bright enough
  if (presenceDetected && lightLevel > 70 && relay2State)
  {
    Serial.println("🤖 AUTO: Bright enough → Lights OFF");
    setRelay2(false);
  }

  // Rule 4: Temperature control (AC/Heater)
  if (presenceDetected)
  {
    if (temperature > 28 && !relay1State)
    {
      Serial.println("🤖 AUTO: High temp → AC ON");
      setRelay1(true);
    }
    else if (temperature < 18 && !relay1State)
    {
      Serial.println("🤖 AUTO: Low temp → Heater ON");
      setRelay1(true);
    }
    else if (temperature >= 20 && temperature <= 26 && relay1State)
    {
      Serial.println("🤖 AUTO: Comfortable temp → HVAC OFF");
      setRelay1(false);
    }
  }
  else
  {
    // Turn off HVAC when no presence
    if (relay1State)
    {
      Serial.println("🤖 AUTO: No presence → HVAC OFF");
      setRelay1(false);
    }
  }
}

// ==================== RELAY CONTROL ====================
void setRelay1(bool state)
{
  relay1State = state;
  digitalWrite(RELAY1_PIN, state ? HIGH : LOW);
  Serial.print("🔌 Relay 1 (HVAC): ");
  Serial.println(state ? "ON" : "OFF");
  publishActuatorStatus();
}

void setRelay2(bool state)
{
  relay2State = state;
  digitalWrite(RELAY2_PIN, state ? HIGH : LOW);
  Serial.print("💡 Relay 2 (Lights): ");
  Serial.println(state ? "ON" : "OFF");
  publishActuatorStatus();
}

// ==================== UTILITY FUNCTIONS ====================
void blinkLED(int times)
{
  for (int i = 0; i < times; i++)
  {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(150);
    digitalWrite(LED_BUILTIN, LOW);
    delay(150);
  }
}