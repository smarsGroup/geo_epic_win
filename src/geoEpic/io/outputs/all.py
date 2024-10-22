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
        
        
class DWC:
    def __init__(self, file_path):
        """
        Initialize the DWC object by reading from a DWC file.
        """
        name = os.path.basename(file_path)
        self.name = (name.split('.'))[0]
        self.data = self._readDWC(file_path)

    def _readDWC(self, file_path):
        """
        Private method to read DWC data.
        """
        data = pd.read_csv(file_path, sep="\s+", skiprows = 10)
        if data.empty: raise ValueError('Data is Empty')
        data['Date'] = pd.to_datetime(data[['Y', 'M', 'D']].astype(str).agg('-'.join, axis=1))
        return data

    def get_var(self, varname):
        """
        Extract variable from the DWC data.
        """
        return self.data[['Date', varname]].copy()


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
    


class DTP:
    def __init__(self, file_path):
        """
        Initialize the DTP object by reading from a DTP file.
        """
        name = os.path.basename(file_path)
        self.name = (name.split('.'))[0]
        self.data = self._readDTP(file_path)

    def _readDTP(self, file_path):
        """
        Private method to read DTP data.
        """
        data = pd.read_csv(file_path, sep="\s+", skiprows = 12)
        if data.empty: raise ValueError('Data is Empty')
        data['Date'] = pd.to_datetime(data[['Y', 'M', 'D']].astype(str).agg('-'.join, axis=1))
        return data

    def get_var(self, varname):
        """
        Extract variable from the DTP data.
        """
        return self.data[['Date', varname]].copy()


class DCS:
    def __init__(self, file_path):
        """
        Initialize the DCS object by reading from a DCS file.
        """
        name = os.path.basename(file_path)
        self.name = (name.split('.'))[0]
        self.data = self._readDCS(file_path)

    def _readDCS(self, file_path):
        """
        Private method to read DCS data.
        """
        data = pd.read_csv(file_path, sep="\s+", skiprows = 12)
        if data.empty: raise ValueError('Data is Empty')
        data['Date'] = pd.to_datetime(data[['Y', 'M', 'D']].astype(str).agg('-'.join, axis=1))
        return data

    def get_var(self, varname):
        """
        Extract variable from the DCS data.
        """
        return self.data[['Date', varname]].copy()
    
    
class ACM:
    def __init__(self, file_path):
        """
        Initialize the ACM object by reading from an ACM file.
        """
        name = os.path.basename(file_path)
        self.name = (name.split('.'))[0]
        self.data = self._readACM(file_path)

    def _readACM(self, file_path):
        """
        Private method to read ACM data.
        """
        widths = [5, 5, 5] + [9] * 24
        data = pd.read_fwf(file_path, widths=widths)
        if data.empty: raise ValueError('Data is Empty')

        data.columns = ["Y", "RT#", "PRCP", "ET_pot", "ET", "Q", "SSF", "PRK", "CVF", "MUSS", "YW", "GMN",
                        "NMN", "NFIX", "NITR", "AVOL", "DN", "YON", "QNO3", "SSFN", "PRKN", "MNP", "YP",
                        "QAP", "PRKP", "LIME", "OCPD", "TOC", "APBC", "TAP", "TNO3"]
        return data

    def get_var(self, varname):
        """
        Extract variable from the ACM data.
        """
        return self.data[[varname]].copy()
