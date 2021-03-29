#!/usr/bin/python3
'''Vehicle monitoring with data output over MQTT'''
__author__ = 'Dylan Gore'
# pylint: disable=unused-argument,invalid-overridden-method,arguments-differ,line-too-long

import json
import logging
import ssl
import sys
import time
from datetime import datetime

import obd
import paho.mqtt.client as mqtt
import toml

# Declare log message format string
LOG_FORMAT = '[%(processName)s] [%(levelname)s] %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# Load config.toml file
try:
    CONFIG = toml.load('config.toml')
except FileNotFoundError:
    logging.error('Config file not found. Exiting.')
    sys.exit(1)


class MQTTClass(mqtt.Client):
    '''MQTT Client instance'''

    def on_connect(self, mqtt_client, userdata, flags, mqtt_rc):
        '''Runs on a successful MQTT connection'''
        logging.info('Connected to MQTT (mqtt_rc: %s)', str(mqtt_rc))
        mqtt_client.publish(f'{CONFIG["mqtt"]["base_topic"]}/status', 'online',
                            qos=CONFIG["mqtt"]['pub_qos'], retain=True)

    def on_message(self, mqtt_client, userdata, msg):
        '''Runs when an MQTT message is received'''
        payload = msg.payload.decode('utf-8')
        logging.info('Msg Received on topic %s - %s', msg.topic, payload)

    def on_publish(self, mqtt_client, userdata, mid):
        '''Runs when an MQTT message is published'''
        logging.debug('mid: %s', str(mid))

    def on_subscribe(self, mqtt_client, userdata, mid, granted_qos):
        '''Runs when a topic is subscribed to'''
        logging.info('Subscribed mid:%s qos:%s', str(mid), str(granted_qos))

    def on_log(self, mqtt_client, userdata, level, buffer):
        '''Runs on MQTT log message'''
        logging.debug(buffer)

    def on_disconnect(self, client, userdata, mqtt_rc):
        '''The callback function run on disconnection from the MQTT broker'''
        logging.info('Disconnected from broker (mqtt_rc: %s)', str(mqtt_rc))
        # If the client disconnected due to an error, log that and increment the Prometheus metric
        if mqtt_rc != 0:
            logging.error('Abnormal disconnect')

    def run(self):
        '''Runs the MQTT client'''
        if CONFIG['mqtt']['ssl']:
            self.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2, cert_reqs=ssl.CERT_NONE)
            self.tls_insecure_set(True)
        self.username_pw_set(username=CONFIG['mqtt']['username'], password=CONFIG['mqtt']['password'])
        self.connect(CONFIG['mqtt']['host'], int(CONFIG['mqtt']['port']), 60)

        mqtt_rc = 0
        while mqtt_rc == 0:
            mqtt_rc = self.loop_start()
        return mqtt_rc


# Define the MQTT Client
MQTT_CLIENT = MQTTClass()


def create_mqtt_client(client):
    '''Creates the MQTT client'''
    client.will_set(f'{CONFIG["mqtt"]["base_topic"]}/status', payload="offline", qos=2, retain=True)
    mqtt_rc = client.run()
    logging.info("mqtt_rc: %s", str(mqtt_rc))


def mqtt_publish_json(topic, json_payload, qos=CONFIG['mqtt']['pub_qos'], retain=CONFIG['mqtt']['retain']):
    '''Publish JSON data to a specified MQTT topic'''
    MQTT_CLIENT.publish(f'{CONFIG["mqtt"]["base_topic"]}/{topic}', json.dumps(json_payload),
                        qos=qos, retain=retain)


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
        create_mqtt_client(MQTT_CLIENT)

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
            mqtt_publish_json('data', json_data)

            # publish_metric('measurement_time', float(time.time() - start_time))

            # Sleep for the configured amount of time
            logging.info('Sleeping for %s seconds', str(CONFIG["obd"]["poll_interval"]))
            time.sleep(CONFIG["obd"]["poll_interval"])

        # Close the OBD connection correctly before exiting the program
        obd_connection.close()
