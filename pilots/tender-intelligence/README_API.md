# JB Tender Intelligence — API integration (server-side)
The static index.html is a **sample/demo** and cannot call G2B without leaking a key. This script fetches published service/goods/construction bid listings from the official data.go.kr API and exports standardized JSON for manual import into the demo. Requires authorized G2B_SERVICE_KEY and network connection.

\`\`\`sh
export G2B_SERVICE_KEY='YOUR_OFFICIAL_KEY'
python pilots/tender-intelligence/fetch_g2b.py --from-date 20261108 --to-date 20261108 --kind service --output bids.json
\`\`\`

Open the JSON output and paste into the MVP input field. For production add credential storage, pagination/quotas, nightly scheduled retrieval, license/region filters, dedup on bid number and revision, audit logs, and actual customer qualification validation. Confirm the current API request parameters against the provider documentation; not tested against the live endpoint without an issued service key. Do not auto-deploy this as part of every production commit. Official API: https://www.data.go.kr/data/15129394/openapi.do.
