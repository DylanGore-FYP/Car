'''MQTT Output Plugin'''
__author__ = 'Dylan Gore'
# pylint: disable=unused-argument,invalid-overridden-method,arguments-differ,line-too-long

import json
import logging
import ssl
import sys

import paho.mqtt.client as mqtt
import toml

# Load config.toml file
try:
    CONFIG = toml.load('config.toml')['plugins']['output']
except (FileNotFoundError, KeyError):
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


class Plugin:
    '''The class that defined this file as a plugin. It is used by the main code to load the plugin'''
    PLUGIN_INFO = {
        'name': 'MQTT_OUTPUT',
        'type': 'OUTPUT'
    }

    # Define the MQTT Client
    MQTT_CLIENT = MQTTClass()

    # def __init__(self, config):
    #     print("CONFIG ",  config)

    def get_plugin_info(self):
        '''Method to return the plugin information data to the main class for initialisation'''
        return self.PLUGIN_INFO

    def create_output_class(self):
        '''Creates the MQTT client'''
        self.MQTT_CLIENT.will_set(f'{CONFIG["mqtt"]["base_topic"]}/status', payload="offline", qos=2, retain=True)
        mqtt_rc = self.MQTT_CLIENT.run()
        logging.info("mqtt_rc: %s", str(mqtt_rc))

    def output_json(self, topic, json_payload, qos=CONFIG['mqtt']['pub_qos'], retain=CONFIG['mqtt']['retain']):
        '''Publish JSON data to a specified MQTT topic'''
        self.MQTT_CLIENT.publish(f'{CONFIG["mqtt"]["base_topic"]}/{topic}', json.dumps(json_payload),
                                 qos=qos, retain=retain)
