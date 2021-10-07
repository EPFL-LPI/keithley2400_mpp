import time
import logging

import numpy as np
from pymeasure.log import console_log
from pymeasure.instruments.keithley import Keithley2400
from pymeasure.experiment import (
    Parameter,
    BooleanParameter,
    FloatParameter,
    IntegerParameter
)

from .keithley2400_procedure import Keithley2400_Procedure


# setup logging
log_level = logging.DEBUG

log = logging.getLogger( __name__ )
log.addHandler( logging.NullHandler() )
console_log( log, level = log_level )
log.debug( 'Debug logging enabled.' )


class JVScan_Procedure( Keithley2400_Procedure ):
    """
    Procedure for JV Scan.

    :param start_voltage: Starting voltage [V]. [Default: 0]
    :param end_voltage: Ending voltage [V]. [Default: 1]
    :param voltage_step: Voltage step [V]. [Default: 0.01]
    :param settle_time: Time to settle before measuring at each set voltage [s]. [Default: 0.1]
    :param max_current: Maximum current [mA]. [Default: 10]
    :param buffer_points: Number of points to average over at each set voltage. [Default: 10]
    :param full_sweep: If True, perform start-end-start scan. [Default: True]
        If False, perform start-end scan only.
    """

    # mpp parameters
    start_voltage       = FloatParameter( 'Start voltage',  units = 'V',    default = 0 )
    end_voltage         = FloatParameter( 'End voltage',    units = 'V',    default = 1 )
    voltage_step        = FloatParameter( 'Voltage step',   units = 'V',    default = 0.01 )
    settle_time         = FloatParameter( 'Settle time',    units = 's',    default = 0.1 )  # settle time at each voltage point.
    max_current         = FloatParameter( 'Max current',    units = 'mA',   default = 10 )
    buffer_points       = IntegerParameter( 'Buffer points',                default = 10 )  # number of measurements for each data point.
    full_sweep          = BooleanParameter( 'Full scan',                    default = True )
    
    DATA_COLUMNS = [
        'voltage [V]', 'current [A]', 'power [W]'
    ]


    def startup( self ):
        """
        Initializes the instrument and variables.
        """
        super().startup()

        self.instrument.write( ':format:data ascii' )
        self.instrument.apply_voltage(
            compliance_current = self.max_current/ 1e3  # convert from mA to A
        )

        # set elements
        log.debug( 'Setting elements.' )
        self.instrument.write( ':format:elements volt,curr' )
        self.__elements = self._get_elements()

        # sweep parameters
        log.debug( 'Setting sweep parameters.' )
        self.voltage_step + self.voltage_step
        self.voltage_step* 2
        # self.test

        self.instrument.write( f':source:voltage:start {self.start_voltage}' )
        self.instrument.write( f':source:voltage:stop {self.end_voltage}' )
        self.instrument.write( f':source:voltage:step {self.voltage_step}' )
        self.instrument.write(  ':source:voltage:mode sweep' )  # set sweep mode
        self.instrument.write(  ':source:sweep:spacing linear' )  # set to linear sweep

        sweep_points = self.instrument.ask( ':source:sweep:points?' )
        self.instrument.write( f':trigger:count {sweep_points}' )


    def execute( self ):
        """
        Begin JV scan.
        """
        super().execute()

        self.instrument.enable_source()

        self._sweep()
        # if self.full_sweep:
        #     self._sweep( -1 )


    def _sweep( self, direction = 1 ):
        """
        Perform a single sweep.

        :param direction: If 1 sweep from start to end,
            if -1 sweep from end to start.
        """
        log.debug( '#_sweep' )

        # set sweep direciton
        if direction == 1:
            # sweep start to end
            self.instrument.write( ':source:sweep:direction up' )
            log.debug( 'Performing sweep up.' )

        elif direction == -1:
            # sweep end to start
            self.instrument.write( ':source:sweep:direction down' )
            log.debug( 'Performing sweep down.' )
            
        else:
            raise ValueError( 'Direction must be +1 or -1.' )

        # initialize sweep
        log.debug( 'Initializing sweep' )
        
        data = self.instrument.ask( 'read?' )
        data = self._format_data( data )

        for datum in data:
            voltage = datum[ self.elements.index( 'VOLT' ) ]
            current = datum[ self.elements.index( 'CURR' ) ]
            power = current* voltage

            self.emit( 'results', {
                'voltage [V]': voltage,
                'current [A]': current,
                'power [W]':   power
            } )
