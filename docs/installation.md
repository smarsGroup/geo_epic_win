<!-- ## <strong>Installation</strong> -->
Before starting the setup, ensure you have [`wget`](https://cloudcone.com/docs/article/the-linux-wget-command/) and [`conda`](https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html) installed. <br> Follow the links for corresponding installation guides.

### Steps to Set Up the GeoEPIC Toolkit

1. **Create a virtual environment in conda**
    ```bash
    conda create --name geo_epic python=3.11.9
    
    ```
2. **Activate the environment**
    ```bash
    conda activate geo_epic
    ```

3. **Install the GeoEPIC Toolkit**  
   There are two options for installing the GeoEPIC Toolkit:

    i. **Option 1: Install Directly from GitHub (recommended)**
        ```bash
        pip install git+https://github.com/smarsGroup/GeoEPIC.git
        ```
    i. **Option 2: Install locally**
        This option is advisable only for developers.
        ```bash
        git clone https://github.com/smarsGroup/GeoEPIC.git
        cd GeoEPIC
        pip install .
        ```

Now, the GeoEPIC toolkit is sucessfully installed on the **geo_epic** conda environment. All the commands and python API can be accessed via that conda environment. Happy coding!