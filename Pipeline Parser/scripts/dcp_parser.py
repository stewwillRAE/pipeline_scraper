import pdfplumber
import pandas as pd
# import core_parser as core
from datetime import datetime as dt
import inputs as inp

def site(page_num):
    if page_num == 1:
        name = "TX15"
    elif page_num == 2:
        name = "TX19"
    elif page_num == 3:
        name = "TX31"
    elif page_num == 4:
        name = "OK3"
    elif page_num == 5:
        name = "TX9"
    elif page_num == 6:
        name = "Ellis County"
    else:
        name = "DCP"
    return name

def parser(file):
    month = inp.month(file)
    year = inp.year()

    pdf_path = file

    # ---------------------------------------------------
    # Open PDF
    # ---------------------------------------------------
    with pdfplumber.open(pdf_path) as pdf:

        # This will hold rows from ALL pages
        data_rows = []

        # ---------------------------------------------------
        # Process every page in the PDF
        # ---------------------------------------------------
        for page_number, page in enumerate(pdf.pages, start=1):

            words = page.extract_words()

            # ---------------------------------------------------
            # 1️⃣ Locate CO2, N2, C1 headers
            # ---------------------------------------------------
            headers = {}

            for w in words:
                if w["text"] in ["CO2", "N2", "C1"]:
                    headers[w["text"]] = w

            if len(headers) != 3:
                print(
                    f"Warning: CO2/N2/C1 headers not found "
                    f"on page {page_number} of {pdf_path}"
                )
                continue

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

                        # Must align horizontally
                        if abs(w["x0"] - hx) < 10:

                            try:
                                val = float(
                                    w["text"].replace(",", "")
                                )

                                candidates.append(
                                    (w["top"], val)
                                )

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
            # 3️⃣ Extract Daily Table
            # ---------------------------------------------------
            text = page.extract_text()

            if not text:
                continue

            lines = text.split("\n")

            start_collecting = False

            for line in lines:

                # Find beginning of daily table
                if "Day Differential" in line:
                    start_collecting = True
                    continue

                if start_collecting:

                    # Stop at Total row
                    if "Total" in line:
                        break

                    parts = line.split()

                    # ---------------------------------------------------
                    # Make sure this is a daily data row
                    # ---------------------------------------------------
                    if (
                        len(parts) >= 10
                        and parts[0].isdigit()
                    ):

                        row = []

                        for p in parts[:10]:

                            try:
                                row.append(
                                    float(
                                        p.replace(",", "")
                                    )
                                )

                            except:
                                row.append(0.0)

                        # ---------------------------------------------------
                        # Add monthly composition values
                        # ---------------------------------------------------
                        row.extend([
                            co2,
                            n2,
                            c1
                        ])

                        # ---------------------------------------------------
                        # Add PDF page number
                        # ---------------------------------------------------
                        row.append(page_number)

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
        "Energy (MMBtu)",
        "CO2",
        "N2",
        "C1",
        "Page"
    ]

    df = pd.DataFrame(
        data_rows,
        columns=columns
    )

    # ---------------------------------------------------
    # 5️⃣ Clean Data
    # ---------------------------------------------------

    df = df.fillna(0)

    if not df.empty:
        df["Day"] = df["Day"].astype(int)
    sites_list = []
    for i in range(len(df['Page'])):
        pg = df['Page'][i]
        name = site(pg)
        sites_list.append(name)
    df['Site'] = sites_list

    dates = []
    for i in range(len(df["Day"])):
        day_num = df["Day"][i]
        day = str(month) + "/" + str(day_num) + "/" + str(year)
        dates.append(dt.strptime(day,"%m/%d/%Y"))

    df["Date"] = dates

    df['Pipeline'] = "DCP"

    col_to_keep = ["Pipeline", "Site", "Date", "Volume (Mcf)","Heating Value (Btu/scf)","Energy (MMBtu)","Pressure (psia)", "Temp. (F)", "Relative Density","CO2", "N2","C1"]

    new_cols = [c for c in col_to_keep if c in df.columns]
# new_cols.extend([c for c in df.columns if c not in col_to_keep])

    df_reordered = df[new_cols]


    return df_reordered
    # ---------------------------------------------------
    # 6️⃣ Export
    # ---------------------------------------------------
