"""
homeassistant.components.sensor.mfi
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Support for Ubiquiti mFi sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.mfi/
"""
import logging

from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD,
                                 TEMP_CELCIUS)
from homeassistant.components.sensor import DOMAIN
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import validate_config

REQUIREMENTS = ['mficlient==0.2']

_LOGGER = logging.getLogger(__name__)

SENSOR_MODELS = [
    'Ubiquiti mFi-THS',
    'Ubiquiti mFi-CS',
    'Outlet',
]


# pylint: disable=unused-variable
def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Sets up mFi sensors. """

    if not validate_config({DOMAIN: config},
                           {DOMAIN: ['host',
                                     CONF_USERNAME,
                                     CONF_PASSWORD]},
                           _LOGGER):
        _LOGGER.error('A host, username, and password are required')
        return False

    host = config.get('host')
    port = int(config.get('port', 6443))
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    from mficlient.client import MFiClient

    try:
        client = MFiClient(host, username, password, port=port)
    except client.FailedToLogin as ex:
        _LOGGER.error('Unable to connect to mFi: %s', str(ex))
        return False

    add_devices(MfiSensor(port, hass)
                for device in client.get_devices()
                for port in device.ports.values()
                if port.model in SENSOR_MODELS)


class MfiSensor(Entity):
    """ An mFi sensor that exposes tag=value. """

    def __init__(self, port, hass):
        self._port = port
        self._hass = hass

    @property
    def name(self):
        return self._port.label

    @property
    def state(self):
        return self._port.value

    @property
    def unit_of_measurement(self):
        if self._port.tag == 'temperature':
            return TEMP_CELCIUS
        elif self._port.tag == 'active_pwr':
            return 'Watts'
        return self._port.tag

    def update(self):
        self._port.refresh()
