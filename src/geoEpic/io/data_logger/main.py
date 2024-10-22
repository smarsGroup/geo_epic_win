import os
import platform
from shortuuid import uuid 
from .sql_writer import SQLTableWriter
from .csv_writer import CSVWriter

class DataLogger:
    """
    A class to handle logging of data using different backends: Redis, CSV, or SQL.
    It supports logging dictionaries and retrieving logged data.

    Attributes:
        output_folder (str): Directory where files are stored (if applicable).
        delete_after_use (bool): Whether to delete the data after retrieving it.
        backend (str): The backend to use ('redis', 'csv', 'sql').
    """

    def __init__(self, output_folder=None, delete_after_use=True, backend='sql', **kwargs):
        """
        Initialize the DataLogger with a specified output folder and backend.

        Args:
            output_folder (str): Directory to store the files (if applicable).
            delete_after_use (bool): Flag to indicate if the data should be deleted after use.
            backend (str): The backend to use ('redis', 'csv', 'sql').
            **kwargs: Additional parameters for backend configuration.
        """
        # Check the platform and adjust the backend if running on Windows
        if platform.system() == 'Windows' and backend.lower() == 'redis':
            print("Redis is not supported on Windows by default. Falling back to 'sql' backend.")
            backend = 'sql'

        self.output_folder = output_folder or '.'
        self.backend = backend.lower()
        if self.backend != 'redis':
            os.makedirs(self.output_folder, exist_ok=True)
        self.delete_after_use = delete_after_use
        self.backend_kwargs = kwargs  # Additional kwargs for the writer classes
        self.uuid = uuid()

    def get_writer(self, func_name):
        """Get the appropriate writer based on the backend."""
        if self.backend == 'redis':
            # For Redis, func_name is used as the table_name
            return RedisWriter(f'{self.uuid}:{func_name}', **self.backend_kwargs)
        elif self.backend == 'sql':
            # For SQL, construct the file path using func_name and uuid
            filename = os.path.join(self.output_folder, f"{self.uuid}_{func_name}")
            return SQLTableWriter(filename, **self.backend_kwargs)
        elif self.backend == 'csv':
            # For CSV, construct the file path using func_name and uuid
            filename = os.path.join(self.output_folder, f"{self.uuid}_{func_name}")
            return CSVWriter(filename, **self.backend_kwargs)
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")

    def log_dict(self, func_name, result):
        """
        Log a dictionary of results using the specified backend.

        Args:
            func_name (str): The name of the function to log the data for.
            result (dict): Dictionary of results to log.

        Raises:
            ValueError: If the result is not a dictionary.
        """
        if not isinstance(result, dict):
            raise ValueError(f"{func_name} output must be a dictionary.")

        with self.get_writer(func_name) as writer:
            writer.write_row(**result)

    def get(self, func_name):
        """
        Retrieve logged data using the specified backend.

        Args:
            func_name (str): The name of the function whose data needs to be retrieved.

        Returns:
            pandas.DataFrame: The DataFrame containing the logged data.
        """
        with self.get_writer(func_name) as writer:
            df = writer.query_rows()
            if self.delete_after_use:
                writer.delete_table()
        return df
