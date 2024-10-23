import os
import lmdb
import json
import pandas as pd
import time
import random

class LMDBWriter:
    def __init__(self, db_path, max_retries=5, initial_wait=0.05, map_size=1e9):
        """
        Initialize the LMDBWriter class with environment parameters and a table name.

        :param db_path: Path to the LMDB environment directory.
        :param max_retries: Maximum number of retries for write operations.
        :param initial_wait: Initial wait time before retrying (in seconds).
        :param map_size: Maximum size of the database (in bytes).
        """
        self.db_path = db_path
        self.table_name = os.path.basename(db_path)
        self.max_retries = max_retries
        self.initial_wait = initial_wait
        self.map_size = int(map_size)

        self.env = None
        self.db = None
        self.connected = False
        self.counter_key = f"{self.table_name}:counter"

    def open(self):
        """Establish connection to LMDB and initialize counter if needed."""
        self.env = lmdb.open(
            self.db_path,
            map_size=self.map_size,
            max_dbs=2,  # One for data, one for the counter
            lock=True,
            readahead=False,
            metasync=True,
            sync=True,
            max_readers=126
        )
        self.db = self.env.open_db(self.table_name.encode('utf-8'))
        self.counter_db = self.env.open_db(b'counters', create=True)
        self.connected = True

        # Initialize the counter if it doesn't exist
        with self.env.begin(write=True, db=self.counter_db) as txn:
            if not txn.get(self.counter_key.encode('utf-8')):
                txn.put(self.counter_key.encode('utf-8'), b'0')

    def write_row(self, row_id=None, **kwargs):
        """Write a row to LMDB database under the specified table name."""
        if not self.connected:
            raise Exception("LMDB is not open. Please call the 'open' method first.")

        self._execute_with_retry(self._write_row, row_id, kwargs)

    def _write_row(self, row_id, data):
        with self.env.begin(write=True, db=self.db) as txn:
            if row_id is None:
                # Generate a new row_id
                with txn.cursor(db=self.counter_db) as cursor:
                    current_counter = int(cursor.get(self.counter_key.encode('utf-8')))
                    row_id = current_counter + 1
                    cursor.put(self.counter_key.encode('utf-8'), str(row_id).encode('utf-8'))
            else:
                row_id = int(row_id)

            key = str(row_id).encode('utf-8')
            value = json.dumps(data).encode('utf-8')
            txn.put(key, value)

    def read_row(self, row_id):
        """Read a row from LMDB database."""
        if not self.connected:
            raise Exception("LMDB is not open. Please call the 'open' method first.")

        return self._execute_with_retry(self._read_row, row_id)

    def _read_row(self, row_id):
        with self.env.begin(db=self.db) as txn:
            key = str(row_id).encode('utf-8')
            value = txn.get(key)
            if value is not None:
                return json.loads(value.decode('utf-8'))
            else:
                return None

    def query_rows(self):
        """Retrieve all rows from the LMDB database.

        Returns:
            pandas.DataFrame: A DataFrame containing all rows, including row_ids.
        """
        if not self.connected:
            raise Exception("LMDB is not open. Please call the 'open' method first.")

        return self._execute_with_retry(self._query_rows)

    def _query_rows(self):
        data_list = []
        with self.env.begin(db=self.db) as txn:
            cursor = txn.cursor()
            for key, value in cursor:
                row_id = key.decode('utf-8')
                row_data = json.loads(value.decode('utf-8'))
                row_data['row_id'] = row_id
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
            raise Exception("LMDB is not open. Please call the 'open' method first.")

        self._execute_with_retry(self._delete_table)

    def _delete_table(self):
        with self.env.begin(write=True, db=self.db) as txn:
            txn.drop(self.db, delete=False)  # Clear the database without deleting it
        with self.env.begin(write=True, db=self.counter_db) as txn:
            txn.delete(self.counter_key.encode('utf-8'))

    def close(self):
        """Close the LMDB environment."""
        if self.connected:
            self.env.close()
            self.env = None
            self.db = None
            self.connected = False

    def _execute_with_retry(self, func, *args, **kwargs):
        retries = 0
        while retries < self.max_retries:
            try:
                return func(*args, **kwargs)
            except lmdb.Error as e:
                if isinstance(e, lmdb.LockError):
                    wait_time = self.initial_wait * (2 ** retries) + random.uniform(0, 0.01)
                    time.sleep(wait_time)
                    retries += 1
                else:
                    raise
        raise Exception(f"Failed to execute after {self.max_retries} retries due to database lock")

    def __enter__(self):
        """Support context manager 'with' statement by opening the connection."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Support context manager 'with' statement by closing the connection."""
        self.close()


if __name__ == '__main__':

    # Use the LMDBWriter
    with LMDBWriter('my_table.lmdb') as writer:
        # Write rows
        writer.write_row(name='Alice', age=30)
        writer.write_row(name='Bob', age=25)
        writer.write_row(name='Charlie', age=35)

        # Read a specific row
        row = writer.read_row(1)
        print("Row with ID 1:", row)

        # Query all rows
        df = writer.query_rows()
        print("All Rows:")
        print(df)

        # Delete the table
        writer.delete_table()