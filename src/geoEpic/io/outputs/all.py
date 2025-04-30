import os
import numpy as np
import pandas as pd


class ACY: 
    def __init__(self, file_path):
        """
        Initialize the ACY object by reading from an ACY file.
        """
        name = os.path.basename(file_path)
        self.name = (name.split('.'))[0]
        self.data = self._readACY(file_path)

    def _readACY(self, file_path):
        """
        Private method to read ACY data.
        """
        data = pd.read_csv(file_path, sep="\s+", skiprows = 10)
        if data.empty: raise ValueError('Data is Empty')
        return data

    def get_var(self, varname):
        """
        Extract variable from the ACY data.
        """
        if varname=='CPNM':
            var_data = self.data[['YR', varname]].copy()
        else:    
            var_data = self.data[['YR', 'CPNM', varname]].copy()
        var_data = var_data.reset_index().sort_values('YR')
        return var_data
    

class DGN:
    def __init__(self, file_path):
        """
        Initialize the DGN object by reading from a DGN file.
        """
        name = os.path.basename(file_path)
        self.name = (name.split('.'))[0]
        self.data = self._readDGN(file_path)

    def _readDGN(self, file_path):
        """
        Private method to read DGN data.
        """
        data = pd.read_csv(file_path, sep="\s+", skiprows = 10)
        if data.empty: raise ValueError('Data is Empty')
        data['Date'] = pd.to_datetime(data[['Y', 'M', 'D']].astype(str).agg('-'.join, axis=1))
        return data

    def get_var(self, varname):
        """
        Extract variable from the DGN data.
        """
        if varname == 'AGB':
            var_data = self.data[['Date']].copy()
            var_data['AGB'] = self.data['BIOM'] - self.data['RW']
        else:
            var_data = self.data[['Date', varname]].copy()
        
        return var_data
    
