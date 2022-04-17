#include <Arduino_GFX_Library.h>
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>
#include <string>
#include <stdio.h>

using namespace std;

// Display Initalisation
#define TFT_CS D1
#define TFT_RST D0
#define TFT_DC D2

/* More data bus class: https://github.com/moononournation/Arduino_GFX/wiki/Data-Bus-Class */
Arduino_DataBus *BUS = new Arduino_ESP8266SPI(TFT_DC /* DC */, TFT_CS /* CS */);

/* More display class: https://github.com/moononournation/Arduino_GFX/wiki/Display-Class */
Arduino_GFX *DSP = new Arduino_ST7735(
    BUS, TFT_RST /* RST */, 3 /* rotation */, true /* IPS */, 80 /* width */, 160 /* height */,
    26 /* col offset 1 */, 1 /* row offset 1 */, 26 /* col offset 2 */, 1 /* row offset 2 */);

Arduino_GFX *GFX = new Arduino_Canvas(160 /* width */, 80 /* height */, DSP);

// WIFI Initalisation
const bool SOFT_AP = true;

const char *SSID = "ESP3266-DSP";
const char *PASSWORD = "ChickenNugget";

WiFiUDP UDP;
const unsigned int LOCAL_UDP_PORT = 4300;
const unsigned int BUFFER_SIZE = 10000;
char buffer[BUFFER_SIZE];

// Misc Globals
const char VALUE_DELIMITER = '.';
const char PIXEL_DELIMITER = '#';

void setup()
{
    Serial.begin(9600);
    Serial.println();

    GFX->begin();
    GFX->fillScreen(BLACK);
    GFX->flush();

    // WIFI Configuration
    if (SOFT_AP)
    {
        // Create Soft AP
        bool success = WiFi.softAP(SSID, PASSWORD);
        if (success)
        {
            Serial.printf("AP: %s Established. PW: %s\n", SSID, PASSWORD);
            Serial.printf("Listening at %s, UDP port %d\n", "192.168.4.1", LOCAL_UDP_PORT);
        }
        else
        {
            Serial.printf("Error Establishing AP\n");
            return;
        }
    }
    else
    {
        // Connect to Existing Network
        Serial.printf("Connecting to %s\n", SSID);
        WiFi.begin(SSID, PASSWORD);

        while (WiFi.status() != WL_CONNECTED)
        {
            delay(500);
            Serial.println("...");
        }
        Serial.printf("Sucessfully Connected to %s\n", SSID);
        Serial.printf("Listening at %s, UDP port %d\n", WiFi.localIP().toString().c_str(), LOCAL_UDP_PORT);
    }

    // Setup UDP
    UDP.begin(LOCAL_UDP_PORT);
}

void parse_pixel(string operation)
{
    u16_t end = operation.find(VALUE_DELIMITER);
    int16_t x = stoi(operation.substr(0, end), 0, 16);
    operation.erase(0, end + 1);

    end = operation.find(VALUE_DELIMITER);
    int16_t y = stoi(operation.substr(0, end), 0, 16);
    operation.erase(0, end + 1);

    u16_t colour = stoi(operation, 0, 16);

    GFX->drawPixel(x, y, colour);
}

void loop()
{
    int packetsize = UDP.parsePacket();
    if (packetsize)
    {
        packetsize, UDP.remoteIP().toString().c_str(),
            UDP.remotePort();

        int length = UDP.read(buffer, BUFFER_SIZE);
        if (length > 0)
        {
            buffer[length] = 0;
        }

        // Process Data
        string stream = buffer;
        unsigned int i = 0;

        while ((i = stream.find(PIXEL_DELIMITER)) != string::npos)
        {
            parse_pixel(stream.substr(0, i));
            stream.erase(0, i + 1);
        }

        parse_pixel(stream);
        GFX->flush();
    }
}
