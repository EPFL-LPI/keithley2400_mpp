def main( port, run_voc = True, run_jv = True, run_mpp = True, **kwargs ):
	"""

	"""
	import math
	import time
	import logging

	import pandas as pd
	from pymeasure.log import console_log
	from pymeasure.experiment import Results, Worker

	from keithley2400_mpp.voc import Voc_Procedure
	from keithley2400_mpp.jv import JVScan_Procedure
	from keithley2400_mpp.mpp_tracking import MPPTracking_Procedure


	# setup logging
	log_level = logging.DEBUG
	
	log = logging.getLogger( __name__ )
	log.addHandler( logging.NullHandler() )
	console_log( log, level = log_level )
	log.debug( 'Debug logging enabled.' )


	# --- universal parameters ---
	use_front_terminals = True
	if 'use_front_terminals' in kwargs:
		use_front_terminals = kwargs[ 'use_front_terminals' ]

	recorder_args = {
		'maxBytes': 1024,
		'backupCount': 10
	}

	# --- setup voc ---
	log.debug( 'Initializing Voc procedure.' )

	voc_proc = Voc_Procedure() 
	voc_proc.port = port
	voc_proc.use_front_terminals = use_front_terminals

	voc_proc.std_threshold 		= 0.01
	voc_proc.threshold_points 	= 5
	voc_proc.data_interval 		= 0.1
	voc_proc.max_time 			= 60
	voc_proc.compliance_voltage = 2
	voc_proc.buffer_points 		= 5

	voc_data_filename = 'voc.csv'

	# --- setup jv ---
	log.debug( 'Initializing JV procedure.' )

	jv_proc = JVScan_Procedure()
	jv_proc.port = port
	jv_proc.use_front_terminals = use_front_terminals

	jv_proc.start_voltage 	= 0
	jv_proc.end_voltage 	= 0.1
	jv_proc.voltage_step 	= 0.01
	jv_proc.settle_time 	= 0.01 
	jv_proc.buffer_points 	= 5
	jv_proc.max_current 	= 0.01
	jv_proc.full_sweep 		= True

	jv_data_filename = 'jv.csv'

	# --- setup mpp tracking ---
	log.debug( 'Initializing MPP tracking procedure.' )

	mpp_proc = MPPTracking_Procedure()
	mpp_proc.port = port
	mpp_proc.use_front_terminals = use_front_terminals

	mpp_proc.run_time 		= 2  # minutes
	mpp_proc.probe_step 	= 0.05
	mpp_proc.probe_points	= 3
	mpp_proc.probe_interval = 15
	mpp_proc.data_interval 	= 3
	
	# If True positive power is produced, negative power is consumed.
 	# If False negative power is produced, positive power is consumed.
	mpp_proc.power_production_mode = False

	mpp_data_filename = 'mpp.csv'

	# --- run procedures ---


	# Voc
	if run_voc:
		log.info( 'Starting Voc.' )
		voc_results = Results( voc_proc, voc_data_filename, recorder_args = recorder_args )
		voc = Worker( voc_results )

		voc.start()
		voc.join( voc_proc.max_time* 1.5 )

		# update jv end voltage
		voc_df = pd.read_csv( voc_data_filename, sep = voc_results.DELIMITER, comment = voc_results.COMMENT )
		voc_measured = voc_df[ 'voltage [V]' ].tail( voc_proc.threshold_points ).mean()
		
		# round end voc to nearest step away from zero
		end_voc = voc_measured/ jv_proc.voltage_step
		end_voc = math.ceil( end_voc ) if ( end_voc > 0 ) else math.floor( end_voc )
		end_voc *= jv_proc.voltage_step

		log.info( f'Setting JV end voltage to {end_voc} from Voc measurement.' )
		jv_proc.end_voltage = end_voc

		time.sleep( 1 )

	# JV
	if run_jv:
		jv_run_time = abs(
			( jv_proc.settle_time + jv_proc.buffer_points* 0.02 )* 
			( jv_proc.end_voltage - jv_proc.start_voltage )/ jv_proc.voltage_step 
		)
		if jv_proc.full_sweep:
			jv_run_time *= 2

		log.info( 'Starting JV scan.' )
		jv_results = Results( jv_proc, jv_data_filename, recorder_args = recorder_args )
		jv = Worker( jv_results )

		jv.start()
		jv.join( jv_run_time* 2 )

		# update mpp initial voltage
		jv_df = pd.read_csv( jv_data_filename, sep = jv_results.DELIMITER, comment = jv_results.COMMENT )
		v_mpp = (
			jv_df.idxmax()[ 'power [W]' ]  # row that produced the most power
			if mpp_proc.power_production_mode else
			jv_df.idxmin()[ 'power [W]' ]
		)
		v_mpp = jv_df.iloc[ v_mpp ][ 'voltage [V]' ]  # voltage that produced the most power

		log.info( f'Setting initial Vmpp to {v_mpp} from JV measurement.' )
		mpp_proc.initial_voltage = v_mpp

		time.sleep( 1 )

	# MPP
	if run_mpp:
		log.info( 'Starting MPP tracking.' )
		mpp_results = Results( mpp_proc, mpp_data_filename, recorder_args = recorder_args )

		mpp = Worker( mpp_results )
		mpp.start()


if __name__ == '__main__':
	# --- general paramerters ---
	port = 'GPIB0::24'
	use_front_terminals = True

	main(
		port = port,
		run_voc = True,
		run_jv  = True,
		run_mpp = False,
		use_front_terminals = use_front_terminals
	)