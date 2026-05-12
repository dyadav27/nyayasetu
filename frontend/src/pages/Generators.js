import { useState } from "react";
import { PageTitle, Card, Btn, Input, Textarea, Ic, ICONS } from "../components/UI";

export default function Generators({ t, toast }) {
  const [token] = useState(localStorage.getItem("ns_token"));
  const [loading, setLoading] = useState(false);
  const [docType, setDocType] = useState("Rent Agreement");
  const [form, setForm] = useState({ party_a: "", party_b: "", details: "" });
  const [result, setResult] = useState("");

  const handleGenerate = async () => {
    if (!token) return toast("Please login via Dashboard first", "error");
    if (!form.party_a || !form.party_b || !form.details) return toast("Fill all fields", "error");
    
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8001/api/generate_doc", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ doc_type: docType, ...form })
      });
      const data = await res.json();
      if (res.ok) {
        setResult(data.content);
        toast("Document Generated", "success");
      } else {
        toast("Error generating document", "error");
      }
    } catch (e) {
      toast("Server Error", "error");
    }
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: 1000, margin: "40px auto", padding: "0 20px" }}>
      <PageTitle 
        icon="doc" 
        title="AI Legal Document Generator" 
        desc="Instantly draft Rent Agreements, Legal Notices, and more using structured templates." 
        badge="BETA"
        t={t} 
      />

      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 24 }}>
        <Card t={t} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <h3 style={{ margin: "0 0 8px", fontSize: 16, fontWeight: 800 }}>Document Details</h3>
          
          <select value={docType} onChange={e => setDocType(e.target.value)} style={{ background:t.surfaceUp, border:`1.5px solid ${t.border}`, borderRadius:9, padding:"10px 16px", color:t.text, fontFamily:"inherit" }}>
            <option value="Rent Agreement">Rent Agreement</option>
            <option value="Legal Notice">Legal Notice</option>
          </select>
          
          <Input 
            value={form.party_a} 
            onChange={e => setForm({...form, party_a: e.target.value})} 
            placeholder={docType === "Rent Agreement" ? "Landlord Name" : "Sender Name"} 
            t={t} 
          />
          <Input 
            value={form.party_b} 
            onChange={e => setForm({...form, party_b: e.target.value})} 
            placeholder={docType === "Rent Agreement" ? "Tenant Name" : "Recipient Name"} 
            t={t} 
          />
          <Textarea 
            value={form.details} 
            onChange={e => setForm({...form, details: e.target.value})} 
            placeholder={docType === "Rent Agreement" ? "Property address, rent amount, tenure..." : "Subject of the notice, demands..."} 
            rows={6}
            t={t} 
          />
          
          <Btn onClick={handleGenerate} loading={loading} t={t} style={{ width: "100%", justifyContent: "center", marginTop: 8 }}>
            Generate Document
          </Btn>
        </Card>

        <Card t={t}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 800 }}>Generated Output</h3>
            {result && <Btn outline small onClick={() => { navigator.clipboard.writeText(result); toast("Copied!", "success"); }} t={t}>Copy</Btn>}
          </div>
          
          <div style={{ 
            background: t.surfaceUp, 
            border: `1.5px solid ${t.border}`, 
            borderRadius: 12, 
            padding: 20, 
            minHeight: 400,
            whiteSpace: "pre-wrap",
            fontFamily: "monospace",
            fontSize: 13,
            lineHeight: 1.6,
            color: result ? t.text : t.sub
          }}>
            {result || "Your generated document will appear here..."}
          </div>
        </Card>
      </div>
    </div>
  );
}
