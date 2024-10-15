import os
import pandas as pd
import redis
import sqlite3
import csv
import json
import fcntl
import time
import random


class CSVWriter:
    def __init__(self, file_path, mode='a+'):
        """Initialize the CSV class with a file path and file mode."""
        self.file_path = file_path
        self.mode = mode
        self.file_handle = None
        self.writer = None
        self.headers_written = False

    def open(self, mode=None):
        """Open the CSV file in the specified mode and lock it for exclusive access."""
        if mode: self.mode = mode
        self.file_handle = open(self.file_path, self.mode)
        self.writer = csv.writer(self.file_handle)
        fcntl.flock(self.file_handle, fcntl.LOCK_EX)  # Lock the file
        # Check if we need to write headers by checking if the file is empty
        if os.stat(self.file_path).st_size == 0:
            self.headers_written = False
        else:
            self._read_header()
    
    def _read_header(self):
        """Read the header from the file if it exists."""
        if self.file_handle:
            self.file_handle.seek(0)  # Go to the start of the file
            first_line = self.file_handle.readline()
            if first_line:
                self.header = first_line.strip().split(',')
                self.headers_written = True

    def write_row(self, *args, **kwargs):
        """Write a row to the CSV file."""
        if self.file_handle is None:
            raise Exception("File is not open. Please call the 'open' method first.")

        if kwargs:
            if not self.headers_written:
                # Write the header based on dictionary keys
                self.header = list(kwargs.keys())
                if os.stat(self.file_path).st_size == 0:
                    self.writer.writerow(self.header)
                    self.headers_written = True
            # Write the row based on dictionary values
            self.writer.writerow([kwargs[key] for key in self.header])
        else:
            # Assume args contains only values in the correct order
            self.writer.writerow(args)

    def query_rows(self):
        """Retrieve all rows from the CSV file.

        Returns:
            pandas.DataFrame: The DataFrame containing all rows.
        """
        if os.path.isfile(self.file_path):
            df = pd.read_csv(self.file_path)
        else:
            df = pd.DataFrame()
        return df

    def delete_table(self):
        """Delete the CSV file."""
        if os.path.isfile(self.file_path):
            os.remove(self.file_path)

    def close(self):
        """Release the lock and close the CSV file."""
        if self.file_handle is not None:
            fcntl.flock(self.file_handle, fcntl.LOCK_UN)  # Unlock the file
            self.file_handle.close()
            self.file_handle = None

    def __enter__(self):
        """Support context manager 'with' statement by opening the file."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Support context manager 'with' statement by closing the file."""
        self.close()


class SQLTableWriter:

    TYPE_MAPPING = {
        int: "INTEGER",
        float: "REAL",
        str: "TEXT",
        bool: "INTEGER",  # SQLite doesn't have a native boolean type
        bytes: "BLOB",
        None: "NULL"
    }
        
    def __init__(self, file_path, columns=None, max_retries=5, initial_wait=0.05):
        self.file_path = file_path
        self.db_path = file_path
        self.table_name = os.path.basename(file_path)
        self.columns = columns
        self.conn = None
        self.cursor = None
        self.initialized = False
        self.max_retries = max_retries
        self.initial_wait = initial_wait

    def open(self):
        self._execute_with_retry(self._open_connection)

    def _open_connection(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        if self.columns:
            columns_stmt = ', '.join([f"{col_name} {col_type}" for col_name, col_type in self.columns.items()])
            self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.table_name} ({columns_stmt})")
            self.conn.commit()
            self.initialized = True
        self.cursor.execute("PRAGMA journal_mode=WAL;")
        self.cursor.execute("PRAGMA synchronous = NORMAL;")
        self.cursor.execute("PRAGMA temp_store = MEMORY;")
        self.cursor.execute("PRAGMA cache_size = -64000;")

    def write_row(self, **kwargs):
        if self.conn is None or self.cursor is None:
            raise Exception("Database is not open. Please call the 'open' method first.")
        
        self._execute_with_retry(self._write_row, kwargs)
    
    def get_sqlite_type(self, value):
        return self.TYPE_MAPPING.get(type(value), "BLOB")

    def _write_row(self, kwargs):
        if not self.initialized:
            # Infer column types from the given arguments
            columns_with_types = [f"{col} {self.get_sqlite_type(value)}" for col, value in kwargs.items()]
            columns_stmt = ', '.join(columns_with_types)
            self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.table_name} ({columns_stmt})")
            self.initialized = True

        columns = ', '.join(kwargs.keys())
        placeholders = ':' + ', :'.join(kwargs.keys())
        self.cursor.execute(f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})", kwargs)
        self.conn.commit()

    def query_rows(self, condition=None, *args, **kwargs):
        return self._execute_with_retry(self._query_rows, condition, *args, **kwargs)

    def _query_rows(self, condition, *args, **kwargs):
        query = f"SELECT * FROM {self.table_name}"
        if condition:
            query += f" WHERE {condition}"
        self.cursor.execute(query, *args, **kwargs)
        rows = self.cursor.fetchall()
        # Get column names from cursor.description
        columns = [description[0] for description in self.cursor.description]
        return pd.DataFrame(rows, columns=columns)

    def delete_table(self):
        if self.conn is None or self.cursor is None:
            raise Exception("Database is not open. Please call the 'open' method first.")
        self._execute_with_retry(self._delete_table)

    def _delete_table(self):
        self.cursor.execute(f"DROP TABLE IF EXISTS {self.table_name}")
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def _execute_with_retry(self, func, *args, **kwargs):
        retries = 0
        while retries < self.max_retries:
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    wait_time = self.initial_wait * (2 ** retries) + random.uniform(0, 0.01)
                    time.sleep(wait_time)
                    retries += 1
                else:
                    raise
        raise Exception(f"Failed to execute after {self.max_retries} retries due to database lock")

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


from geoEpic.utils.redis import connect_to_redis

class RedisWriter:
    def __init__(self, table_name, host='localhost', port=6379, db=0):
        """Initialize the Redis class with connection parameters and a table name."""
        self.table_name = table_name
        self.client = connect_to_redis(host='localhost', port=6379, db=0)
        self.connected = False

    def open(self):
        """Establish connection to Redis and initialize counter if needed."""
        self.connected = True
        # Initialize the counter if it doesn't exist
        counter_key = f"{self.table_name}:counter"
        if not self.client.exists(counter_key):
            # Set counter to -1 so that the first INCR gives 0
            self.client.set(counter_key, -1)

    def write_row(self, row_id=None, **kwargs):
        """Write a row to Redis hash under the specified table name."""
        if not self.connected:
            raise Exception("Redis is not open. Please call the 'open' method first.")
        
        if row_id is None:
            # Generate a new row_id
            row_id = self.client.incr(f"{self.table_name}:counter")
        row_id = str(row_id)  # Ensure row_id is a string

        data = json.dumps(kwargs)
        self.client.hset(self.table_name, row_id, data)

    def read_row(self, row_id):
        """Read a row from Redis hash."""
        if not self.connected:
            raise Exception("Redis is not open. Please call the 'open' method first.")
        
        row_id = str(row_id)  # Ensure row_id is a string
        data = self.client.hget(self.table_name, row_id)
        if data is not None:
            return json.loads(data)
        return None

    def query_rows(self):
        """Retrieve all rows from the Redis hash.

        Returns:
            pandas.DataFrame: A DataFrame containing all rows, including row_ids.
        """
        if not self.connected:
            raise Exception("Redis is not open. Please call the 'open' method first.")

        rows = self.client.hgetall(self.table_name)
        data_list = []
        for row_id, data in rows.items():
            row_data = json.loads(data)
            row_data['row_id'] = row_id.decode('utf-8')
            data_list.append(row_data)
        if data_list:
            df = pd.DataFrame(data_list)
            df.set_index('row_id', inplace=True)
            df.index.name = None 
        else:
            df = pd.DataFrame()
        return df

    def delete_table(self):
        """Delete all entries associated with the table name, including the counter."""
        if not self.connected:
            raise Exception("Redis is not open. Please call the 'open' method first.")
        
        self.client.delete(self.table_name)
        self.client.delete(f"{self.table_name}:counter")

    def close(self):
        """Close the connection to Redis."""
        if self.connected:
            # Note: redis-py does not have a 'close' method for the client.
            self.connected = False

    def __enter__(self):
        """Support context manager 'with' statement by opening the connection."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Support context manager 'with' statement by closing the connection."""
        self.close()



class DataLogger:
    """
    A class to handle logging of data using different backends: Redis, CSV, or SQL.
    It supports logging dictionaries and retrieving logged data.

    Attributes:
        output_folder (str): Directory where files are stored (if applicable).
        delete_after_use (bool): Whether to delete the data after retrieving it.
        backend (str): The backend to use ('redis', 'csv', 'sql').
    """

    def __init__(self, output_folder=None, delete_after_use=True, backend='redis', **kwargs):
        """
        Initialize the DataLogger with a specified output folder and backend.

        Args:
            output_folder (str): Directory to store the files (if applicable).
            delete_after_use (bool): Flag to indicate if the data should be deleted after use.
            backend (str): The backend to use ('redis', 'csv', 'sql').
            **kwargs: Additional parameters for backend configuration.
        """
        self.output_folder = output_folder or '.'
        self.backend = backend.lower()
        if self.backend != 'redis':
            os.makedirs(self.output_folder, exist_ok=True)
        self.delete_after_use = delete_after_use
        self.backend_kwargs = kwargs  # Additional kwargs for the writer classes

    def get_writer(self, func_name):
        """Get the appropriate writer based on the backend."""
        if self.backend == 'redis':
            # For Redis, func_name is used as the table_name
            return RedisWriter(func_name, **self.backend_kwargs)
        elif self.backend == 'sql':
            # For SQL, construct the file path using func_name
            filename = os.path.join(self.output_folder, func_name)
            return SQLTableWriter(filename, **self.backend_kwargs)
        elif self.backend == 'csv':
            # For CSV, construct the file path using func_name
            filename = os.path.join(self.output_folder, func_name)
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



# class CSVWriter:
#     def __init__(self, file_path, mode='a+'):
#         """Initialize the CSV class with a file path and file mode.
        
#         Args:
#             file_path (str): The full path to the CSV file.
#             mode (str): The mode to open the file ('w' for writing, 'a' for appending).
#         """
#         self.file_path = file_path
#         self.mode = mode
#         self.file_handle = None
#         self.writer = None
#         self.headers_written = False

#     def open(self, mode=None):
#         """Open the CSV file in the specified mode and lock it for exclusive access.
        
#         Args:
#             mode (str): Optionally specify a mode ('w' for writing, 'a' for appending) at opening.
#         """
#         if mode: self.mode = mode
#         # if not os.path.exists(self.file_path):
#         #     if 'a' in self.mode: open(self.file_path, 'w+').close()
#         self.file_handle = open(self.file_path, self.mode)
#         self.writer = csv.writer(self.file_handle)
#         fcntl.flock(self.file_handle, fcntl.LOCK_EX)  # Lock the file
#         # Check if we need to write headers by checking if the file is empty
#         if os.stat(self.file_path).st_size == 0:
#             self.headers_written = False
#         else:
#             self._read_header()
    
#     def _read_header(self):
#         """Read the header from the file if it exists."""
#         if self.file_handle:
#             self.file_handle.seek(0)  # Go to the start of the file
#             first_line = self.file_handle.readline()
#             if first_line:
#                 self.header = first_line.strip().split(',')
#                 self.headers_written = True

#     def write_row(self, *args, **kwargs):
#         """Write a row to the CSV file.
        
#         Args can be a variable length argument list representing the columns of the row,
#         or kwargs can be a dict with column names and values.
#         """
#         if self.file_handle is None:
#             raise Exception("File is not open. Please call the 'open' method first.")

#         if kwargs:
#             if not self.headers_written:
#                 # Write the header based on dictionary keys
#                 self.header = list(kwargs.keys())
#                 if os.stat(self.file_path).st_size == 0:
#                     self.writer.writerow(self.header)
#                     self.headers_written = True
#             # Write the row based on dictionary values
#             self.writer.writerow([kwargs[key] for key in self.header])
#         else:
#             # Assume args contains only values in the correct order
#             self.writer.writerow(args)

#     def close(self):
#         """Release the lock and close the CSV file."""
#         if self.file_handle is not None:
#             fcntl.flock(self.file_handle, fcntl.LOCK_UN)  # Unlock the file
#             self.file_handle.close()
#             self.file_handle = None

#     def __enter__(self):
#         """Support context manager 'with' statement by opening the file."""
#         self.open()
#         return self

#     def __exit__(self, exc_type, exc_value, traceback):
#         """Support context manager 'with' statement by closing the file."""
#         self.close()



# class SQLTableWriter:

#     TYPE_MAPPING = {
#         int: "INTEGER",
#         float: "REAL",
#         str: "TEXT",
#         bool: "INTEGER",  # SQLite doesn't have a native boolean type
#         bytes: "BLOB",
#         None: "NULL"
#     }
        
#     def __init__(self, table_path, columns=None, max_retries=5, initial_wait=0.05):
#         self.db_path = table_path
#         self.table_name = os.path.basename(table_path).split('.')[0]
#         self.columns = columns
#         self.conn = None
#         self.cursor = None
#         self.initialized = False
#         self.max_retries = max_retries
#         self.initial_wait = initial_wait

#     def open(self):
#         self._execute_with_retry(self._open_connection)

#     def _open_connection(self):
#         self.conn = sqlite3.connect(self.db_path)
#         self.cursor = self.conn.cursor()
#         if self.columns:
#             columns_stmt = ', '.join([f"{col_name} {col_type}" for col_name, col_type in self.columns.items()])
#             self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.table_name} ({columns_stmt})")
#             self.conn.commit()
#             self.initialized = True
#         self.cursor.execute("PRAGMA journal_mode=WAL;")
#         self.cursor.execute("PRAGMA synchronous = NORMAL;")
#         self.cursor.execute("PRAGMA temp_store = MEMORY;")
#         self.cursor.execute("PRAGMA cache_size = -64000;")

#     def write_row(self, **kwargs):
#         if self.conn is None or self.cursor is None:
#             raise Exception("Database is not open. Please call the 'open' method first.")
        
#         self._execute_with_retry(self._write_row, kwargs)
    
#     def get_sqlite_type(self, value):
#         return self.TYPE_MAPPING.get(type(value), "BLOB")

#     def _write_row(self, kwargs):
#         if not self.initialized:
#             # Infer column types from the given arguments
#             columns_with_types = [f"{col} {self.get_sqlite_type(value)}" for col, value in kwargs.items()]
#             columns_stmt = ', '.join(columns_with_types)
#             self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.table_name} ({columns_stmt})")
#             self.initialized = True

#         columns = ', '.join(kwargs.keys())
#         placeholders = ':' + ', :'.join(kwargs.keys())
#         self.cursor.execute(f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})", kwargs)
#         self.conn.commit()

#     def query_rows(self, condition=None, *args, **kwargs):
#         return self._execute_with_retry(self._query_rows, condition, *args, **kwargs)

#     def _query_rows(self, condition, *args, **kwargs):
#         query = f"SELECT * FROM {self.table_name}"
#         if condition:
#             query += f" WHERE {condition}"
#         self.cursor.execute(query, *args, **kwargs)
#         rows = self.cursor.fetchall()
#         # Get column names from cursor.description
#         columns = [description[0] for description in self.cursor.description]
#         return pd.DataFrame(rows, columns=columns)

#     def delete_table(self):
#         if self.conn is None or self.cursor is None:
#             raise Exception("Database is not open. Please call the 'open' method first.")
#         self._execute_with_retry(self._delete_table)

#     def _delete_table(self):
#         self.cursor.execute(f"DROP TABLE IF EXISTS {self.table_name}")
#         self.conn.commit()

#     def close(self):
#         if self.conn:
#             self.conn.close()
#             self.conn = None

#     def _execute_with_retry(self, func, *args, **kwargs):
#         retries = 0
#         while retries < self.max_retries:
#             try:
#                 return func(*args, **kwargs)
#             except sqlite3.OperationalError as e:
#                 if "database is locked" in str(e):
#                     wait_time = self.initial_wait * (2 ** retries) + random.uniform(0, 0.01)
#                     # print(f"Database is locked. Retrying in {wait_time:.2f} seconds...")
#                     time.sleep(wait_time)
#                     retries += 1
#                 else:
#                     raise
#         raise Exception(f"Failed to execute after {self.max_retries} retries due to database lock")

#     def __enter__(self):
#         self.open()
#         return self

#     def __exit__(self, exc_type, exc_value, traceback):
#         self.close()




# import redis
# import json

# class RedisWriter:
#     def __init__(self, table_name, host='localhost', port=6379, db=0):
#         """Initialize the Redis class with connection parameters and a table name.

#         Args:
#             table_name (str): The main key for the Redis hash.
#             host (str): Redis server host.
#             port (int): Redis server port.
#             db (int): Redis database number.
#         """
#         self.table_name = table_name
#         self.client = redis.Redis(host=host, port=port, db=db)
#         self.connected = False

#     def open(self):
#         """Establish connection to Redis and initialize counter if needed."""
#         try:
#             self.client.ping()  # Check if the connection is alive
#             self.connected = True
#         except redis.ConnectionError:
#             raise Exception("Failed to connect to Redis server.")
        
#         # Initialize the counter if it doesn't exist
#         counter_key = f"{self.table_name}:counter"
#         if not self.client.exists(counter_key):
#             # Set counter to -1 so that the first INCR gives 0
#             self.client.set(counter_key, -1)

#     def write_row(self, row_id=None, **kwargs):
#         """Write a row to Redis hash under the specified table name.

#         Args:
#             row_id (str or int, optional): The identifier for the row. If not provided, an auto-incremented ID will be used.
#             kwargs: The key-value pairs to store.
#         """
#         if not self.connected:
#             raise Exception("Redis is not open. Please call the 'open' method first.")
        
#         if row_id is None:
#             # Generate a new row_id
#             row_id = self.client.incr(f"{self.table_name}:counter")
#         row_id = str(row_id)  # Ensure row_id is a string

#         data = json.dumps(kwargs)
#         self.client.hset(self.table_name, row_id, data)

#     def read_row(self, row_id):
#         """Read a row from Redis hash.

#         Args:
#             row_id (str or int): The identifier for the row.

#         Returns:
#             dict: The retrieved data as a dictionary, or None if not found.
#         """
#         if not self.connected:
#             raise Exception("Redis is not open. Please call the 'open' method first.")
        
#         row_id = str(row_id)  # Ensure row_id is a string
#         data = self.client.hget(self.table_name, row_id)
#         if data is not None:
#             return json.loads(data)
#         return None

#     def query_rows(self):
#         """Retrieve all rows from the Redis hash.

#         Returns:
#             dict: A dictionary containing all rows with row_ids as keys.
#         """
#         if not self.connected:
#             raise Exception("Redis is not open. Please call the 'open' method first.")

#         rows = self.client.hgetall(self.table_name)
#         # Decode bytes to strings and parse JSON
#         return {row_id.decode('utf-8'): json.loads(data) for row_id, data in rows.items()}

#     def delete_row(self, row_id):
#         """Delete a row from Redis hash.

#         Args:
#             row_id (str or int): The identifier for the row to delete.
#         """
#         if not self.connected:
#             raise Exception("Redis is not open. Please call the 'open' method first.")
        
#         row_id = str(row_id)
#         self.client.hdel(self.table_name, row_id)

#     def delete_table(self):
#         """Delete all entries associated with the table name, including the counter."""
#         if not self.connected:
#             raise Exception("Redis is not open. Please call the 'open' method first.")
        
#         self.client.delete(self.table_name)
#         self.client.delete(f"{self.table_name}:counter")

#     def close(self):
#         """Close the connection to Redis."""
#         if self.connected:
#             self.client.close()
#             self.connected = False

#     def __enter__(self):
#         """Support context manager 'with' statement by opening the connection."""
#         self.open()
#         return self

#     def __exit__(self, exc_type, exc_value, traceback):
#         """Support context manager 'with' statement by closing the connection."""
#         self.close()



# class DataLogger:
#     """
#     A class to handle logging of data to CSV files. It supports logging dictionaries
#     and retrieving logged data.

#     Attributes:
#         output_folder (str): Directory where CSV files are stored.
#         delete_after_use (bool): Whether to delete the file after retrieving it.
#         dataframes (dict): Cache for dataframes loaded from CSV files.
#     """

#     def __init__(self, output_folder, delete_after_use=True):
#         """
#         Initialize the DataLogger with a specified output folder.

#         Args:
#             output_folder (str): Directory to store the CSV files.
#             delete_after_use (bool): Flag to indicate if the file should be deleted after use.
#         """
#         self.output_folder = output_folder
#         os.makedirs(output_folder, exist_ok=True)
#         self.dataframes = {}
#         self.delete_after_use = delete_after_use

#     def get(self, func_name):
#         """
#         Retrieve a DataFrame from a CSV file.

#         Args:
#             func_name (str): The name of the function whose data needs to be retrieved.

#         Returns:
#             pandas.DataFrame: The DataFrame containing the logged data.

#         Raises:
#             FileNotFoundError: If the corresponding CSV file does not exist.
#         """
#         filename = os.path.join(self.output_folder, f"{func_name}.db")
#         # if func_name not in self.dataframes:
#         if os.path.isfile(filename):
#             with SQLTableWriter(filename) as writer:
#                 df = writer.query_rows()
#             if self.delete_after_use:
#                 os.remove(filename)
#             return df
#         else:
#             return pd.DataFrame()
        

#     def log_dict(self, func_name, result):
#         """
#         Log a dictionary of results to a CSV file.

#         Args:
#             func_name (str): The name of the function to log the data for.
#             result (dict): Dictionary of results to log.

#         Raises:
#             ValueError: If the result is not a dictionary.
#         """
#         if not isinstance(result, dict):
#             raise ValueError(f"{func_name} output must be a dictionary.")
#         filename = os.path.join(self.output_folder, f"{func_name}.db")
#         with SQLTableWriter(filename) as writer:
#             writer.write_row(**result)




# class CSVDataLogger:
#     """
#     A class to handle logging of data to CSV files. It supports logging dictionaries
#     and retrieving logged data.

#     Attributes:
#         output_folder (str): Directory where CSV files are stored.
#         delete_after_use (bool): Whether to delete the file after retrieving it.
#         dataframes (dict): Cache for dataframes loaded from CSV files.
#     """

#     def __init__(self, output_folder, delete_after_use=True):
#         """
#         Initialize the DataLogger with a specified output folder.

#         Args:
#             output_folder (str): Directory to store the CSV files.
#             delete_after_use (bool): Flag to indicate if the file should be deleted after use.
#         """
#         self.output_folder = output_folder
#         os.makedirs(output_folder, exist_ok=True)
#         self.dataframes = {}
#         self.delete_after_use = delete_after_use

#     def get(self, func_name):
#         """
#         Retrieve a DataFrame from a CSV file.

#         Args:
#             func_name (str): The name of the function whose data needs to be retrieved.

#         Returns:
#             pandas.DataFrame: The DataFrame containing the logged data.

#         Raises:
#             FileNotFoundError: If the corresponding CSV file does not exist.
#         """
#         filename = os.path.join(self.output_folder, f"{func_name}.csv")
#         # if func_name not in self.dataframes:
#         if os.path.isfile(filename):
#             return pd.read_csv(filename)
#         else:
#             raise FileNotFoundError(f"No data found for name: {func_name}")
        

#     def log_dict(self, func_name, result):
#         """
#         Log a dictionary of results to a CSV file.

#         Args:
#             func_name (str): The name of the function to log the data for.
#             result (dict): Dictionary of results to log.

#         Raises:
#             ValueError: If the result is not a dictionary.
#         """
#         if not isinstance(result, dict):
#             raise ValueError(f"{func_name} output must be a dictionary.")
#         filename = os.path.join(self.output_folder, f"{func_name}.csv")
#         with CSVWriter(filename) as writer:
#             writer.write_row(**result)
