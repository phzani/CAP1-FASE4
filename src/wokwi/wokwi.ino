#include <Arduino.h>
#include "DHT.h"
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// Definição dos pinos
#define DHTPIN 15          
#define DHTTYPE DHT22

#define BUTTON_P 4         
#define BUTTON_K 5         
#define LDR_PIN 34         
#define RELAY_PIN 18       
#define LED_PIN 2          

#define SCALE_K 50
#define SCALE_P 75

// LCD I2C: 20 colunas, 4 linhas
LiquidCrystal_I2C lcd(0x27, 20, 4);
DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_P, INPUT_PULLUP);
  pinMode(BUTTON_K, INPUT_PULLUP);
  pinMode(LDR_PIN, INPUT);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);

  dht.begin();
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(LED_PIN, LOW);

  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Temp Umid  pH Bomba");
}

void loop() {
  // Leitura dos sensores
  bool fosforo = !digitalRead(BUTTON_P);
  bool potassio = !digitalRead(BUTTON_K);
  uint16_t ldrValue = analogRead(LDR_PIN);
  float pH = map(ldrValue, 0, 4095, 0, 14);
  float umidade = dht.readHumidity();
  float temperatura = dht.readTemperature();

  // Lógicas de decisão
  bool falta_nutriente = (!fosforo || !potassio);
  bool solo_seco = (umidade < 40.0);
  bool ph_ruim = (pH < 5.5 || pH > 7.5);
  bool bombaOn = (falta_nutriente || solo_seco || ph_ruim);

  digitalWrite(RELAY_PIN, bombaOn ? HIGH : LOW);
  digitalWrite(LED_PIN, bombaOn ? HIGH : LOW);

  // ======== SERIAL PLOTTER OUTPUT ========
  // Sempre nesse formato fixo: fosforo,potassio,temp,pH,umidade
  Serial.print("fosforo:");
  Serial.print(fosforo);
  Serial.print(",");
  Serial.print("potassio:");
  Serial.print(potassio);
  Serial.print(",");
  Serial.print("temperatura:");
  Serial.print(temperatura);
  Serial.print(",");
  Serial.print("ph:");
  Serial.print(pH);
  Serial.print(",");
  Serial.print("umidade:");
  Serial.println(umidade);

  // LCD – Linha 2 (valores principais)
  lcd.setCursor(0, 1);
  char linha2[21];
  snprintf(linha2, sizeof(linha2), "%2.0fC %3d%% %4.1f %s", temperatura, (int)umidade, pH, bombaOn ? " ON " : "OFF ");
  lcd.print(linha2);

  // LCD – Linha 3 (estado dos nutrientes)
  lcd.setCursor(0, 2);
  lcd.print("K:"); lcd.print(potassio ? "OK" : "Baixo");
  lcd.print("  P:"); lcd.print(fosforo ? "OK" : "Baixo");
  lcd.print("    "); // padding pra limpar resto da linha

  // LCD – Linha 4 (motivo)
  lcd.setCursor(0, 3);
  lcd.print("                    "); // limpa
  lcd.setCursor(0, 3);
  String motivoStr = "---";
  if (bombaOn) {
    motivoStr = "";
    if (falta_nutriente) motivoStr += "Falta Nutriente ";
    if (solo_seco) motivoStr += "Solo Seco ";
    if (ph_ruim) motivoStr += "pH Fora ";
  }
  motivoStr = motivoStr.substring(0, 20);
  lcd.print(motivoStr);


  delay(2000);
}
