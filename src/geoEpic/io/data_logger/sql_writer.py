import os
import sqlite3
import pandas as pd
import time
import random

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

    # def _write_row(self, kwargs):
    #     if not self.initialized:
    #         # Infer column types from the given arguments
    #         columns_with_types = [f"{col} {self.get_sqlite_type(value)}" for col, value in kwargs.items()]
    #         columns_stmt = ', '.join(columns_with_types)
    #         self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.table_name} ({columns_stmt})")
    #         self.initialized = True

    #     columns = ', '.join(kwargs.keys())
    #     placeholders = ':' + ', :'.join(kwargs.keys())
    #     self.cursor.execute(f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})", kwargs)
    #     self.conn.commit()

    def _write_row(self, kwargs):
        if not self.initialized:
            # Mark site_id as PRIMARY KEY
            cols = []
            for col, val in kwargs.items():
                sql_type = self.get_sqlite_type(val)
                if col == "SiteID":
                    cols.append(f"{col} {sql_type} PRIMARY KEY")
                else:
                    cols.append(f"{col} {sql_type}")
            schema = ", ".join(cols)
            self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.table_name} ({schema})")
            self.initialized = True

        columns      = ', '.join(kwargs.keys())
        placeholders = ':' + ', :'.join(kwargs.keys())
        self.cursor.execute(
            f"INSERT OR REPLACE INTO {self.table_name} ({columns}) VALUES ({placeholders})",
            kwargs
        )
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