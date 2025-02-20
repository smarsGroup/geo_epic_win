**Welcome to the geoEpic package documentation!** This guide will help you get started with using geoEpic, a Python package designed for agricultural stakeholders to streamline the process of running the EPIC Model, downloading input files, leveraging remote sensing data, and calibrating EPIC models.

## **Environmental Policy Integrated Climate Model**

The Environmental Policy Integrated Climate **(EPIC)** model, originally known as the Erosion/Productivity Impact Calculator, is **designed to simulate a field, farm or small watershed**, that is homogenous in terms of climate, soil, land use, and topography. The model simulates biophysical and biogeochemical processes as influenced by climate, landscape, soil and management conditions.Processes simulated include plant growth and yield, water and wind erosion, and water, carbon and nutrient cycling. EPIC is capable of **simulating around hundred crops** including annual, perennial and woody cropping systems grown as monocultures or polycultures. Model has been validated for multiple crops and in over 30 countries and regions and it has been used to assess productivity, environmental impacts, sustainability and climate change impacts and mitigation. EPIC has regularly been used by federal programs to investigate potential impacts of agricultural policies.

For more details on EPIC model, visit [Texas A&M AgriLife site](https://epicapex.tamu.edu/about/epic/). 

## **Important Functionalities and Use Cases of EPIC**

- **Weather Simulation**: Generates daily weather data, including precipitation, temperature, solar radiation, wind speed, and direction, to drive other model components. [EPICAPEX.TAMU.EDU](https://epicapex.tamu.edu/)
- **Hydrology**: Simulates surface runoff, infiltration, percolation, and evapotranspiration to understand water movement within the soil-plant-atmosphere continuum.
- **Erosion-Sedimentation**: Assesses soil erosion caused by water and wind, predicting sediment yield and deposition.
- **Nutrient Cycling**: Models the transformations and movements of nutrients like nitrogen and phosphorus within the soil-plant system.
- **Crop Growth**: Simulates the growth and yield of various crops, considering factors such as photosynthesis, respiration, and nutrient uptake. [ARS.USDA.GOV](https://www.ars.usda.gov/)
- **Soil Temperature**: Calculates soil temperature dynamics, influencing seed germination and microbial activity.
- **Tillage**: Evaluates the effects of different tillage practices on soil properties and crop production.
- **Economics**: Analyzes the economic implications of various agricultural practices, aiding in cost-benefit assessments.

## **Essential Input Files and Key Variables for EPIC**

To effectively run the EPIC model, several input files are required, each containing specific data. Understanding the critical variables within each input file is essential for accurate EPIC simulations. Below are the descriptions and key parameters for each input file, along with links to the relevant geoEpic modules.

### **Soil Data File (.SOL)**

The Soil Data File details soil properties such as texture, bulk density, hydraulic conductivity, albedo, and layer-specific information. These parameters are crucial for simulating hydrological and nutrient cycling processes. Accurate soil data helps in understanding water retention, root penetration, and nutrient availability, which are vital for crop growth and yield predictions.

- **Key Soil Variables**:
    - **Texture**: Determines water retention and movement.
    - **Bulk Density**: Affects root penetration and water movement.
    - **Hydraulic Conductivity**: Influences infiltration rates.
    - **Albedo**: Impacts soil temperature and evaporation rates.

By meticulously preparing the Soil Data File with accurate and site-specific data, users can leverage the EPIC model to simulate and evaluate the impacts of various agricultural practices. For more information, visit the [Soil Module](pages/Soil.md).

### **Weather Data File (.DLY)**

The Weather Data File contains daily weather parameters, including precipitation, maximum and minimum temperatures, solar radiation, and wind speed. Accurate weather data is vital for driving the model's simulations. Weather data influences crop growth, water balance, and erosion processes, making it essential for reliable model outputs.

- **Key Weather Variables**:
    - **Precipitation**: Drives hydrological processes.
    - **Temperature**: Affects crop growth rates and development stages.
    - **Solar Radiation**: Influences photosynthesis and evapotranspiration.
    - **Wind Speed**: Impacts evapotranspiration and erosion rates.

For more information on weather data inputs, visit the [Weather Module](pages/Weather.md).

### **Operation Schedule File (.OPC)**

The Operation Schedule File outlines the sequence of field operations, such as planting, fertilization, irrigation, tillage, and harvesting. This schedule helps the model understand management practices applied to the crop. Properly scheduled operations ensure optimal growth conditions and resource use efficiency.

- **Key Operation Schedule Variables**:
    - **Planting Dates**: Determine the start of the growing season.
    - **Fertilization Amounts and Timing**: Affect nutrient availability and uptake.
    - **Irrigation Scheduling**: Ensures adequate water supply during critical growth stages.
    - **Tillage Practices**: Influence soil structure and erosion potential.

For more information on crop management practices, visit the [Crop Management Module](pages/OPC.md).

### **Site Data File (.SIT)**

The Site Data File provides information about the specific location, including latitude, longitude, elevation, and slope. This data influences climatic inputs and topographical considerations in the model. Accurate site data helps in tailoring the model to specific geographic conditions, improving simulation accuracy.

- **Key Site Variables**:
    - **Latitude and Longitude**: Define the geographic location, affecting climatic inputs.
    - **Elevation**: Impacts temperature and precipitation patterns.
    - **Slope**: Affects runoff and erosion rates.

By meticulously preparing these input files with accurate and site-specific data, users can leverage the EPIC model to simulate and evaluate the impacts of various agricultural practices, aiding in sustainable land management and decision-making.


## **Calibration**
Calibration is the process of adjusting model parameters to ensure that the model's output accurately reflects real-world data. This step is crucial for achieving reliable and valid simulations. Proper calibration involves comparing model predictions with observed data and iteratively refining the model parameters to minimize discrepancies. For detailed guidelines and instructions on how to perform calibration, refer to the calibration module.
Guidelines on how to calibrate the model for accurate simulations.

## **Earth Engine Utility**
Google Earth Engine (GEE) is a cloud-based platform for planetary-scale environmental data analysis. It hosts a vast collection of satellite imagery and other geospatial datasets, enabling users to perform large-scale data analysis. To explore the available datasets, visit [Google Earth Engine's dataset catalog](https://developers.google.com/earth-engine/datasets) and [GEE Community Catalog](https://gee-community-catalog.org/). Private assets can also be uploaded to Earth Engine, to use them in combination with existing datasets.

This module can be used to combine various datasets and extract the required timeseries directly from Google Earth Engine.
