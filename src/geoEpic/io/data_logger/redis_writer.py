import redis
import json
import pandas as pd
from geoEpic.utils.redis_utils import connect_to_redis

class RedisWriter:
    def __init__(self, table_name, host='localhost', port=56379, db=0):
        """Initialize the Redis class with connection parameters and a table name."""
        self.table_name = table_name
        self.client = connect_to_redis(host=host, port=port, db=db)
        self.connected = False
        self._write_script = None  # set in open()

    def open(self):
        """Establish connection to Redis and initialize counter if needed."""
        self.connected = True
        # Initialize the counter if it doesn't exist (atomic)
        counter_key = f"{self.table_name}:counter"
        # NX makes this race-free even if multiple threads call open()
        # Set counter to -1 so the first INCR returns 0.
        self.client.set(counter_key, -1, nx=True)
        # Prepare a Lua script that atomically: INCR counter -> HSET table[id] = payload
        # Returns the new id as a string.
        lua = """
        local counter_key = KEYS[1]
        local table_name  = KEYS[2]
        local payload     = ARGV[1]
        local id = redis.call('INCR', counter_key)
        redis.call('HSET', table_name, id, payload)
        return tostring(id)
        """
        # Register once; redis-py will EVALSHA subsequently
        self._write_script = self.client.register_script(lua)

    def write_row(self, row_id=None, **kwargs):
        """Write a row to Redis hash under the specified table name."""
        if not self.connected:
            raise Exception("Redis is not open. Please call the 'open' method first.")
        # Serialize outside the script so any JSON errors surface here
        payload = json.dumps(kwargs)
        if row_id is None:
            # Atomic allocate+write
            new_id = self._write_script(
                keys=[f"{self.table_name}:counter", self.table_name],
                args=[payload],
            )
            # new_id is a str if decode_responses=True, else bytes; normalize to str
            if isinstance(new_id, bytes):
                new_id = new_id.decode('utf-8')
            return new_id
        else:
            # Caller provided an id; just write it
            row_id = str(row_id)
            self.client.hset(self.table_name, row_id, payload)
            return row_id

    def read_row(self, row_id):
        """Read a row from Redis hash."""
        if not self.connected:
            raise Exception("Redis is not open. Please call the 'open' method first.")
        row_id = str(row_id)
        data = self.client.hget(self.table_name, row_id)
        if data is not None:
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            return json.loads(data)
        return None

    def query_rows(self):
        """Retrieve all rows from the Redis hash as a DataFrame with row_id as index."""
        if not self.connected:
            raise Exception("Redis is not open. Please call the 'open' method first.")

        rows = self.client.hgetall(self.table_name)
        data_list = []
        for row_id, data in rows.items():
            # Normalize bytes -> str
            if isinstance(row_id, bytes):
                row_id = row_id.decode('utf-8')
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            row_data = json.loads(data)
            row_data['row_id'] = row_id
            data_list.append(row_data)

        if data_list:
            df = pd.DataFrame(data_list)
            df.set_index('row_id', inplace=True)
            df.index.name = None
            return df
        return pd.DataFrame()

    def delete_table(self):
        """Delete all entries associated with the table name, including the counter."""
        if not self.connected:
            raise Exception("Redis is not open. Please call the 'open' method first.")
        self.client.delete(self.table_name)
        self.client.delete(f"{self.table_name}:counter")

    def close(self):
        """Close the connection to Redis (flag only; redis client is pooled)."""
        if self.connected:
            self.connected = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()