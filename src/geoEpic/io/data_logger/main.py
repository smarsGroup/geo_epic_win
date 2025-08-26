import os
import platform
from shortuuid import uuid 
from .sql_writer import SQLTableWriter
from .redis_writer import RedisWriter
from .lmdb_writer import LMDBTableWriter

class DataLogger:
    """
    A class to handle logging of data using different backends: Redis, SQL, or LMDB.
    It supports logging dictionaries and retrieving logged data.

    Attributes:
        output_folder (str): Directory where files are stored (if applicable).
        delete_on_read (bool): Whether to delete the data after retrieving it.
        backend (str): The backend to use ('redis', 'sql', 'lmdb').
    """

    def __init__(self, output_folder=None, delete_on_read=True, backend='redis', **kwargs):
        """
        Initialize the DataLogger with a specified output folder and backend.

        Args:
            output_folder (str, optional): Directory to store the files. Defaults to current directory.
            delete_on_read (bool): Whether to delete the data after retrieval. Defaults to True.
            backend (str): The backend to use ('redis', 'sql', 'lmdb'). Defaults to 'redis'.
            **kwargs: Additional parameters for backend configuration.

        Raises:
            ValueError: If an unsupported backend is specified.
        """
        self.output_folder = output_folder or os.getcwd()
        self.backend = backend.lower()
        self.delete_on_read = delete_on_read
        self.backend_kwargs = kwargs
        self.uuid = uuid()

        os.makedirs(self.output_folder, exist_ok=True)

        if self.backend not in ['redis', 'sql', 'lmdb']:
            raise ValueError(f"Unsupported backend: {self.backend}")

    def get_writer(self, func_name):
        """
        Get the appropriate writer based on the backend.

        Args:
            func_name (str): The name of the function to create a writer for.

        Returns:
            Writer: An instance of the appropriate writer class.

        Raises:
            ValueError: If an unsupported backend is specified.
        """
        filename = os.path.join(self.output_folder, f"{self.uuid}_{func_name}")
        writer_classes = {
            'redis': RedisWriter,
            'sql': SQLTableWriter,
            'lmdb': LMDBTableWriter
        }
        writer_class = writer_classes.get(self.backend)
        if not writer_class:
            raise ValueError(f"Unsupported backend: {self.backend}")
        return writer_class(filename, **self.backend_kwargs)

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

    def get(self, func_name, keep = False):
        """
        Retrieve logged data using the specified backend.

        Args:
            func_name (str): The name of the function whose data needs to be retrieved.
            keep (bool): If True, do not delete the table even if delete_on_read is True.

        Returns:
            pandas.DataFrame: The DataFrame containing the logged data.
        """
        with self.get_writer(func_name) as writer:
            df = writer.query_rows()
            if self.delete_on_read and not keep:
                writer.delete_table()
        return df
