
import numpy as np
import pandas as pd

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
        return cls(data)

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

    def save(self, path):
        """
        Save DataFrame into a DLY file.
        """
        path = str(path)
        # Remove duplicate rows from the DataFrame
        self.drop_duplicates(subset=['year', 'month', 'day'], inplace=True)
        if not path.endswith('.DLY'): path += '.DLY'
        columns = ['year', 'month', 'day', 'srad', 'tmax', 'tmin', 'prcp', 'rh', 'ws']
        with open(path, 'w') as ofile:
            fmt = '%6d%4d%4d%6.2f%6.2f%6.2f%6.2f%6.2f%6.2f'
            np.savetxt(ofile, self[columns].values, fmt = fmt)
    
    
    def to_monthly(self, path):
        """
        Save as monthly file
        """
        # Remove duplicate rows from the DataFrame
        self.drop_duplicates(subset=['year', 'month', 'day'], inplace=True)
        grouped = self.groupby('month')
        # Calculate mean for all columns except 'prcp'
        ss = grouped.mean()
        dayinmonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        ss['prcp'] = ss['prcp'] * dayinmonth
        # Standard deviations
        ss['sdtmx'] = grouped['tmax'].std()
        ss['sdtmn'] = grouped['tmin'].std()
        ss['sdrf'] = grouped['prcp'].std()
        # Additional calculations
        ss['dayp'] = grouped.apply(lambda x: (x['prcp'] > 0.5).sum() / len(x))
        ss['skrf'] = 3 * abs(ss['prcp'] - ss['prcp'].median()) / ss['sdrf']
        ss['prw1'] = grouped.apply(lambda x: np.sum(np.diff(x['prcp'] > 0.5) == -1) / len(x))
        # ss['prw2'] = grouped.apply(lambda x: np.sum((x['prcp'] > 0.5).shift().fillna(False) & (x['prcp'] > 0.5)) / len(x))
        ss['prw2'] = grouped.apply(lambda x: np.sum((x['prcp'].fillna(0) > 0.5).shift(fill_value=False) & (x['prcp'].fillna(0) > 0.5)) / len(x))
        ss['wi'] = 0
        # Reorder columns
        ss = ss[['tmax', 'tmin', 'prcp', 'srad', 'rh', 'ws', 'sdtmx', 'sdtmn', 'sdrf', 'dayp', 'skrf', 'prw1', 'prw2', 'wi']]
        ss.columns = ['OBMX', 'OBMN', 'RMO', 'OBSL', 'RH','UAVO', 'SDTMX', 'SDTMN','RST2', 'DAYP', 'RST3', 'PRW1', 'PRW2', 'WI']
        order = [0, 1, 6, 7, 2, 8, 10, 11, 12, 9, 13, 3, 4, 5]
        ss = ss[ss.columns[order]]
        values = np.float64(ss.T.values)
        
        lines = ['Monthly Weather', 'Statistics']
        fmt = "%10.2f%10.2f%10.2f%10.2f%10.2f%10.2f%10.2f%10.2f%10.2f%10.2f%10.2f%10.2f%8s"
        for i, row in enumerate(values):
            line = fmt % tuple(row.tolist() + [str(ss.columns[i])])
            lines.append(line)
        
        path = str(path)
        if not path.endswith('.WP1'): path += '.WP1'
        with open(path, 'w') as ofile:
            ofile.write('\n'.join(lines))
            
        # Generate WND file
        wnd_path = path.replace('.WP1', '.WND')
        with open(wnd_path, 'w') as wnd_file:
            # Write station name (placeholder)
            wnd_file.write("Monthly Wind Statistics\n")
            # Write two placeholder values
            wnd_file.write("     .00     .00\n")
            # Write last row of values (UAVO - wind speed)
            wind_speeds = [f"{speed:10.2f}" for speed in values[-1]]
            wnd_file.write("".join(wind_speeds) + "\n")
            # Write 16 lines of zeros (4 to 19)
            for _ in range(16):
                wnd_file.write("".join([f"{0.0:10.1f}" for _ in range(12)]) + "\n")
        return ss

