// This sketch reads ADC0 at a high sample rate, packs four 10-bit samples
// into five 8-bit bytes, and sends them over UART.

// --- Configuration ---
// You can adjust the sample rate by changing the ADC prescaler.
// A lower prescaler value results in a faster sample rate.
// Note: A prescaler of 16 gives the fastest rate recommended by the datasheet
// for full 10-bit resolution.  Going to 8 might reduce accuracy.
//
// Prescaler | ADC Clock | Sample Rate (approx.)
// ---------------------------------------------
// 128 (default) | 125 KHz   | 9.6 kS/s
// 64            | 250 KHz   | 19.2 kS/s
// 32            | 500 KHz   | 38.5 kS/s
// 16            | 1 MHz     | 76.9 kS/s (might be unstable)

// Set the desired ADC prescaler.
// ADPS2, ADPS1, ADPS0 bits in ADCSRA register
// 111 -> 128
// 110 -> 64
// 101 -> 32
// 100 -> 16
const byte adcPrescaler = (1 << ADPS2) | (0 << ADPS1) | (1 << ADPS0); // Prescaler of 32 for ~38.5kS/s

void setup() {

  Serial.begin(250000);

  // --- Configure ADC ---
  // We will be directly manipulating the ADC registers for speed.
  
  // ADMUX: ADC Multiplexer Selection Register
  // REFS0: Use AVcc as the reference voltage.
  // MUX[3:0]: Select ADC0 as the input channel.
  ADMUX = (1 << REFS0);

  // ADCSRA: ADC Control and Status Register A
  // ADEN: Enable the ADC.
  // ADSC: Start the first conversion.
  // ADATE: Enable auto-triggering. This means a new conversion will start
  //        as soon as the previous one finishes.
  ADCSRA = (1 << ADEN) | (1 << ADSC) | (1 << ADATE) | adcPrescaler;
}

void loop() {
  // The ADC is in "free-running" mode, so it's continuously sampling.
  // We just need to read the data as it becomes available.

  // Array to hold the four 10-bit ADC samples
  uint16_t samples[4];

  // --- Acquire 4 Samples ---
  // Wait for the ADC conversion to complete, then read the value.
  // The ADIF bit in ADCSRA is set when a conversion is complete.
  for (int i = 0; i < 4; i++) {
    while (!(ADCSRA & (1 << ADIF))); // Wait for conversion to finish
    samples[i] = ADC;               // Read the 10-bit result
    ADCSRA |= (1 << ADIF);            // Clear the flag by writing a 1
  }

  
  byte packedData[5];

  packedData[0] = samples[0] & 0xFF;                         // Lower 8 bits of sample 0
  packedData[1] = (samples[0] >> 8) & 0x03;                  // Upper 2 bits of sample 0
  packedData[1] |= (samples[1] & 0x3F) << 2;                 // Lower 6 bits of sample 1
  
  packedData[2] = (samples[1] >> 6) & 0x0F;                  // Upper 4 bits of sample 1
  packedData[2] |= (samples[2] & 0x0F) << 4;                 // Lower 4 bits of sample 2
  
  packedData[3] = (samples[2] >> 4) & 0x3F;                  // Upper 6 bits of sample 2
  packedData[3] |= (samples[3] & 0x03) << 6;                 // Lower 2 bits of sample 3

  packedData[4] = (samples[3] >> 2) & 0xFF;                  // Upper 8 bits of sample 3


  // send 5 bytes to PC
  Serial.write(packedData, 5);
}