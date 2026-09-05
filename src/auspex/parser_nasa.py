import argparse
import datetime as dt
import gzip
import re
import sys
from pathlib import Path

import pandas as pd

#regex for pattern matching of the urls 
LOG_RE = re.compile(r'^(?P<host>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<req>[^"]*)" (?P<status>\d{3}) (?P<size>\S+)')


def parse_line(line):
    #checks if the line matches the regex or not
    #also makes columns accordingly like host col , ts col , req col , status col , size col 
    m = LOG_RE.match(line)

    # if it dosetn match the regex
    if m==None:
        return None

    #size here just means the request size 
    size = None if m["size"] == "-" else int(m["size"]) 

    # basically req col has url and method seperated so we use split to extract each one of em
    list_request = m["req"].split()
    #if its missing either return None basically means malformed
    if len(list_request) < 2:
        return None

    #naming cols
    (method , url) = (list_request[0] , list_request[1])

    #extracts everything before the first occurance of # and returns it in 0th index 
    url = url.split('#' , 1)[0]

    # converting the time col into something nicer
    t = int(dt.datetime.strptime(m["ts"] , "%d/%b/%Y:%H:%M:%S %z").timestamp())

    #return dict of data for each col 
    return {"host" : m["host"], "ts" : t, "method" : method , "url" : url  , "status" : int(m["status"]),"size" : size}


def parse_file(path):
    malformed , filtered , kept , total  = 0 , 0 , 0 , 0
    kept_rows = []

    #use gzip to unzip stuff like .tgz files in linux 
    with gzip.open(path , "rt" , encoding="latin-1") as f:
        #enumerate cuz just wanna calculate total
        for i , line in enumerate(f):
            total +=1
            # finally parse indv line
            response = parse_line(line)

            #increment malformed if the line dosetn meet our requiremetns 
            if response is None:
                malformed+=1 

            #we only need GET and non 400 if its other than those then we can just skip em and increment filtered count
            # we only need em cuz other stuff would contribute to cache pollution
            elif response["method"] != "GET" or response["status"] != 200:
                filtered+=1 

            # now we know its get and 200 so we drop the method and status column 
            # as they will just be repeated values atp
            else:
                kept+=1
                response.pop("method" , None)
                response.pop("status" , None)
                response["seq"] = i
                #append it in kept rows to finally indicate that we have kept thsi row ig its a list
                kept_rows.append(response)   

    return {"kept_rows" : kept_rows , "malformed" : malformed , "dropped" : filtered , "kept" : kept , "total" : total}



def write_parquet(kept_rows , output_path):
    # convert to df 
    df = pd.DataFrame(kept_rows)
    # i think we did it cuz it was int64 before and that cause some issue i am not sure what exaclty 
    df["size"] = df["size"].astype("Int32")

    #just simple parquet write
    df.to_parquet(output_path , index=False)



def make_dir_fetch_details_write_parquet(name : str):
    # get the location for /data foldere 
    # .parents[2] aka .parent.parent.parent init
    parent_path = Path(__file__).resolve().parents[2] / "data"
    output_path = parent_path / "processed/"

    #make processed folder if its not there inside the data folder otherwise its k 
    output_path.mkdir(exist_ok=True , parents=True)

    #just naming 
    combined_data_path_string = "raw/NASA_access_log_" + name + ".gz"
    comobined_file_path_string = "NASA_access_log_" + name + ".parquet" 

    #actual file path init
    data_path = parent_path / combined_data_path_string
    file_path = output_path / comobined_file_path_string

    #parse the file 
    response = parse_file(data_path)

    #get data from the return 
    kept_rows , malformed , dropped , kept , total = response["kept_rows"] , response["malformed"] , response["dropped"] , response["kept"] , response["total"]

    # check if the stuff we dropped , the stuff we kept and the stuff that didnt match regex is equal to 
    # the total number of rows we had orignally 
    # just a safety check so we know taht we havent lost anything 
    assert malformed + dropped + kept == total

    # we aim to keep it less than 0.001 if its nto that then our regex is cooked
    if malformed/total > 0.001:
        print("WARNING MALFORMED IS TOO MUCH YOUR REGEX IS WRONG" , file=sys.stderr)
    print(f"Malformed :  {malformed}  | dropped :  {dropped}  | kept : {kept}  | total :  {total}")
   #finally write our newly formed parquet 
    write_parquet(kept_rows , file_path)



def main():
    # just for arguments so user can enter arguments form cli 
    ap = argparse.ArgumentParser()
    ap.add_argument("-j" , action="store_true")
    ap.add_argument("-a" , action="store_true")
    args = ap.parse_args()

    #will print help if the user didnt give any arguments dont really need it ig cuz we have makefile and 
    # obv eveyrone gonna run that 
    if not args.j and not args.a:  
        ap.print_help()
        return 

    #if user gave -a as arg
    if args.a:

        make_dir_fetch_details_write_parquet("Aug95")

    #if they gave -j as arg
    if args.j:
        
        make_dir_fetch_details_write_parquet("Jul95")

#only run file if its run direclty and dosent run anything if its imported as a module
if __name__ == "__main__":
    main()