import requests
import json
import pandas as pd

class SoilDataAccess:
    BASE_URL = "https://sdmdataaccess.nrcs.usda.gov/Tabular/SDMTabularService/post.rest"

    @staticmethod
    def query(query):
        """
        Performs a query to the NRCS Soil Data Access service.

        Args:
        query (str): The SQL query to execute.

        Returns:
        pd.DataFrame: A DataFrame containing the results of the query.

        Raises:
        ValueError: If no data is found for the provided query.
        requests.RequestException: If there is an issue with the network request.
        """
        request_params = {
            "format": "JSON+COLUMNNAME",
            "query": query
        }
        
        try:
            response = requests.post(url=SoilDataAccess.BASE_URL, json=request_params)
            response.raise_for_status()  # Check for HTTP errors
        except requests.RequestException as e:
            raise requests.RequestException(f"Network error occurred: {e}")

        try:
            response_data = response.json()
        except ValueError:
            raise ValueError("Invalid JSON response received.")

        if response_data.get('Table'):
            columns = response_data['Table'][0]
            data = response_data['Table'][1:]
            if not data:
                raise ValueError("No data found for the provided query.")
            return pd.DataFrame(data, columns=columns)
        else:
            raise ValueError("No data found for the provided query.")
    
    @staticmethod
    def _mukey_condition(input_value):
        """
        Generate the appropriate SQL condition for mukey based on the input type.

        Args:
        input_value (int or str): The input value representing either a mukey (int) or a WKT location (str).

        Returns:
        str: A SQL condition string for use in queries.
        """
        if isinstance(input_value, int):
            return f"'{input_value}'"
        elif isinstance(input_value, str):
            return f"SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{input_value}')"
        else:
            raise ValueError("Input must be an integer (mukey) or a string (WKT).")
        
    @staticmethod
    def get_mukey(wkt):
        """
        Fetches the mukey for a given WKT location.

        Args:
        wkt (str): The WKT location.

        Returns:
        int: The mukey for the specified location.
        """
        query = f"""
        SELECT mukey
        FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{wkt}')
        """
        result = SoilDataAccess.query(query)
        return result['mukey'].values[0]
    
    @staticmethod
    def get_mukey_list(wkt):
        """
        Fetches the mukey for a given WKT location.

        Args:
        wkt (str): The WKT location.

        Returns:
        int: The mukey for the specified location.
        """
        query = f"""
        SELECT mukey
        FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{wkt}')
        """
        result = SoilDataAccess.query(query)
        return result['mukey'].values
    
    @staticmethod
    def get_cokey_from_wkt(wkt_string):
        """
        Fetches a list of cokey (Component Key) values based on a WKT spatial location.

        Args:
        wkt_string (str): A WKT string representing the spatial location (e.g., POLYGON, POINT).

        Returns:
        List[int]: A list of cokey values corresponding to the input WKT location.
        """

        # Step 1: Query the mapunit table to get mukey values based on WKT
        mukey_list = SoilDataAccess.get_mukey_list(wkt_string)

        if len(mukey_list)==0:
            raise ValueError("No map units found for the given WKT location.")

        # Step 2: Query the component table to get cokey values for the corresponding mukey values
        cokey_query = f"""
        SELECT mukey, cokey
        FROM component
        WHERE mukey IN ({', '.join(map(str, mukey_list))})
        """

        # Run the query and get the list of cokey values
        print(f"Running cokey query: {cokey_query}")

        result = SoilDataAccess.query(cokey_query)
        if result.empty:
            raise ValueError("No components found for the map units corresponding to the WKT location.")
        return result

        
    @staticmethod
    def fetch_properties(input_value):
        """
        Fetches soil data based on the input value. If the input is an integer, it is used as mukey. If the input is a string, it is used as WKT.

        Args:
        input (int or str): The input value representing either a mukey (int) or a WKT location (str).

        Returns:
        pd.DataFrame: A DataFrame containing the soil data for the specified input.
        """
        query = f''' 
        SELECT DISTINCT mu.mukey,co.cokey,ch.chkey,mu.musym, desgnvert,hzdepb_r,dbthirdbar_r,
        wfifteenbar_r,wthirdbar_r,sandtotal_r,silttotal_r,ph1to1h2o_r,awc_r,sumbases_r,om_r,
        caco3_r,cec7_r,sieveno10_r,fraggt10_r,frag3to10_r,dbovendry_r,ksat_r,compname,hydgrp,
        comppct_r,slope_r,slopelenusle_r, albedodry_r
        FROM sacatalog sc
        LEFT JOIN legend lg ON sc.areasymbol = lg.areasymbol
        LEFT JOIN (
        SELECT * FROM mapunit
        WHERE mukey in ({SoilDataAccess._mukey_condition(input_value)})
        ) mu ON lg.lkey = mu.lkey
        LEFT JOIN component co ON mu.mukey = co.mukey
        LEFT JOIN chorizon ch ON co.cokey = ch.cokey
        WHERE mu.mukey IS NOT NULL
        AND compkind='Series'
        AND wthirdbar_r > 0
        '''
        merged = SoilDataAccess.query(query)

        merged['hydgrp'] = merged['hydgrp'].replace('', 'C').fillna('C').str.slice(stop=1)
        merged['Hydgrp_conv'] = merged['hydgrp'].map({'A': 1, 'B': 2, 'C': 3, 'D': 4})
        for col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce').fillna(0)

        soil_df = pd.DataFrame({
        'mukey': merged['mukey'],
        'Layer_number': merged['desgnvert'],
        'Layer_depth': merged['hzdepb_r'] * 0.01,
        'Bulk_Density': merged['dbthirdbar_r'],
        'Wilting_capacity': merged['wfifteenbar_r'] * 0.01,
        'Field_Capacity': merged['wthirdbar_r'] * 0.01,
        'Sand_content': merged['sandtotal_r'],
        'Silt_content': merged['silttotal_r'],
        'N_concen': 0, 'pH': merged['ph1to1h2o_r'],
        'Sum_Bases': merged['sumbases_r'],
        'Organic_Carbon': merged['om_r'] * 0.58,
        'Calcium_Carbonate': merged['caco3_r'],
        'Cation_exchange': merged['cec7_r'],
        'Course_Fragment': 100 - (merged['sieveno10_r'] + merged['fraggt10_r'] + merged['frag3to10_r']),
        'cnds' : 0, 'pkrz' : 0, 'rsd' : 0,
        'Bulk_density_dry': merged['dbovendry_r'], 'psp' : 0,
        'Saturated_conductivity': merged['ksat_r'] * 3.6,
        'albedo': merged['albedodry_r'] * 0.625,
        'slope_length': merged['slopelenusle_r'],
        'hydgrp_conv': merged['Hydgrp_conv']
        })

        # Add new rounded_layer column
        soil_df['rounded_layer'] = (soil_df['Layer_depth'] * 10).round() / 10
        # Group by mukey and rounded_layer, then take median of all values
        soil_df = soil_df.groupby(['mukey', 'rounded_layer']).median().reset_index()
        # Remove the rounded_layer column
        soil_df = soil_df.drop(columns=['rounded_layer'])
        soil_df['mukey'] = soil_df['mukey'].astype(int)
        return soil_df.round(4)
    
    @staticmethod
    def fetch_slope_length(input_value):
        """
        Fetches the slope length for a given input value. If the input is an integer, it is used as mukey. If the input is a string, it is used as WKT.

        Args:
        input (int or str): The input value representing either a mukey (int) or a WKT location (str).

        Returns:
        float: The slope length for the specified input value.
        """
        query = f"""
        SELECT slopelenusle_r
        FROM component
        WHERE mukey in ({SoilDataAccess._mukey_condition(input_value)})
        """
        result = SoilDataAccess.query(query)
        return result['slopelenusle_r'].values[0]

    @staticmethod
    def fetch_value(input_value, values, table):
        """
        Fetches specific values from a given table for a given input value.

        Args:
        input_value (int or str): The input value representing either a mukey (int) or a WKT location (str).
        values (List[str]): A list of column names for the values to fetch.
        table (str): The name of the table to query.

        Returns:
        List[Dict[str, Any]]: A list of dictionaries containing the key (mukey, cokey, etc.) and fetched values.
        """

        # Define key columns for different tables
        key_columns = {
            'mapunit': 'mukey',
            'component': 'mukey',
            'chorizon': 'cokey',
            'cointerp': 'cokey',
            # Add other tables and their respective key columns as necessary
        }

        # Get the correct key column based on the table
        key_column = key_columns.get(table)
        if not key_column:
            raise ValueError(f"Key column for table '{table}' not found or not supported.")
        
        # Get the list of mukey values based on input_value
        key_list = SoilDataAccess.get_mukey_list(input_value)
        if len(key_list) == 0:
            raise ValueError(f"No keys found for the given input in table '{table}'.")

        # Convert the list of values (columns) to a comma-separated string
        values_str = ', '.join(values)

        # Construct query based on the key column
        if key_column == 'mukey':
            # Query using mukey directly
            query = f"""
            SELECT {key_column}, {values_str}
            FROM {table}
            WHERE {key_column} IN ({', '.join(map(str, key_list))})
            """
        
        elif key_column == 'cokey':
            # Query the component or chorizon table based on cokey, but also return mukey
            query = f"""
            SELECT component.mukey, component.cokey, {values_str}
            FROM {table}
            JOIN component ON component.cokey = {table}.cokey
            WHERE component.mukey IN ({', '.join(map(str, key_list))})
            """

        # Assuming there's a method to run the query against the database
        result = SoilDataAccess.query(query)
        
        # Return the result (this could be a list of dictionaries with key_column and values)
        return result


