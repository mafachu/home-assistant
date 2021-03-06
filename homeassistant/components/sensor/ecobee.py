"""
homeassistant.components.sensor.ecobee
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Sensor platform for Ecobee sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.ecobee/
"""
import logging

from homeassistant.helpers.entity import Entity
from homeassistant.components import ecobee
from homeassistant.const import TEMP_FAHRENHEIT

DEPENDENCIES = ['ecobee']
SENSOR_TYPES = {
    'temperature': ['Temperature', TEMP_FAHRENHEIT],
    'humidity': ['Humidity', '%'],
    'occupancy': ['Occupancy', None]
}

_LOGGER = logging.getLogger(__name__)
ECOBEE_CONFIG_FILE = 'ecobee.conf'


def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Sets up the Ecobee sensors. """
    if discovery_info is None:
        return
    data = ecobee.NETWORK
    dev = list()
    for index in range(len(data.ecobee.thermostats)):
        for sensor in data.ecobee.get_remote_sensors(index):
            for item in sensor['capability']:
                if item['type'] not in ('temperature',
                                        'humidity', 'occupancy'):
                    continue

                dev.append(EcobeeSensor(sensor['name'], item['type'], index))

    add_devices(dev)


class EcobeeSensor(Entity):
    """ An Ecobee sensor. """

    def __init__(self, sensor_name, sensor_type, sensor_index):
        self._name = sensor_name + ' ' + SENSOR_TYPES[sensor_type][0]
        self.sensor_name = sensor_name
        self.type = sensor_type
        self.index = sensor_index
        self._state = None
        self._unit_of_measurement = SENSOR_TYPES[sensor_type][1]
        self.update()

    @property
    def name(self):
        """ Returns the name of the Ecobee sensor.. """
        return self._name.rstrip()

    @property
    def state(self):
        """ Returns the state of the device. """
        return self._state

    @property
    def unit_of_measurement(self):
        """ Unit of measurement this sensor expresses itself in. """
        return self._unit_of_measurement

    def update(self):
        """ Get the latest state of the sensor. """
        data = ecobee.NETWORK
        data.update()
        for sensor in data.ecobee.get_remote_sensors(self.index):
            for item in sensor['capability']:
                if (
                        item['type'] == self.type and
                        self.type == 'temperature' and
                        self.sensor_name == sensor['name']):
                    self._state = float(item['value']) / 10
                elif (
                        item['type'] == self.type and
                        self.type == 'humidity' and
                        self.sensor_name == sensor['name']):
                    self._state = item['value']
                elif (
                        item['type'] == self.type and
                        self.type == 'occupancy' and
                        self.sensor_name == sensor['name']):
                    self._state = item['value']
