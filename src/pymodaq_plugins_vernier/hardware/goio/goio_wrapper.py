from dataclasses import dataclass
import os
import sys
import ctypes
from pathlib import Path

from typing import Union, Optional

from packaging.version import Version, parse

from pymodaq.utils.enums import BaseEnum, enum_checker
dll_path = Path('../goio')
os.add_dll_directory(str(dll_path.absolute()))



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


@dataclass
class SensorStatus:
    last_command: str
    last_status: int

    last_command_with_error = str
    last_error: int


class GoIOError(Exception):
    pass


class SensorCommand(BaseEnum):
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


class LEDColor(BaseEnum):
    BLACK = 0xC0
    RED = 0x40
    GREEN = 0x80
    RED_GREEN = 0


class LEDBrightness(BaseEnum):
    BRIGHTNESS_MIN = 0
    BRIGHTNESS_MAX = 0x10

class DefaultResponse(ctypes.Structure):
    _fields_ = [('status', ctypes.c_uint8)]


class LEDParam(ctypes.Structure):
    _fields_ = [("color", ctypes.c_uint8),
               ("brightness", ctypes.c_uint8)]




class GoIOWrapper:
    def __init__(self):
        self._dll = ctypes.WinDLL('GoIO_DLL.dll')

    def __enter__(self):
        self.open_library()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_library()

    def open_library(self):
        res = self._dll.GoIO_Init()
        if res != 0:
            raise GoIOError('Library opening failed')

    def close_library(self):
        res = self._dll.GoIO_Uninit()
        if res != 0:
            raise GoIOError('Library closing failed')

    def get_version(self):
        major = ctypes.c_uint16(0)
        minor = ctypes.c_uint16()
        patch = ctypes.c_uint16()
        res = self._dll.GoIO_GetDLLVersion(ctypes.byref(minor), ctypes.byref(patch))
        if res != 0:
            raise GoIOError('Incorrect version query')
        return Version(f'{major.value}.{minor.value}.{patch.value}')

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
        return self._dll.GoIO_UpdateListOfAvailableDevices(VendorID.Vernier.value, product.value)

    def get_device_by_index(self, product: Union[ProductID, str], index: int = 0) -> str:
        product = enum_checker(ProductID, product)
        n_products = self.get_connected_products(product)
        device = ctypes.create_string_buffer(256)
        if index < n_products:

            self._dll.GoIO_GetNthAvailableDeviceName(ctypes.byref(device), 256,
                                                     VendorID.Vernier.value, product.value, index)
        return device.value.decode()

    def open_sensor(self, device_id: str, product: Union[ProductID, str]) -> SensorInfo:
        product = enum_checker(ProductID, product)
        device = ctypes.create_string_buffer(device_id.encode())

        handle = self._dll.GoIO_Sensor_Open(ctypes.byref(device), VendorID.Vernier.value,
                                            product.value, 1)
        return SensorInfo(handle, device.value.decode(), VendorID.Vernier, product)

    def close_sensor(self, handle: int):
        res = self._dll.GoIO_Sensor_Close(handle)
        return res

    def clear_sensor(self, handle: int):
        res = self._dll.GoIO_Sensor_ClearIO(handle)
        return res

    def send_command(self, handle: int, command: Union[SensorCommand, str],
                     parameter: Optional[Union[LEDParam]] = None,
                     response: Optional[Union[DefaultResponse, LEDParam]] = None):
        command = enum_checker(SensorCommand, command)
        command_char = ctypes.c_uint8(command.value)

        param_pointer = ctypes.POINTER(ctypes.c_int)() if parameter is None\
            else ctypes.pointer(parameter)
        parameter_len = ctypes.sizeof(param_pointer)

        response_pointer = ctypes.POINTER(ctypes.c_int)() if response is None\
            else ctypes.pointer(response)
        response_len = ctypes.sizeof(response)

        res = self._dll.GoIO_Sensor_SendCmdAndGetResponse(handle, command_char,
                                                          param_pointer,
                                                          parameter_len,
                                                          response_pointer,
                                                          response_len, 1000)
        if res != 0:
            raise GoIOError(f'Command {command.name} returned with error {res}')

    def get_status(self, handle: int):
        command = SensorCommand['GET_STATUS']
        response = DefaultResponse(-1)
        self.send_command(handle, command, response=response)


    def get_response_status(self, handle: int, ) -> SensorStatus:

        last_command = ctypes.c_uint8()
        last_status = ctypes.c_uint8()

        last_command_with_error = ctypes.c_uint8()
        last_error = ctypes.c_uint8()

        res = self._dll.GoIO_Sensor_GetLastCmdResponseStatus(handle,
                                                             ctypes.byref(last_command),
                                                             ctypes.byref(last_status),
                                                             ctypes.byref(last_command_with_error),
                                                             ctypes.byref(last_error))
        if res != 0:
            raise GoIOError(f'Status could not be fetched')

        return SensorStatus(SensorCommand(last_command.value), last_status.value,
                            SensorCommand(last_command_with_error.value), last_error.value)

    def get_led_status(self, handle):
        command = SensorCommand['GET_LED_STATE']

    def blink_led(self, handle: int, do_blink: bool = True, color: LEDColor = LEDColor.GREEN,
                  brightness: LEDBrightness = LEDBrightness.BRIGHTNESS_MAX):

        command = SensorCommand['SET_LED_STATE']
        color = enum_checker(LEDColor, color)
        brightness = enum_checker(LEDBrightness, brightness)
        led_param = LEDParam(color.value, brightness.value)
        led_response = DefaultResponse()

        self.send_command(handle, command, led_param, led_response)


#
#
# class GoIO:
#
#     def close(self):
#         self.goio.Uninit()
#
#     def __enter__(self):
#         return self
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         self.close()
#
#     @property
#     def version(self):
#         return Version('.'.join([str(x) for x in self.goio.GetDLLVersion()]))
#
#     def get_connected_products(self, product: Union[ProductID, str]) -> int:
#         """ Get the number of connected product by name
#
#         Parameters
#         ----------
#         product: one of the ProductID enum name
#
#         Returns
#         -------
#         int: he number of connected device of this type
#         """
#         product = enum_checker(ProductID, product)
#         return self.goio.UpdateListOfAvailableDevices(VendorID.Vernier.value, product.value)
#
#     def _get_device_by_index(self, product: Union[ProductID, str], index: int = 0):
#         product = enum_checker(ProductID, product)
#         self.get_connected_products(product)
#         device = StringBuilder('', self.goio.MAX_SIZE_SENSOR_NAME)
#         self.goio.GetNthAvailableDeviceName(device, self.goio.MAX_SIZE_SENSOR_NAME,
#                                              product, index)
#         return str(device)
#
#     def get_sensor(self, id_str: str, product: Union[ProductID, str]):
#         product = enum_checker(ProductID, product)
#         handle = self.goio.Sensor_Open(id_str, VendorID.Vernier.value, product.value, 0)
#         return Sensor(self, handle)
#
#
# class Sensor:
#     def __init__(self, parent: GoIO, handle: int):
#         self.goio = parent.goio
#         self._handle = handle
#
#


if __name__ == '__main__':

    with GoIOWrapper() as goio:
        print(goio.get_version())
        print(goio.get_connected_products('GoLink'))
        dev = goio.get_device_by_index('GoLink', 0)
        print(dev)
        sensor = goio.open_sensor(dev, 'GoLink')
        print(sensor)
        print(goio.clear_sensor(sensor.handle))
        # try:
        #     goio.get_status(sensor.handle)
        #     goio.blink_led(sensor.handle)
        #     print(goio.get_response_status(sensor.handle))
        # except Exception as e:
        #     print(goio.get_response_status(sensor.handle))

        print(goio.close_sensor(sensor.handle))
