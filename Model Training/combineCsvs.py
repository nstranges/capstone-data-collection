import pandas as pd

df1 = pd.read_csv("processed_data1.csv")
df2 = pd.read_csv("processed_data2.csv")

df_combined = pd.concat([df1, df2], ignore_index=True)

df_combined.to_csv("processed_data.csv", index=False)
