import sys
sys.path.append('d:/major-project/backend')
from document_analyzer import fetch_case_laws

res = fetch_case_laws('"State of Maharashtra Act"', 'Act Search')
print(len(res))
for r in res[:5]:
    print(r['title'])
