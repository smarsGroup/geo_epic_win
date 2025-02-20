

Before starting the setup, ensure you have [`conda`](https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html) installed. Follow the links for corresponding installation guides.

### **Automatic Installation Using Script (Recommended)**

1. **Download the setup script**:
   Download the [`epic_setup.bat`](https://smarsgroup.github.io/geo_epic_win/epic_setup.bat) script to your local machine.

2. **Run the setup script**:
   Execute the downloaded script using the following command:
   ```bash
   call epic_setup.bat
   ```
   This script will automate the installation process for you.

### **Setting up GeoEPIC manually**

1. **Create a virtual environment in conda**:
   To keep your dependencies isolated and avoid conflicts, it is recommended to create a virtual environment. Run the following command to create a new environment named `epic_env` with Python 3.11:
   ```bash
   conda create --name epic_env python=3.11
   ```

2. **Activate the environment**:
   Once the environment is created, activate it using the following command:
   ```bash
   conda activate epic_env
   ```

3. **Install the GeoEPIC Toolkit**:
   You have two options to install the GeoEPIC Toolkit:

      - **Option 1: Install Directly from GitHub**:
         This method is straightforward and installs the latest version of the toolkit directly from the GitHub repository. Use the following command:
         ```bash
         pip install git+https://github.com/smarsGroup/geo_epic_win.git
         ```

      - **Option 2: Install locally (for developers)**:
      If you are a developer and plan to make changes to the toolkit, you can clone the repository and install it locally. Follow these steps:
      ```bash
      git clone https://github.com/smarsGroup/geo_epic_win.git
      cd geo_epic_win
      pip install .
      ```
      This will clone the repository to your local machine, navigate into the cloned directory, and install the toolkit from the local files.

### **Verify installation**

```bash
conda activate epic_env
geo_epic init
```

### **Additional Notes**

- **Updating GeoEPIC Toolkit**: To update the toolkit to the latest version, use the following command:
   ```bash
   pip install --upgrade git+https://github.com/smarsGroup/geo_epic_win.git
   ```

- **Uninstalling GeoEPIC Toolkit**: If you need to uninstall the toolkit, you can do so with:
   ```bash
   pip uninstall geo_epic_win
   ```

- **Troubleshooting**: If you encounter any issues during installation or setup, refer to the [GeoEPIC Toolkit documentation](https://smarsgroup.github.io/geo_epic_win/docs) or seek help from the community.

### **Example Usage**

After setting up the GeoEPIC Toolkit, you can start using it in your projects. Here is a simple example to get you started:

1. **Initialize a new GeoEPIC project**:
    ```bash
    geo_epic init my_project
    ```

2. **Navigate to your project directory**:
    ```bash
    cd my_project
    ```

3. **Run a sample analysis**:
    ```bash
    geo_epic analyze sample_data.csv
    ```

This will create a new project directory with the necessary files and run a sample analysis on the provided data.

Happy coding!
