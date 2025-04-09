---
hide:
  - navigation
  - toc
---


### <strong style="font-size:35px;">Python package for geospatial Crop Simulations</strong>
<img src="./assets/Yield_MD.png" alt="Maryland_Yield" width="60%"/> 
<p>GeoEpic is an open source package that expands the capabilities of the <strong>EPIC crop simulation model</strong>, to simulate crop growth and development across large geographies, such as entire states or counties by leveraging openly availabe remote sensing products and geospatial databases. Additionally, the package features a unique calibration module that allows fine-tuning of model parameters to reflect specific local conditions or experimental results. This toolkit allows researchers to assess crop production potential, management scenarios and risks at broader scales, informing decision-making for sustainable agricultural practices.</p>

<div style="display: flex; justify-content: flex-start; gap:10px; margin: 20px 0;">
  <a href="/geo_epic_win/getting_started/overview" class="md-button md-button--primary" style="background-color:rgb(203, 220, 56); color: #111; border-radius: 5px; padding: 10px;">Go to Overview</a>

  <a href="/geo_epic_win/getting_started/installation" class="md-button md-button--primary" style="background-color:rgb(203, 220, 56); color: #111; border-radius: 5px; padding: 10px;">Install GeoEpic</a>
</div>

### **What is EPIC Model?**

The **Environmental Policy Integrated Climate (EPIC) Model** is a process-based tool designed to simulate agricultural systems at the field, farm, or small watershed scale under uniform climate, soil, land use, and topographic conditions. It is capable of addressing numerous facets of agricultural sustainability and environmental analysis.

#### **Key Features of EPIC**
- Simulates **crop yields** under various management practices.
- Calculates **leaf area index (LAI)** and **net ecosystem exchange (NEE)** for plants.
- Evaluates **soil erosion** (wind, sheet, and channel) and **water quality** impacts.
- Models **nutrient cycling** for sustainable agricultural management.
- Incorporates **pesticide fate** including runoff, leaching, and degradation.
- Assesses impacts of **climate change** and **CO₂ concentrations** on agriculture.
- Designs systems for **biomass production** for energy and economic feasibility.
- Simulates diverse **agricultural management practices** like irrigation, crop rotation, and tillage.

EPIC has evolved to address global challenges and is widely used in environmental and agricultural research. To extend its capabilities even further, the model can be integrated with **GeoEPIC** for enhanced spatial analyses.

For more details on EPIC model, visit [Texas A&M AgriLife site](https://epicapex.tamu.edu/about/epic/).

### <strong>What can you do with GeoEPIC?</strong>


<div style="display: flex; flex-direction: column; gap: 20px; align-items: center; width: 100%;">

  <div style="width: 100%; border: 1px solid #ddd; border-radius: 5px; padding: 10px;">
    <h3><strong>1. Getting Input Files</strong></h3>
    <p>GeoEPIC enables you to download and customize essential input files for crop simulations, including:</p>
    <ul>
      <li><strong>Soil Data:</strong> Access soil properties from sources like USDA SSURGO and ISRIC SoilGrids.</li>
      <li><strong>Site Data:</strong> Specify location parameters such as latitude, longitude, elevation, and slope.</li>
      <li><strong>Crop Management Data:</strong> Define planting schedules, irrigation, fertilization, and tillage operations.</li>
      <li><strong>Weather Data:</strong> Extract historical and forecasted weather information, including temperature, precipitation, and solar radiation, from datasets like AgERA5 on Google Earth Engine.</li>
    </ul>
    <p>Modifying these inputs to reflect local conditions ensures more accurate simulation results.</p>
    <a href="/geo_epic_win/getting_started/weather" class="button-primary">Learn More</a>
  </div>

  <div style="width: 100%; border: 1px solid #ddd; border-radius: 5px; padding: 10px;">
    <h3><strong>2. Site Simulation</strong></h3>
    <p>GeoEPIC enhances the EPIC crop simulation model by enabling large-scale geospatial simulations. It allows users to model crop growth, yields, and water usage across extensive areas, such as entire states or counties. By integrating remote sensing data and geospatial databases, GeoEPIC facilitates the creation of detailed model inputs, supporting assessments of crop production potential and the evaluation of various management scenarios.</p>
    <a href="/geo_epic_win/getting_started/calibration" class="button-primary">Learn More</a>
  </div>

  <div style="width: 100%; border: 1px solid #ddd; border-radius: 5px; padding: 10px;">
    <h3><strong>3. Model Calibration</strong></h3>
    <p>GeoEPIC's Calibration Module enables precise tuning of the EPIC model parameters to align simulations with observed data, such as Leaf Area Index (LAI), Net Ecosystem Exchange (NEE), crop yield, or biomass. This calibration process ensures that the model accurately reflects specific local conditions or experimental results, enhancing the reliability of simulations.</p>
    <a href="/geo_epic_win/getting_started/simulation" class="button-primary">Learn More</a>
  </div>

  <div style="width: 100%; border: 1px solid #ddd; border-radius: 5px; padding: 5px 10px;">
    <h3><strong>4. Remote Sensing</strong></h3>
    <p>GeoEPIC's Remote Sensing Module leverages satellite imagery and geospatial data to enhance crop simulation accuracy. By integrating data from platforms like Google Earth Engine, users can incorporate up-to-date environmental information into their models, leading to more precise assessments of crop growth and productivity.</p>
    <a href="/geo_epic_win/getting_started/gee" class="button-primary">Learn More</a>
  </div>

</div>

### **Additional Resources**

Explore more about GeoEPIC through the following resources:

1. **Tutorials**  
  These tutorials provide detailed examples of what you can achieve using GeoEPIC, including site simulation, model calibration, and creating site input files. Explore the guides below to enhance your understanding:

    - [Site Simulation Tutorial](site_simulation_tutorial_link)
    - [Calibration Example](calibration_example_link)
    - [Creating Site Input Files Tutorial](creating_site_input_files_link)
    - [Spatial Crop Simulations Tutorial](spatial_crop_simulations_link)
    - [USDA Soil Data Access Guide](usda_soil_data_access_link)

2. **Python API Reference**  
  [Python API Reference](python_api_reference_link) contains detailed information about the various functions and classes available in GeoEPIC. This helps you to import the package into your Python scripts and utilize its functionalities directly, enabling efficient geospatial crop simulations and data analysis.  

3. **Contribution**  
  [Contribution Guide](contribution_guide_link) contains instructions on how to contribute. This document outlines how to contribute to GeoEPIC through code changes, bug reports, feature requests, and other helpful contributions.


### <strong>Contributors</strong> 

- [Bharath Irigireddy](https://github.com/Bharath2), [Varaprasad Bandaru](https://www.ars.usda.gov/pacific-west-area/maricopa-arizona/us-arid-land-agricultural-research-center/plant-physiology-and-genetics-research/people/prasad-bandaru/), [Sachin Velmurgan](https://github.com/SachinVel), [SMaRS Group](https://www.smarsgroup.org/)
- Contact: prasad.bandaru@usda.gov

<style>
.md-content__inner h1{
    width:0px;
    height:0px;
    overflow: hidden;
}
.md-content{
  padding: 0px 50px;
}
</style>