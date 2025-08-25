import os
import numpy as np
import pandas as pd


class CropCom:
    """
    Class for handling CROPCOM.DAT file.
    """

    # Columns that need to be split into integer and decimal parts
    split_columns = ['DLAP1', 'DLAP2', 'WAC2', 'PPLP1', 'PPLP2', 'FRST1', 'FRST2']
    
    def __init__(self, path):
        """
        Load data from a file into DataFrame.
        """
        wd = [5, 5] + [8] * 58 + [50]
        if not path.endswith('.DAT'): 
          path = os.path.join(path, 'CROPCOM.DAT')
        self.data = pd.read_fwf(path, widths=wd, skiprows=1)
        self.path = path
        with open(path, 'r') as file:
            self.header = [file.readline() for _ in range(2)]
        self.name = 'CROPCOM'
        self.vars = None
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
        cols = self.vars['Parm'].values
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
        cols = self.vars['Parm'].values
        values_split = np.split(values, self.split[:-1])
        for i, id in enumerate(self.crops):
            self.data.loc[self.data['#'] == id, cols] = values_split[i]

    def set_sensitive(self, parms_input, crop_codes, all = False):
        """
        Sets sensitive parameters based on a CSV path or list of parameter names.
        If `all` is True, all parameters are considered sensitive.

        Args:
            parms_input (str or list): Either a CSV file path or list of parameter names to select
            crop_codes (list): List of crop codes to apply parameters to
            all (bool): If True, all parameters are considered sensitive regardless of input

        """
        # Get path to CROPCOM.sens in same folder as CROPCOM.DAT
        sens_path = os.path.join(os.path.dirname(self.path), 'CROPCOM.sens')
        
        if all:
            vars = pd.read_csv(sens_path)
            vars['Select'] = 1
            vars['Range'] = vars.apply(lambda x: (x['Min'], x['Max']), axis=1)
        else:
            if isinstance(parms_input, str):
                # Single CSV path provided
                vars = pd.read_csv(parms_input)
                vars['Select'] = vars.get('Select', False)
                vars = vars[vars['Select'] == 1]
            else:
                # List of parameter names provided
                vars = pd.read_csv(sens_path)
                vars['Select'] = vars['Parm'].isin(parms_input)
                vars = vars[vars['Select'] == 1]
            vars['Range'] = vars.apply(lambda x: (x['Min'], x['Max']), axis=1)
            
        self.vars = vars.copy()
        self.crops = crop_codes
        self.split = np.cumsum([len(self.vars)]*len(crop_codes))
        
    def constraints(self):
        """
        Returns the constraints (min, max ranges) for the parameters.
        """
        return list(self.vars['Range'].values)*len(self.crops)
    
    def var_names(self):
        names = []
        for crop in self.crops:
            temp = [f'{p}_{crop}' for p in list(self.vars['Parm'].values)]
            names.extend(temp)
        return names

