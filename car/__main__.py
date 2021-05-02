'''Vehicle monitoring with data output over MQTT'''
import sys

from .car import Car

if __name__ == '__main__':
    # Run the car code and handle an exit by KeyboardInterrupt
    try:
        Car.run()
    except KeyboardInterrupt:
        print('Exiting...')
        sys.exit(0)
