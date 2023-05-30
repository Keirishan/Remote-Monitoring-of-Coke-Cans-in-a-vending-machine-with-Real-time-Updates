import time
from umqttsimple import MQTTClient
import ubinascii
import machine
import micropython
import network
import esp
from machine import Pin, PWM
import dht
from hcsr04 import HCSR04

esp.osdebug(None)
import gc
gc.collect()

ssid = 'Mobitel_4G_Keirish'
password = 'Keirish@1511'
mqtt_server = 'test.mosquitto.org'
client_id = ubinascii.hexlify(machine.unique_id())

topic_pub_temp = b'esp/dht/temperature'
topic_pub_hum = b'esp/dht/humidity'
topic_pub_distance = b'esp/ultrasonic/distance'
topic_pub_availability = b'esp/coke/availability'
topic_pub_detect = b'esp/coin/detect'

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

ir_sensor_pin = 14  # Pin connected to the IR sensor D5
servo_pin = 12  # Pin connected to the servo motor D6

ir_sensor = Pin(ir_sensor_pin, Pin.IN)
servo_pwm = PWM(Pin(servo_pin), freq=50)

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
            temp_str = str(temp)  # Default string conversion
            hum_str = str(hum)  # Default string conversion
            distance_str = str(distance)  # Default string conversion
            return temp_str, hum_str, distance_str
        else:
            return 'Invalid sensor readings.', '', ''
    except OSError as e:
        return 'Failed to read sensor.', '', ''

def rotate_servo(angle):
    # Map the angle value from the range 0-180 to the corresponding duty cycle value
    duty_cycle = int(102 + (angle / 180) * 74)
    servo_pwm.duty(duty_cycle)

def stop_servo():
    servo_pwm.duty(0)  # Stop the servo motor

try:
    client = connect_mqtt()
except OSError as e:
    restart_and_reconnect()

detect = b''  # Initialize detect variable with an empty value

while True:
    try:
        if (time.time() - last_message) > message_interval:
            temp, hum, distance = read_sensor()
            print(temp)
            print(hum)
            print(distance)

            if float(temp) < 33 and float(distance) < 10:
                availability = b'6 Coke Available'
            elif float(temp) < 33 and float(distance) < 20:
                availability = b'5 Coke Available'
            elif float(temp) < 33 and float(distance) < 30:
                availability = b'4 Coke Available'
            elif float(temp) < 33 and float(distance) < 40:
                availability = b'3 Coke Available'
            elif float(temp) < 33 and float(distance) < 50:
                availability = b'2 Coke Available'
            elif float(temp) < 33 and float(distance) < 60:
                availability = b'1 Coke Available'
            else:
                availability = b'Coke is not available'
                
            if ir_sensor.value() == 1:  # IR sensor detects an obstacle
                detect = b'Coin not detected'
                rotate_servo(-180)  # Rotate the servo motor to 180 degrees
            else:
                detect = b'Coin detected'
                rotate_servo(0)  # Rotate the servo motor to initial position

            print(availability)  # Print availability in the command line
            print(detect) # Print IR detection in the command line

            client.publish(topic_pub_availability, availability)
            client.publish(topic_pub_temp, temp)
            client.publish(topic_pub_hum, hum)
            client.publish(topic_pub_distance, distance)
            client.publish(topic_pub_detect, detect)

            last_message = time.time()
    except OSError as e:
        restart_and_reconnect()

