import pdfplumber
import pandas as pd
import re

def parser(file):
    # month_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

    pdf_path = file
       
    headers = [
        "DATE",
        "MCF",
        "MMBTU",
        "PRESSURE PSIG",
        "TEMP (T)",
        "PULSE/lbMass",
        "FLOW TIME (MINUTES)",
        "Pulse Count",
        "LBS Mass",
        "WATER VAPOR FACTOR",
        "(*) BTU FACTOR",
        "GRAVITY",
        "CO2",
        "N2",
        "EST / ACT",
        "REV"
    ]

    rows = []

    # Match numbers AND words (EST / ACT)
    token_pattern = re.compile(r"[A-Z]+|-?\d+(?:,\d{3})*(?:\.\d+)?")

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[1]
        text = page.extract_text() or ""

    for line in text.split("\n"):
        if not re.match(r"\d{2}/\d{2}/\d{4}", line):
            continue

        date_val = line[:10]
        remainder = line[10:]

        tokens = token_pattern.findall(remainder)

        # We expect at least:
        # 5 decimals + 2 integers + 6 decimals = 13 numeric tokens
        numeric_tokens = [t for t in tokens if re.search(r"\d", t)]
        text_tokens = [t for t in tokens if t.isalpha()]

        if len(numeric_tokens) < 13:
            continue

        row = (
            [date_val] +
            numeric_tokens[:5] +        # MCF → FLOW TIME
            numeric_tokens[5:7] +        # Pulse Count, LBS Mass
            numeric_tokens[7:13] +       # WATER VAPOR → N2
            [text_tokens[0] if text_tokens else None] +
            [None]
        )

        rows.append(row)

    df = pd.DataFrame(rows, columns=headers)

    # --- Cleanup & typing ---

    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    df = df.dropna(subset=["DATE"])

    numeric_cols = headers[1:14]

    for col in numeric_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .pipe(pd.to_numeric, errors="coerce")
            .fillna(0)
        )

    df["DATE"] = df["DATE"].dt.date
    df['CH4'] = 100 - (df['CO2'] + df['N2'])
    df['Pipeline'] = "Kinder Morgan"
    df['Site'] = "Snowflake"
    df['(*) BTU FACTOR'] = df['(*) BTU FACTOR'] * 1000

    col_to_keep = ["Pipeline", "Site", "DATE", "MCF","(*) BTU FACTOR","MMBTU","PRESSURE PSIG", "TEMP (T)", "GRAVITY","CO2", "N2","CH4"]

    new_cols = [c for c in col_to_keep if c in df.columns]
    # new_cols.extend([c for c in df.columns if c not in col_to_keep])

    df_reordered = df[new_cols]

    return df_reordered