import argparse
import json
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from auspex.config import Cfg


def get_parquet(name : str) -> tuple[pd.DataFrame , str]:

    parent_path = Path(__file__).resolve().parents[2] /"data/processed" 
    file_name = "NASA_access_log_cleaned_" + name +".parquet"
    path = parent_path / file_name
    df = pd.read_parquet(path)

    #debugging
    # print(df.head(5)) 

    return (df , file_name)

def calculate_stats(gap_without_na : pd.Series , gap_time_in_sec : int) -> float:
   
    return float((gap_without_na >=gap_time_in_sec ).mean())
    

def get_stats(name : str):

    df , file_name = get_parquet(name)

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

    frac_gap_ge_1 = calculate_stats(gap_without_na , 1)

    frac_gap_ge_2 = calculate_stats(gap_without_na , 2)

    frac_gap_ge_5 = calculate_stats(gap_without_na , 5)

    gap_p50 = gap_without_na.quantile(0.50)
    gap_p90 = gap_without_na.quantile(0.90)
    gap_p99 = gap_without_na.quantile(0.99)

    top_20_frequency_url = df["url"].value_counts().head(20)
    # can also use df.groupby("url").size().sort_values(ascending = False).head(20)

    fig , ax = plt.subplots(nrows=1 , ncols=2 , figsize=(12 , 5))
    
    bins = np.arange(1, 52)
    ax[0].hist(indv_session_length , bins = bins, log=True)
    ax[0].set_xlabel("Session length in requests ( upto 50)")
    ax[0].grid()
    ax[0].set_ylabel("Num sessions (log scale)")

    frac_zero_gap = (gap_without_na == 0).mean()
    postive_gaps = gap_without_na[gap_without_na > 0]

    cfg = Cfg()
    bins = np.geomspace(1 , cfg.session_gap_s , 30)

    ax[1].hist(postive_gaps , bins = bins , log=True)
    ax[1].set_xscale("log")
    ax[1].set_title(f"{frac_zero_gap:.1%} of gaps are 0 s")
    ax[1].set_xlabel("Inter request gap sec (log scale)")
    ax[1].set_ylabel("number of transitions (log)")
    ax[1].grid()

    save_path_parent = Path(__file__).resolve().parent.parent.parent
    save_file = "results/" + name + ".png"
    save_path = save_path_parent / save_file
    
    fig.savefig(save_path)

    return {
            "trace": file_name,
            "total_requests": int(num_requests),
            "unique_urls": int(unique_url),
            "unique_hosts": int(unique_hosts),
    
            "num_sessions": int(num_sessions),
            "session_len_p50": float(median_session_length),
            "session_len_p90": float(ninety_th_percentile),
            "session_len_max": int(max_session_lenght),
    
            "singleton_sessions": int(singleton_session_num),
            "singleton_sessions_share": float(singleton_sessions_share),
            "singleton_requests": int(singleton_request_num),
            "singleton_requests_share": float(singleton_requests_share),
    
            "num_transitions": len(gap_without_na),
            "gap_p50": float(gap_p50),
            "gap_p90": float(gap_p90),
            "gap_p99": float(gap_p99),
            "frac_gap_zero": float(frac_zero_gap),
            "frac_gap_ge_1": float(frac_gap_ge_1),
            "frac_gap_ge_2": float(frac_gap_ge_2),
            "frac_gap_ge_5": float(frac_gap_ge_5),
    
            "top_20_urls": {k: int(v) for k, v in top_20_frequency_url.items()},
        }
    

def main():

    ap = argparse.ArgumentParser()
    ap.add_argument("-j" , action="store_true")
    ap.add_argument("-a" , action="store_true")
    args = ap.parse_args()

    if not args.j and not args.a:
        ap.print_help()
        return 

    months = {}

    if args.a:

        months["Aug95"] = get_stats("Aug95")
    

    if args.j:
    
        months["Jul95"] = get_stats("Jul95")

    repo_root = Path(__file__).resolve().parents[2]
    
    payload = {
        "git_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip(),
        "generated_at": datetime.now(UTC).isoformat(),
        "cfg": asdict(Cfg()),
        "months": months,          
    }

    out = repo_root / "results" / "stage0_summary.json"

    text = json.dumps(payload, indent=2)
    print(text)                 
    out.write_text(text)
            


if __name__ == "__main__":

    main()
    
    #debugging
    # getParquet("Aug95")