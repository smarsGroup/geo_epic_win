import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from osgeo import gdal, osr
from pyproj import Transformer
from sklearn.neighbors import BallTree
from rasterio.mask import mask
from collections import Counter
from shapely.geometry import mapping
from geoEpic.utils import parallel_executor
from tqdm import tqdm



def find_nearest(src, dst, metric = 'minkowski', k = 1):
    """
    Find the indices in dst that correspond to each row in src based on the k nearest neighbors.
    Returns: numpy.ndarray: Indices in dst for each row in src
    """
    # Check if the metric is 'haversine' and convert DataFrame lat/lon to radians if necessary
    if metric == 'haversine':
        src = np.deg2rad(src)
        dst = np.deg2rad(dst)

    # Fit the nearest neighbors model on the destination DataFrame
    tree = BallTree(dst, metric = metric)
    _, inds = tree.query(src, k = k)
    if k == 1: inds = inds[:, 0]
    return inds


def raster_to_dataframe(raster_file):
    """
    Converts .tiff file to DataFrame with pixel locations and band values.
    """
    with rasterio.open(raster_file) as src:
        bands = src.read() 
        trans = src.transform
        band_names = src.descriptions
 
    # Get the location of pixel centers
    lon_coords, lat_coords = _lon_lat_coords(trans, bands[0].shape)

    # Create a dictionary with coordinates and band data
    data_dict = {'lon': lon_coords, 'lat': lat_coords}
    for i, band in enumerate(bands, 1):
        band_name = band_names[i-1] if band_names[i-1] else f'band_{i}'
        data_dict[band_name] = band.flatten()

    return pd.DataFrame(data_dict)

def sample_raster_aggregated(raster_file, geometries, crs="EPSG:4326", agg_type="mean"):
    """
    Sample a raster file based on geometries (polygons) and return aggregated pixel values.
    
    Args:
        raster_file (str): Path to the raster file.
        geometries (list): List of geometries (polygons) in GeoJSON-like format or Shapely geometries.
        crs (str): The CRS of the geometries.
        agg_type (str): Type of aggregation ('mean', 'median', or 'mode').
        
    Returns:
        pd.DataFrame: A dataframe with geometry indices and aggregated pixel values.
    """
    agg_funcs = {
        'mean': np.mean,
        'median': np.median,
        'mode': lambda x: Counter(x).most_common(1)[0][0]  # custom function to get the mode
    }

    if agg_type not in agg_funcs:
        raise ValueError(f"Invalid aggregation type: {agg_type}. Choose 'mean', 'median', or 'mode'.")

    # Ensure the geometries are in the raster's CRS
    with rasterio.open(raster_file) as src:
        if crs != src.crs:
            geometries = [g.to_crs(src.crs) for g in geometries]
        
        band_names = src.descriptions or [f"band_{i}" for i in range(1, src.count + 1)]
        
        # Collect the results
        results = []
            
        for i, geom in enumerate(tqdm(geometries, desc="Processing Geometries")):
            geom = [mapping(geom)]  # Convert the geometry to GeoJSON format for rasterio masking
            try:
                out_image, out_transform = mask(src, geom, crop=True, filled=False)

                # Flatten the raster values and filter out nodata values
                # out_image is a masked array; use `out_image.data` to get valid values
                flattened_values = out_image.data[~out_image.mask].flatten()

                if flattened_values.size > 0:
                    # Apply the chosen aggregation function
                    agg_values = {band_names[j]: agg_funcs[agg_type](flattened_values[j::src.count])
                                  for j in range(src.count)}
                else:
                    # No valid values within the geometry
                    agg_values = {band_name: np.nan for band_name in band_names}

                results.append(agg_values)

            except Exception as e:
                print(f"Error processing geometry {i}: {e}")
                continue

    return pd.DataFrame(results)


def sample_raster_nearest(raster_file, coords, crs="EPSG:4326"):
    """
    Sample a raster file at specific coordinates, taking the nearest pixel.
    
    Args:
        raster_file (str): Path to the raster file.
        coords (list of tuples): List of (x, y)/(lon, lat) tuples.
        crs (str): The CRS the coords are in.
        
    Returns:
        dict: A dictionary with band names as keys and lists of pixel values at the given coordinates as values.
    """
    with rasterio.open(raster_file) as src:
        bands = src.read()
        band_names = src.descriptions

        # Convert coordinates to raster's CRS
        transformer = Transformer.from_crs(crs, src.crs, always_xy=True)
        transformed_coords = np.array([transformer.transform(*coord) for coord in coords])

        # Get the values of the nearest pixels
        rows, cols = src.index(*transformed_coords.T)
        
        # Clip rows and cols to be within bounds
        rows = np.clip(rows, 0, src.height - 1)
        cols = np.clip(cols, 0, src.width - 1)

        samples = {"lon": transformed_coords[:, 0], "lat": transformed_coords[:, 1]}
        
        for i, band in enumerate(bands, 1):
            band_name = band_names[i-1] if band_names[i-1] else f'band_{i}'
            samples[band_name] = band[rows, cols]
        
    return pd.DataFrame(samples)


def reproject_crop_raster(src, dst, out_epsg, min_coords, max_coords):
    """
    Reproject and crop a raster file.
    src_filename: Source file path.
    dst_filename: Destination file path.
    out_epsg: Output coordinate system as EPSG code.
    min_lon, min_lat, max_lon, max_lat: Bounding box coordinates.
    """
    # Define target SRS
    out_srs = osr.SpatialReference()
    out_srs.ImportFromEPSG(out_epsg)
    
    # Call Warp function
    gdal.Warp(dst, src, format='GTiff', 
              outputBounds = [*min_coords, *max_coords], 
              dstSRS = out_srs)
    

class GeoInterface:
    def __init__(self, data_source):
        """Initialize the interface by loading the data source."""
        if isinstance(data_source, str):
            if data_source.lower().endswith(('.tif', '.tiff')):
                # Handle raster file
                self.df = raster_to_dataframe(data_source).dropna()
            elif data_source.lower().endswith('.csv'):
                # Handle CSV file
                self.df = pd.read_csv(data_source).dropna()
            elif data_source.lower().endswith(('.shp', '.shapefile')):
                # Handle shapefile
                gdf = gpd.read_file(data_source)
                # Ensure the GeoDataFrame has a latitude and longitude column
                if 'lat' not in gdf.columns or 'lon' not in gdf.columns:
                    # Calculate the centroids if the geometry column exists
                    if 'geometry' in gdf.columns:
                        gdf['lon'] = gdf['geometry'].centroid.x
                        gdf['lat'] = gdf['geometry'].centroid.y
                    else:
                        raise ValueError("No geometry column found")
                self.df = gdf.dropna(subset=['lat', 'lon'])
            else:
                raise ValueError("Unsupported file format. The file must be a CSV, TIF/TIFF, or shapefile.")
        elif isinstance(data_source, pd.DataFrame):
            self.df = data_source.dropna()  # Handle DataFrame
        else:
            raise ValueError("data_source must be a file path (CSV, TIF, or shapefile) or a pandas DataFrame.")
        
        # Prepare data for haversine distance queries
        self.points_rad = np.deg2rad(self.df[['lat', 'lon']].values)
        self.tree = BallTree(self.points_rad, metric='haversine')

    def lookup(self, lat, lon):
        """
        Find the nearest data point to a single latitude and longitude.

        Args:
            lat (float): Latitude of the query point.
            lon (float): Longitude of the query point.

        Returns:
            pandas.Series: The row from the DataFrame corresponding to the nearest point.
        """
        query_point_rad = np.deg2rad(np.array([[lat, lon]]))
        _, index = self.tree.query(query_point_rad, k=1)
        nearest_index = index[0][0]
        return self.df.iloc[nearest_index]

    def find_nearest(self, lats, lons, k=1):
        """
        Find the nearest 'k' data points for each latitude and longitude provided separately.

        Args:
            lats (list of float): A list of latitudes.
            lons (list of float): A list of longitudes.
            k (int): Number of nearest neighbors to find.

        Returns:
            list or pandas.DataFrame: Depending on 'k', returns a DataFrame or a list of DataFrames with the nearest points.
        """
        if len(lats) != len(lons):
            raise ValueError("Latitude and longitude lists must have the same length.")
            
        lat_lon_pairs = np.vstack((lats, lons)).T
        query_points_rad = np.deg2rad(lat_lon_pairs)
        distances, indices = self.tree.query(query_points_rad, k=k)
        
        if k == 1:
            return self.df.iloc[indices.flatten()]
        else:
            return [self.df.iloc[index] for index in indices]
    
def _lon_lat_coords(trans, shape):
    """
    Computes longitude, latitude coordinates for pixel centers.
    """
    # Create a new Affine object with modified c and f attributes
    t_shifted = rasterio.Affine(trans.a, trans.b, trans.c + trans.a/2, 
                                trans.d, trans.e, trans.f + trans.e/2)
    indices = np.indices(shape)
    lon_coords, lat_coords = t_shifted * (indices[1].flatten(), indices[0].flatten())
    return lon_coords, lat_coords
