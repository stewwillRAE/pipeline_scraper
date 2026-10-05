import pdfplumber
import pandas as pd
from datetime import datetime as dt
import inputs as inp

#  This script only works for pipeline statements from June 2024 to present

def parser(file):
    month = inp.month(file)
    year = inp.year()

    pdf_pathway = file

    with pdfplumber.open(pdf_pathway) as pdf:
        first_page = pdf.pages[0]
        first_table = first_page.extract_tables()[0]

    df = pd.DataFrame(first_table)
    df = df.dropna(how="all")
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # Remove first 6 rows
    df = df.iloc[5:].reset_index(drop=True)

    # Set headers and remove empty columns
    df.columns = df.iloc[0]
    df = df.iloc[1:].reset_index(drop=True)
    df = df.loc[:, df.columns.notna()]
    df = df.loc[:, df.columns.astype(str).str.strip() != ""]
    df = df.dropna(axis=1, how="all")

    # 🔽 ADD THE MISSING-DATES CODE RIGHT HERE 🔽

    # Convert Flow Date to datetime

    df = df[df["Flow Date"] != "Flow Date"]

    # Convert Flow Date to datetime
    df["Flow Date"] = pd.to_datetime(df["Flow Date"], errors="coerce")
    df = df.dropna(subset=["Flow Date"])

    # Force all other columns to numeric
    for col in df.columns:
        if col != "Flow Date":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Create full daily date range
    full_dates = pd.date_range(
        start=df["Flow Date"].min(),
        end=df["Flow Date"].max(),
        freq="D"
    )

    # Reindex and fill missing rows with 0
    df = df.set_index("Flow Date").reindex(full_dates).fillna(0)

    # Restore Flow Date column
    df = df.rename_axis("Flow Date").reset_index()

    # Convert datetime to date only
    df["Flow Date"] = df["Flow Date"].dt.date


    df['Pipeline'] = "Columbia Gas"
    df['Site'] = "Waverly"
    # Temp\n(F)  Static\nPress\n(PSIA)  Spec\nGrav  Mol %\nN2  Mol %\nCO2  Meter Index\nReading  Meter Index\nDiff  Meas Vol\n(Mcf)  BTU\nContent  Energy Qty\n(Dth)
    df['CH4'] = (100 - (df["Mol %\nCO2"] + df["Mol %\nN2"]))

    col_to_keep = ["Pipeline", "Site", "Flow Date", "Meas Vol\n(Mcf)","BTU\nContent","Energy Qty\n(Dth)","Static\nPress\n(PSIA)", "Temp\n(F)", "Spec\nGrav","Mol %\nCO2", "Mol %\nN2","CH4"]

    new_cols = [c for c in col_to_keep if c in df.columns]
# new_cols.extend([c for c in df.columns if c not in col_to_keep])

    df_reordered = df[new_cols]


    return df_reordered