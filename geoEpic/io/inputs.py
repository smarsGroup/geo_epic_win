import os
import numpy as np
import pandas as pd
from tqdm import tqdm
from datetime import datetime

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

    def validate(self, start_year, end_year):
        date_range = pd.date_range(start=f'{start_year}-01-01', end=f'{end_year}-12-31', freq='D')
        expected_df = pd.DataFrame({
            'year': date_range.year,
            'month': date_range.month,
            'day': date_range.day
        })

        # Merge with original DataFrame to check for missing dates
        merged_df = pd.merge(expected_df, self, on=['year', 'month', 'day'], how='left')
        
        if self.isnull().values.any():
            print("The DataFrame contains NaN values.")
            return False
    
        missing_dates = merged_df[merged_df.isnull().any(axis=1)]
        if not missing_dates.empty:
            print("Missing rows for the following dates:")
            print(missing_dates[['year', 'month', 'day']])
            return False

        return True

    def save(self, path):
        """
        Save DataFrame into a DLY file.
        """
        path = str(path)
        if not path.endswith('.DLY'): path += '.DLY'
        with open(path, 'w') as ofile:
            fmt = '%6d%4d%4d%6.2f%6.2f%6.2f%6.2f%6.2f%6.2f'
            np.savetxt(ofile, self.values[:], fmt = fmt)
    
    
    def to_monthly(self, path):
        """
        Save as monthly file
        """
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
        
        lines = ['Monthly', ' ']
        fmt = "%6.2f%6.2f%6.2f%6.2f%6.2f%6.2f%6.2f%6.2f%6.2f%6.2f%6.2f%6.2f%5s"
        for i, row in enumerate(values):
            line = fmt % tuple(row.tolist() + [str(ss.columns[i])])
            lines.append(line)
        
        path = str(path)
        if not path.endswith('.INP'): path += '.INP'
        with open(path, 'w') as ofile:
            ofile.write('\n'.join(lines))
            
        return ss



class OPC(pd.DataFrame):
    _metadata = ['header', 'name', 'prms', 'start_year']

    # Class attributes for codes
    plantation_codes = [2, 3]
    harvest_code = 650
    fertilizer_code = 71

    @classmethod
    def load(cls, path):
        """
        Load data from an OPC file into DataFrame.
        
        Parameters:
        path (str): Path to the OPC file.

        Returns:
        OPC: An instance of the OPC class containing the loaded data.
        """
        path = str(path)
        if not path.endswith('.OPC'): path += '.OPC'
        widths = [3, 3, 3, 5, 5, 5, 5, 8, 8, 8, 8, 8, 8, 8, 8]
        data = pd.read_fwf(path, widths=widths, skiprows=2, header=None)
        data = data.dropna().astype(float)
        data.columns = ['Yid', 'Mn', 'Dy', 'CODE', 'TRAC', 'CRP', 'XMTU', 'OPV1', 'OPV2', 'OPV3',
                        'OPV4', 'OPV5', 'OPV6', 'OPV7', 'OPV8']
        inst = cls(data)
        with open(path, 'r') as file:
            inst.header = [file.readline() for _ in range(2)]
            try:
                start_year_line = inst.header[0].strip().split(':')[1].strip()
                inst.start_year = int(start_year_line)
            except (IndexError, ValueError):
                inst.start_year = 2006  # Default start year
                inst.header[0] = inst.header[0].strip() + ' : ' + str(inst.start_year) + '\n'

        inst.name = path.split('/')[-1]
        return inst

    def save(self, path):
        """
        Save DataFrame into an OPC file.

        Parameters:
        path (str): Path to save the OPC file.
        """
        # Check if the path is a directory
        if not os.path.isdir(path):
            raise ValueError(f"The specified path '{path}' is not a valid directory.")
    
        with open(f'{path}/{self.name}', 'w') as ofile:
            ofile.write(''.join(self.header))
            fmt = '%3d%3d%3d%5d%5d%5d%5d%8.3f%8.2f%8.2f%8.3f%8.2f%8.2f%8.2f%8.2f'
            np.savetxt(ofile, self.values, fmt=fmt)

    def auto_irrigation(self, on = True):
        luc, irr = self.header[1][:4], self.header[1][4:]
        if on:
            self.header[1] = luc + '  72' + '\n'
        else: 
            self.header[1] = luc + '   0' + '\n'

    def edit_plantation_date(self, year_id, month, day, crop_code=None):
        """
        Edit the plantation date for a given year and optionally crop code.

        Parameters:
        year_id (int): Year identifier.
        month (int): Month of plantation.
        day (int): Day of plantation.
        crop_code (int, optional): Crop code. If not provided, the first instance is changed.
        """
        if crop_code is not None:
            plantation_idx = self[(self['CODE'].isin(self.plantation_codes)) & (self['Yid'] == year_id) & (self['CRP'] == crop_code)].index
        else:
            plantation_idx = self[(self['CODE'].isin(self.plantation_codes)) & (self['Yid'] == year_id)].index

        if not plantation_idx.empty:
            self.loc[plantation_idx[0], ['Mn', 'Dy']] = [month, day]

    def edit_fertilizer_rate(self, rate, year_id=15, month=None, day=None):
        """
        Edit the fertilizer rate for a given year.

        Parameters:
        rate (float): Fertilizer rate to be set.
        year_id (int, optional): Year identifier. Defaults to 15.
        month (int, optional): Month for the fertilizer rate application.  If not provided, the first instance is changed.
        day (int, optional): Day for the fertilizer rate application. Defaults to None.
        """
        condition = (self['CODE'] == self.fertilizer_code) & (self['Yid'] == year_id)
        if month is not None and day is not None:
            condition &= (self['Mn'] == month) & (self['Dy'] == day)
            if condition.any():
                last_index = self[condition].index[-1]
                self.loc[last_index, 'OPV1'] = 0.2 if rate == 0 else rate
        else:
            if condition.any():
                last_index = self[condition].index[-1]
                self.loc[last_index, 'OPV1'] = 0.2 if rate == 0 else rate

    def edit_harvest_date(self, year_id, month, day, crop_code=None):
        """
        Edit the harvest date for a given year and optionally crop code.

        Parameters:
        year_id (int): Year identifier.
        month (int): Month of harvest.
        day (int): Day of harvest.
        crop_code (int, optional): Crop code. If not provided, the first instance is changed.
        """
        if crop_code is not None:
            harvest_idx = self[(self['CODE'] == self.harvest_code) & (self['Yid'] == year_id) & (self['CRP'] == crop_code)].index
        else:
            harvest_idx = self[(self['CODE'] == self.harvest_code) & (self['Yid'] == year_id)].index

        if not harvest_idx.empty:
            self.loc[harvest_idx[0], ['Mn', 'Dy']] = [month, day]

    def edit_nrates(self, nrates):
        """
        Edit the fertilizer rates for all years.

        Parameters:
        nrates (list): List of fertilizer rates to be set for each year.
        """
        for i, nrate in enumerate(nrates, start=1):
            self.edit_fertilizer_rate(nrate, i)

    def update_phu(self, dly, cropcom):
        """
        Update the OPV1 value with the calculated PHU from the DLY data for all years.

        Parameters:
        dly (DLY): DLY object containing weather data.
        cropcom (DataFrame): DataFrame containing crop code and TBS values.
        """
        # Convert DLY data to datetime format
        dly['date'] = pd.to_datetime(dly[['year', 'month', 'day']])
        
        # Ensure the cropcom DataFrame columns are of integer type
        cropcom['#'] = cropcom['#'].astype(int)
        cropcom['TBS'] = cropcom['TBS'].astype(float)

        years = self['Yid'].unique()
        for year_id in years:
            # Get plantation and harvest dates from the OPC file
            plantation_date = self[(self['CODE'].isin(self.plantation_codes)) & (self['Yid'] == year_id)].iloc[0]
            harvest_date = self[(self['CODE'] == self.harvest_code) & (self['Yid'] == year_id)].iloc[0]
            
            pd_year = self.start_year + int(plantation_date['Yid']) - 1
            hd_year = self.start_year + int(harvest_date['Yid']) - 1

            pd_date = datetime(pd_year, int(plantation_date['Mn']), int(plantation_date['Dy']))
            hd_date = datetime(hd_year, int(harvest_date['Mn']), int(harvest_date['Dy']))

            # Get the crop code and TBS value
            crop_code = int(plantation_date['CRP'])
            tbs = cropcom.loc[cropcom['#'] == crop_code, 'TBS'].values[0]

            # Filter data between planting date (PD) and harvesting date (HD)
            dat1 = dly[(dly['date'] > pd_date) & (dly['date'] < hd_date)].copy()

            # Calculate Heat Units (HU) and PHU
            HU = (0.5 * (dat1['tmax'] + dat1['tmin'])) - tbs
            HU = HU.clip(lower=0)  # Replace negative values with 0
            phu = HU.sum()

            # Update OPV1 with PHU
            self.loc[(self['CODE'].isin(self.plantation_codes)) & (self['Yid'] == year_id), 'OPV1'] = phu



class SIT:
    def __init__(self, site_info = None):
        """
        Initialize the SiteFile class with a dictionary of site information.

        Parameters:
        site_info (dict): Dictionary containing site information (optional).
        """
        self.template = []
        self.site_info = {
            "ID": None,
            "lat": None,
            "lon": None,
            "elevation": None,
            "slope_length": None,
            "slope_steep": None
        }

        if site_info: self.site_info.update(site_info)

    @classmethod
    def load(cls, file_path):
        """
        Class method to load the .sit file and return a SiteFile instance.

        Parameters:
        file_path (str): Path to the .sit file.

        Returns:
        SiteFile: An instance of the SiteFile class with loaded data.
        """
        instance = cls()
        with open(file_path, 'r') as file:
            instance.template = file.readlines()

        # Extract information based on the template positions
        instance.site_info["ID"] = instance.template[2].split(":")[1].strip()
        instance.site_info["lat"] = float(instance.template[3][0:8].strip())
        instance.site_info["lon"] = float(instance.template[3][8:16].strip())
        instance.site_info["elevation"] = float(instance.template[3][16:24].strip())
        instance.site_info["slope_length"] = float(instance.template[4][48:56].strip())
        instance.site_info["slope_steep"] = float(instance.template[4][56:64].strip())

        return instance

    def save(self, output_dir):
        """
        Save the current site information to a .sit file.

        Parameters:
        output_dir (str): Directory where the .sit file will be saved, or the full path including the .sit extension.
        """
        if not self.site_info["ID"]:
            raise ValueError("Site ID is not set. Cannot write to file.")

        # Determine if output_dir already includes the .sit extension
        if output_dir.endswith('.sit'):
            output_file_path = output_dir
        else:
            output_file_path = os.path.join(output_dir, f"{self.site_info['ID']}.sit")
        
        # Modify the template lines or create a new template if not read from a file
        if not self.template:
            self.template = [''] * 7  # Assuming the template has at least 7 lines
        self.template[0] = 'Crop Simulations\n'
        self.template[1] = 'Prototype\n'
        self.template[2] = f'ID: {self.site_info["ID"]}\n'
        self.template[3] = f'{self.site_info["lat"]:8.2f}{self.site_info["lon"]:8.2f}{self.site_info["elevation"]:8.2f}{self.template[3][24:]}' if len(self.template) > 3 else ''
        self.template[4] = f'{self.template[4][:48]}{self.site_info["slope_length"]:8.2f}{self.site_info["slope_steep"]:8.2f}{self.template[4][64:]}' if len(self.template) > 4 else ''
        self.template[6] = '                                                   \n' if len(self.template) > 6 else ''
        
        # Write the modified template to the new file
        with open(output_file_path, 'w') as f:
            f.writelines(self.template)

        # print(f"File written to: {output_file_path}")