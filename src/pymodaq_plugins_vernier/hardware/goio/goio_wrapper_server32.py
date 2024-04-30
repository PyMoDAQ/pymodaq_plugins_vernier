from dataclasses import dataclass
import os
import sys
import ctypes
from ctypes import c_int, c_uint8, byref
from pathlib import Path
import time
from typing import Union, Optional, List
from msl.loadlib import Server32
from enum import Enum

here = Path(__file__).parent
dll_path = here.joinpath('win32')

os.add_dll_directory(str(dll_path.absolute().resolve()))


class BaseEnum(Enum):
    """Enum to be used within pymodaq with some utility methods"""

    @classmethod
    def names(cls) -> List[str]:
        """Returns all the names of the enum"""
        return list(cls.__members__.keys())

    @classmethod
    def values(cls) -> List[str]:
        """Returns all the names of the enum"""
        return [cls[name].value for name in cls.names()]

    def __eq__(self, other: Union[str, Enum]):
        """testing for equality using the enum name"""
        if isinstance(other, str):
            if other == self.name:
                return True
        return super().__eq__(other)


def enum_checker(enum: BaseEnum, item: Union[BaseEnum, str]):
    """Check if the item parameter is a valid enum or at least one valid string name of the enum

    If a string, transforms it to a valid enum (case not important)

    Parameters
    ----------
    enum: BaseEnum class or one of its derivated class

    item: str or BaseEnum instance

    Returns
    -------
    BaseEnum class or one of its derivated class
    """

    if not isinstance(item, enum):
        if not isinstance(item, str):
            raise ValueError(f'{item} is an invalid {enum}. Should be a {enum} enum or '
                             f'a string in {enum.names()}')
        for ind, name in enumerate(enum.names()):
            if item.lower() == name.lower():
                item = enum[name]
                break
        else:
            raise ValueError(f'{item} is an invalid {enum}. Should be a {enum} enum or '
                             f'a string in {enum.names()}')
    return item


class VendorID(BaseEnum):
    Vernier = 0x08F7


class ProductID(BaseEnum):
    Default = 0x0001
    GoTemp = 0x0002  # GoTemp
    GoLink = 0x0003  # GoLink
    GoMotion = 0x0004  # GoMotion
    LabQuest = 0x0005


@dataclass
class SensorInfo:
    handle: int
    name: str
    vendor: VendorID
    product: ProductID


class SensorCommand(BaseEnum):
    NONE = 0
    GET_STATUS = 0x10
    START_MEASUREMENTS = 0x18
    STOP_MEASUREMENTS = 0x19
    INIT = 0x1A
    SET_MEASUREMENT_PERIOD = 0x1B
    GET_MEASUREMENT_PERIOD = 0x1C
    SET_LED_STATE = 0x1D
    GET_LED_STATE = 0x1E
    GET_SERIAL_NUMBER = 0x20
    GET_SENSOR_ID = 0x28
    SET_ANALOG_INPUT_CHANNEL = 0x29
    GET_ANALOG_INPUT_CHANNEL = 0x2A


class SensorStatus(BaseEnum):
    SUCCESS = 0
    NOT_READY_FOR_NEW_CMD = 0x30
    CMD_NOT_SUPPORTED = 0x31
    INTERNAL_ERROR1 = 0x32
    INTERNAL_ERROR2 = 0x33
    ERROR_CANNOT_CHANGE_PERIOD_WHILE_COLLECTING = 0x34
    ERROR_CANNOT_READ_NV_MEM_BLK_WHILE_COLLECTING_FAST = 0x35
    ERROR_INVALID_PARAMETER = 0x36
    ERROR_CANNOT_WRITE_FLASH_WHILE_COLLECTING = 0x37
    ERROR_CANNOT_WRITE_FLASH_WHILE_HOST_FIFO_BUSY = 0x38
    ERROR_OP_BLOCKED_WHILE_COLLECTING = 0x39
    ERROR_CALCULATOR_CANNOT_MEASURE_WITH_NO_BATTERIES = 0x3A
    ERROR_SLAVE_POWERUP_INIT = 0x40
    ERROR_SLAVE_POWERRESTORE_INIT = 0x41
    ERROR_COMMUNICATION = 0xF0


@dataclass
class SensorErrorStatus:
    last_command: SensorCommand
    last_status: SensorStatus
    last_command_with_error: SensorCommand
    last_error: SensorStatus


class GoIOError(Exception):
    pass


class LEDColor(BaseEnum):
    BLACK = 0xC0
    RED = 0x40
    GREEN = 0x80
    RED_GREEN = 0


class LEDBrightness(BaseEnum):
    BRIGHTNESS_MIN = 0
    BRIGHTNESS_MAX = 0x10
    OrangeLedBrightness = 4


class ProbeType(BaseEnum):
    kProbeTypeNoProbe = 0
    kProbeTypeAnalog5V = 2
    kProbeTypeAnalog10V = 3
    kProbeTypeHeatPulser = 4
    kProbeTypeAnalogOut = 5
    kProbeTypeMD = 6
    kProbeTypePhotoGate = 7
    kProbeTypeDigitalCount = 10
    kProbeTypeRotary = 11
    kProbeTypeDigitalOut = 12
    kProbeTypeLabquestAudio = 13
    kNumProbeTypes = 14


class DefaultResponse(ctypes.Structure):
    _fields_ = [('status', c_uint8)]


class LEDParam(ctypes.Structure):
    _fields_ = [("color", c_uint8),
                ("brightness", c_uint8)]

    def __repr__(self):
        return (f'{self.__class__.__name__}: <color: {LEDColor(self.color)}> '
                f'<brightness: {LEDBrightness(self.brightness)}>')


class GoIOWrapper32(Server32):

    def __init__(self, host, port, **kwargs):
        super().__init__(
            str(dll_path.absolute().resolve().joinpath('GoIO_DLL.dll')), 'cdll', host, port)

    def __enter__(self):
        self.open_library()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_library()

    def open_library(self):
        res = self.lib.GoIO_Init()
        if res != 0:
            raise GoIOError('Library opening failed')

    def close_library(self):
        res = self.lib.GoIO_Uninit()
        if res != 0:
            raise GoIOError('Library closing failed')

    def get_version(self) -> str:
        major = ctypes.c_uint16(0)
        minor = ctypes.c_uint16()
        patch = ctypes.c_uint16()
        res = self.lib.GoIO_GetDLLVersion(byref(minor), byref(patch))
        if res != 0:
            raise GoIOError('Incorrect version query')
        return f'{major.value}.{minor.value}.{patch.value}'

    def get_connected_products(self, product: Union[ProductID, str]) -> int:
        """ Get the number of connected product by name

        Parameters
        ----------
        product: one of the ProductID enum name

        Returns
        -------
        int: he number of connected device of this type
        """
        product = enum_checker(ProductID, product)
        return self.lib.GoIO_UpdateListOfAvailableDevices(VendorID.Vernier.value, product.value)

    def get_device_by_index(self, product: Union[ProductID, str], index: int = 0) -> str:
        product = enum_checker(ProductID, product)
        n_products = self.get_connected_products(product)
        device = ctypes.create_string_buffer(256)
        if index < n_products:

            self.lib.GoIO_GetNthAvailableDeviceName(byref(device), 256,
                                                     VendorID.Vernier.value, product.value, index)
        return device.value.decode()

    def get_devices(self, product: Union[str, ProductID]) -> List[str]:
        n_devices = self.get_connected_products(product)
        devices = []
        for ind in range(n_devices):
            devices.append(self.get_device_by_index(product, ind))
        return devices

    def open_sensor(self, device_id: str, product: Union[ProductID, str]) -> SensorInfo:
        product = enum_checker(ProductID, product)
        device = ctypes.create_string_buffer(device_id.encode())

        handle = self.lib.GoIO_Sensor_Open(byref(device), VendorID.Vernier.value,
                                            product.value, 1)
        return SensorInfo(handle, device.value.decode(), VendorID.Vernier, product)

    def close_sensor(self, handle: int) -> int:
        res = self.lib.GoIO_Sensor_Close(handle)
        return res

    def clear_sensor(self, handle: int) -> int:
        res = self.lib.GoIO_Sensor_ClearIO(handle)
        return res

    def get_sensor_info(self, handle) -> SensorInfo:
        vendor = c_int()
        product = c_int()
        device = ctypes.create_string_buffer(256)

        res = self.lib.GoIO_Sensor_GetOpenDeviceName(handle, byref(device), 256,
                                                      byref(vendor), byref(product))

        if res != 0:
            raise GoIOError(f'Get Sensor Info returned with error {res}')

        return SensorInfo(handle, device.value.decode(), VendorID(vendor.value),
                          ProductID(product.value))

    def send_command_get_response(
            self, handle: int, command: Union[SensorCommand, str],
            parameter: Optional[Union[LEDParam]] = None,
            response: Optional[Union[DefaultResponse, LEDParam]] = None) -> \
            Union[DefaultResponse, LEDParam]:

        command = enum_checker(SensorCommand, command)
        command_char = c_uint8(command.value)

        parameter_len = 0 if parameter is None else ctypes.sizeof(parameter)
        response_len = 0 if response is None else ctypes.sizeof(response)

        res = self.lib.GoIO_Sensor_SendCmdAndGetResponse(
            handle, command_char,
            byref(parameter) if parameter is not None else None,
            parameter_len,
            byref(response) if response is not None else None,
            byref(c_int(response_len)) if response is not None else None, 1000)

        if res != 0:
            raise GoIOError(f'Command {command.name} returned with error {res}')

        return response

    def get_status(self, handle: int) -> SensorStatus:
        command = SensorCommand['GET_STATUS']
        response = DefaultResponse()
        self.send_command_get_response(handle, command, response=response)
        return SensorStatus(response.status)

    def get_response_status(self, handle: int, ) -> SensorErrorStatus:

        last_command = c_uint8()
        last_status = c_uint8()

        last_command_with_error = c_uint8()
        last_error = c_uint8()

        res = self.lib.GoIO_Sensor_GetLastCmdResponseStatus(handle,
                                                             byref(last_command),
                                                             byref(last_status),
                                                             byref(last_command_with_error),
                                                             byref(last_error))
        if res != 0:
            raise GoIOError(f'Status could not be fetched')

        return SensorErrorStatus(SensorCommand(last_command.value),
                                 SensorStatus(last_status.value),
                                 SensorCommand(last_command_with_error.value),
                                 SensorStatus(last_error.value))

    def get_led_status(self, handle):
        command = SensorCommand['GET_LED_STATE']
        response = LEDParam()

        self.send_command_get_response(handle, command, None, response)
        return response

    def set_led(self, handle: int, color: Union[str, LEDColor] = LEDColor.GREEN,
                brightness: Union[str, LEDBrightness] = LEDBrightness.BRIGHTNESS_MAX):

        command = SensorCommand['SET_LED_STATE']
        color = enum_checker(LEDColor, color)
        brightness = enum_checker(LEDBrightness, brightness)
        led_param = LEDParam(color.value, brightness.value)
        led_response = LEDParam()

        self.send_command_get_response(handle, command, led_param, led_response)
        return led_response

    def start(self, handle):
        command = SensorCommand['START_MEASUREMENTS']
        self.send_command_get_response(handle, command)

    def stop(self, handle):
        command = SensorCommand['STOP_MEASUREMENTS']
        self.send_command_get_response(handle, command)

    def get_n_available_measurements(self, handle):
        """ Get the available number of measurements in the buffer"""
        return self.lib.GoIO_Sensor_GetNumMeasurementsAvailable(handle)

    def read_raw(self, handle) -> list:
        """ Get all stored measurements from the buffer"""
        max_count = self.get_n_available_measurements(handle)
        data = (c_int * max_count)()
        self.lib.GoIO_Sensor_ReadRawMeasurements(handle, byref(data), max_count)
        return list(data)

    def read_raw_latest(self, handle) -> int:
        """ Get the last stored measurement from the buffer, then clears it"""
        return self.lib.GoIO_Sensor_GetLatestRawMeasurement(handle)

    def raw_to_voltage(self, handle, raw_data: int) -> float:
        """ Convert raw integer data into a voltage data """
        return self.lib.GoIO_Sensor_ConvertToVoltage(handle, raw_data)

    def volt_to_calibrated(self, handle, volt_data: float) -> float:
        """ Convert a voltage data into a calibrated one

        Units depend on the connected sensor
        """
        return self.lib.GoIO_Sensor_CalibrateData(handle, ctypes.c_float(volt_data))

    def raw_to_calibrated(self, handle: int, raw_data: int) -> float:
        return self.volt_to_calibrated(handle, self.raw_to_voltage(handle, raw_data))

    def get_probe_type(self, handle: int):
        return ProbeType(self.lib.GoIO_Sensor_GetProbeType(handle))


if __name__ == '__main__':

    with GoIOWrapper() as goio:
        print(goio.get_version())
        print(goio.get_connected_products('GoLink'))
        dev = goio.get_device_by_index('GoLink', 0)
        print(dev)
        sensor = goio.open_sensor(dev, 'GoLink')
        print(sensor)
        print(goio.clear_sensor(sensor.handle))
        print(goio.get_sensor_info(sensor.handle))
        print(goio.get_probe_type(sensor.handle))

        try:
            print(goio.get_status(sensor.handle))
            print(goio.get_led_status(sensor.handle))
            print(goio.set_led(sensor.handle))
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

        except Exception as e:
            print(goio.get_response_status(sensor.handle))

        goio.stop(sensor.handle)
        print(goio.close_sensor(sensor.handle))
