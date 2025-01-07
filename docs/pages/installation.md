<!-- ## <strong>Installation</strong> -->
Before starting the setup, ensure you have [`conda`](https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html) installed. <br> Follow the links for corresponding installation guides.

### GeoEPIC Toolkit Installation (Recommended)
1. Download [`epic_setup.bat`](https://smarsgroup.github.io/geo_epic_win/epic_setup.bat)
2. Install with the following command
   ```
   call epic_setup.bat
   ```
   
### Setting up GeoEPIC manually

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

    **Option 1: Install Directly from GitHub**
        ```bash
        pip install git+https://github.com/smarsGroup/geo_epic_win.git
        ```
   
    **Option 2: Install locally**
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

### Verify installation
   ```
   conda activate epic_env
   geo_epic init
   ```

All the commands and python API can be accessed via **epic_env** conda environment. Happy coding!
