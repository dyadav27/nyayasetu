import sys
sys.path.append("d:/major-project/backend")
from document_analyzer import fetch_case_laws

query = '"Union of India" act'
cases = fetch_case_laws(query, "Act Search", pagenum=0)
print("Returned cases count:", len(cases))
for c in cases[:5]:
    print(c)
