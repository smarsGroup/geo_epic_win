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
            path = os.path.join(path, 'PARM.DAT')
        
        self.data = self.read_parm(path)
        self.path = path
        self.name = 'PARM'
        self.vars = None

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
        cols = self.vars['Parm'].values
        self.data.loc[0, cols] = values
        
    @property
    def current(self):
        """
        Returns the current values of parameters in the DataFrame.
        """
        cols = self.vars['Parm'].values
        return self.data.loc[0, cols]

    def set_sensitive(self, parms_input, all=False):
        """
        Sets sensitive parameters based on a CSV path or list of parameter names.
        If `all` is True, all parameters are considered sensitive.

        Args:
            parms_input (str or list): Either a CSV file path or list of parameter names to select
            all (bool): If True, all parameters are considered sensitive regardless of input

        """
        # Get path to PARM.sens in same folder as PARM.DAT
        sens_path = os.path.join(os.path.dirname(self.path), 'PARM.sens')
        
        if all:
            vars = pd.read_csv(parms_input if isinstance(parms_input, str) else sens_path)
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
        
    def constraints(self):
        """
        Returns the constraints (min, max ranges) for the parameters.
        """
        return list(self.vars['Range'].values)
    
    def var_names(self):
        return list(self.vars['Parm'].values)

    def get_vars(self):
        """
        Returns the vars DataFrame with an additional column containing current values.
        """
        if self.vars is None: return None
        vars_with_current = self.vars.copy()
        # Get current values
        cols = self.vars['Parm'].values
        current_values = self.data.loc[0, cols].values
        vars_with_current['Current'] = current_values
        # Drop specified columns if they exist
        columns_to_drop = ['Range', 'Category', 'Unit', 'ID']
        for col in columns_to_drop:
            if col in vars_with_current.columns:
                vars_with_current.drop(columns=[col], inplace=True)
         # Rename columns
        if 'Parm' in vars_with_current.columns:
            vars_with_current.rename(columns={'Parm': 'Parameter'}, inplace=True)
        if 'Parm.Description' in vars_with_current.columns:
            vars_with_current.rename(columns={'Parm.Description': 'Description'}, inplace=True)
        return vars_with_current
