# import os

# from pyeed import Pyeed

# user = "neo4j"
# password = "12345678"
# uri = "bolt://localhost:7689"
# api_key = os.getenv("OPENAI_API_KEY")


# eedb = Pyeed(uri, user, password)

# question = """What were the induction concentration during expression of the three most
# active enzymes (most negative normalized slope). Give me the wells of the
# enzymes, and the slope values. Additionally return the peak area of the peak
# that contained the respective expression product
# """

# res = eedb.chat(question, openai_key=api_key)

# print(res)


# eedb.db.close()

import pandas as pd

# Your data
data = [
    {
        "well": "H12",
        "slope": -85.11494252873565,
        "induction_concentration": 0.5,
        "peak_area": 4.103516441191671,
    },
    {
        "well": "D9",
        "slope": -15.705073086844365,
        "induction_concentration": 0.5,
        "peak_area": 1.5472013210083344,
    },
    {
        "well": "E11",
        "slope": -13.250000000000004,
        "induction_concentration": 0.5,
        "peak_area": 0.3245452508500001,
    },
]

# Convert the data to a DataFrame
df = pd.DataFrame(data)

# Write the DataFrame to an Excel file
output_file = "output.xlsx"
df.to_excel(output_file, index=False, sheet_name="Data")

print(f"Data has been successfully written to {output_file}.")
