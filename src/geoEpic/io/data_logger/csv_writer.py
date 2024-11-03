import os
import pandas as pd
import csv
from geoEpic.utils import FileLockHandle

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
        if mode:
            self.mode = mode
        self.file_lock = FileLockHandle(self.file_path)
        self.file_handle = self.file_lock.acquire(self.mode)
        self.writer = csv.writer(self.file_handle)
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
        """Close the CSV file and release lock."""
        if hasattr(self, 'file_lock'):
            self.file_lock.release()
            self.file_handle = None
            self.writer = None

    def __enter__(self):
        """Support context manager 'with' statement by opening the file."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Support context manager 'with' statement by closing the file."""
        self.close()
