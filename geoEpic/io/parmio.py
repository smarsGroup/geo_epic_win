import pandas as pd
import numpy as np
from decimal import Decimal
import os

class CropCom:
    
    def __init__(self, path):
        """
        Load data from a file into DataFrame.
        """
        wd = [5, 5] + [8] * 58 + [50]
        if not path.endswith('.DAT'): 
          path = os.path.join(path, 'CROPCOM.DAT')
        self.data = pd.read_fwf(path, widths=wd, skiprows=1)
        with open(path, 'r') as file:
            self.header = [file.readline() for _ in range(2)]
        self.name = 'CROPCOM'
        self.prms = None
        self.split_columns = ['DLAP1', 'DLAP2', 'WAC2', 'PPLP1', 'PPLP2']
        self.original_columns = self.data.columns.tolist()
        
        # Split the specified columns
        self._split_integer_decimal()

    def _split_integer_decimal(self):
        for col in self.split_columns:
            int_col = col + '_v1'
            dec_col = col + '_v2'
            self.data[int_col] = np.floor(self.data[col])
            self.data[dec_col] = (self.data[col] - self.data[int_col])*100
            int_idx = self.data.columns.get_loc(col)
            self.data.insert(int_idx + 1, dec_col, self.data.pop(dec_col))
            self.data.insert(int_idx + 1, int_col, self.data.pop(int_col))

    def _combine_integer_decimal(self):
        data = self.data.copy()
        for col in self.split_columns:
            int_col = col + '_v1'
            dec_col = col + '_v2'
            data[col] = data[int_col].astype(int) + data[dec_col]/100
            data.drop(columns=[int_col, dec_col], inplace=True)
        data = data[self.original_columns]
        return data

    @property
    def current(self):
        """
        Returns the current values of parameters in the DataFrame.
        """
        cols = self.prms['Parm'].values
        all_values = []
        for crop in self.crops:
            crop_values = self.data.loc[self.data['#'] == crop, cols].values.flatten()
            all_values.append(crop_values)
        concatenated_values = np.concatenate(all_values)
        return concatenated_values

    def save(self, path):
        """
        Save DataFrame into an OPC file.
        """
        data = self._combine_integer_decimal()
        if not path.endswith('.DAT'): 
          path = os.path.join(path, 'CROPCOM.DAT')
        with open(path, 'w') as ofile:
            ofile.write(''.join(self.header))
            fmt = '%5d%5s' + '%8.2f'*11 + '%8.4f' + \
              '%8.2f'*5 + '%8.4f'*3 + '%8.2f'*6 + '%8.4f'*9 + \
              '%8.3f'*3 + '%8d' + '%8.2f'*18 + '%8.3f' + '  %s'
            np.savetxt(ofile, data.values, fmt = fmt)
    
    def edit(self, values):
        """
        Updates the parameters in the DataFrame with new values.
        """
        cols = self.prms['Parm'].values
        values_split = np.split(values, self.split[:-1])
        for i, id in enumerate(self.crops):
            self.data.loc[self.data['#'] == id, cols] = values_split[i]

    def set_sensitive(self, df_paths, crop_codes, all = False):
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
        self.crops = crop_codes
        self.split = np.cumsum([len(self.prms)]*len(crop_codes))
    
    def constraints(self):
        """
        Returns the constraints (min, max ranges) for the parameters.
        """
        return list(self.prms['Range'].values)*len(self.crops)
    
    def var_names(self):
        names = []
        for crop in self.crops:
            temp = [f'{p}_{crop}' for p in list(self.prms['Parm'].values)]
            names.extend(temp)
        return names


class ieParm:

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
