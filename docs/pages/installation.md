<!-- ## <strong>Installation</strong> -->
Before starting the setup, ensure you have [`conda`](https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html) installed. <br> Follow the links for corresponding installation guides.

### Steps to Set Up the GeoEPIC Toolkit

1. **Create a virtual environment in conda**
    ```bash
    conda create --name epic_env python=3.11
    
    ```
2. **Activate the environment**
    ```bash
    conda activate epic_env
    ```

3. **Install the GeoEPIC Toolkit**  
   There are two options for installing the GeoEPIC Toolkit:

    i. **Option 1: Install Directly from GitHub (recommended)**
        ```bash
        pip install git+https://github.com/smarsGroup/geo_epic_win.git
        ```
    i. **Option 2: Install locally**
        This option is advisable only for developers.
        ```bash
        git clone https://github.com/smarsGroup/geo_epic_win.git
        ```
        ```bash
        cd geo_epic_win
        ```
        ```bash
        pip install .
        ```

Now, the GeoEPIC toolkit is sucessfully installed on the **epic_env** conda environment. All the commands and python API can be accessed via that conda environment. Happy coding!