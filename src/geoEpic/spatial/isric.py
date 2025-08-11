import hashlib
import pandas as pd
import ee
from geoEpic.io import SOL

class SoilGrids:
    """
    A class to retrieve and process soil data from Earth Engine
    """
    
    @staticmethod
    def fetch(lat, lon):
        """
    Retrieves combined soil data with depth layers from HiHydro SoilGrids v2.0 and ISRIC SoilGrids for a given latitude and longitude.

    Args:
        lat (float): Latitude.
        lon (float): Longitude.
        resolution (int): Resolution in meters.

    Returns:
        tuple: A tuple containing two pandas DataFrames: the raw combined data and the converted soil layer data.
    """
        resolution = 250 

        point = ee.Geometry.Point([lon, lat])  # Earth Engine uses [lon, lat]

        # HiHydro SoilGrids v2.0 data retrieval (depth-specific)
        hihydro_soil_collections = {
            "ksat": ee.ImageCollection("projects/sat-io/open-datasets/HiHydroSoilv2_0/ksat"),
            "satfield": ee.ImageCollection("projects/sat-io/open-datasets/HiHydroSoilv2_0/sat-field"),
            "N": ee.ImageCollection("projects/sat-io/open-datasets/HiHydroSoilv2_0/N"),
            "alpha": ee.ImageCollection("projects/sat-io/open-datasets/HiHydroSoilv2_0/alpha"),
            "crit_wilt": ee.ImageCollection("projects/sat-io/open-datasets/HiHydroSoilv2_0/crit-wilt"),
            "field_crit": ee.ImageCollection("projects/sat-io/open-datasets/HiHydroSoilv2_0/field-crit"),
            "ormc": ee.ImageCollection("projects/sat-io/open-datasets/HiHydroSoilv2_0/ormc"),
            "stc": ee.ImageCollection("projects/sat-io/open-datasets/HiHydroSoilv2_0/stc"),
            "wcavail": ee.ImageCollection("projects/sat-io/open-datasets/HiHydroSoilv2_0/wcavail"),
            "wcpf2": ee.ImageCollection("projects/sat-io/open-datasets/HiHydroSoilv2_0/wcpf2"),
            "wcpf3": ee.ImageCollection("projects/sat-io/open-datasets/HiHydroSoilv2_0/wcpf3"),
            "wcpf4_2": ee.ImageCollection("projects/sat-io/open-datasets/HiHydroSoilv2_0/wcpf4-2"),
            "wcres": ee.ImageCollection("projects/sat-io/open-datasets/HiHydroSoilv2_0/wcres"),
            "wcsat": ee.ImageCollection("projects/sat-io/open-datasets/HiHydroSoilv2_0/wcsat"),
            "hydrologic_soil_group": ee.Image("projects/sat-io/open-datasets/HiHydroSoilv2_0/Hydrologic_Soil_Group_250m") # Single Image
        }

        depths = ["0-5cm","5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm"]

        hihydro_results = {}

        # Iterate through each HiHydro soil property to fetch data.
        for name, collection in hihydro_soil_collections.items():
            try:
                if name == "hydrologic_soil_group":
                    sampled_features = collection.sample(region=point, scale=resolution, geometries=False)
                    first_feature = ee.Feature(sampled_features.first())
                    data = first_feature.getInfo()['properties']
                    if data:
                        hihydro_results[name] = {"HSG": data.get(collection.bandNames().get(0).getInfo())}
                    else:
                        hihydro_results[name] = {"HSG": None}
                else:
                    depth_results = {}
                    images = collection.toList(collection.size()).getInfo()
                    for i, depth in enumerate(depths):
                        if i < len(images):  # Check if there are enough images
                            matching_image = next((img for img in images if depth in img['id']), None)
                            image_id = matching_image['id']
                        
                            image_ee = ee.Image(image_id)
                            reduction = image_ee.reduceRegion(
                                reducer=ee.Reducer.first(), geometry=point, scale=resolution, maxPixels=1e9
                            )
                            data = reduction.getInfo()
                            if data:
                                depth_results[depth] = data.get(image_ee.bandNames().get(0).getInfo()) * 0.0001
                            else:
                                depth_results[depth] = None  # No data for this depth
                        else:
                            depth_results[depth] = None  # No image for this depth
                    hihydro_results[name] = depth_results
            
            except ee.ee_exception.EEException as e:
                print(f"Error retrieving {name}: {e}")
                hihydro_results[name] = None

        # ISRIC SoilGrids data retrieval (depth-specific)
        # Define Earth Enginer Images for ISRIC SoilGrids properties.
        isric_soil_layers = {
            "bdod": ee.Image("projects/soilgrids-isric/bdod_mean"),
            "cec": ee.Image("projects/soilgrids-isric/cec_mean"),
            "cfvo": ee.Image("projects/soilgrids-isric/cfvo_mean"),
            "clay": ee.Image("projects/soilgrids-isric/clay_mean"),
            "sand": ee.Image("projects/soilgrids-isric/sand_mean"),
            "silt": ee.Image("projects/soilgrids-isric/silt_mean"),
            "nitrogen": ee.Image("projects/soilgrids-isric/nitrogen_mean"),
            "phh2o": ee.Image("projects/soilgrids-isric/phh2o_mean"),
            "soc": ee.Image("projects/soilgrids-isric/soc_mean"),
            "ocd": ee.Image("projects/soilgrids-isric/ocd_mean"),
        }

        isric_results = {}

        # Iterate through each ISRIC soil layer
        for layer_name, image in isric_soil_layers.items():
            isric_results[layer_name] = {}
            for depth in depths:
                try:
                    band_name = f"{layer_name.split('_')[0]}_{depth}_mean"
                    sampled_features = image.select(band_name).sample(region=point, scale=resolution, geometries=False)
                    first_feature = ee.Feature(sampled_features.first())
                    data = first_feature.getInfo()['properties']
                    if data:
                        isric_results[layer_name][depth] = data.get(band_name)
                    else:
                        isric_results[layer_name][depth] = None
                except ee.ee_exception.EEException as e:
                    print(f"Error retrieving {layer_name} depth {depth}: {e}")
                    isric_results[layer_name][depth] = None

        # Combine HiHydro and ISRIC results
        combined_results = {**hihydro_results, **isric_results}
    
        # Apply unit conversions
        soil_layer = pd.DataFrame({
            'Layer_depth': [0.05, 0.15, 0.30, 0.60, 1.00, 2.00], # Assuming depths are midpoints of the ranges
            'Bulk_Density': [combined_results['bdod'][depth]/100 for depth in depths],
            'Wilting_capacity': [combined_results['wcpf4_2'][depth] for depth in depths],
            'Field_Capacity': [combined_results['wcpf2'][depth] for depth in depths],
            'Sand_content': [combined_results['sand'][depth]/10 for depth in depths],
            'Silt_content': [combined_results['silt'][depth]/10 for depth in depths],
            'N_concen': [combined_results['nitrogen'][depth]/100 for depth in depths],
            'pH': [combined_results['phh2o'][depth]/10 for depth in depths],
            'Sum_Bases': [0] * 6, # No data in ISRIC or HiHydro, set to 0,
            'Organic_Carbon': [combined_results['soc'][depth]/100 for depth in depths],
            'Calcium_Carbonate': [0] * 6, # No data in ISRIC or HiHydro, set to 0
            'Cation_exchange': [combined_results['cec'][depth]/10 for depth in depths],
            'Course_Fragment': [combined_results['cfvo'][depth]/10 for depth in depths],
            'cnds': [0] * 6, # No data in ISRIC or HiHydro, set to 0
            'pkrz': [0] * 6, # No data in ISRIC or HiHydro, set to 0
            'rsd': [0] * 6, # No data in ISRIC or HiHydro, set to 0
            'Bulk_density_dry': [combined_results['bdod'][depth]/100 for depth in depths], # Using bdod as proxy
            'psp': [0] * 6, # No data in ISRIC or HiHydro, set to 0
            'Saturated_conductivity': [combined_results['ksat'][depth] * 0.416 for depth in depths]
        })
        
        # Extract and normalize hydrologic soil group to one of 'A','B','C','D'
        hsg_value = combined_results.get("hydrologic_soil_group", {}).get('HSG', None)
        if isinstance(hsg_value, (int, float)):
            try:
                hsg_int = int(hsg_value)
            except Exception:
                hsg_int = 3
            hydrologic_soil_group = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}.get(hsg_int, 'C')
        elif isinstance(hsg_value, str) and len(hsg_value) > 0:
            hydrologic_soil_group = hsg_value.strip()[0].upper()
            if hydrologic_soil_group not in {'A','B','C','D'}:
                hydrologic_soil_group = 'C'
        else:
            hydrologic_soil_group = 'C'

        # Generate unique soil ID based on latitude and longitude
        soil_id = SoilGrids.generate_soil_id(lat, lon)
        
        # Choose a reasonable default albedo if unavailable from datasets
        default_albedo = 0.15

        # Extract data into soil object and return the object.
        soil = SOL(soil_id, default_albedo, hydrologic_soil_group, len(depths), layers_df=soil_layer)

        return soil
    

    @staticmethod
    def generate_soil_id(lat, lon):
        res_deg = 0.0025
        # grid indices at 250 m-ish resolution
        i = int(round(lat / res_deg))
        j = int(round(lon / res_deg))
        # 8-digit stable hash
        h = hashlib.blake2s(f"{i},{j}".encode(), digest_size=8).digest()
        return int.from_bytes(h, "big") % 100_000_000

if __name__ == "__main__":
    test_lat = 35.9768
    test_lon = -90.1399
    
    print(f"\n--- Running SoilGrids.fetch for ({test_lat}, {test_lon}) ---")
    try:
        soil_object = SoilGrids.fetch(test_lat, test_lon)

        if soil_object:
            print("\n--- Fetched Soil Object Details ---")
            print(f"Soil ID: {soil_object.soil_id}")
            print(f"Albedo: {soil_object.albedo}")
            print(f"Number of Layers: {soil_object.num_layers}")
            print(f"Hydrologic Group: {soil_object.hydgrp}")
            print("\nSoil Layers DataFrame:")
            print(soil_object.layers_df)
        else:
            print("Failed to retrieve soil data. Check logs above for errors.")

    except Exception as e:
        print(f"An unexpected error occurred during fetch: {e}")
