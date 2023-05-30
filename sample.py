import time
from umqttsimple import MQTTClient
import ubinascii
import machine
import micropython
import network
import esp
from machine import Pin
import dht
esp.osdebug(None)
import gc
gc.collect()
from hcsr04 import HCSR04

ssid = 'Mobitel_4G_Keirish'
password = 'Keirish@1511'
mqtt_server = 'test.mosquitto.org'
client_id = ubinascii.hexlify(machine.unique_id())

topic_pub_temp = b'esp/dht/temperature'
topic_pub_hum = b'esp/dht/humidity'
topic_pub_distance = b'esp/ultrasonic/distance'

last_message = 0
message_interval = 1

station = network.WLAN(network.STA_IF)
station.active(True)
station.connect(ssid, password)

while not station.isconnected():
    pass

print('Connection successful')

sensor = dht.DHT11(Pin(4))
ultrasonic = HCSR04(trigger_pin=15, echo_pin=2)

def connect_mqtt():
    global client_id, mqtt_server
    client = MQTTClient(client_id, mqtt_server)
    client.connect()
    print('Connected to %s MQTT broker' % mqtt_server)
    return client

def restart_and_reconnect():
    print('Failed to connect to MQTT broker. Reconnecting...')
    time.sleep(10)
    machine.reset()

def read_sensor():
    try:
        sensor.measure()
        temp = sensor.temperature()
        hum = sensor.humidity()
        distance = ultrasonic.distance_cm()
        if isinstance(temp, (float, int)) and isinstance(hum, (float, int)) and isinstance(distance, (float, int)):
            temp_str = '{:.1f}'.format(temp)  # Modified formatting
            hum_str = '{:.1f}'.format(hum)  # Modified formatting
            distance_str = '{:.1f}'.format(distance)  # Modified formatting
            return temp_str, hum_str, distance_str
        else:
            return 'Invalid sensor readings.', '', ''
    except OSError as e:
        return 'Failed to read sensor.', '', ''


try:
    client = connect_mqtt()
except OSError as e:
    restart_and_reconnect()

while True:
    try:
        if (time.time() - last_message) > message_interval:
            temp, hum, distance = read_sensor()
            print(temp)
            print(hum)
            print(distance)

            if float(temp) < 30 and float(distance) < 10:
                availability = b'Coke is available'
            else:
                availability = b'Coke is not available'

            print(availability)  # Print availability in the command line

            client.publish(b'esp/coke/availability', availability)
            client.publish(topic_pub_temp, temp)
            client.publish(topic_pub_hum, hum)
            client.publish(topic_pub_distance, distance)

            last_message = time.time()
    except OSError as e:
        restart_and_reconnect()

