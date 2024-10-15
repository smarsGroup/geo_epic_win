import pandas as pd
import os
import numpy as np
from datetime import datetime,timedelta
from geoEpic.io import DLY

class OPC(pd.DataFrame):
    _metadata = ['header', 'name', 'prms', 'start_year']

    # Class attributes for codes
    plantation_codes = [2, 3]
    harvest_code = 650
    fertilizer_code = 71

    @classmethod
    def load(cls, path, start_year=None):
        """
        Load data from an OPC file into DataFrame.
        
        Parameters:
        path (str): Path to the OPC file.

        Returns:
        OPC: An instance of the OPC class containing the loaded data.
        """
        path = str(path)
        if not path.endswith('.OPC'): 
            path += '.OPC'
        widths = [3, 3, 3, 5, 5, 5, 5, 8, 8, 8, 8, 8, 8, 8, 8]
        data = pd.read_fwf(path, widths=widths, skiprows=2, header=None)
        data = data.dropna().astype(float)
        data.columns = ['Yid', 'Mn', 'Dy', 'CODE', 'TRAC', 'CRP', 'XMTU', 'OPV1', 'OPV2', 'OPV3',
                        'OPV4', 'OPV5', 'OPV6', 'OPV7', 'OPV8']
        inst = cls(data)
        with open(path, 'r') as file:
            inst.header = [file.readline() for _ in range(2)]
            if start_year is not None:
                inst.start_year = start_year
            else:
                try:
                    start_year_line = inst.header[0].strip().split(':')[1].strip()
                    inst.start_year = int(start_year_line)
                except (IndexError, ValueError):
                    raise ValueError("Bad Input: start_year must be a specified either in file or as param.")
            inst.header[0] = inst.header[0].split(':')[0].strip() + ' : ' + str(inst.start_year) + '\n'
            
        inst.name = path.split('/')[-1]
        return inst

    def save(self, path):
        """
        Save DataFrame into an OPC file.

        Parameters:
        path (str): Path to save the OPC file.
        """
        # Check if the path is a directory
        if os.path.isdir(path):
            path = os.path.join(path,self.name)
    
        final_data = self[self['Yid']>=1]
        with open(f'{path}', 'w') as ofile:
            ofile.write(''.join(self.header))
            fmt = '%3d%3d%3d%5d%5d%5d%5d%8.3f%8.2f%8.2f%8.3f%8.2f%8.2f%8.2f%8.2f'
            np.savetxt(ofile, final_data.values, fmt=fmt)

    def auto_irrigation(self, on = True):
        luc, _ = self.header[1][:4], self.header[1][4:]
        if on:
            self.header[1] = luc + '  72' + '\n'
        else: 
            self.header[1] = luc + '   0' + '\n'

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
            plantation_date = self[(self['CODE'].isin(self.plantation_codes)) & (self['Yid'] == year_id)]
            harvest_date = self[(self['CODE'] == self.harvest_code) & (self['Yid'] == year_id)]
            if plantation_date.empty or harvest_date.empty:
                continue

            plantation_date = plantation_date.iloc[0]
            harvest_date = harvest_date.iloc[0]
            
            pd_year = self.start_year + int(plantation_date['Yid']) - 1
            hd_year = self.start_year + int(harvest_date['Yid']) - 1

            pd_date = datetime(pd_year, int(plantation_date['Mn']), int(plantation_date['Dy']))
            hd_date = datetime(hd_year, int(harvest_date['Mn']), int(harvest_date['Dy']))

            # print(f'{pd_date} {hd_date}')
            # Get the crop code and TBS value
            crop_code = int(plantation_date['CRP'])
            tbs = cropcom.loc[cropcom['#'] == crop_code, 'TBS'].values[0]

            # Filter data between planting date (PD) and harvesting date (HD)
            dat1 = dly[(dly['date'] > pd_date) & (dly['date'] < hd_date)].copy()
            # print(dat1)
            # Calculate Heat Units (HU) and PHU
            HU = (0.5 * (dat1['tmax'] + dat1['tmin'])) - tbs
            HU = HU.clip(lower=0)  # Replace negative values with 0
            phu = HU.sum()
            # print(HU)

            # Update OPV1 with PHU
            self.loc[(self['CODE'].isin(self.plantation_codes)) & (self['Yid'] == year_id), 'OPV1'] = phu

        
    def _get_date(self, year_id, code, crop_code=None):
        """
        Retrieve the plantation date for a specific year.

        Parameters:
        year_id (int): Year identifier.

        Returns:
        datetime: The plantation date or None if not found.
        """
        
        if crop_code is None:
            cur_row = self[(self['Yid'] == year_id) & (self['CODE']==code)]
        else:
            cur_row = self[(self['Yid'] == year_id) & (self['CODE']==code) & (self['CRP']==crop_code)]
            
        if not cur_row.empty:
            year = year_id+self.start_year-1
            month = int(cur_row['Mn'].values[0])
            day = int(cur_row['Dy'].values[0])
            try:
                return datetime(year=year, month=month, day=day), cur_row.index[0]
            except:
                print(self.name) 
                print(year_id, month, day)
        return None, None
    
    def _adjust_pre_planting_operations(self, new_plant_date, year_id, crop_code=None):
        """
        Adjust dates for operations before planting for a specific year based on their index.

        Parameters:
        year_id (int): Year identifier.
        """
        plantation_date, plantation_idx = None, None
        for pc in self.plantation_codes:
            plantation_date, plantation_idx = self._get_date(year_id, pc, crop_code)
            if plantation_date is not None:
                break
        if plantation_idx is not None:
            # Filter for operations before the planting index
            if crop_code is None:
                pre_planting_ops = self[(self['Yid'] == year_id) & (self.index < plantation_idx)]
            else:
                pre_planting_ops = self[(self['Yid'] == year_id) & (self['CRP'] == crop_code) & (self.index < plantation_idx)]
            
            for idx, row in pre_planting_ops.iterrows():
                month = int(self.at[idx, 'Mn'])
                day = int(self.at[idx, 'Dy'])
                cur_opr_date = datetime(new_plant_date.year, month, day)
                offset = plantation_date - cur_opr_date
                adjusted_date = new_plant_date - timedelta(days=offset.days)
                self.at[idx, 'Mn'] = adjusted_date.month
                self.at[idx, 'Dy'] = adjusted_date.day
        
    def _adjust_post_harvesting_operations(self, new_harvest_date, year_id, crop_code=None):
        """
        Adjust dates for operations before planting for a specific year based on their index.

        Parameters:
        year_id (int): Year identifier.
        """
        hc = self.harvest_code
        harvest_date, harvest_idx = self._get_date(year_id,hc,crop_code)
        if harvest_idx is not None:
            # Filter for operations before the planting index
            if crop_code is None:
                post_harvest_ops = self[(self['Yid'] == year_id) & (self.index > harvest_idx)]
            else:
                post_harvest_ops = self[(self['Yid'] == year_id) & (self['CRP'] == crop_code) & (self.index > harvest_idx)]
            
            for idx, row in post_harvest_ops.iterrows():
                month = int(self.at[idx, 'Mn'])
                day = int(self.at[idx, 'Dy'])
                cur_opr_date = datetime(harvest_date.year, month, day)
                offset = cur_opr_date - harvest_date
                adjusted_date = new_harvest_date + timedelta(days=offset.days)
                self.at[idx, 'Mn'] = adjusted_date.month
                self.at[idx, 'Dy'] = adjusted_date.day
    
    def _stretch_middle_operations(self, year_id, new_planting_date, new_harvest_date, crop_code=None):
        prev_plantation_date, plantation_idx = None, None
        for pc in self.plantation_codes:
            prev_plantation_date, plantation_idx = self._get_date(year_id, pc, crop_code)
            if prev_plantation_date is not None:
                break
        prev_harvest_date, harvest_idx = self._get_date(year_id,self.harvest_code,crop_code)
        
        original_range = (prev_harvest_date - prev_plantation_date).days
        new_range = (new_harvest_date - new_planting_date).days
        # Process rows between start_index and end_index
        for idx in range(plantation_idx+1, harvest_idx):
            if idx in self.index:
                row = self.loc[idx]
                # Calculate the scale of the current date
                year = int(row['Yid'])+self.start_year-1
                row_date = datetime(year, int(row['Mn']),int(row['Dy']))
                days_from_start = (row_date - prev_plantation_date).days
                scale = days_from_start / original_range
                
                
                # Calculate the new date
                new_days_from_start = int(scale * new_range)
                new_date = row_date + timedelta(days=new_days_from_start)
                
                # Update the DataFrame in place
                self.at[idx, 'Mn'] = new_date.month
                self.at[idx, 'Dy'] = new_date.day
        

    def edit_plantation_date(self, year, month, day, crop_code=None):
        """
        Edit the plantation date for a given year.

        Parameters:
        year_id (int): Year identifier.
        month (int): Month of plantation.
        day (int): Day of plantation.
        """
        year_id = year-self.start_year+1
        plantation_idx = None
        if crop_code is None:
            plantation_idx = self[(self['CODE'].isin(self.plantation_codes)) & (self['Yid'] == year_id)].iloc[0].name      
        else:
            plantation_idx = self[(self['CODE'].isin(self.plantation_codes)) & (self['Yid'] == year_id) & (self['CRP'] == crop_code)].iloc[0].name
            
        if plantation_idx is not None:
            new_harvest_date, _ = self._get_date(year_id,self.harvest_code,crop_code)
            new_planting_date = datetime(year,month,day)
            self._stretch_middle_operations(year_id, new_planting_date,new_harvest_date,crop_code)
            self._adjust_pre_planting_operations(new_planting_date,year_id,crop_code)
            self.loc[plantation_idx, ['Mn', 'Dy']] = [month, day]
            return
    
    def edit_operation_date(self, code, year, month, day, crop_code=None):
        """
        Edit the operation date for a given year.

        Parameters:
        year_id (int): Year identifier.
        month (int): Month of harvest.
        day (int): Day of harvest.
        """
        year_id = year-self.start_year+1
        if( crop_code is None ):
            op_code_idx = self[(self['CODE'] == code) & (self['Yid'] == year_id)].index
        else:
            op_code_idx = self[(self['CODE'] == code) & (self['Yid'] == year_id) & (self['CRP'] == crop_code)].index
        if not op_code_idx.empty:
            self.loc[op_code_idx, ['Mn', 'Dy']] = [month, day]
            
    def edit_operation_value(self, code, year, value, crop_code=None):
        """
        Edit the operation date for a given year.

        Parameters:
        year_id (int): Year identifier.
        month (int): Month of harvest.
        day (int): Day of harvest.
        """
        year_id = year-self.start_year+1
        if( crop_code is None ):
            op_code_idx = self[(self['CODE'] == code) & (self['Yid'] == year_id)].index
        else:
            op_code_idx = self[(self['CODE'] == code) & (self['Yid'] == year_id) & (self['CRP'] == crop_code)].index
        if not op_code_idx.empty:
            self.loc[op_code_idx, 'OPV1'] = value

    def edit_harvest_date(self, year, month, day, crop_code=None):
        """
        Edit the harvest date for a given year.

        Parameters:
        year_id (int): Year identifier.
        month (int): Month of harvest.
        day (int): Day of harvest.
        """
        year_id = year-self.start_year+1
        hc = self.harvest_code
        harvest_idx
        if crop_code is None:
            harvest_idx = self[(self['CODE'] == hc) & (self['Yid'] == year_id)].index
        else:
            harvest_idx = self[(self['CODE'] == hc) & (self['Yid'] == year_id)  & (self['CRP'] == crop_code)].index
        if not harvest_idx.empty:
            new_planting_date, _ = self._get_date(year_id,hc,crop_code)
            new_harvest_date = datetime(year,month,day)
            self.stretch_middle_operations(year_id,new_planting_date,new_harvest_date,crop_code)
            self._adjust_post_harvesting_operations(new_harvest_date,year_id,crop_code)
            self.loc[harvest_idx, ['Mn', 'Dy']] = [month, day]
            
    def edit_crop_dates(self, year, new_planting_date, new_harvest_date, crop_code=None):
        year_id = year-self.start_year+1
        hc = self.harvest_code
        plantation_idx = None
        if crop_code is None:
            plantation_idx = self[(self['CODE'].isin(self.plantation_codes)) & (self['Yid'] == year_id)].index      
        else:
            plantation_idx = self[(self['CODE'].isin(self.plantation_codes)) & (self['Yid'] == year_id) & (self['CRP'] == crop_code)].index
        
        if crop_code is None:
            harvest_idx = self[(self['CODE'] == hc) & (self['Yid'] == year_id)].index
        else:
            harvest_idx = self[(self['CODE'] == hc) & (self['Yid'] == year_id)  & (self['CRP'] == crop_code)].index
           
        if not plantation_idx.empty:
            self._stretch_middle_operations(year_id, new_planting_date,new_harvest_date,crop_code)
            self._adjust_pre_planting_operations(new_planting_date,year_id,crop_code)
            
        if not harvest_idx.empty:
            self._adjust_post_harvesting_operations(new_harvest_date,year_id,crop_code)
        
        if not plantation_idx.empty:
            self.loc[plantation_idx, ['Mn', 'Dy']] = [new_planting_date.month, new_planting_date.day]
            
        if not harvest_idx.empty:
            self.loc[harvest_idx, ['Mn', 'Dy']] = [new_harvest_date.month, new_harvest_date.day]
        
            
    def append(self,second_opc):
        if not isinstance(second_opc, (pd.DataFrame, OPC)):
            raise ValueError("The 'other' parameter must be a pandas DataFrame or OPC instance.")
        last_yid = self['Yid'].max()
        
        second_opc_copy = second_opc.copy()
        
        if second_opc_copy['Yid'].min()!=0:
            second_opc_copy['Yid'] = (second_opc_copy['Yid'] - second_opc_copy['Yid'].min() + 1)
        second_opc_copy['Yid'] = second_opc_copy['Yid'] + last_yid
        
        combined_data = pd.concat([self, second_opc_copy], ignore_index=True)
        
        combined_opc = OPC(combined_data)
        combined_opc.header = self.header
        combined_opc.start_year = self.start_year
        combined_opc.name = self.name

        return combined_opc
