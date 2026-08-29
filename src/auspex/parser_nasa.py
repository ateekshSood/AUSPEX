import gzip
import re
import sys
import datetime as dt
import pandas as pd
from pathlib import Path
import argparse

LOG_RE = re.compile(r'^(?P<host>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<req>[^"]*)" (?P<status>\d{3}) (?P<size>\S+)')


def parse_line(line):
    m = LOG_RE.match(line)

    if m==None:
        return None
    
    size = None if m["size"] == "-" else int(m["size"]) 
    
    list_request = m["req"].split()
    if len(list_request) < 2:
        return None

    (method , url) = (list_request[0] , list_request[1]) 
    url = url.split('#' , 1)[0]
    
    t = int(dt.datetime.strptime(m["ts"] , "%d/%b/%Y:%H:%M:%S %z").timestamp())
    
    return {"host" : m["host"], "ts" : t, "method" : method , "url" : url  , "status" : int(m["status"]),"size" : size}


def parse_file(path):
    malformed , filtered , kept , total  = 0 , 0 , 0 , 0
    kept_rows = []
    with gzip.open(path , "rt" , encoding="latin-1") as f:
        for i , line in enumerate(f):
            total +=1
            response = parse_line(line)

            if response is None:
                malformed+=1 

            elif response["method"] != "GET" or response["status"] != 200:
                filtered+=1 

            else:
                kept+=1
                response.pop("method" , None)
                response.pop("status" , None)
                response["seq"] = i
                kept_rows.append(response)   

    return {"kept_rows" : kept_rows , "malformed" : malformed , "dropped" : filtered , "kept" : kept , "total" : total}

def write_parquet(kept_rows , output_path):
    df = pd.DataFrame(kept_rows)
    df["size"] = df["size"].astype("Int32")
    
    df.to_parquet(output_path , index=False)

def make_dir_fetch_details_write_parquet(name : str):
    parent_path = Path(__file__).resolve().parents[2] / "data"
    output_path = parent_path / "processed/"

    output_path.mkdir(exist_ok=True , parents=True)
    
    combined_data_path_string = "raw/NASA_access_log_" + name + ".gz"
    comobined_file_path_string = "NASA_access_log_" + name + ".parquet" 
    
    data_path = parent_path / combined_data_path_string
    file_path = output_path / comobined_file_path_string

    
    response = parse_file(data_path)
    
    kept_rows , malformed , dropped , kept , total = response["kept_rows"] , response["malformed"] , response["dropped"] , response["kept"] , response["total"]

    assert malformed + dropped + kept == total
    
    if malformed/total > 0.001:
        print("WARNING MALFORMED IS TOO MUCH YOUR REGEX IS WRONG" , file=sys.stderr)
    print(f"Malformed :  {malformed}  | dropped :  {dropped}  | kept : {kept}  | total :  {total}") 
    write_parquet(kept_rows , file_path)



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-j" , action="store_true")
    ap.add_argument("-a" , action="store_true")
    args = ap.parse_args()

    if not args.j and not args.a:
        ap.print_help()
        return 

    
    if args.a:

        make_dir_fetch_details_write_parquet("Aug95")

    if args.j:
        
        make_dir_fetch_details_write_parquet("Jul95")

if __name__ == "__main__":
    main()