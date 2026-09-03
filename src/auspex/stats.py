import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt 
import pandas as pd
from typing import TypedDict


class GapStats(TypedDict):
    frac_gap : float
    p50 : float 
    p90 : float 
    p99 : float

def get_parquet(name : str) -> pd.DataFrame:

    parent_path = Path(__file__).resolve().parents[2] /"data/processed" 
    file_name = "NASA_access_log_cleaned_" + name +".parquet"
    path = parent_path / file_name
    df = pd.read_parquet(path)

    #debugging
    # print(df.head(5)) 

    return df

def calculate_stats(gap_without_na : pd.Series , gap_time_in_sec : int) -> GapStats:
    return {
    "frac_gap" : (gap_without_na >=gap_time_in_sec ).mean(),
    "p50" :  (gap_without_na >=gap_time_in_sec).median(),
    "p90" : (gap_without_na >=gap_time_in_sec).quantile(0.9),
    "p99" : (gap_without_na >=gap_time_in_sec).quantile(0.99),
    }

def get_stats(name : str):

    df = get_parquet(name)

    num_requests = len(df)
    unique_url = df["url"].nunique()
    unique_hosts = df["host"].nunique()

    num_sessions = df["session_id"].nunique()

    indv_session_length = df.groupby("session_id").size()
    median_session_length = indv_session_length.median()
    ninety_th_percentile = indv_session_length.quantile(0.9) 
    max_session_lenght = indv_session_length.max()

    singleton_session_num = (indv_session_length == 1).sum()
    #its equal cuz singleton sessions will have one request only 
    singleton_request_num = singleton_session_num 

    singleton_sessions_share = singleton_session_num / num_sessions
    singleton_requests_share = singleton_request_num / num_requests

    #gap

    gap = df.groupby("session_id")["ts"].diff()
    gap_without_na = gap.dropna()

    assert len(gap_without_na) == len(df) - num_sessions , "Gap size dosent match"

    gap_ge_1_stats = calculate_stats(gap_without_na , 1)
    frac_gap_ge_1 , gap_ge_1_p50 , gap_ge_1_p90 , gap_ge_1_p99 = gap_ge_1_stats["frac_gap"] , gap_ge_1_stats["p50"] , gap_ge_1_stats["p90"] , gap_ge_1_stats["p99"]

    gap_ge_2_stats = calculate_stats(gap_without_na , 2)
    frac_gap_ge_2 , gap_ge_2_p50 , gap_ge_2_p90 , gap_ge_2_p99 = gap_ge_2_stats["frac_gap"] , gap_ge_2_stats["p50"] , gap_ge_2_stats["p90"] , gap_ge_2_stats["p99"]

    gap_ge_1_stats = calculate_stats(gap_without_na , 1)
    frac_gap_ge_5 , gap_ge_5_p50 , gap_ge_5_p90 , gap_ge_5_p99 = gap_ge_5_stats["frac_gap"] , gap_ge_5_stats["p50"] , gap_ge_5_stats["p90"] , gap_ge_5_stats["p99"]
    

    top_20_frequency_url = df["url"].value_counts().head(20)
    # can also use df.groupby("url").size().sort_values(ascending = False).head(20)


    plt.hist(indv_session_length , log=True)
    


    
    
    
     
    

    

def main():

     ap = argparse.ArgumentParser()
     ap.add_argument("-j" , action="store_true")
     ap.add_argument("-a" , action="store_true")
     args = ap.parse_args()
     
     if not args.j and not args.a:
         ap.print_help()
         return 
     
     if args.a:
     
         get_stats("Aug95")
         
     
     if args.j:
         
         get_stats("Jul95")
     
         


if __name__ == "__main__":

    main()
    
    #debugging
    # getParquet("Aug95")