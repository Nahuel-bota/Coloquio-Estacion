#include <Wire.h>
#include <Adafruit_BMP280.h>

Adafruit_BMP280 bmp;

// --- Pines ---
const int boton = 4;
const int azul = 16;
const int verde = 18;
const int rojo = 19;

// --- Variables ---
int estadoAnteriorBoton = LOW;

void setup() {
  Serial.begin(115200);
  
  pinMode(boton, INPUT_PULLUP);
  pinMode(azul, OUTPUT);
  pinMode(verde, OUTPUT);
  pinMode(rojo, OUTPUT);
  
  // Apagar los LEDs por defecto al iniciar
  digitalWrite(azul, LOW);
  digitalWrite(verde, LOW);
  digitalWrite(rojo, LOW);
  
  if (!bmp.begin(0x76)) {
    Serial.println("ERROR: BMP280");
    while (1); 
  }
}

void loop() {
  // ==========================================
  // 1. ESCUCHAR ORDENES 
  // ==========================================
  if (Serial.available() > 0) {
    char comando = Serial.read();
    
    // LEDs individuales: Invierten el estado actual (!digitalRead)
    if (comando == 'A') digitalWrite(azul, !digitalRead(azul));
    if (comando == 'V') digitalWrite(verde, !digitalRead(verde));
    if (comando == 'R') digitalWrite(rojo, !digitalRead(rojo));

    // TODOS los LEDS
    if (comando == 'E') { // Encender todos
      digitalWrite(azul, HIGH);
      digitalWrite(verde, HIGH);
      digitalWrite(rojo, HIGH);
    }
    if (comando == 'X') { // Apagar todos 
      digitalWrite(azul, LOW);
      digitalWrite(verde, LOW);
      digitalWrite(rojo, LOW);
    }
    
    // SENSOR: Si Python envía la 'T', el ESP32 lee y devuelve la temperatura
    if (comando == 'T') {
      float temperatura = bmp.readTemperature();
      
      // CAMBIO APLICADO: Solo envía el número seguido de la letra 'c'
      Serial.print(temperatura);
      Serial.println("c");
    }
  }

  // ==========================================
  // 2. ENVIAR ESTADO DEL BOTÓN 
  // ==========================================
  int estadoBoton = !digitalRead(boton); 

  if (estadoBoton == HIGH && estadoAnteriorBoton == LOW) {
    Serial.println("BOTON_ON"); 
  } 
  else if (estadoBoton == LOW && estadoAnteriorBoton == HIGH) {
    Serial.println("BOTON_OFF"); 
  }
  estadoAnteriorBoton = estadoBoton;

  // Antirrebote
  delay(10);
}
