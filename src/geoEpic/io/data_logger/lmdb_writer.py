# pip install lmdb pandas
import os, json, struct
import lmdb
import pandas as pd

class LMDBTableWriter:
    """
    Minimal, efficient row store with auto-increment row_id.
    - write_row(row_id=None, **kwargs) -> returns the row_id (string)
    - read_row(row_id) -> dict or None
    - query_rows() -> DataFrame with row_id index
    - delete_table(), open(), close(), context manager
    """

    def __init__(self, file_path: str,
                 map_size: int = 128 << 20,   # 128 MB start; auto-grows on demand
                 sync: bool = True,         # set False for max write speed (less durable)
                 readahead: bool = False):
        self.dir_path = file_path
        # robust basename even if file_path ends with a slash
        self.table_name = os.path.basename(os.path.normpath(file_path)) or "table"
        self.map_size = map_size
        self.sync = sync
        self.readahead = readahead
        self.env = None
        self.db = None
        self.meta_db = None

    def open(self):
        os.makedirs(self.dir_path, exist_ok=True)
        self.env = lmdb.open(
            self.dir_path, subdir=True, max_dbs=4,
            map_size=self.map_size, lock=True,
            readahead=self.readahead, writemap=False,
            metasync=False, sync=self.sync
        )
        self.meta_db = self.env.open_db(b"__meta__", create=True)
        self.db = self.env.open_db(self.table_name.encode("utf-8"), create=True)
        # initialize counter if missing
        with self.env.begin(write=True) as txn:
            if txn.get(b"next_id", db=self.meta_db) is None:
                txn.put(b"next_id", struct.pack(">Q", 0), db=self.meta_db)

    # ---------- helpers ----------
    def _grow_mapsize(self, factor=2.0, minimum_increment_mb=64):
        info = self.env.info()
        new_size = max(int(info["map_size"] * factor), info["map_size"] + minimum_increment_mb * (1 << 20))
        self.env.set_mapsize(new_size)

    @staticmethod
    def _pack_id(n: int) -> bytes:
        return struct.pack(">Q", n)          # 8-byte big-endian

    @staticmethod
    def _unpack_id(b: bytes) -> int:
        return struct.unpack(">Q", b)[0]

    # ---------- public API ----------
    def write_row(self, row_id=None, **kwargs):
        """Atomically allocate/increment row ID (if None) and write the row."""
        if self.env is None or self.db is None:
            raise Exception("Database is not open. Call open() first.")
        
                # 2) If caller provided SiteID, coerce/check row_id against it
        if "SiteID" in kwargs:
            site_id = kwargs["SiteID"]
            if row_id is None:
                row_id = site_id
        
        payload = json.dumps(kwargs, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        while True:
            try:
                with self.env.begin(write=True) as txn:
                    if row_id is None:
                        # allocate new id
                        raw = txn.get(b"next_id", db=self.meta_db)
                        curr = self._unpack_id(raw) if raw else 0
                        new_id = curr + 1
                        txn.put(b"next_id", self._pack_id(new_id), db=self.meta_db)
                        key = self._pack_id(new_id)
                        txn.put(key, payload, db=self.db, append=True)
                        return str(new_id)
                    else:
                        if isinstance(row_id, str):
                            # treat as alphanumeric ID
                            key = row_id.encode("utf-8")
                        else:
                            # treat as integer
                            rid = int(row_id)
                            key = self._pack_id(rid)
                        txn.put(key, payload, db=self.db)
                        return str(rid)
            except lmdb.MapFullError:
                self._grow_mapsize()
                # retry

    def read_row(self, row_id):
        if self.env is None or self.db is None:
            raise Exception("Database is not open. Call open() first.")
        rid = int(row_id)
        key = self._pack_id(rid)
        with self.env.begin(db=self.db) as txn:
            data = txn.get(key)
            return None if data is None else json.loads(data.decode("utf-8"))

    def query_rows(self):
        """Return all rows as a DataFrame with numeric-sorted row_id."""
        if self.env is None or self.db is None:
            raise Exception("Database is not open. Call open() first.")

        rows = []
        with self.env.begin(db=self.db) as txn:
            with txn.cursor() as cur:
                for k, v in cur:
                    # keys are binary 8-byte ids; meta is in meta_db, so no need to skip
                    rid = self._unpack_id(k)
                    row = json.loads(v.decode("utf-8"))
                    row["row_id"] = rid
                    rows.append(row)

        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows).set_index("row_id").sort_index()
        df.index = df.index.map(str)  # keep your original string-like index feel
        df.index.name = None
        return df

    def delete_table(self):
        if self.env is None or self.db is None:
            raise Exception("Database is not open. Call open() first.")
        with self.env.begin(write=True) as txn:
            txn.drop(self.db, delete=True)
            # reset counter too
            txn.put(b"next_id", self._pack_id(0), db=self.meta_db)
        self.db = self.env.open_db(self.table_name.encode("utf-8"), create=True)

    def close(self):
        if self.env:
            self.env.close()
            self.env = None
            self.db = None
            self.meta_db = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
