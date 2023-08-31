import paho.mqtt.client as mqtt
from dataclasses import dataclass
from pyowm.owm import OWM
from enum import Enum
from threading import Event
import signal
import json
import time
import sys
import os

MQTT_BROKER = os.getenv('MQTT_BROKER', default='127.0.0.1')
MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', default='1883'))
MQTT_SUBSCRIBER_ID = os.getenv('MQTT_SUBSCRIBER_ID', default='enmon_weather')
REPORTING_INTERVAL = int(os.getenv('REPORTING_INTERVAL', default='900'))
OWM_API_KEY = os.getenv('OWM_API_KEY')

WeatherCondition = Enum('WeatherCondition',
	['UNKNOWN', 'SUN', 'FEW_CLOUDS', 'CLOUDS', 'RAIN', 'THUNDERSTORM', 'NIGHT'])

@dataclass
class PlantWeatherProvider:
	TIMEOUT = 3600

	__weather_manager = OWM(OWM_API_KEY).weather_manager()
	def __update_weather(self):
		self.weather = PlantWeatherProvider.__weather_manager.weather_at_coords(
			self.__longitude, self.__latitude).weather

	def __is_night(self):
		return not(self.weather.srise_time < self.weather.ref_time < self.weather.sset_time)

	def __weather_condition(self):
		if self.__is_night():
			return WeatherCondition.NIGHT
		elif 200 <= self.weather.weather_code < 300:
			return WeatherCondition.THUNDERSTRM
		elif 300 <= self.weather.weather_code < 700:
			return WeatherCondition.RAIN
		elif 701 <= self.weather.weather_code < 800 or 802 <= self.weather.weather_code < 900:
			return WeatherCondition.CLOUDS
		elif 801 == self.weather.weather_code:
			return WeatherCondition.FEW_CLOUDS
		elif 800 == self.weather.weather_code:
			return WeatherCondition.SUN
		else:
			return WeatherCondition.UNKNOWN

	def __weather_temperature(self):
		return round(self.weather.temperature('celsius')['temp'])

	def __timed_out(self):
		return (time.time() - self.__last_alive) > PlantWeatherProvider.TIMEOUT

	def keep_alive(self):
		print('KEEPALIVE', self.__enmon_id)
		self.__last_alive = time.time()

	def report_weather(self, client):
		if self.__timed_out():
			return
		try:
			self.__update_weather()
			condition = self.__weather_condition()
			report = json.dumps({
				'code': condition.value,
				'tag': condition.name,
				'temperature': self.__weather_temperature(),
			})
			client.publish(self.__topic, report, qos=1, retain=True)
			print('REPORT', self.__enmon_id)
		except Exception as ex:
			print(f'FAIL {self.__enmon_id}: {ex}')

	def __init__(self, enmon_id, longitude, latitude):
		self.__enmon_id = enmon_id
		self.__longitude, self.__latitude = longitude, latitude
		self.__last_alive = time.time()
		self.__topic = f'enmon/{enmon_id}/weather'


def main():
	weather_providers = {}

	# setup exit handler
	exit = Event()
	def sigint_handler(signal, frame):
		exit.set()
	signal.signal(signal.SIGINT, sigint_handler)

	# setup MQTT
	client = mqtt.Client(client_id=MQTT_SUBSCRIBER_ID)
	# register plants on enmon info
	def on_enmon_info(client, userdata, message):
		enmon_id = message.topic.split('/')[1]
		info = json.loads(message.payload.decode("utf-8"))
		if not 'longitude' in info or not 'latitude' in info:
			return

		provider = PlantWeatherProvider(enmon_id,
			float(info['longitude']),
			float(info['latitude']))
		weather_providers[enmon_id] = provider

		# register weather provider
		client.subscribe('enmon/+/status', qos=0)
		client.message_callback_add('enmon/+/status',
			lambda client, userdata, message: provider.keep_alive())
		print(f'REGISTER {enmon_id}')

		# send initial weather report
		provider.report_weather(client)


	def on_connect(client, userdata, flags, rc):
		print('MQTT connected, rc =', rc)
		client.subscribe('enmon/+/info', qos=1)
		client.message_callback_add('enmon/+/info', on_enmon_info)

	client.on_connect = on_connect
	client.connect_async(MQTT_BROKER, MQTT_BROKER_PORT, 60)

	client.loop_start()
	while not exit.is_set():
		if client.is_connected():
			for provider in weather_providers.values():
				provider.report_weather(client)
		exit.wait(REPORTING_INTERVAL)

	print('Exit ...')
	client.loop_stop()
	client.disconnect()


if __name__ == '__main__':
	main()
