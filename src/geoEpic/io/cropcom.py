import os
import numpy as np
import pandas as pd


class CropCom:
    """
    Class for handling CROPCOM.DAT file.
    """

    # Columns that need to be split into integer and decimal parts
    split_columns = ['DLAP1', 'DLAP2', 'WAC2', 'PPLP1', 'PPLP2']
    
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

