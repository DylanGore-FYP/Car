'''Python-based service for basic monitoring of a Raspberry Pi with data being output to MQTT'''
from .car import Car

if __name__ == '__main__':
    Car.run()
