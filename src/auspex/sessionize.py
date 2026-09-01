from pathlib import Path

import numpy as np
import pandas as pd

from auspex.config import Cfg


def load(name : str) -> pd.DataFrame:
    
    parent_path = Path(__file__).resolve().parents[2] /"data/processed" 
    file_name = "NASA_access_log_" + name +".parquet"
    path = parent_path / file_name
    df = pd.read_parquet(path)
    return df


def label_sessions(df : pd.DataFrame, cfg : Cfg) -> pd.DataFrame:
    
    df_sorted = df.sort_values(by = ["host" , "ts" , "seq"] ,  ignore_index=True)
    host_changed_boolean = df_sorted["host"] != df_sorted["host"].shift(1)
    session_gap_boolean = df_sorted["ts"] - df_sorted["ts"].shift(1) > cfg.session_gap_s 
   
    sorted_host_session = host_changed_boolean | session_gap_boolean

    df_sorted["session_id"] = sorted_host_session.cumsum()

    df_sorted["pos_in_session"] = df_sorted.groupby("session_id").cumcount() 

    return df_sorted

def drop_robots_hosts(df : pd.DataFrame) -> tuple[pd.DataFrame , int]:

    bad_hosts =  df.loc[df["url"] == "/robots.txt" , "host"].unique()
    mask = df["host"].isin(bad_hosts)
    rows_dropped = mask.sum()
    robot_hosts_free_df = df[~mask]

    return (robot_hosts_free_df , rows_dropped)


def drop_long_sessions(df : pd.DataFrame, cfg : Cfg) -> tuple[pd.DataFrame , int]:

    session_length = df.groupby("session_id").size()

    mask_length = session_length[session_length > cfg.bot_max_session_len]

    print(f"Maximum sessions in the file : {mask_length.nlargest(5)}")

    mask = df.session_id.isin(mask_length.index)
    rows_dropped = mask.sum()
    long_session_free_df = df[~mask]

    return (long_session_free_df , rows_dropped)
    
    


def main():
    df = load("Aug95")

    cfg = Cfg()
    df_sorted = label_sessions(df , cfg )
    robot_free_df , robot_rows_removed = drop_robots_hosts(df_sorted)

    print(f"Number of robot rows removed are : {robot_rows_removed}" )

    long_session_free_df , long_session_rows_removed = drop_long_sessions(robot_free_df , cfg)

    print(f"Number of long session rows removed are : {long_session_rows_removed}" )

    

if __name__ == "__main__":
    main()