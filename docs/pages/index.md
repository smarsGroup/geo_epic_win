
# GeoEPIC

###<strong>A toolkit for geospatial Crop Simulations</strong>


<img src="./assets/Yield_MD.png" alt="Maryland_Yield" width="90%"/> 
<!-- ### <strong>Overview</strong> -->

This package expands the capabilities of the **EPIC crop simulation model**, to simulate crop growth and development across large geographies, such as entire states or counties by leveraging openly availabe remote sensing products and geospatial databases. Additionally, the toolkit features a unique calibration module that allows fine-tuning of model parameters to reflect specific local conditions or experimental results. This toolkit allows researchers to assess crop production potential, management scenarios and risks at broader scales, informing decision-making for sustainable agricultural practices.



<!-- !['Maryland_Yield'](./assets/Yield_MD.png) -->

### <strong>Installation</strong>

Before starting the setup, ensure you have [`wget`](https://cloudcone.com/docs/article/the-linux-wget-command/) and [`conda`](https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html) installed. Follow the links for corresponding installation guides. Find the detailed instructions in the setup section.

```bash
conda create --name epic_env python=3.11.9

```
```bash
conda activate epic_env
```
```bash
pip install git+https://github.com/smarsGroup/geo-epic.git
```

<!-- 
### <strong>Getting Started</strong>

To begin using GeoEPIC:

1. **Installation**: Follow the [installation guide](installation.md) to set up the toolkit in your Python environment.
2. **Data Preparation**: Prepare your geospatial datasets, including soil, weather, and crop management data.
3. **Running Simulations**: Use the provided modules to set up and execute your EPIC model simulations.
4. **Result Analysis**: Analyze simulation outputs with built-in tools or export data for external analysis.

For detailed instructions, visit the [Getting Started](index.md) section. -->

### <strong>Use Cases</strong>
<!-- 
GeoEPIC has been adopted in various research projects and integrated into several tools: -->

- **Crop Yield Forecasting**: Used in studies predicting crop yields under different climate scenarios.
- **Sustainable Agriculture Tools**: Incorporated into platforms promoting sustainable farming practices.
<!-- - **Academic Research**: Featured in numerous [publications](#) exploring geospatial crop modeling.
- **Collaborations**:
  - **University of Agriculture**: Partnership focusing on soil health and crop productivity.
  - **AgriTech Solutions**: Integration of GeoEPIC into precision agriculture tools. -->


### <strong>Contributors</strong>

- Bharath Irigireddy, Varaprasad Bandaru, Sachin Velmurgan, Rohit Nandan, SMaRS Group