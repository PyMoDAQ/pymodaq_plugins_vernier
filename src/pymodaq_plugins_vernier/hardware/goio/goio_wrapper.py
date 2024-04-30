import time
from typing import Union, Optional, List

from pymodaq_plugins_vernier.hardware.goio.goio_wrapper_client64 import (
    GoIOWrapper64, ProductID, SensorInfo)


class Sensor:
    def __init__(self, goiowrapper: GoIOWrapper64 = None):
        self._goio: GoIOWrapper64 = goiowrapper
        self._handle: int = None

    def init_library(self):
        self._goio = GoIOWrapper64()
        self._goio.open_library()

    @property
    def goio(self):
        return self._goio

    def get_devices(self, product: Union[str, ProductID]) -> List[str]:
        return self._goio.get_devices(product)

    def open(self, device: str, product: Union[str, ProductID]) -> SensorInfo:
        sensor_info: SensorInfo = self._goio.open_sensor(device, product)
        self._handle = sensor_info.handle
        return sensor_info

    def close(self):
        if self._handle is not None:
            self._goio.close_sensor(self._handle)

    def clear(self):
        if self._handle is not None:
            self._goio.clear_sensor(self._handle)

    def start(self):
        if self._handle is not None:
            self._goio.start(self._handle)

    def stop(self):
        if self._handle is not None:
            self._goio.stop(self._handle)

    def get_last_measurement(self):
        if self._handle is not None:
            return self._goio.read_raw_latest(self._handle)

    def get_all_measurements(self):
        if self._handle is not None:
            return self._goio.read_raw(self._handle)


