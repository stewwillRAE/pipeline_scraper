import pdfplumber
import pandas as pd
import re
from datetime import datetime as dt
import inputs as inp

def parser(file):
    month = inp.month(file)
    year = inp.year()

    pdf_path = file

    def extract_numbers(line):
        # Remove commas from large numbers first
        line = line.replace(",", "")
        return re.findall(r"-?\d+\.\d+|-?\d+", line)

    # =====================================================
    # 1️⃣ Extract Monthly CO2 / N2 / C1 (Coordinate Based)
    # =====================================================

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()

    co2 = n2 = c1 = 0.0

    headers = {}

    for w in words:
        if w["text"] in ["CO2", "N2", "C1"]:
            headers[w["text"]] = w

    vertical_tolerance = 25

    for key, header_word in headers.items():

        hx0 = header_word["x0"]
        hbottom = header_word["bottom"]

        for w in words:
            if w["top"] > hbottom and w["top"] < hbottom + vertical_tolerance:
                if abs(w["x0"] - hx0) < 8:
                    try:
                        value = float(w["text"])
                        if key == "CO2":
                            co2 = value
                        elif key == "N2":
                            n2 = value
                        elif key == "C1":
                            c1 = value
                        break
                    except:
                        continue

    # =====================================================
    # 2️⃣ Extract Daily Table
    # =====================================================

    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text()

    lines = text.split("\n")

    data_rows = []
    start = False

    for line in lines:

        if "Day Pulses" in line:
            start = True
            continue

        if start:

            if "Total" in line:
                break

            if "No" in line:

                nums = extract_numbers(line)

                # Expected numeric structure:
                # Day, Pulses, Pressure, Temp,
                # Relative Density, K-Factor,
                # Volume, Heating Value, Energy

                if len(nums) >= 9:

                    nums = [float(n) for n in nums]

                    day = nums[0]
                    pulses = nums[1]
                    pressure = nums[2]
                    temp = nums[3]
                    rel_density = nums[4]
                    k_factor = nums[5]
                    volume = nums[6]
                    heating = nums[7]
                    energy = nums[8]

                    row = [
                        day,
                        pulses,
                        pressure,
                        temp,
                        rel_density,
                        k_factor,
                        volume,
                        heating,
                        energy
                    ]

                    data_rows.append(row)

    # =====================================================
    # 3️⃣ Build DataFrame
    # =====================================================

    columns = [
        "Day",
        "Pulses (Counts)",
        "Pressure (psig)",
        "Temp. (F)",
        "Relative Density",
        "K-Factor (counts/lbm)",
        "Volume (Mcf)",
        "Heating Value (Btu/scf)",
        "Energy (MMBtu)"
    ]

    df = pd.DataFrame(data_rows, columns=columns)

    df["Day"] = df["Day"].astype(int)

    # =====================================================
    # 4️⃣ Add Monthly Composition Columns
    # =====================================================

    df["CO2"] = co2
    df["N2"] = n2
    df["C1"] = c1

    dates = []
    for i in range(len(df["Day"])):
        day_num = df["Day"][i]
        day = str(month) + "/" + str(day_num) + "/" + str(year)
        dates.append(dt.strptime(day,"%m/%d/%Y"))

    df["Date"] = dates

    df['Pipeline'] = "Tallgrass"
    df['Site'] = "Scott City"

    col_to_keep = ["Pipeline", "Site", "Date", "Volume (Mcf)","Heating Value (Btu/scf)","Energy (MMBtu)","Pressure (psia)", "Temp. (F)", "Relative Density","CO2", "N2","C1"]

    new_cols = [c for c in col_to_keep if c in df.columns]
# new_cols.extend([c for c in df.columns if c not in col_to_keep])

    df_reordered = df[new_cols]


    return df_reordered