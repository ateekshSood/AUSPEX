from pathlib import Path

import pandas as pd

from auspex.config import Cfg


def load(name : str) -> pd.DataFrame:
    
    parent_path = Path(__file__).resolve().parents[2] /"data/processed" 
    file_name = "NASA_access_log_" + name +".parquet"
    path = parent_path / file_name
    df = pd.read_parquet(path)
    return df


def label_sessions(df : pd.DataFrame, cfg : Cfg):
    
    df_sorted = df.sort_values(by = ["host" , "ts" , "seq"] ,  ignore_index=True)
    host_changed = df_sorted["host"] != df_sorted["host"].shift(1)
    session_gap = df_sorted["ts"] - df_sorted["ts"].shift(1) > cfg.session_gap_s 
   
    sorted_host_session = host_changed | session_gap

    df_sorted["session_id"] = sorted_host_session.cumsum()

    return df_sorted

    


def main():
    df = load("Aug95")

    cfg = Cfg()
    df_sorted = label_sessions(df , cfg )
    

if __name__ == "__main__":
    main()