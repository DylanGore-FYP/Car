#!/usr/bin/python3
'''Python-based service for basic monitoring of a Raspberry Pi with data being output to MQTT'''
__author__ = 'Dylan Gore'
# pylint: disable=unused-argument,invalid-overridden-method,arguments-differ,line-too-long

import json
import logging
import ssl
import time

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
    exit(1)


class MQTTClass(mqtt.Client):
    '''MQTT Client instance'''

    def on_connect(self, mqtt_client, userdata, flags, mqtt_rc):
        '''Runs on a successful MQTT connection'''
        logging.info('Connected to MQTT (mqtt_rc: %s)', str(mqtt_rc))
        mqtt_client.publish(f'{CONFIG["mqtt"]["base_topic"]}/status', 'online', qos=CONFIG["mqtt"]['pub_qos'], retain=True)

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


def publish_metric(metric, payload):
    '''Publish a system metric to MQTT'''
    json_data = {
        metric: payload
    }
    if payload is not None:
        logging.debug('Metric: %s %s', metric, str(payload))
        MQTT_CLIENT.publish(f'{CONFIG["mqtt"]["base_topic"]}/{metric}', json.dumps(json_data),
                            qos=CONFIG['mqtt']['pub_qos'],
                            retain=CONFIG['mqtt']['retain'])


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
        start_time = time.time()
        # break
        # if obd_connection.status() == obd.OBDStatus.OBD_CONNECTED:
        #     break
        #     logging.info('Connected to OBD')
        # else:
        #     logging.warn('OBD connection attempt ' + str(count) + ' has failed')
        #     time.sleep(2)

        fault_codes = obd.commands.GET_DTC
        response = obd_connection.query(fault_codes)
        # logging.info(response.value.magnitude)

        # obd_connection.close()

        print('\n\n\n', response.value)
        # print(obd_connection.query(obd.commands.SPEED).value.magnitude)
        # logging.info(obd_connection.query(obd.commands['SPEED']))
        while True:
            logging.info(obd_connection.supported_commands)
            try:
                publish_metric('speed', float(obd_connection.query(obd.commands['SPEED']).value.magnitude))
                publish_metric('rpm', float(obd_connection.query(obd.commands['RPM']).value.magnitude))
                publish_metric('coolant_temp', float(obd_connection.query(obd.commands['COOLANT_TEMP']).value.magnitude))
                publish_metric('engine_load', float(obd_connection.query(obd.commands['ENGINE_LOAD']).value.magnitude))
                publish_metric('intake_temp', float(obd_connection.query(obd.commands['INTAKE_TEMP']).value.magnitude))
                # publish_metric('throttle_pos', float(obd_connection.query(obd.commands['THROTTLE_POS']).value.magnitude))
                # publish_metric('relative_throttle_pos', float(obd_connection.query(obd.commands['RELATIVE_THROTTLE_POS']).value.magnitude))
                # publish_metric('run_time', float(obd_connection.query(obd.commands['RUN_TIME']).value.magnitude))
                # publish_metric('fuel_level', float(obd_connection.query(obd.commands['FUEL_LEVEL']).value.magnitude))
                # publish_metric('ambiant_air_temp', float(obd_connection.query(obd.commands['AMBIANT_AIR_TEMP']).value.magnitude))
                # publish_metric('barometric_pressure', float(obd_connection.query(obd.commands['BAROMETRIC_PRESSURE']).value.magnitude))
                # publish_metric('fuel_type', str(obd_connection.query(obd.commands['FUEL_TYPE']).value.magnitude))
                # publish_metric('oil_temp', float(obd_connection.query(obd.commands['OIL_TEMP']).value.magnitude))
                # publish_metric('fuel_rate', float(obd_connection.query(obd.commands['FUEL_RATE']).value.magnitude))
            except Exception as err:
                logging.error(err)
            publish_metric('measurement_time', float(time.time() - start_time))
            logging.info(f'Sleeping for {CONFIG["obd"]["poll_interval"]} seconds')
            time.sleep(CONFIG["obd"]["poll_interval"])
        obd_connection.close()
    #     except Exception as err:
    #         logging.error(err)
    #     logging.debug('Going to sleep')
    #     time.sleep(300)
