# MPP Tracking

import sys
import time
import logging

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


class MPPTracking_Procedure( SKeithley2400_Procedure ):
    """
    Procedure for basic step and probe MPP tracking.

    :param run_time: Run time [min]. [Default: 60]
    :param probe_step: Probe step size [V]. [Default: 10]
    :param voltage_range:  Voltage range [V]. [Default: None]
    :param compliance_current: Compliance current, maximum allowed current [mA]. [Default: 5]
    :param initial_voltage: Starting voltage [V]. [Default: 0]
    :param buffer_points: Number of measurements to average over for each data point. [Default: 10]
    :param probe_points: Number of points to collect during probe. [Default: 3]
    :param probe_interval: Seconds between probes [s]. [Default: 60]
    :param data_interval: Seconds between data collections [s]. [Default: 10]
    :param power_production_mode: If True positive power is produced, negative power is consumed.
        If False negative power is produced, positive power is consumed.
        [Default: False]
    :param use_front_terminals: If True front terminals are used.
        If False rear terminals are used.
        [Default: True]
    """

    # mpp parameters
    run_time            = FloatParameter( 'Run time',           units = 'min',  default = 60 )  # run time in minutes.
    probe_step          = FloatParameter( 'Probe step',         units = 'mV',   default = 10 )    # voltage step for probing in mV.
    voltage_range       = FloatParameter( 'Voltage range',      units = 'V',    default = 2 )
    compliance_current  = FloatParameter( 'Compliance current', units = 'mA',   default = 5 )  # maximum current to apply in mA.
    initial_voltage     = FloatParameter( 'Initial_voltage',    units = 'V',    default = 0 )
    buffer_points       = IntegerParameter( 'Buffer points',                    default = 10 )  # number of measurements for each data point.
    probe_points        = IntegerParameter( 'Probe points',                     default = 3 )  # number of data points to collect for probe.
    probe_interval      = IntegerParameter( 'Probe interval',    units = 's',   default = 60 )  # seconds between probes.
    data_interval       = IntegerParameter( 'Data interval',     units = 's',   default = 10 )  # seconds between data points.
    power_prodution_mode = BooleanParameter( 'Power production mode',           default = False )  # is power production or consumption beign measured?
    use_front_terminals  = BooleanParameter( 'Use front terminals',             default = True )

    DATA_COLUMNS = [
        'time', 'voltage [V]', 'current [A]', 'power [W]'
    ]


    @property
    def measurement_time( self ):
        """
        :returns: Approximate time to measure one data point.
        """
        log.debug( '.measurement_time' )

        return self.buffer_points* 0.065
    

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
            progress = self.time_elapsed/( self.run_time* 60 )  # convert run_time in minutes, to seconds
            progress = min( progress, 1 )  # cap at 1
            return progress


    def startup( self ):
        """
        Initializes the instrument and variables.
        """
        super().startup()

        # convert probe step from mV to V
        self.probe_step /= 1e3

        log.debug( 'Connecting and configuring the instrument.' )
        self.__instrument = Keithley2400( self.port )
        self.instrument.reset()  # apply voltage, measure current
        self.instrument.apply_voltage(
            voltage_range = self.voltage_range,
            compliance_current = self.compliance_current/ 1e3  # convert from mA to A
        )

        # set elements
        log.debug( 'Setting elements.' )
        self.instrument.write( ':format:elements volt,curr' )
        self.__elements = self._get_elements()

        # set terminals
        log.debug( 'Setting terminals.' )
        if self.use_front_terminals:
            self.instrument.use_front_terminals()
        
        else:
            self.instrument.use_rear_terminals()

        time.sleep( 0.1 )  # wait to give instrument time to react


    def execute( self ):
        """
        Begin MPP tracking.
        """
        super().execute()

        self._start_time = time.time()
        self._end_time = self.start_time + 60* self.run_time  # convert run time from minutes to seconds

        probe_direction = 1
        self.instrument.enable_source()
        self.instrument.source_voltage = self.initial_voltage

        while self.progress < 1:
            # run mpp tracking until end time
            baseline_data = self._baseline()
            probe_data = self._probe( probe_direction )  # leaves voltage at probe voltage
            better_voltage = self._better_voltage( baseline_data, probe_data )

            if better_voltage == baseline_data[ 0 ]:
                # baseline voltage is better
                # try to probe in other direction
                # reset voltage to baseline
                probe_direction *= -1
                self.instrument.source_voltage += baseline_voltage
                log.debug( f'Original voltage was better. Returning to {baseline_voltage} V' )

            else:
                # probe voltage is better
                log.debug( f'Probe voltage is better. New set point is {probe_data[ 0 ]} V.' )


    def _baseline( self ):
        """
        Collect baseline data at current voltage.

        :returns: Tuple of ( voltage, data ).
        """
        # collect data
        log.debug( '#_baseline' )

        # intialize last probe tiem if needed
        try:
            self._last_probe_time

        except AttributeError as err:
            # last probe time not set
            self._last_probe_time = time.time()

        powers = []
        while ( time.time() - self._last_probe_time ) < self.probe_interval:
            cycle_start = time.time()
            datum = self._measure_datum()
            powers.append( datum[ 'power' ] )

            # wait for next measurement
            self._wait_for(
                self._time_remaining(
                    cycle_start,
                    self.data_interval
                )
            )

        return ( self.instrument.source_voltage, powers )


    def _probe( self, direction = 1 ):
        """
        Collect probe data.
        SIDE EFFECT: Source voltage is left at probe voltage.

        :param direction: Probe direction.
            Either 1 or -1.
            [Default: 1] 
        :returns: Tuple of ( voltage, data ).
        """
        log.debug( '#_probe' )

        # set voltage
        self.instrument.source_voltage += ( direction* self.probe_step )
        log.debug( f'Probing at {self.instrument.source_voltage} V.' )

        # collect data
        powers = []
        for i in range( self.probe_points ):
            cycle_start = time.time()
            datum = self._measure_datum()
            powers.append( datum[ 'power' ] )

            # wait for next measurement
            self._wait_for(
                self._time_remaining(
                    cycle_start,
                    self.data_interval
                )
            )

        self._last_probe_time = time.time()
        return ( self.instrument.source_voltage, powers )


    def _better_voltage( self, d1, d2 ):
        """
        Determines the better voltage setting.

        :param d1: Tuple of ( voltage, [ data ] ) to be compared.
        :param d2: Tuple of ( voltage, [ data ] ) to be compared.
        :returns: Better voltage setting determined by data.
        """
        log.debug( '#_better_voltage' )
        v1, p1 = d1
        v2, p2 = d2

        # compare equal number of data points
        # don't need mean becaseu same number of points,
        # sum will do.
        num_points = min( self.probe_points, len( p1 ), len( p2) )
        m1 = sum( p1[ -num_points: ] )
        m2 = sum( p2[ -num_points: ] )

        if not self.power_prodution_mode:
            # power consumption is measured
            # power production is negative
            m1 *= -1
            m2 *= -1

        if m1 > m2:
            # m1 is better
            return v1

        else:
            # m2 is better
            # default if equal
            return v2


    def _measure_datum( self ):
        """
        Measures data, summarizes it, and saves it.
        Summary uses a mean over the colelcted measurements.

        :returns: Dictionary of summarized data.
        """
        log.debug( '#_measure_datum' )

        # run baseline measurements until it is time for another probe
        data = self._measure()

        # take mean over collected data
        means = data.mean( axis = 0 )
        voltage = means[ self.elements.index( 'VOLT' ) ]
        current = means[ self.elements.index( 'CURR' ) ]
        power = data.prod( axis = 1 ).mean()

        # save results
        m_time = self.time_elapsed
        self.emit( 'results', {
            'time':        m_time,
            'voltage [V]': voltage,
            'current [A]': current,
            'power [W]':   power
        } )

        return {
            'time':    m_time,
            'voltage': voltage,
            'current': current,
            'power':   power
        }


    def _measure( self ):
        """
        Collect data.

        :returns: 2D numpy.array of collected data.
        """
        log.debug( '#_measure' )

        self.instrument.config_buffer( points = self.buffer_points )
        self.instrument.start_buffer()
        self.instrument.wait_for_buffer()

        data = self.instrument.buffer_data
        data = self._format_data( data )
        return data


    def _time_remaining( self, start, interval ):
        """
        Calculate remaining time in interval.

        :param start: Start time.
        :param interval: Desired interval.
        """
        elapsed = ( time.time() - start )
        return ( interval - elapsed )


    def _wait_for( self, seconds, interval = 1 ):
        """
        Sleep for given number of seconds.
        Used to intercept interupts.
        
        :param seconds: Number of seconds to sleep for.
        :param interval: Interval to check for an interupt.
        """
        end = time.time() + seconds
        while time.time() < end:
            if self.should_stop():
                # user canceled
                log.info( 'Procedure stopped by user.' )
                self.shutdown()
                break

            time.sleep( interval )
