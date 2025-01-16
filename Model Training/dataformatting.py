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
processed_data = pd.concat([x_data_df, labels_df], axis=1)

# Save the processed data to a CSV file
output_path = "processed_data.csv"
processed_data.to_csv(output_path, index=False)

print(f"Processed data saved to {output_path}")