import pdfplumber
import pandas as pd
from datetime import datetime as dt
import inputs as inp

def site(file):
    if "Moscow" in file:
        site = "Mowcow"
    elif "Lakin" in file:
        site = "Lakin"
    return site

def parser(file):
    month = inp.month(file)
    year = inp.year()
    
    pdf_path = file

# pdf_path = "Ellis County December 2024.pdf"
# xlsx_path = "Ellis County December 2024.xlsx"

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]

        words = page.extract_words()

        # ---------------------------------------------------
        # 1️⃣ Locate CO2, N2, C1 headers by x-position
        # ---------------------------------------------------
        headers = {}
        for w in words:
            if w["text"] in ["CO2", "N2", "C1"]:
                headers[w["text"]] = w

        if len(headers) != 3:
            raise ValueError("Could not locate CO2, N2, C1 headers.")

        # ---------------------------------------------------
        # 2️⃣ Find numeric values directly BELOW each header
        # ---------------------------------------------------
        def get_value_below(header_word):
            hx = header_word["x0"]
            hy = header_word["top"]

            candidates = []
            for w in words:
                # Must be below header
                if w["top"] > hy:
                    # Must align horizontally (same column region)
                    if abs(w["x0"] - hx) < 10:
                        try:
                            val = float(w["text"].replace(",", ""))
                            candidates.append((w["top"], val))
                        except:
                            pass

            # Return closest value below header
            if candidates:
                candidates.sort()
                return candidates[0][1]
            return 0.0

        co2 = get_value_below(headers["CO2"])
        n2 = get_value_below(headers["N2"])
        c1 = get_value_below(headers["C1"])

        # ---------------------------------------------------
        # 3️⃣ Extract Daily Table Using Text Parsing
        # ---------------------------------------------------
        text = page.extract_text()
        lines = text.split("\n")

        data_rows = []
        start_collecting = False

        for line in lines:
            if "Day Differential" in line:
                start_collecting = True
                continue

            if start_collecting:
                if "Total" in line:
                    break

                parts = line.split()
                if len(parts) >= 10 and parts[0].isdigit():
                    row = []
                    for p in parts[:10]:
                        try:
                            row.append(float(p))
                        except:
                            row.append(0.0)
                    data_rows.append(row)

    # ---------------------------------------------------
    # 4️⃣ Build DataFrame
    # ---------------------------------------------------

    columns = [
        "Day",
        "Differential (In. H2o)",
        "Pressure (psia)",
        "Temp. (F)",
        "Flow Time (hrs)",
        "Relative Density",
        "Plate (inches)",
        "Volume (Mcf)",
        "Heating Value (Btu/scf)",
        "Energy (MMBtu)"
    ]

    df = pd.DataFrame(data_rows, columns=columns)

    df = df.fillna(0)
    df["Day"] = df["Day"].astype(int)

    # ---------------------------------------------------
    # 5️⃣ Add Repeating Monthly Values
    # ---------------------------------------------------

    df["CO2"] = co2
    df["N2"] = n2
    df["C1"] = c1

    # ---------------------------------------------------
    # 6️⃣ Export
    # ---------------------------------------------------

    dates = []
    for i in range(len(df["Day"])):
        day_num = df["Day"][i]
        day = str(month) + "/" + str(day_num) + "/" + str(year)
        dates.append(dt.strptime(day,"%m/%d/%Y"))

    df["Date"] = dates

    df['Pipeline'] = "Eiger"
    df['Site'] = site(file)

    col_to_keep = ["Pipeline", "Site", "Date", "Volume (Mcf)","Heating Value (Btu/scf)","Energy (MMBtu)","Pressure (psia)", "Temp. (F)", "Relative Density","CO2", "N2","C1"]

    new_cols = [c for c in col_to_keep if c in df.columns]
# new_cols.extend([c for c in df.columns if c not in col_to_keep])

    df_reordered = df[new_cols]


    return df_reordered
    # ----------------------