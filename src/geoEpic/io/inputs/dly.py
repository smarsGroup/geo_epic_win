
import numpy as np
import pandas as pd
import os

from geoEpic.epicfiles import dly as light_dly

class DLY(pd.DataFrame):
    @classmethod
    def load(cls, path):
        """
        Load data from a DLY file into DataFrame.
        """
        path = str(path)
        if not path.endswith('.DLY'): path += '.DLY'
        data = pd.read_fwf(path, widths=[6, 4, 4, 6, 6, 6, 6, 6, 6], header=None)
        data.columns = ['year', 'month', 'day', 'srad', 'tmax', 'tmin', 'prcp', 'rh', 'ws']
        df = cls(data)
        setattr(df, 'basename', os.path.splitext(os.path.basename(path))[0])
        return df

    def validate(self, start_date, end_date):
        """
        Validate the DataFrame to ensure it contains a continuous range of dates 
        between start_date and end_date, without duplicates.
        """
        # Create the full date range
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        expected_df = pd.DataFrame({
            'year': date_range.year,
            'month': date_range.month,
            'day': date_range.day
        })

        # Remove duplicate rows from the DataFrame
        self.drop_duplicates(subset=['year', 'month', 'day'], inplace=True)
        # Merge with expected dates to find any missing rows
        merged_df = pd.merge(expected_df, self, on=['year', 'month', 'day'], how='left')
        # Check for missing dates
        missing_dates = merged_df[merged_df.isnull().any(axis=1)][['year', 'month', 'day']]
        if not missing_dates.empty:
            print("Missing rows for the following dates:")
            print(missing_dates)
            return False
        return True

    def save(self, path=None):
        """
        Save DataFrame into a DLY file.
        """
        if path is None:
            basename = "1" if not hasattr(self, 'basename') else self.basename
            path = f"./{basename}.DLY"
        else:
            path = str(path)
            if not path.endswith('.DLY'): path += '.DLY'
            
        # Formatting lives in the dependency-light writer so this class and the
        # QGIS plugin cannot emit different bytes. Output is pinned by
        # tests/fixtures/weather_2016.DLY.
        self.drop_duplicates(subset=['year', 'month', 'day'], inplace=True)
        light_dly.write(path, self[list(light_dly.COLUMNS)].values.tolist())
    
    
    def to_monthly(self, path=None):
        """Save the monthly statistics (.WP1) and wind (.WND) companions.

        Rendering lives in the dependency-light writer so this class and the
        QGIS plugin cannot emit different bytes. Pinned by
        tests/fixtures/weather_2016.WP1 and .WND.
        """
        basename = "1" if not hasattr(self, 'basename') else self.basename
        if path is None:
            path = f"./{basename}"
        else:
            path = str(path)
            for suffix in ('.WP1', '.WND', '.DLY'):
                if path.upper().endswith(suffix):
                    path = path[:-4]
                    break
        self.drop_duplicates(subset=['year', 'month', 'day'], inplace=True)
        rows = self[list(light_dly.COLUMNS)].to_dict("records")
        light_dly.write_monthly(path, rows, name=basename)
        months, stats = light_dly.monthly_statistics(rows)
        return pd.DataFrame({name: stats[name] for name in light_dly.WP1_ROWS},
                            index=months)
