"""JB Tender: official G2B API ingest (run locally or on scheduled server).
Never embed the data.go.kr service key in frontend HTML. Python 3.10+ standard library.
Usage:
 export G2B_SERVICE_KEY='your-issued-key'
 python pilots/tender-intelligence/fetch_g2b.py --from-date 20261108 --to-date 20261108 --kind service --output bids.json
"""
import argparse, json, os, sys, urllib.parse, urllib.request, datetime, time
ROOT="https://apis.data.go.kr/1230000/ad/BidPublicInfoService02"
OPS={"service":"getBidPblancListInfoServc02","goods":"getBidPblancListInfoThng02","construction":"getBidPblancListInfoCnstwk02"}
def fetch(day1,day2,kind,key,max_pages):
    start=datetime.datetime.strptime(day1,"%Y%m%d").strftime("%Y%m%d")+"0000"
    end=datetime.datetime.strptime(day2,"%Y%m%d").strftime("%Y%m%d")+"2359"
    out=[]
    seen=set()
    for page in range(1,max_pages+1):
        query={"serviceKey":key,"pageNo":page,"numOfRows":100,"type":"json","inqryDiv":1,"inqryBgnDt":start,"inqryEndDt":end}
        url=ROOT+"/"+OPS[kind]+"?"+urllib.parse.urlencode(query)
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"JB-Tender-Intelligence/0.1"})
            with urllib.request.urlopen(req,timeout=30) as response: payload=json.load(response)
        except Exception as exc:
            raise RuntimeError(f"API network or parsing error (page {page}): {exc}") from exc
        response=payload.get("response",{})
        header=response.get("header",{})
        if str(header.get("resultCode","00")) not in ("00","0"):
            raise RuntimeError(f"G2B API error: {header.get('resultCode')} {header.get('resultMsg')}")
        body=response.get("body",{})
        rows=body.get("items",[])
        if isinstance(rows,dict): rows=rows.get("item",[])
        if isinstance(rows,dict): rows=[rows]
        if not isinstance(rows,list): raise RuntimeError('Unexpected G2B items shape')
        if not rows: break
        for row in rows:
            if not isinstance(row,dict): continue
            identity=(str(row.get('bidNtceNo','')),str(row.get('bidNtceOrd','')))
            if identity != ('','') and identity in seen: continue
            seen.add(identity)
            out.append({"title":row.get("bidNtceNm",""),"agency":row.get("ntceInsttNm",""),
                "region":"","amount":row.get("presmptPrce",""),
                "deadline":row.get("bidClseDt",""),"url":row.get("bidNtceDtlUrl",""),
                "bid_number":row.get("bidNtceNo",""),"round":row.get("bidNtceOrd",""),
                "source":"G2B BidPublicInfoService02","retrieved_at":datetime.datetime.now(datetime.timezone.utc).isoformat()})
        if len(rows)<100:break
        time.sleep(0.25)
    return out
def main():
    parser=argparse.ArgumentParser()
    today=datetime.datetime.now().strftime("%Y%m%d")
    parser.add_argument("--from-date",default=today)
    parser.add_argument("--to-date",default=today)
    parser.add_argument("--kind",choices=list(OPS),default="service")
    parser.add_argument("--max-pages",type=int,default=10)
    parser.add_argument("--output",default="bids.json")
    args=parser.parse_args()
    key=os.environ.get("G2B_SERVICE_KEY")
    if not key:sys.exit("Missing G2B_SERVICE_KEY; apply for key at data.go.kr first.")
    try:
        datetime.datetime.strptime(args.from_date,'%Y%m%d')
        datetime.datetime.strptime(args.to_date,'%Y%m%d')
    except ValueError:
        sys.exit('Dates must use YYYYMMDD')
    if args.from_date>args.to_date:sys.exit("Invalid date range")
    data=fetch(args.from_date,args.to_date,args.kind,key,max(1,min(100,args.max_pages)))
    with open(args.output,"w",encoding="utf-8") as f:json.dump(data,f,ensure_ascii=False,indent=2)
    print(f"Saved {len(data)} bid records to {args.output}. Review source details before offering to customers.")
if __name__=="__main__":main()
