import time
import logging

import numpy as np
from pymeasure.log import console_log
from pymeasure.instruments.keithley import Keithley2400
from pymeasure.experiment import Procedure


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
    """

    # instrument parameters
    port = Parameter( 'Port', default = None )

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


    def shutdown(self):
        log.debug( '#shutdown' )

        self.instrument.shutdown()
        log.info( 'Procedure complete' )


    def execute( self ):
        """
        Begin MPP tracking.
        """
        log.debug( '#execute' )


    def _format_data( self, data ):
        """
        Format read data into.
        When data is originally read from the instrument,
        all the fields are flattened into a 1D list.
        This reshapes the data into a 2D array where rows 
        represent measurements, and columns are the fields.

        :param data: 1D numpy.array of data to format.
        :returns: 2D numpy.array of formatted data.
        """
        log.debug( '#_format_data' )

        # convert to numpy array
        if isinstance( data, str ):
            data = data.split( ',' )

        if not isinstance( data, np.array ):
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


    def _get_elements( self ):
        """
        :returns: List of the saved measurement elements.
        """
        log.debug( '#_get_elements' )

        elms = self.instrument.ask( ':format:elements?' ).strip()
        elms = elms.split( ',' )
        return elms