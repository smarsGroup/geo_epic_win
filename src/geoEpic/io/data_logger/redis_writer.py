import redis
import json
import pandas as pd
from geoEpic.utils.redis import connect_to_redis

class RedisWriter:
    def __init__(self, table_name, host='localhost', port=56379, db=0):
        """Initialize the Redis class with connection parameters and a table name."""
        self.table_name = table_name
        self.client = connect_to_redis(host=host, port=port, db=db)
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