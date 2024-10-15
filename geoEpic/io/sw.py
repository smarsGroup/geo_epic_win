import pandas as pd
import numpy as np

class DSL:
    def __init__(self, file_path):
        """
        Initialize the DSL object by reading from a DSL file.
        """
        self.filename = file_path.split('/')[-1]
        self.data = self._extractSW(file_path)

    def _convert_SW(self, sw_text):
        sw_values = np.fromstring(sw_text, sep=' ')
        sw_dict = {f"SW{i+1}": val for i, val in enumerate(sw_values[:-1])}
        sw_dict["SWavg"] = sw_values[-1]
        return sw_dict

    def _extractSW(self, file_path):
        with open(file_path, 'r') as file:
            dsl_lines = file.readlines()

        if len(dsl_lines) <= 10:
            columns = ['Date'] + [f'SW{i}' for i in range(1, 16)] + ['SWavg']
            return pd.DataFrame(columns=columns)

        dsl_data = dsl_lines[11:]
        no_days = len(dsl_data) // 57

        dates = [pd.to_datetime(dsl_data[i * 57].replace("  ", "-").strip()) for i in range(no_days)]
        sw_data = [self._convert_SW(dsl_data[i * 57 + 7]) for i in range(no_days)]

        sw_df = pd.DataFrame(sw_data)
        sw_df.insert(0, 'Date', dates)

        return sw_df

    def get_data(self):
        """
        Return stored water data.
        """
        return self.data
