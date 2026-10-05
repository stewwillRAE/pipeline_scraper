import os
import pandas as pd
import kinder_morgan_parser as kmp
import dcp_parser as dcp
import eiger_parser as eig
import spire_parser as spr
import tallgrass_parser as tgr
import columbia_gas_parser as clg
import williams_parser as wil
import sqlite3


folder_path = "Pipeline Parser/pdfs"  # change to your folder

files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

dataframes = []

for i in range(len(files)):
    file = files[i]
    if "SF" in file:
        dataframe = pd.DataFrame(kmp.parser(folder_path + "/" + file))
        dataframes.append(dataframe)
    elif "DCP" in file:
        dataframe = pd.DataFrame(dcp.parser(folder_path + "/" + file))
        dataframes.append(dataframe) 
    elif "Lakin" in file or "Moscow" in file:
        dataframe = pd.DataFrame(eig.parser(folder_path + "/" + file))
        dataframes.append(dataframe)
    elif "Nevada" in file:
        dataframe = pd.DataFrame(spr.parser(folder_path + "/" + file))
        dataframes.append(dataframe)
    elif "Scott City" in file:
        dataframe = pd.DataFrame(tgr.parser(folder_path + "/" + file))
        dataframes.append(dataframe)
    elif "WV" in file:
        dataframe = pd.DataFrame(clg.parser(folder_path + "/" + file))
        dataframes.append(dataframe)
    elif "Williams" in file:
        dataframe = pd.DataFrame(wil.parser(folder_path + "/" + file))
        dataframes.append(dataframe) 


conn = sqlite3.connect("Pipeline Parser/Pipeline DB.db")
cursor = conn.cursor()
for index, row in dataframes[0].iterrows():
    # The timestamp value cannot transfer correctly?
    cursor.execute("INSERT INTO PipelineDB (pipeline_company, rae_inj_site, date, volume_MMSCF, hhv_btu, energy_Dth, pressure_Psia, temp_F, specific_grav, co2, n2, ch4) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    (row[0], row[1], str(row[2]), row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11]))
    conn.commit()
    # rows = cursor.fetchall()
    # for row in rows:
    #     print(row)
    
