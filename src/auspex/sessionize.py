import argparse
from pathlib import Path

import pandas as pd
import sys

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


#IT WILL BE ZERO SINCE ALL ROBOT ROWS ARE ALREADY DELETED SINCE THEY WERE NON GET AND 400

def drop_robots_hosts(df : pd.DataFrame) -> tuple[pd.DataFrame , int]:

    bad_hosts =  df.loc[df["url"] == "/robots.txt" , "host"].unique()
    mask = df["host"].isin(bad_hosts)
    rows_dropped = mask.sum()
    robot_hosts_free_df = df[~mask]

    return (robot_hosts_free_df , rows_dropped)


def drop_long_sessions(df : pd.DataFrame, cfg : Cfg) -> tuple[pd.DataFrame , int]:

    session_length = df.groupby("session_id").size()

    mask_length = session_length[session_length > cfg.bot_max_session_len]

    print(f"Longest sessions in the file : {mask_length.nlargest(5)}")

    mask = df["session_id"].isin(mask_length.index)
    rows_dropped = mask.sum()
    long_session_free_df = df[~mask]

    return (long_session_free_df , rows_dropped)



#if we simply remove anyone who has more than 100 requests per session then we can remove 
# normal ppl too since normal humans can request for a particular thing 100 times as well 
# hence we combine it with something called cv which stands for coeff of variation 
# simply defines how much the data has spread from its mean and since humans gonna request 
# at random and not at fixed time they will have high cv while bots will request at some fixed interval hence will 
# have low cv 
# 
# IT WILL BE 0 FOR THIS DATASET SINCE THE AUTO CLOCK REQUESTS ARE HELLA RANODM LIKE [ 0 , 0 , 100 , 0 , 100]
# AND NOT BALANCED LIKE [ 100 , 100 , 100 , 100 ,100]
def drop_metronome_hosts(df : pd.DataFrame , cfg : Cfg) -> tuple[pd.DataFrame , int]:

    df = df.copy()
    
    df["gap"] = df.groupby("host")["ts"].diff()

    host_group = df.groupby("host")["gap"]

    cv_per_host = host_group.std() / host_group.mean()
    count_per_host = host_group.size()

    flags = (count_per_host >= cfg.bot_cv_min_request) & (cv_per_host < cfg.bot_cv_threshold)

    bad_hosts = flags[flags].index

    mask = df["host"].isin(bad_hosts)
    num_dropped = mask.sum()
    df = df.drop(columns=["gap"])
    df = df[~mask]

    return (df , num_dropped)


    
def write(df : pd.DataFrame , name : str) -> None:

    parent_path = Path(__file__).resolve().parents[2] /"data/processed"
    file_name = "NASA_access_log_cleaned_" + name +".parquet"
    output_path = parent_path / file_name
    
    df_sorted_again = df.sort_values(by = ["ts" , "seq"] ,  ignore_index=True) 
    df_sorted_again.to_parquet(output_path , index=False)


    
def process_month(name: str) -> None:

    df = load(name)
    
    cfg = Cfg()
    df_sorted = label_sessions(df , cfg )
    robot_free_df , robot_rows_removed = drop_robots_hosts(df_sorted)

    print(f"Number of robot rows removed are : {robot_rows_removed}" )

    long_session_free_df , long_session_rows_removed = drop_long_sessions(robot_free_df , cfg)

    print(f"Number of long session rows removed are : {long_session_rows_removed}" )

    processed_df , bot_removed = drop_metronome_hosts(long_session_free_df , cfg)

    print(f"Number of bot removed are  : {bot_removed}" )

    total_dropped = robot_rows_removed + long_session_rows_removed + bot_removed 
    if total_dropped / len(df) > 0.10:
        print("MORE THAN 10% OF THE DATA HAS BEEN REMOVED WARNING " , file = sys.stderr)

    write(processed_df , name)

    

def main():
    
    ap = argparse.ArgumentParser()
    ap.add_argument("-j" , action="store_true")
    ap.add_argument("-a" , action="store_true")
    args = ap.parse_args()
    
    if not args.j and not args.a:
        ap.print_help()
        return 
    
    if args.a:
    
        process_month("Aug95")
        print("Cleaned August file")
    
    if args.j:
        
        process_month("Jul95")
        print("Cleaned July file")
        

    
if __name__ == "__main__":
    main()