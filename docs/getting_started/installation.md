# GeoEPIC Toolkit Installation Guide

This guide provides instructions for installing the GeoEPIC Toolkit.

## 1. Prerequisites

Before you begin, ensure you have Conda installed. You can find installation guides here: [Conda Installation](https://conda.io/projects/conda/en/latest/user-guide/install/index.html).

## 2. Automatic Installation (Recommended)

This method automates the installation process using a script.

1.  **Download the setup script:**
    * Download the `epic_setup.bat` script to your local machine.

2.  **Run the setup script:**
    * Open your command prompt or PowerShell.
    * Navigate to the directory where you saved the `epic_setup.bat` script.
    * Execute the script using the following command:
        ```bash
        call epic_setup.bat
        ```
    * **What to expect:** The script will automatically create a Conda environment, install the GeoEPIC Toolkit, and configure necessary dependencies. You should see the progress of these actions in the command prompt.

## 3. Manual Installation (Alternative)

This method allows for more control over the installation process. **Choose either this method or the automatic installation method (section 2), not both.**

1.  **Create a virtual environment in Conda:**
    * Open your command prompt or terminal.
    * Run the following command to create a new Conda environment named `epic_env` with Python 3.11:
        ```bash
        conda create --name epic_env python=3.11
        ```
    * **What to expect:** Conda will create the environment and install Python 3.11.

2.  **Activate the environment:**
    * After the environment is created, activate it using:
        ```bash
        conda activate epic_env
        ```
    * **What to expect:** Your command prompt or terminal will show `(epic_env)` at the beginning of the line, indicating the environment is active.

3.  **Install the GeoEPIC Toolkit:**

    * **Option 1: Install Directly from GitHub (Recommended for general users):**
        * Run the following command:
            ```bash
            pip install git+[https://github.com/smarsGroup/geo_epic_win.git](https://github.com/smarsGroup/geo_epic_win.git)
            ```
        * **What to expect:** `pip` will download and install the latest version of the GeoEPIC Toolkit from the GitHub repository.

    * **Option 2: Install Locally (for developers):**
        * Clone the repository:
            ```bash
            git clone [https://github.com/smarsGroup/geo_epic_win.git](https://github.com/smarsGroup/geo_epic_win.git)
            ```
        * Navigate to the cloned directory:
            ```bash
            cd geo_epic_win
            ```
        * Install the toolkit:
            ```bash
            pip install .
            ```
        * **What to expect:** The repository will be downloaded, and the toolkit will be installed from your local files, allowing you to make and test changes.

## 4. Verify Installation

1.  **Activate the environment (if not already active):**
    ```bash
    conda activate epic_env
    ```
2.  **Initialize GeoEPIC:**
    ```bash
    geo_epic init
    ```
    * **What to expect:** If the installation was successful, the `geo_epic init` command will run without errors. If you see an error, recheck your installation steps.

## 5. Additional Notes

* **Updating GeoEPIC Toolkit:**
    * To update to the latest version, use:
        ```bash
        pip install --upgrade git+[https://github.com/smarsGroup/geo_epic_win.git](https://github.com/smarsGroup/geo_epic_win.git)
        ```

* **Uninstalling GeoEPIC Toolkit:**
    * To uninstall, use:
        ```bash
        pip uninstall geo_epic_win
        ```

* **Troubleshooting:**
    * If you encounter issues, refer to the GeoEPIC Toolkit documentation or seek help from the community.

## 6. Example Usage

After successful installation, you can begin using the GeoEPIC Toolkit.

1.  **Initialize a new GeoEPIC project:**
    ```bash
    geo_epic init my_project
    ```
    * **What to expect:** A new directory named `my_project` will be created with the necessary project files.

2.  **Navigate to your project directory:**
    ```bash
    cd my_project
    ```

3.  **Run a sample analysis:**
    ```bash
    geo_epic analyze sample_data.csv
    ```
    * **What to expect:** The `geo_epic analyze` command will run an analysis on the `sample_data.csv` file within your project directory. Ensure that you have a file called sample_data.csv in your my_project folder, or replace sample_data.csv with the correct filename.