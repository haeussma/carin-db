import pandas as pd
from rich import print

# read your data
df = pd.read_excel("uploads/lilly_data.xlsx", sheet_name="Measurement")

# melt the measurement columns
df_melted = df.melt(
    id_vars=[col for col in df.columns if not col.startswith("measurement_")],
    value_vars=["measurement_1", "measurement_2", "measurement_3"],
    var_name="measurement_id",
    value_name="measurement",
)

# get rid of old measurement columns
df = df.drop(columns=["measurement_1", "measurement_2", "measurement_3"])

# print nrow of original df and melted df
print(df.shape[0])
print(df_melted.shape[0])

# n columns of original df and melted df
print(df.shape[1])
print(df_melted.shape[1])


# save melted df in correct sheet
df_melted.to_excel(
    "uploads/lilly_data_melted_fixed.xlsx", sheet_name="Measurement", index=False
)
