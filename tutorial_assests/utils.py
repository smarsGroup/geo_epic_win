
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.cm import ScalarMappable

# Update global matplotlib settings
def spatial_plot(shp_file, values, title):
    plt.rcParams.update({
    'font.family': 'Times New Roman',
    'font.size': 12,
    'axes.titlesize': 16,
    'axes.labelsize': 12,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'pdf.fonttype': 42,   # Embeds fonts using Type 42 (TrueType)
    'ps.fonttype': 42
    })

    # Create a custom colormap
    blue_to_red = LinearSegmentedColormap.from_list("blue_to_red", ["lightcoral", "blue"])

    # Define cutoff values for outlier capping
    cutoff_high = 820  # e.g., shp[col].quantile(0.95)
    cutoff_low = 580   # e.g., shp[col].quantile(0.05)

    # Create a figure with a single subplot
    fig, ax = plt.subplots(figsize=(9, 8))
    #########################
    # Plot for Soybean Only
    #########################
    # Get first column name in values other than SiteID
    col = [col for col in values.columns if col != 'SiteID'][0]
    shp_filtered_soybean = gpd.read_file(shp_file)
    # Merge values on to the shape file based on SiteID column
    shp_filtered_soybean = shp_filtered_soybean.merge(values, on='SiteID', how='left')
    # Filter out zero values
    shp_filtered_soybean = shp_filtered_soybean[shp_filtered_soybean[col] != 0]
    # Cap values above the high cutoff and below the low cutoff
    shp_filtered_soybean.loc[shp_filtered_soybean[col] > cutoff_high, col] = cutoff_high
    shp_filtered_soybean.loc[shp_filtered_soybean[col] < cutoff_low, col] = cutoff_low

    # Plot the filtered soybean data (without its own legend - later use a shared colorbar)
    shp_filtered_soybean.plot(column=col, cmap=blue_to_red, legend=False, ax=ax)
    ax.set_title(title, fontweight='bold', pad=15, loc='center')
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))

    #########################
    # Create a Common Horizontal Colorbar at the Bottom
    #########################
    norm = Normalize(vmin=cutoff_low, vmax=cutoff_high)
    sm = ScalarMappable(norm=norm, cmap=blue_to_red)
    sm.set_array([])

    cbar = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.09, pad=0.05, shrink=0.5)
    cbar.set_label("Evapotranspiration (mm)")
    plt.tight_layout()
    # Save and show the figure
    return plt


from scipy.stats import linregress


# Function to compute RMSE
def rmse(y_true, y_pred):
    return np.sqrt(np.mean((y_true - y_pred)**2))


def compare_et(target_dir, predicted_dir):
    plt.rcParams.update({
        'font.family': 'Times New Roman',
        'font.size': 14,
        'axes.titlesize': 16,
        'axes.labelsize': 12,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        'pdf.fonttype': 42,   # Embeds fonts using Type 42 (TrueType)
        'ps.fonttype': 42
    })

    # Read and stack all CSV files from target directory
    target_files = [f for f in os.listdir(target_dir) if f.endswith('.csv')]
    target_dfs = []
    for file in target_files:
        df = pd.read_csv(os.path.join(target_dir, file))
        df['filename'] = file.replace('.csv', '')
        target_dfs.append(df)
    target_stacked = pd.concat(target_dfs, ignore_index=True)

    # Read and stack all CSV files from predicted directory
    predicted_files = [f for f in os.listdir(predicted_dir) if f.endswith('.csv')]
    predicted_dfs = []
    for file in predicted_files:
        df = pd.read_csv(os.path.join(predicted_dir, file))
        df['filename'] = file.replace('.csv', '')
        predicted_dfs.append(df)
    predicted_stacked = pd.concat(predicted_dfs, ignore_index=True)

    # Merge target and predicted data based on filename and date
    merged_df = target_stacked.merge(predicted_stacked, on=['filename', 'date'], suffixes=('_target', '_predicted'))

    # Define the two select conditions
    select_options = [1, 0]  # 1: Calibration, 0: Validation

    # Define subplot titles for each select condition
    titles = {
        1: "a) Calibration",
        0: "b) Validation"
    }

    # Prepare the 2x1 figure
    fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(5, 9))

    # Loop through each select condition and populate the subplot
    for i, select in enumerate(select_options):
        ax = axes[i]
        
        # Filter data based on select condition
        data = merged_df[merged_df['select'] == select]
        
        # Get observed and simulated ET values
        x_observed = data['et_tar']  # Target ET from target files
        y_simulated = data['ET_predicted']  # Predicted ET from predicted files
        
        # Check for sufficient data before proceeding
        if len(x_observed) < 2:
            ax.text(0.5, 0.5, "Insufficient data", transform=ax.transAxes,
                    ha='center', va='center', fontsize=12)
            ax.set_title(titles[select], loc='left', pad=15)
            continue
        
        # Perform regression analysis
        reg = linregress(x_observed, y_simulated)
        R2 = reg.rvalue**2
        RMSE = rmse(y_simulated, x_observed)
        
        # Plot scatter points
        ax.scatter(x_observed, y_simulated, s=10, color='k', zorder=3,
                   label=f"R²={R2:.2f}, RMSE={RMSE:.2f}")
        
        # Determine range for regression line
        x_min = 0
        x_max = 11
        x_range = np.linspace(x_min - 0.5, x_max + 0.5, 100)
        
        # Plot regression line
        y_fit = reg.slope * x_range + reg.intercept
        ax.plot(x_range, y_fit, color='k', linestyle='--', linewidth=2, zorder=3)
        
        # Plot 1:1 line for reference
        ax.plot(x_range, x_range, color='r', linestyle='-', linewidth=1, alpha=0.7, label='1:1 line')
        
        # Set subplot title
        ax.set_title(titles[select], loc='left', pad=15)
        
        # Set labels
        ax.set_xlabel("Observed ET (mm/day)")
        ax.set_ylabel("Simulated ET (mm/day)")
        
        # Add legend
        ax.legend(loc='upper right', frameon=True, fontsize=10)
        
        # Add grid and set limits
        ax.grid(True)
        ax.set_xlim(-1, 14.5)
        ax.set_ylim(-1, 14.5)

    # Adjust layout, save, and display the image
    plt.tight_layout()
    # plt.show()
    return plt