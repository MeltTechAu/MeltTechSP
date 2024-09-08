
from simple_pid import PID

# Moving Average Filter to smooth out temperature readings
class MovingAverageFilter:
    def __init__(self, size=10):  # Original size was 10
        self.size = size
        self.data = []

    def add_data(self, value):
        self.data.append(value)
        if len(self.data) > self.size:
            self.data.pop(0)
        return sum(self.data) / len(self.data)

# Initialize the filter with a size of 10
filter = MovingAverageFilter(size=20)

import RPi.GPIO as GPIO
import time
from flask import Flask, render_template, request, jsonify
from threading import Thread
import logging
import signal
import sys

# MAX31855 bit-banged SPI class
class MAX31855:
    def __init__(self, cs_pin, clock_pin, data_pin):
        self.cs_pin = cs_pin
        self.clock_pin = clock_pin
        self.data_pin = data_pin
        
        # Set up GPIO pins
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.cs_pin, GPIO.OUT)
        GPIO.setup(self.clock_pin, GPIO.OUT)
        GPIO.setup(self.data_pin, GPIO.IN)

    def read_temp(self):
        # Pull CS low to start communication
        GPIO.output(self.cs_pin, GPIO.LOW)
        time.sleep(0.001)  # Small delay

        # Read 32 bits of data from the sensor
        value = 0
        for i in range(32):
            GPIO.output(self.clock_pin, GPIO.HIGH)
            time.sleep(0.001)
            value <<= 1
            if GPIO.input(self.data_pin):
                value |= 1
            GPIO.output(self.clock_pin, GPIO.LOW)
            time.sleep(0.001)

        # Pull CS high to end communication
        GPIO.output(self.cs_pin, GPIO.HIGH)

        # Extract the temperature from the raw value
        temp = (value >> 18) & 0x3FFF
        if temp & 0x2000:  # Check if the temperature is negative
            temp -= 16384
        return temp * 0.25  # Return temperature in Celsius
        temp = filter.add_data(temp * 0.25)

# Set up the GPIO pins for the MAX31855 bit-banged SPI
cs_pin = 8  # Chip select pin
clock_pin = 11  # Clock pin
data_pin = 9  # Data (MISO) pin
max31855_sensor = MAX31855(cs_pin, clock_pin, data_pin)

# Set up the GPIO pin for relay control
RELAY_PIN = 20
GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.output(RELAY_PIN, GPIO.LOW)  # Turn off the relay initially

# Initialize Flask app
app = Flask(__name__)

# PID parameters
pid = PID(1, 0.1, 0.05, setpoint=0)
pid.output_limits = (0, 1)  # PID output will be between 0 and 1

# Global variables
current_temperature = 0
set_point = 0
hold_time = 0
start_time = None
kiln_running = False

# Logging configuration
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')

# Function to read the temperature from MAX31855
def get_temperature():
    try:
        temp = max31855_sensor.read_temp()
        if temp is not None:
            return temp
        else:
            raise RuntimeError('Failed to read temperature')
    except Exception as e:
        logging.error(f"Error reading temperature: {e}")
        return None  # Return None in case of an error

# Function to control the relay based on the PID output
def control_kiln(output):
    try:
        if output >= 0.6:  # Add hysteresis to avoid rapid switching
            GPIO.output(RELAY_PIN, GPIO.HIGH)  # Turn the relay on
            logging.debug("Relay turned ON")
        elif output <= 0.4:  # Avoid turning off too quickly
            GPIO.output(RELAY_PIN, GPIO.LOW)  # Turn the relay off
            logging.debug("Relay turned OFF")
    except Exception as e:
        logging.error(f"Error controlling kiln: {e}")
        logging.debug("Relay turned OFF")
    except Exception as e:
        logging.error(f"Error controlling kiln: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_kiln():
    global set_point, hold_time, start_time, kiln_running
    try:
        data = request.get_json()
        set_point = float(data['set_point'])
        hold_time = int(data['hold_time'])
        pid.setpoint = set_point
        start_time = time.time()
        kiln_running = True
        logging.info(f"Kiln started with set point: {set_point}°C, hold time: {hold_time} seconds")
        return jsonify(success=True)
    except Exception as e:
        logging.error(f"Error starting kiln: {e}")
        return jsonify(success=False)

@app.route('/stop', methods=['POST'])
def stop_kiln():
    global kiln_running
    try:
        kiln_running = False
        GPIO.output(RELAY_PIN, GPIO.LOW)  # Turn off the relay
        logging.info("Kiln stopped")
        return jsonify(success=True)
    except Exception as e:
        logging.error(f"Error stopping kiln: {e}")
        return jsonify(success=False)

@app.route('/status', methods=['GET'])
def status():
    global current_temperature
    try:
        current_temperature = get_temperature()
        elapsed_time = time.time() - start_time if start_time else 0
        total_time = hold_time  # Placeholder logic for total time
        return jsonify(total_time=total_time, current_temperature=current_temperature, set_point=set_point, elapsed_time=elapsed_time)
    except Exception as e:
        logging.error(f"Error getting status: {e}")
        return jsonify(success=False)

def control_loop():
    global current_temperature, kiln_running
    while True:
        try:
            if kiln_running:
                current_temperature = get_temperature()
                if current_temperature is not None:
                    output = pid(current_temperature)
                    control_kiln(output)
                    logging.debug(f"Control loop output: {output}")
                else:
                    logging.error("Current temperature is None, stopping kiln")
                    kiln_running = False
                    GPIO.output(RELAY_PIN, GPIO.LOW)
            time.sleep(1)
        except Exception as e:
            logging.error(f"Error in control loop: {e}")

# Signal handling for graceful shutdown
def handle_exit(sig, frame):
    logging.info("Shutting down...")
    GPIO.output(RELAY_PIN, GPIO.LOW)  # Ensure relay is turned off
    GPIO.cleanup()  # Clean up GPIO
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

if __name__ == '__main__':
    control_thread = Thread(target=control_loop)
    control_thread.start()
    try:
        app.run(host='0.0.0.0', port=5001)
    except Exception as e:
        logging.error(f"Error running Flask app: {e}")
        raise SystemExit("Failed to start the Flask app.")
