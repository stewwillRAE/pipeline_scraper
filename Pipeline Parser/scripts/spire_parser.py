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
        return re.findall(r"-?\d+\.\d+|-?\d+", line)

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        text = page.extract_text()

    lines = text.split("\n")

    # =====================================================
    # 1️⃣ Extract Monthly CO2 / N2 / C1  (Correct Direction)
    # =====================================================

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()

    co2 = n2 = c1 = 0.0

    # First: find header words
    headers = {}
    header_bottom = None

    for w in words:
        if w["text"] in ["CO2", "N2", "C1"]:
            headers[w["text"]] = w
            header_bottom = w["bottom"]  # store bottom of header row

    # Define vertical search window (only first numeric row)
    vertical_tolerance = 25  # adjust if needed

    for key, header_word in headers.items():

        hx0 = header_word["x0"]
        hbottom = header_word["bottom"]

        for w in words:

            # Must be below header
            if w["top"] > hbottom:

                # Must be within vertical window
                if w["top"] < hbottom + vertical_tolerance:

                    # Must align horizontally
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
    # 2️⃣ Extract Daily Table (Correct Column Positions)
    # =====================================================

    data_rows = []
    start = False

    for line in lines:

        if "Day" in line and "Pressure" in line:
            start = True
            continue

        if start:

            if "Total" in line:
                break

            nums = extract_numbers(line)

            if len(nums) >= 7 and nums[0].isdigit():

                nums = [float(n) for n in nums]

                # True structure in this file:
                day = nums[0]
                pressure = nums[1]
                temp = nums[2]
                rel_density = nums[3]
                volume = nums[4]
                heating = nums[5]
                energy = nums[6]

                # These DO NOT exist in PDF
                pulses = 0.0
                raw_volume = 0.0
                k_factor = 0.0

                row = [
                    day,
                    pulses,
                    pressure,
                    temp,
                    raw_volume,
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
        "Raw Volume (Mcf)",
        "Relative Density",
        "K-Factor (pulses/Mcf)",
        "Volume (Mcf)",
        "Heating Value (Btu/scf)",
        "Energy (MMBtu)"
    ]

    df = pd.DataFrame(data_rows, columns=columns)

    df["Day"] = df["Day"].astype(int)

    # =====================================================
    # 4️⃣ Add Monthly Composition
    # =====================================================

    df["CO2"] = co2
    df["N2"] = n2
    df["C1"] = c1

    # =====================================================
    # 5️⃣ Export
    # =====================================================
    dates = []
    for i in range(len(df["Day"])):
        day_num = df["Day"][i]
        day = str(month) + "/" + str(day_num) + "/" + str(year)
        dates.append(dt.strptime(day,"%m/%d/%Y"))

    df["Date"] = dates

    df['Pipeline'] = "Spire"
    df['Site'] = "Nevada"

    col_to_keep = ["Pipeline", "Site", "Date", "Volume (Mcf)","Heating Value (Btu/scf)","Energy (MMBtu)","Pressure (psia)", "Temp. (F)", "Relative Density","CO2", "N2","C1"]

    new_cols = [c for c in col_to_keep if c in df.columns]
# new_cols.extend([c for c in df.columns if c not in col_to_keep])

    df_reordered = df[new_cols]


    return df_reordered
# print("Excel file created:", excel_output)