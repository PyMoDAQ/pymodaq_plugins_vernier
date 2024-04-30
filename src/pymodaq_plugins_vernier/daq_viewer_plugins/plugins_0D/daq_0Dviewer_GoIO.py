import numpy as np
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins, DataToExport
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter

from pymodaq_plugins_vernier.hardware.goio.goio_wrapper import Sensor, GoIOWrapper64

with GoIOWrapper64() as goio:
    version = goio.get_version()
    devices = goio.get_devices('GoLink')


class DAQ_0DViewer_GoIO(DAQ_Viewer_base):
    """ Instrument plugin class for a OD viewer.
    
    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Viewer module through inheritance via
    DAQ_Viewer_base. It makes a bridge between the DAQ_Viewer module and the Python wrapper of a particular instrument.

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.
         
    """
    params = comon_parameters+[
        {'title': 'Device', 'name': 'device', 'type': 'list', 'value': devices[0],
         'limits': devices}
        ]

    def ini_attributes(self):
        self.controller: Sensor = None
        self._running = True

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        ## TODO for your custom plugin
        if param.name() == "a_parameter_you've_added_in_self.params":
           pass

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator/detector by controller
            (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        self.ini_detector_init(old_controller=controller,
                               new_controller=Sensor())

        if self.settings['controller_status'] == 'Master':
            self.controller.init_library()

        sensor_info = self.controller.open(self.settings['device'], 'GoLink')

        info = str(sensor_info)
        initialized = True
        return info, initialized

    def close(self):
        self.controller.close()

    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging (if hardware averaging is possible, self.hardware_averaging should be set to
            True in class preamble and you should code this implementation)
        kwargs: dict
            others optionals arguments
        """
        if not self._running:
            self.controller.start()
            self._running = True

        data_array = np.array([self.controller.get_last_measurement()])

        self.dte_signal.emit(
            DataToExport(name='myplugin',
                         data=[
                             DataFromPlugins(name='GoLink', data=[data_array],
                                             dim='Data0D', labels=[''])]))

    def stop(self):
        self._running = False
        self.controller.stop()


if __name__ == '__main__':
    main(__file__, init=False)
