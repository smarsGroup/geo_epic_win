import os
import numpy as np
import pandas as pd

class ACY: 
    def __init__(self, file_path):
        """
        Initialize the ACY object by reading from an ACY file.
        """
        if not isinstance(file_path, (str, os.PathLike)):
            file_path = file_path.outputs['ACY']
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
        if not isinstance(file_path, (str, os.PathLike)):
            file_path = file_path.outputs['DGN']
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


class DWC:
    def __init__(self, file_path):
        """
        Initialize the DWC object by reading from a DWC file.
        """
        if not isinstance(file_path, (str, os.PathLike)):
            dwc_file_path = file_path.outputs['DWC']
            acy_file_path = file_path.outputs['ACY']
        else:
            # Derive ACY file path from DWC file path
            base_dir = os.path.dirname(file_path)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            acy_file_path = os.path.join(base_dir, f"{base_name}.ACY")
        
        name = os.path.basename(dwc_file_path)
        self.name = (name.split('.'))[0]
        self.data = self._readDWC(dwc_file_path, acy_file_path)

    def _readDWC(self, file_path, acy_file_path):
        """
        Private method to read DWC data and merge with ACY data.
        """
        data = pd.read_csv(file_path, sep="\s+", skiprows = 10)
        if data.empty: raise ValueError('Data is Empty')
        data['Date'] = pd.to_datetime(data[['Y', 'M', 'D']].astype(str).agg('-'.join, axis=1))
        data['ET'] = pd.to_numeric(data['ET'], errors='coerce')
        
        # Read ACY data and merge CPNM column
        if os.path.exists(acy_file_path):
            acy_data = pd.read_csv(acy_file_path, sep="\s+", skiprows = 10)
            if not acy_data.empty:
                # Merge on YR (from ACY) and Y (from DWC)
                data = data.merge(acy_data[['YR', 'CPNM']], left_on='Y', right_on='YR', how='left')
                data = data.drop('YR', axis=1)
        return data

    def get_var(self, varname):
        """
        Extract variable from the DWC data.
        """
        if 'CPNM' in self.data.columns:
            var_data = self.data[['Y', 'M', 'Date', 'CPNM', varname]].copy()
        else:
            var_data = self.data[['Y', 'M', 'Date', varname]].copy()
        return var_data