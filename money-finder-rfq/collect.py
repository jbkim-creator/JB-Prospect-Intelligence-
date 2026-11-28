import os, json, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
FEED="https://netroq.com/feed/rfq.xml"
def parse(data):
    root=ET.fromstring(data)
    ns={"a":"http://www.w3.org/2005/Atom"}
    rows={}
    for e in root.findall("a:entry",ns):
        key=e.findtext("a:id",namespaces=ns)
        title=e.findtext("a:title",namespaces=ns)
        link=e.find("a:link",ns)
        if key and title:
            rows[key]={"source":"netroq","external_id":key,"title":title,"source_url":link.get("href") if link is not None else None,"published_at":e.findtext("a:published",namespaces=ns),"last_seen_at":datetime.now(timezone.utc).isoformat()}
    if not rows: raise ValueError("No valid Atom entries")
    return list(rows.values())
def main():
    with urllib.request.urlopen(FEED,timeout=30) as r:
        rows=parse(r.read(5000000))
    key=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    url=os.environ["SUPABASE_URL"].rstrip("/")+"/rest/v1/mf_rfq_items?on_conflict=source,external_id"
    req=urllib.request.Request(url,data=json.dumps(rows).encode(),headers={"apikey":key,"Authorization":"Bearer "+key,"Content-Type":"application/json","Prefer":"resolution=merge-duplicates,return=minimal"},method="POST")
    with urllib.request.urlopen(req,timeout=30) as r:
        print("Upserted",len(rows),"RFQs; HTTP",r.status)
if __name__=="__main__": main()
