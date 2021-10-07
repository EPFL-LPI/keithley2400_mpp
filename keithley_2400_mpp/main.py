import logging

from pymeasure.log import console_log
from pymeasure.experiment import Results, Worker


if __name__ == '__main__':
	# from large_results import LargeResults
	from jv import JVScan_Procedure
	from mpp_tracking import MPPTracking_Procedure


	# setup logging
	log_level = logging.DEBUG
	
	log = logging.getLogger( __name__ )
	log.addHandler( logging.NullHandler() )
	console_log( log, level = log_level )
	log.debug( 'Debug logging enabled.' )

	# --- general paramerters ---
	port = 'GPIB0::24'

	# --- setup jv ---
	log.debug( 'Initializing JV procedure.' )

	jv_scan = JVScan_Procedure()
	jv_scan.port = port

	jv_scan.start_voltage = 0
	jv_scan.end_voltage = 0.1
	jv_scan.voltage_step = 0.01
	jv_scan.settle_time = 100  # ms
	jv_scan.buffer_points = 10
	jv_scan.max_current = 3  # mA
	jv_scan.full_sweep = True    

	jv_data_filename = 'jv_data.csv'

	jv_results = Results( jv_scan, jv_data_filename )
	jv = Worker( jv_results )

	# --- setup mpp tracking ---
	log.debug( 'Initializing MPP tracking procedure.' )

	mpp_tracking = MPPTracking_Procedure()
	mpp_tracking.port = port

	mpp_tracking.run_time = 10  # minutes
	mpp_tracking.probe_step = 5  # mV
	mpp_tracking.probe_points = 5
	mpp_tracking.probe_interval = 30  # seconds
	mpp_tracking.data_interval = 5  # seconds

	mpp_data_filename = 'mpp_data.csv'

	mpp_results = Results( mpp_tracking, mpp_data_filename )
	mpp_results.MAX_FILE_SIZE = 1e-3

	mpp = Worker( mpp_results )


	# --- run procedures ---
	log.info( 'Starting JV scan.' )
	jv.start()

	log.info( 'Starting MPP tracking.' )
	# mpp.start()