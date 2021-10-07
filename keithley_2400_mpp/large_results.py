# Large Results

import os 

from pymeasure.experiment import Results

class LargeResults( Results ):
	"""
	Handles Results where data can not fit into a single file.
	"""

	MAX_FILE_SIZE = 1024  # max file size in megabytes
	BYTES_PER_MEGABYTE = 1048576  # bytes ber megabyte

	def __init__( self, procedure, data_filename ):
		"""

		"""
		self._data_filename = data_filename
		
		self.__super_init = False  # special care needed when initializing super
		filename = self._index_filename( data_filename )
		super().__init__( procedure, filename )
		self.__super_init = True

		self._file_index = 0
		self._max_bytes = self.MAX_FILE_SIZE* self.BYTES_PER_MEGABYTE


	@property
	def file_index( self ):
		"""
		:returns: Current file index.
		"""
		try:
			print( '---', self._file_index )
			return self._file_index

		except AttributeError as err:
			# index has not yet been initialized
			return 0


	@property
	def data_filename( self ):
		"""
		Append data file name with index.
		:returns: Current data file to use.
		"""
		return self._index_filename(
			self._data_filename,
			self.file_index 
		)


	@data_filename.setter
	def data_filename( self, value ):
		"""
		Sets _data_filename
		"""
		if not self.__super_init:
			# super not yet initialized
			# do not change file name
			return

		self._data_filename = value


	@property
	def data( self ):
		"""
		Update file index when needed.

		:returns: Current data.
		"""
		size = os.path.getsize( self.data_filename )
		if size > self._max_bytes:
			self._file_index += 1

		return super().data


	@staticmethod
	def _index_filename( filename, index = 0 ):
		"""
		:param filename: Base name of file.
		:param index: Desired index. [Defualt: 0]
		:returns: Indexed file name.
		"""
		basename, ext = os.path.splitext( filename )
		return f'{basename}-{index}{ext}'
