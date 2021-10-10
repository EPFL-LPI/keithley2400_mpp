import time
import logging

import numpy as np
from pymeasure.log import console_log
from pymeasure.instruments.keithley import Keithley2400
from pymeasure.experiment import (
    Procedure,
    Parameter,
    BooleanParameter
)


# setup logging
log_level = logging.DEBUG

log = logging.getLogger( __name__ )
log.addHandler( logging.NullHandler() )
console_log( log, level = log_level )
log.debug( 'Debug logging enabled.' )


class Keithley2400_Procedure( Procedure ):
    """
    Standard Procedure for Keithley2400.
    Contains commonly used functionality.

    :param port: Port to connect to.
    :param use_front_terminals: If True front terminals are used.
        If False rear terminals are used.
        [Default: True]
    """

    # instrument parameters
    port = Parameter( 'Port', default = None )
    use_front_terminals = BooleanParameter( 'Use front terminals', default = True )


    @property
    def instrument( self ):
        """
        :returns: Reference to the instrument
            or None if it has not yet been created.
        """
        log.debug( '.instrument' )

        try:
            return self.__instrument

        except AttributeError as err:
            # procedure not yet started
            return None


    @property
    def elements( self ):
        """
        :returns: List of measurement elements
            or None if they have not yet been quried.
        """
        log.debug( '.elements' )

        try:
            return self.__elements

        except AttributeError as err:
            # elements not yet set
            return None


    def startup( self ):
        """
        Initializes the instrument and variables.
        """
        log.debug( '#startup' )

        if self.port is None:
            raise RuntimeError( 'Port has not been set.' )

        log.debug( 'Connecting and configuring the instrument.' )
        self.__instrument = Keithley2400( self.port )
        self.instrument.reset()  # apply voltage, measure current

        # set terminals
        log.debug( 'Setting terminals.' )
        if self.use_front_terminals:
            self.instrument.use_front_terminals()
        
        else:
            self.instrument.use_rear_terminals()


    def shutdown(self):
        log.debug( '#shutdown' )

        if self.instrument:
            self.instrument.shutdown()
        
        log.info( 'Procedure complete.' )


    def execute( self ):
        """
        Begin MPP tracking.
        """
        log.debug( '#execute' )


    def format_data( self, data ):
        """
        Format read data into.
        When data is originally read from the instrument,
        all the fields are flattened into a 1D list.
        This reshapes the data into a 2D array where rows 
        represent measurements, and columns are the fields.

        :param data: 1D numpy.array of data to format.
        :returns: 2D numpy.array of formatted data.
        """
        log.debug( '#format_data' )

        # convert to numpy array
        if isinstance( data, str ):
            data = data.split( ',' )

        if not isinstance( data, np.ndarray ):
            # data is not a numpy array
            # try to convert
            data = np.array( data, dtype = np.float64 )
        
        # format data into rows of measurements
        cols = len( self.elements )
        rows = data.shape[ 0 ]/ cols
        if not rows.is_integer():
            raise ValueError( 'Invalid data length. Data is not divisible by number of elements.' )

        rows = int( rows )
        data = data.reshape( rows, cols )
        return data


    def get_elements( self ):
        """
        :returns: List of the saved measurement elements.
        """
        log.debug( '#get_elements' )

        elms = self.instrument.ask( ':format:elements?' ).strip()
        elms = elms.split( ',' )
        return elms


    def set_elements( self, elms ):
        """
        Sets measurement elements.

        :param elms: A list of elements to set.
            Values must be in [ 'time', 'voltage', 'current', 'resistance', 'status' ]
        """
        valid_elms = [ 'time', 'voltage', 'current', 'resistance', 'status' ]
        if not all ( elm.lower() in valid_elms for elm in elms ):
            # invalid element
            raise ValueError( 'Invalid element.' )

        # set elements
        elm_str = ','.join( elms )
        self.instrument.write( f':format:elements {elm_str}' )
        self.__elements = self.get_elements()


    def wait_for( self, seconds, interval = 1 ):
        """
        Sleep for given number of seconds.
        Used to intercept interupts.
        
        :param seconds: Number of seconds to sleep for.
        :param interval: Interval to check for an interupt.
        """
        log.debug( '#wait_for' )

        end = time.time() + seconds
        while time.time() < end:
            if self.should_stop():
                # user canceled
                log.info( 'Procedure stopped by user.' )
                self.shutdown()
                raise RuntimeError( 'Procedure stopped by user.' )

            time.sleep( interval )
