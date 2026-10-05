import pdfplumber
import pandas as pd
import re
from datetime import datetime as dt
import inputs as inp

def parser(file):
    month = inp.month(file)
    year = inp.year()


    pdf_path = file

    def extract_page_data(page):
        EXPECTED_NUMBERS = 10  
        text = page.extract_text()
        lines = text.split("\n")

        # --------------------------------------------------
        # Extract Monthly Composition (CO2, N2, C1 only)
        # --------------------------------------------------
        composition = {"CO2": 0.0, "N2": 0.0, "C1": 0.0}

        for i, line in enumerate(lines):
            if line.strip().startswith("CO2"):
                values = re.findall(r"\d+\.\d+|\d+", lines[i+1])
                if len(values) >= 3:
                    composition["CO2"] = float(values[0])
                    composition["N2"] = float(values[1])
                    composition["C1"] = float(values[2])
                break

        # --------------------------------------------------
        # Extract Daily Table
        # --------------------------------------------------
        daily_rows = []

        for line in lines:
            if re.match(r"^\d{2}\s", line):  # Line starts with Day (01–31)

                numbers = re.findall(r"\d+\.\d+|\d+", line)
                numbers = [float(n) for n in numbers]

                # Pad missing numeric values with zeros
                if len(numbers) < EXPECTED_NUMBERS:
                    numbers += [0.0] * (EXPECTED_NUMBERS - len(numbers))

                # Map columns safely
                daily_rows.append({
                    "Day": int(numbers[0]),
                    "Pulses (Counts)": numbers[1],
                    "Pressure (psig)": numbers[2],
                    "Temperature (F)": numbers[3],
                    "Raw Volume()": numbers[4],
                    "Relative Density": numbers[5],
                    "No Header Column": numbers[6],
                    "Volume (Mcf)": numbers[7],
                    "Heating Value (Btu/scf)": numbers[8],
                    "Energy (MMBTU)": numbers[9],
                    "Type": 0  # Always set to 0 per your requirement
                })

        df = pd.DataFrame(daily_rows)

        return df, composition


    # --------------------------------------------------
    # Extract Page 1 and Page 2
    # --------------------------------------------------
    with pdfplumber.open(pdf_path) as pdf:
        df1, comp1 = extract_page_data(pdf.pages[0])
        df2, comp2 = extract_page_data(pdf.pages[1])


    # --------------------------------------------------
    # Merge Daily Tables
    # --------------------------------------------------
    merged = df1.merge(df2, on="Day", suffixes=("_1", "_2"))


    def weighted_avg(col):
        return (
            merged[f"{col}_1"] * merged["Volume (Mcf)_1"] +
            merged[f"{col}_2"] * merged["Volume (Mcf)_2"]
        ) / (merged["Volume (Mcf)_1"] + merged["Volume (Mcf)_2"]).replace(0, 1)


    # --------------------------------------------------
    # Build Final Aggregated Table
    # --------------------------------------------------
    final = pd.DataFrame()

    final["Day"] = merged["Day"]

    # Sums
    final["Pulses (Counts)"] = merged["Pulses (Counts)_1"] + merged["Pulses (Counts)_2"]
    final["Raw Volume()"] = merged["Raw Volume()_1"] + merged["Raw Volume()_2"]
    final["No Header Column"] = merged["No Header Column_1"] + merged["No Header Column_2"]
    final["Volume (Mcf)"] = merged["Volume (Mcf)_1"] + merged["Volume (Mcf)_2"]
    final["Energy (MMBTU)"] = merged["Energy (MMBTU)_1"] + merged["Energy (MMBTU)_2"]

    # Weighted averages
    final["Pressure (psig)"] = (merged["Pressure (psig)_1"] + merged["Pressure (psig)_2"]) / 2
    final["Temperature (F)"] = (merged["Temperature (F)_1"] + merged["Temperature (F)_2"]) / 2
    final["Relative Density"] = weighted_avg("Relative Density")
    final["Heating Value (Btu/scf)"] = weighted_avg("Heating Value (Btu/scf)")

    final["Type"] = 0


    # --------------------------------------------------
    # Monthly Composition Weighted by Page Volume Totals
    # --------------------------------------------------
    total_vol_1 = df1["Volume (Mcf)"].sum()
    total_vol_2 = df2["Volume (Mcf)"].sum()
    total_vol = total_vol_1 + total_vol_2

    if total_vol == 0:
        weighted_CO2 = 0
        weighted_N2 = 0
        weighted_C1 = 0
    else:
        weighted_CO2 = (
            comp1["CO2"] * total_vol_1 +
            comp2["CO2"] * total_vol_2
        ) / total_vol

        weighted_N2 = (
            comp1["N2"] * total_vol_1 +
            comp2["N2"] * total_vol_2
        ) / total_vol

        weighted_C1 = (
            comp1["C1"] * total_vol_1 +
            comp2["C1"] * total_vol_2
        ) / total_vol

    final["CO2"] = weighted_CO2
    final["N2"] = weighted_N2
    final["C1"] = weighted_C1


    # --------------------------------------------------
    # Force Final Column Order
    # --------------------------------------------------
    final = final[[
        "Day",
        "Pulses (Counts)",
        "Pressure (psig)",
        "Temperature (F)",
        "Raw Volume()",
        "Relative Density",
        "No Header Column",
        "Volume (Mcf)",
        "Heating Value (Btu/scf)",
        "Energy (MMBTU)",
        "Type",
        "CO2",
        "N2",
        "C1"
    ]]


    # --------------------------------------------------
    # Export
    # --------------------------------------------------

    dates = []
    for i in range(len(final["Day"])):
        day_num = final["Day"][i]
        day = str(month) + "/" + str(day_num) + "/" + str(year)
        dates.append(dt.strptime(day,"%m/%d/%Y"))

    final["Date"] = dates

    final['Pipeline'] = "Williams"
    final['Site'] = "Spuds Lane"

    col_to_keep = ["Pipeline", "Site", "Date", "Volume (Mcf)","Heating Value (Btu/scf)","Energy (MMBtu)","Pressure (psia)", "Temp. (F)", "Relative Density","CO2", "N2","C1"]

    new_cols = [c for c in col_to_keep if c in final.columns]
# new_cols.extend([c for c in df.columns if c not in col_to_keep])

    df_reordered = final[new_cols]


    return df_reordered