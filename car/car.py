#!/usr/bin/python3
'''Vehicle monitoring with data output over MQTT'''
__author__ = 'Dylan Gore'
# pylint: disable=unused-argument,invalid-overridden-method,arguments-differ,line-too-long

import importlib
import logging
import subprocess
import sys
import time
from datetime import datetime
from platform import system

import eel
import gps
import obd
import toml

# Declare log message format string
LOG_FORMAT = '[%(processName)s] [%(levelname)s] %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# The format string for timestamps
TIME_FMT = '%Y-%m-%dT%H:%M:%SZ%z'

OUTPUT_PLUGINS = []
CONFIG_PLUGINS = []

# The list of metrics to query
metrics = ['speed', 'rpm', 'coolant_temp', 'engine_load', 'intake_temp', 'throttle_pos',
           'relative_throttle_pos', 'run_time', 'fuel_level', 'ambiant_air_temp', 'barometric_pressure',
           'fuel_type', 'oil_temp', 'fuel_rate']

eel.init('ui')

# Run using Chromium if on Linux, use ChromeDriver on Windows
if system() == 'Linux':
    eel.start('index.html', block=False, size=(800, 600), mode='custom',
              cmdline_args=['chromium-browser', '--kiosk', '--incognito', '--disable-pinch',
                            '--overscroll-history-navigation=0', 'http://localhost:8000/index.html'])
else:
    eel.start('index.html', block=False, size=(800, 600),
              cmdline_args=['--kiosk', '--incognito', '--disable-pinch',
                            '--overscroll-history-navigation=0'], port=5500)

# Load config.toml file
try:
    CONFIG = toml.load('config.toml')
    # Get configured plugin names and add them to a list
    for plugin_type in CONFIG['plugins'].keys():
        for config_plugin in CONFIG['plugins'][plugin_type]:
            CONFIG_PLUGINS.append(f'{plugin_type}_{config_plugin}')
except KeyError as err:
    logging.error('Malformed configuration file! Key %s was not found', err)
    sys.exit(1)
except FileNotFoundError:
    logging.error('Config file not found. Exiting.')
    sys.exit(1)


def load_plugins():
    '''Load all plugins from the plugins folder'''
    logging.info('Loading plugins...')
    # Loop through the list of user-configured plugins
    for plugin_name in CONFIG_PLUGINS:
        # Split the plugin name to get the type name separately
        plugin_info = plugin_name.split('_')
        # If the plugin is enabled in the config file, try to load the Python module
        if CONFIG['plugins'][plugin_info[0]][plugin_info[1]]['enabled']:
            try:
                # Load the module
                plugin_module = importlib.import_module(f'car.plugins.{plugin_name}')
                # Initialise the plugin
                plugin = plugin_module.Plugin()
                # Get the plugin info
                plugin_info = plugin.get_plugin_info()

                # If the plugin is an output plugin, add it to the list
                if plugin_info['type'] == 'OUTPUT':
                    OUTPUT_PLUGINS.append(plugin)

                logging.info('%s plugin has been loaded [type: %s]', plugin_info['name'], plugin_info['type'])
            except ModuleNotFoundError:
                logging.warning('Attempted to load missing plugin: %s', plugin_name)
            except AttributeError:
                logging.error('Malformed plugin %s will not be loaded', plugin_name)


def get_obd_data(metric_name, obd_connection):
    '''Get a specified metric from the OBD interface and return the result as a dictionary'''
    value = None

    # The list of metrics that have a data type of string
    str_metrics = ['fuel_type']

    try:
        if metric_name not in str_metrics:
            value = float(obd_connection.query(obd.commands[metric_name.upper()]).value.magnitude)
        else:
            value = str(obd_connection.query(obd.commands[metric_name.upper()]).value.magnitude)
    except Exception as err:
        logging.warning('Unable to get metric %s - %s', metric_name, err)

    return {'metric': metric_name, 'value': value}


def poll_gps():
    '''Method to handle getting and parsing the GPS coordinates if enabled in the config'''
    gps_data = {'lat': 0.0, 'lon': 0.0, 'alt': 0.0}

    if CONFIG['gps']['enabled']:
        gpsd = gps.gps(mode=gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
        count = 20
        while count > 0:
            # pylint: disable=not-callable
            packet = gpsd.next()
            # If the packet is a GPS data packet
            if packet['class'] == 'TPV':
                gps_data['lat'] = getattr(packet, 'lat', 0.0)
                gps_data['lon'] = getattr(packet, 'lon', 0.0)
                gps_data['alt'] = getattr(packet, 'alt', 0.0)
                # End the retry counter
                count = 0
            else:
                # Decrement the retry counter
                count -= 1
    return gps_data


def update_speed_metric(value):
    '''Function to update the eel UI'''
    logging.info('update speed %s', value)
    # pylint: disable=no-member
    eel.updateGauges(value, 0)


@eel.expose
def close_program():
    '''Method to cleanly exit, exposed via eel so can be called from JS'''
    print('Close python')
    sys.exit(0)


@eel.expose
def pi_power(mode):
    '''Method to handle shutting down or rebooting a Raspberry Pi'''
    accepted = ['shutdown', 'reboot']

    # Only run the command if it is in the above list
    if mode in accepted:
        subprocess.run(["sudo", mode, "now"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        close_program()


class Car:
    '''Class to handle getting data from the vehicle'''
    # pylint: disable=too-many-branches
    @ staticmethod
    def run():
        '''Initial entrypoint'''

        load_plugins()

        for plugin in OUTPUT_PLUGINS:
            plugin.create_output_class()
        time.sleep(5)

        obd_connection = None

        if CONFIG['obd']['enabled']:
            # Attempt to connect to OBD, retry if connection fails
            for count in range(1, 6):
                obd.logger.setLevel(obd.logging.INFO)
                obd_connection = obd.Async(check_voltage=False)

                if not obd_connection.is_connected():
                    time.sleep(2)
                    logging.warning('OBD connection failed - Attempt: %d', count)
                    CONFIG['obd']['enabled'] = False
                else:
                    CONFIG['obd']['enabled'] = True
                    break

            if obd_connection.is_connected():
                # ui_metrics = ['speed', 'rpm']

                # Set the OBD metrics to watch
                for metric_name in metrics:
                    try:
                        if metric_name == 'speed':
                            obd_connection.watch(obd.commands[metric_name.upper()], callback=update_speed_metric)
                        else:
                            obd_connection.watch(obd.commands[metric_name.upper()])
                    except Exception as err:
                        logging.warning('Unable to watch metric %s - %s', metric_name, err)

                obd_connection.start()

        fault_codes = {}
        # if CONFIG['obd']['enabled']:
        # pylint: disable=no-member
        # response = obd_connection.query(obd.commands.GET_DTC)

        # if response is not None:
        #    for fault in response:
        #        fault_codes[fault[0]] = fault[1]

        # obd_connection.close()

        # print('\n\n\n', response.value)

        while True:
            if CONFIG['obd']['enabled']:
                supported_commands = obd_connection.supported_commands
                # logging.info(supported_commands)
                with open('supported_commands.txt', 'w') as file:
                    file.write(str(supported_commands))

            # Define the dictionary to store the metric data
            json_data = {}

            # Add vehicle information to payload
            for entry in CONFIG['vehicle']:
                if CONFIG['vehicle'][entry] is not None and CONFIG['vehicle'][entry] != '':
                    json_data[entry] = CONFIG['vehicle'][entry]

            # Add fault codes to payload
            if len(fault_codes) > 0:
                json_data['fault_codes'] = fault_codes

            # For each metric in the list attempt to get a value for it and add it to the dictionary
            if CONFIG['obd']['enabled']:
                for metric in metrics:
                    metric_data = get_obd_data(metric, obd_connection)
                    if metric_data['value'] is not None:
                        json_data[metric_data['metric']] = metric_data['value']

            # Add the current UTC timestamp to the dictionary
            json_data['timestamp'] = str(datetime.utcnow().strftime(TIME_FMT))

            # Get the GPS location
            json_data = {**json_data, **poll_gps()}

            # Publish the dictionary of metric data as a JSON object
            for plugin in OUTPUT_PLUGINS:
                plugin.output_json('data', json_data)

            # publish_metric('measurement_time', float(time.time() - start_time))

            # Sleep for the configured amount of time
            logging.info('Sleeping for %s seconds', str(CONFIG["obd"]["poll_interval"]))
            eel.sleep(CONFIG["obd"]["poll_interval"])

        # Close the OBD connection correctly before exiting the program
        if CONFIG['obd']['enabled']:
            obd_connection.stop()
            obd_connection.close()
