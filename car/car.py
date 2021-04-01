#!/usr/bin/python3
'''Vehicle monitoring with data output over MQTT'''
__author__ = 'Dylan Gore'
# pylint: disable=unused-argument,invalid-overridden-method,arguments-differ,line-too-long

import importlib
import json
import logging
import pkgutil
import sys
import time
from datetime import datetime

import obd
import toml

import car.plugins

# Declare log message format string
LOG_FORMAT = '[%(processName)s] [%(levelname)s] %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

OUTPUT_PLUGINS = []

# Load config.toml file
try:
    CONFIG = toml.load('config.toml')
except FileNotFoundError:
    logging.error('Config file not found. Exiting.')
    sys.exit(1)


def iter_namespace(ns_pkg):
    '''Return a list of python modules in the same namespace'''
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + ".")


def load_plugins():
    '''Load all plugins from the plugins folder'''
    logging.info('Loading plugins...')
    for _, name, _ in iter_namespace(car.plugins):
        plugin_module = importlib.import_module(name)
        plugin = plugin_module.Plugin()
        plugin_info = plugin.get_plugin_info()

        if plugin_info['type'] == 'OUTPUT':
            OUTPUT_PLUGINS.append(plugin)

        logging.info('%s plugin has been loaded [type: %s]', plugin_info['name'], plugin_info['type'])


def get_obd_data(metric_name, obd_connection):
    '''Get a specified metric from the OBD interface and return the result as a dictionary'''
    value = None

    str_metrics = ['fuel_type']

    try:
        if metric_name not in str_metrics:
            value = float(obd_connection.query(obd.commands[metric_name.upper()]).value.magnitude)
        else:
            value = str(obd_connection.query(obd.commands[metric_name.upper()]).value.magnitude)
    except Exception as err:
        logging.warning('Unable to get metric %s - %s', metric_name, err)

    return {'metric': metric_name, 'value': value}


class Car:
    '''Class to handle getting data from the vehicle'''
    @staticmethod
    def run():
        '''Initial entrypoint'''

        load_plugins()

        for plugin in OUTPUT_PLUGINS:
            plugin.create_output_class()
        # create_mqtt_client(MQTT_CLIENT)

        # time.sleep(5)
        obd.logger.setLevel(obd.logging.DEBUG)

        time.sleep(5)

        obd_connection = None

        # for count in range(1, 11):
        obd_connection = obd.OBD()
        # start_time = time.time()
        # break
        # if obd_connection.status() == obd.OBDStatus.OBD_CONNECTED:
        #     break
        #     logging.info('Connected to OBD')
        # else:
        #     logging.warn('OBD connection attempt ' + str(count) + ' has failed')
        #     time.sleep(2)

        # fault_codes = obd.commands.GET_DTC
        # response = obd_connection.query(fault_codes)
        # logging.info(response.value.magnitude)

        # obd_connection.close()

        # print('\n\n\n', response.value)

        while True:
            logging.info(obd_connection.supported_commands)

            # Define the dictionary to store the metric data
            json_data = {}

            # The list of metrics to query
            metrics = ['speed', 'rpm', 'coolant_temp', 'engine_load', 'intake_temp', 'throttle_pos',
                       'relative_throttle_pos', 'run_time', 'fuel_level', 'ambiant_air_temp', 'barometric_pressure',
                       'fuel_type', 'oil_temp', 'fuel_rate']

            # For each metric in the list attempt to get a value for it and add it to the dictionary
            for metric in metrics:
                metric_data = get_obd_data(metric, obd_connection)
                if metric_data['value'] is not None:
                    json_data[metric_data['metric']] = metric_data['value']

            # Add the current UTC timestamp to the dictionary
            json_data['timestamp'] = datetime.utcnow()

            # Publish the dictionary of metric data as a JSON object
            for plugin in OUTPUT_PLUGINS:
                plugin.output_json('data', json)

            # publish_metric('measurement_time', float(time.time() - start_time))

            # Sleep for the configured amount of time
            logging.info('Sleeping for %s seconds', str(CONFIG["obd"]["poll_interval"]))
            time.sleep(CONFIG["obd"]["poll_interval"])

        # Close the OBD connection correctly before exiting the program
        obd_connection.close()
