from dataclasses import dataclass
import os
import sys
import ctypes
from ctypes import c_int, c_uint8, byref
from pathlib import Path
import time
from typing import Union, Optional, List
import numpy as np
from packaging.version import Version, parse
from msl.loadlib import Client64

from pymodaq_plugins_vernier.hardware.goio.goio_wrapper_server32 import (
    VendorID, ProductID, SensorInfo, SensorCommand, SensorStatus,
    SensorErrorStatus, GoIOError, LEDColor, LEDBrightness,
    LEDParam, ProbeType, DefaultResponse, enum_checker)

here = Path(__file__).parent


class GoIOWrapper64(Client64):

    def __init__(self):
        super().__init__(module32=str(here.joinpath('goio_wrapper_server32.py')),
                         append_sys_path=str(here))

    def __enter__(self):
        self.open_library()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_library()

    def open_library(self):
        return self.request32('open_library')

    def close_library(self):
        return self.request32('close_library')

    def get_version(self) -> Version:
        return Version(self.request32('get_version'))

    def get_connected_products(self, product: Union[ProductID, str]) -> int:
        """ Get the number of connected product by name

        Parameters
        ----------
        product: one of the ProductID enum name

        Returns
        -------
        int: the number of connected device of this type
        """
        return self.request32('get_connected_products', product)

    def get_device_by_index(self, product: Union[ProductID, str], index: int = 0) -> str:
        return self.request32('get_device_by_index', product, index)

    def get_devices(self, product: Union[str, ProductID]) -> List[str]:
        return self.request32('get_devices', product)

    def open_sensor(self, device_id: str, product: Union[ProductID, str]) -> SensorInfo:
        return self.request32('open_sensor', device_id, product)

    def close_sensor(self, handle: int) -> int:
        return self.request32('close_sensor', handle)

    def clear_sensor(self, handle: int) -> int:
        return self.request32('clear_sensor', handle)

    def get_sensor_info(self, handle) -> SensorInfo:
        return self.request32('get_sensor_info', handle)

    def send_command_get_response(
            self, handle: int, command: Union[SensorCommand, str],
            parameter: Optional[Union[LEDParam]] = None,
            response: Optional[Union[DefaultResponse, LEDParam]] = None) -> \
            Union[DefaultResponse, LEDParam]:
        return self.request32('send_command_get_response', handle, command, parameter,
                              response)

    def get_status(self, handle: int) -> SensorStatus:
        return self.request32('get_status', handle)

    def get_response_status(self, handle: int, ) -> SensorErrorStatus:
        return self.request32('get_response_status', handle)

    def get_led_status(self, handle):
        return self.request32('get_led_status', handle)

    def set_led(self, handle: int, color: Union[str, LEDColor] = LEDColor.GREEN,
                brightness: Union[str, LEDBrightness] = LEDBrightness.BRIGHTNESS_MAX):
        return self.request32('set_led', handle, color, brightness)

    def start(self, handle):
        return self.request32('start', handle)

    def stop(self, handle):
        return self.request32('stop', handle)

    def get_n_available_measurements(self, handle):
        """ Get the available number of measurements in the buffer"""
        return self.request32('get_n_available_measurements', handle)

    def read_raw(self, handle) -> np.ndarray:
        """ Get all stored measurements from the buffer"""
        return np.array(self.request32('read_raw', handle))

    def read_raw_latest(self, handle) -> int:
        """ Get the last stored measurement from the buffer, then clears it"""
        return self.request32('read_raw_latest', handle)

    def raw_to_voltage(self, handle, raw_data: int) -> float:
        """ Convert raw integer data into a voltage data """
        return self.request32('raw_to_voltage', handle)

    def volt_to_calibrated(self, handle, volt_data: float) -> float:
        """ Convert a voltage data into a calibrated one

        Units depend on the connected sensor
        """
        return self.request32('volt_to_calibrated', handle, volt_data)

    def raw_to_calibrated(self, handle: int, raw_data: int) -> float:
        return self.request32('raw_to_calibrated', handle, raw_data)

    def get_probe_type(self, handle: int):
        return self.request32('get_probe_type', handle)


if __name__ == '__main__':

    with GoIOWrapper64() as goio:
        print(goio.get_version())
        print(goio.get_connected_products('GoLink'))
        dev = goio.get_device_by_index('GoLink', 0)
        print(dev)
        sensor = goio.open_sensor(dev, 'GoLink')
        print(sensor)
        print(goio.clear_sensor(sensor.handle))
        print(goio.get_sensor_info(sensor.handle))
        print(goio.get_probe_type(sensor.handle))


        print(goio.get_status(sensor.handle))
        print(goio.get_led_status(sensor.handle))
        #print(goio.set_led(sensor.handle))
        print(goio.set_led(sensor.handle, color='RED', brightness='BRIGHTNESS_MAX'))
        print(goio.set_led(sensor.handle, color='RED', brightness='BRIGHTNESS_MIN'))
        print(goio.set_led(sensor.handle, color='GREEN', brightness='BRIGHTNESS_MAX'))

        print(f'Nmeasurements: {goio.get_n_available_measurements(sensor.handle)}')
        goio.start(sensor.handle)
        time.sleep(2)
        print(f'Nmeasurements: {goio.get_n_available_measurements(sensor.handle)}')
        print(goio.read_raw(sensor.handle))

        print(goio.read_raw_latest(sensor.handle))
        print(goio.raw_to_calibrated(sensor.handle, goio.read_raw_latest(sensor.handle)))

        goio.stop(sensor.handle)
        print(goio.close_sensor(sensor.handle))
