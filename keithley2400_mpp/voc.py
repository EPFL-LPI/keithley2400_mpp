# Voc

import time
import logging

import numpy as np
from pymeasure.log import console_log
from pymeasure.experiment import (
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


class Voc_Procedure( Keithley2400_Procedure ):
    """
    Determines Voc.

    Data: [ time, voltage, current ]

    :param std_threshold: Standard deviation threshold to consider settled [V]. [Default: 0.01]
    :param threshold_points: Number of points to consider when determining settling. [Default: 5]
    :param data_interval: Interval between data acquisitions [s]. [Default: 0.1]
    :param max_time: Maximum run time [s]. [Default: 10]
    :param compliance_voltage: Maximum voltage [V]. [Default: 2]
    :param buffer_points: Number of measurements to average over for each data point. [Default: 10]
    """

    # voc parameters
    std_threshold       = FloatParameter( 'Maximum variation to consider settled.',    units = 'V',    default = 0.01 )
    threshold_points    = IntegerParameter( 'Number of points to settle on.',                          default = 5 )   
    data_interval       = FloatParameter( 'How often to run a measurement.',           units = 's',    default = 0.1 )
    max_time            = IntegerParameter( 'Maximum run time.',                       units = 's',    default = 10 )
    compliance_voltage  = FloatParameter( 'Compliance voltage.',                       units = 'V',    default = 2 )
    buffer_points       = IntegerParameter( 'Buffer points',                                           default = 10 )  # number of measurements for each data point.


    DATA_COLUMNS = [
        'time [s]', 'voltage [V]', 'current [A]'
    ]


    @property
    def start_time( self ):
        """
        :returns: Start time in seconds from epoch 
            if the procedure has been executed,
            otherwise None.
        """
        log.debug( '.start_time' )

        try:
            return self._start_time

        except AttributeError as err:
            # procedure not yet started
            return None


    @property
    def end_time( self ):
        """
        :returns: End time in seconds from epoch 
            if the procedure has been executed,
            otherwise None.
        """
        log.debug( '.end_time' )

        try:
            return self._end_time

        except AttributeError as err:
            # procedure not yet started
            return None


    @property
    def time_elapsed( self ):
        """
        :returns: Seconds the experiment has been running.
        """
        log.debug( '.time_elapsed' )

        if self.start_time is None:
            # procedure not yet executed
            return 0

        else:
            return ( time.time() - self.start_time )


    @property
    def progress( self ):
        """
        :returns: Proportion of procedure complete.
        """
        log.debug( '.progress' )

        if self.start_time is None:
            # procedure not yet executed
            return 0

        else:
            progress = self.time_elapsed/ self.max_time
            progress = min( progress, 1 )  # cap at 1
            return progress


    def startup( self ):
        super().startup()

        self.instrument.measure_voltage()
        self.instrument.apply_current(  # set current, measure voltage
            compliance_voltage = self.compliance_voltage
        )

        self.instrument.source_current = 0

        # set elements
        log.debug( 'Setting elements.' )
        self.set_elements( [ 'time', 'voltage', 'current' ] )

        time.sleep( 0.1 )  # wait to give instrument time to react


    def execute( self ):
        super().execute()
        self._start_time = time.time()
        self._end_time = self.start_time + self.max_time
        
        self.instrument.enable_source()
        data = []
        while self.progress < 1:
            datum = self._measure()
            data.append( datum )
            if len( data ) > self.threshold_points:
                # prune data
                data = data[ : -self.threshold_points ]

            if len( data ) >= self.threshold_points:
                # only check settled if enough points have been taken
                if self._settled( data ):
                    # data is settled
                    # end program
                    log.debug( 'Voltage settled.' )
                    return

            self.wait_for( self.data_interval, interval = self.data_interval/ 5 )


    def _measure( self ):
        """
        Collect data.

        :returns: 2D numpy.array of collected data.
        """
        log.debug( '#_measure' )

        data = self._get_data()
        data = self.format_data( data )
        
        # save data
        means = data.mean( axis = 0 )
        m_time  = means[ self.elements.index( 'TIME' ) ]
        time = self.time_elapsed - m_time  # adjust time to account for measurement
        
        voltage = means[ self.elements.index( 'VOLT' ) ]
        current = means[ self.elements.index( 'CURR' ) ]

        # save results
        self.emit( 'results', {
            'time [s]':        time,
            'voltage [V]': voltage,
            'current [A]': current,
        } )

        return {
            'time':    time,
            'voltage': voltage,
            'current': current,
        }


    def _get_data( self ):
        """
        Gets data from the measurement.

        :returns: Data from the instrument.
        """
        try:
            self.instrument.config_buffer( points = self.buffer_points )
            self.instrument.start_buffer()
            self.instrument.wait_for_buffer()

        except Exception as err:
            log.debug( err )
            self.shutdown()
        
        data = self.instrument.buffer_data
        return data


    def _settled( self, data ):
        """
        Determine whether the given data is considered settled.

        :param data: List of datum items.
        :returns: Whether the data is considered settled.
        """
        voltage = self._extract_voltage( data )
        v_std = voltage.std()
        return ( v_std <= self.std_threshold )


    @staticmethod    
    def _extract_voltage( self, data ):
        """
        :param data: List of datum dictionaries.
        :returns: numpy.ndarray of voltage data. 
        """
        return np.array( list( map( lambda x: x[ 'voltage' ], data ) ) )