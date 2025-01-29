import pandas as pd
import numpy as np

def create_sliding_windows(data, window_size, step_size):
    windows = []
    labels = []
    
    for orientation, group in data.groupby(['Orientation']):
        group_values = group.drop(columns=['Timestamp', 'Position', 'Orientation']).values
        position_values = group['Position'].values
        
        for i in range(0, len(group_values) - window_size + 1, step_size):
            window = group_values[i:i + window_size]
            windows.append(window.flatten())
            labels.append(position_values[i + window_size - 1])

    return np.array(windows), np.array(labels)

# Load the data file
data_path = "C:/Users/nicho/OneDrive - The University of Western Ontario/Fifth Year/Capstone/Code/Data/nick_data.xlsx"

data_df = pd.read_excel(data_path, sheet_name='Data')

# Parameters for sliding window
window_size = 15
step_size = 1

# Generate sliding windows
x_data, y_labels = create_sliding_windows(data_df, window_size, step_size)

# Convert labels to a DataFrame for easy merging and use
labels_df = pd.DataFrame(y_labels, columns=['Position'])

# Combine features and labels into a single DataFrame
feature_columns = [f"{col}_{i}" for i in range(1, window_size + 1) for col in data_df.columns[1:-2]]
x_data_df = pd.DataFrame(x_data, columns=feature_columns)

# Calculate average and variance for each variable
average_columns = {}
variance_columns = {}
rms_columns = {}
first_derivative_columns = {}
second_derivative_columns = {}

variables = data_df.columns[1:-2]
for var in variables:
    var_columns = [col for col in x_data_df.columns if col.startswith(var)]
    average_columns[f"{var}_avg"] = x_data_df[var_columns].mean(axis=1)
    variance_columns[f"{var}_var"] = x_data_df[var_columns].var(axis=1)
    rms_columns[f"{var}_rms"] = np.sqrt((x_data_df[var_columns]**2).mean(axis=1))
    first_derivative_columns[f"{var}_first_derivative"] = x_data_df[var_columns].diff(axis=1).mean(axis=1)
    second_derivative_columns[f"{var}_second_derivative"] = x_data_df[var_columns].diff(axis=1).diff(axis=1).mean(axis=1)

# Add the average and variance columns to the DataFrame
x_data_df = pd.concat([x_data_df, pd.DataFrame(average_columns), pd.DataFrame(variance_columns), pd.DataFrame(rms_columns), pd.DataFrame(first_derivative_columns), 
    pd.DataFrame(second_derivative_columns)], axis=1)

processed_data = pd.concat([x_data_df, labels_df], axis=1)

# Save the processed data to a CSV file
output_path = "processed_data.csv"
processed_data.to_csv(output_path, index=False)

print(f"Processed data saved to {output_path}")