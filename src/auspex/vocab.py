from pathlib import Path

import numpy as np
import pandas as pd


def get_parquet(name : str) -> tuple[pd.Series , str]:

    parent_path = Path(__file__).resolve().parents[2] /"data/processed" 
    file_name = "NASA_access_log_cleaned_" + name +".parquet"
    path = parent_path / file_name
    df = pd.read_parquet(path) #only load the url column

    assert df["ts"].is_monotonic_decreasing , "The parquet is not sorted by (ts, seq) sort it..."
    

    return (df["url"] , file_name)

def set_int() -> None:
    
    df_aug , _ = get_parquet("Aug95")
    df_jul , _ = get_parquet("Jul95")

    df_concat = pd.concat([df_jul , df_aug] , ignore_index=True)

    #returns id based order 0...1..1..1..2. so on based on first occursace 
    # can also use sort=True wiht it , retursn tuple of numpy arr of the id and 
    # the unique values as well
    _ , unique_url = pd.factorize(df_concat["url"]) 
    df_url_id = pd.DataFrame({"url" : unique_url , "url_id" : np.arange(len(unique_url))})

    write_parquet(df_url_id)


    
def write_parquet(df : pd.DataFrame) -> None:
    
    parent_path = Path(__file__).resolve().parents[2] / "data/processed"
    file_path = "vocab.parquet"
    path = parent_path / file_path

    df.to_parquet(path = path , index=False)
    
    

def main():
    
       set_int()

if __name__ == "__main__":
    main()