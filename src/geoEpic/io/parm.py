import os
import numpy as np
import pandas as pd
from decimal import Decimal


class Parm:

    def __init__(self, path):
        """
        Load data from an ieParm file into DataFrame.
        """
        if not path.endswith('.DAT'): 
            path = os.path.join(path, 'ieParm.DAT')
        
        self.data = self.read_parm(path)
        self.name = 'ieParm'
        self.prms = None

    def read_parm(self, file_name):
        """
        Reads and constructs a DataFrame from a .DAT file.
        """
        # Read the first part of the file with two columns of width 8 each
        parm1 = pd.read_fwf(file_name, widths=[8, 8], header=None, nrows=30, skip_blank_lines=False)
        parm2 = pd.read_fwf(file_name, widths=[8] * 10, header=None, skiprows=30, nrows=13, skip_blank_lines=False)

        # Flatten parm1 and parm2 data, then concatenate
        parm1_flattened = parm1.values.T.ravel()
        parm2_flattened = parm2.values.flatten()
        self.nan_mask = np.isnan(parm2_flattened)
        parm2_cleaned = parm2_flattened[~self.nan_mask]  # Remove NaNs

        # Combine all parts into one DataFrame
        data = np.concatenate([parm1_flattened, parm2_cleaned])
        column_names = ["SCRP1_" + str(i) for i in range(1, 31)] + \
                       ["SCRP2_" + str(i) for i in range(1, 31)] + \
                       ["PARM" + str(i) for i in range(1, 113)]
        df = pd.DataFrame([data], columns=column_names)
        return df

    def save(self, path):
        """
        Saves the current DataFrame to a .DAT file.
        """
        if not path.endswith('.DAT'): 
            path = os.path.join(path, 'ieParm.DAT')
        PARM1 = self.data[[col for col in self.data.columns if "SCRP" in col]]
        PARM2 = self.data[[col for col in self.data.columns if "PARM" in col]]
        
        PARM1_data = PARM1.values.reshape((2, 30)).T
        PARM2_values = PARM2.values.flatten()
        full_parm2_data = np.empty(self.nan_mask.size)
        full_parm2_data[:] = np.nan
        full_parm2_data[~self.nan_mask] = PARM2_values
        PARM2_data = full_parm2_data.reshape((13, 10))
        
        s = ''
        for row in PARM2_data:
            for col in row:
                if np.isnan(col): break
                max_dec = 7 - len(str(int(col)))
                col = np.round(col, max_dec)
                dec = 0 if col == int(col) else len(str(Decimal(str(col))).split(".")[1])
                if dec <= 2: fmt = "%8.2f"
                else: fmt = f"%8.{dec}f"
                s += fmt % col
            s += '\n'

        with open(path, 'w') as file:
            np.savetxt(file, PARM1_data[:-3], fmt='%8.2f%8.2f')
            file.write('\n')
            np.savetxt(file, PARM1_data[-2:], fmt='%8.2f%8.2f')
            file.write(s)

    def edit(self, values):
        """
        Updates the parameters in the DataFrame with new values.
        """
        cols = self.prms['Parm'].values
        self.data.loc[0, cols] = values
        
    @property
    def current(self):
        """
        Returns the current values of parameters in the DataFrame.
        """
        cols = self.prms['Parm'].values
        return self.data.loc[0, cols]

    def set_sensitive(self, df_paths, all=False):
        """
        Sets sensitive parameters based on a list of CSV paths or a single CSV path.
        If `all` is True, all parameters are considered sensitive.

        Args:
            df_paths (list or str): A list of CSV file paths or a single CSV file path.
            all (bool): If True, all parameters are considered sensitive regardless of the CSV contents.

        """
        if isinstance(df_paths, str):
            df_paths = [df_paths]  # Convert a single path into a list for uniform processing
        if all:
            prms = pd.read_csv(df_paths[0])
            prms['Select'] = 1
            prms['Range'] = prms.apply(lambda x: (x['Min'], x['Max']), axis=1)
        else:
            prms = pd.read_csv(df_paths[0])
            prms['Select'] = prms.get('Select', False)  # Ensure 'Select' column exists
            for sl in df_paths[1:]:
                df_temp = pd.read_csv(sl)
                df_temp['Select'] = df_temp.get('Select', False)  # Ensure 'Select' column exists
                prms['Select'] |= df_temp['Select']  # Combine selections with logical OR
            # Filter parameters where 'Select' is True
            prms = prms[prms['Select'] == 1]
            prms['Range'] = prms.apply(lambda x: (x['Min'], x['Max']), axis=1)
        self.prms = prms.copy() 
        
    def constraints(self):
        """
        Returns the constraints (min, max ranges) for the parameters.
        """
        return list(self.prms['Range'].values)
    
    def var_names(self):
        return list(self.prms['Parm'].values)
