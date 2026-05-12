import { useState, useEffect } from "react";
import { PageTitle, Card, Btn, Input, Tag, Ic, ICONS } from "../components/UI";

export default function Billing({ t, toast }) {
  const [token] = useState(localStorage.getItem("ns_token"));
  const [loading, setLoading] = useState(false);
  const [invoices, setInvoices] = useState([]);
  const [newInv, setNewInv] = useState({ client_name: "", amount: "", due_date: "" });

  useEffect(() => {
    if (token) fetchInvoices();
  }, [token]);

  const fetchInvoices = async () => {
    try {
      const res = await fetch("http://localhost:8001/api/invoices", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) setInvoices(await res.json());
    } catch (e) {
      console.log(e);
    }
  };

  const handleCreate = async () => {
    if (!token) return toast("Please login via Dashboard first", "error");
    if (!newInv.client_name || !newInv.amount || !newInv.due_date) return toast("Fill all fields", "error");
    
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8001/api/invoices", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ ...newInv, amount: parseFloat(newInv.amount) })
      });
      if (res.ok) {
        toast("Invoice Created", "success");
        setNewInv({ client_name: "", amount: "", due_date: "" });
        fetchInvoices();
      } else {
        toast("Error creating invoice", "error");
      }
    } catch (e) {
      toast("Server Error", "error");
    }
    setLoading(false);
  };

  if (!token) {
    return <div style={{ textAlign: "center", padding: 100 }}>Please log in via Dashboard to access Firm Billing.</div>;
  }

  const totalRevenue = invoices.filter(i => i.status === "Paid").reduce((acc, i) => acc + i.amount, 0);
  const pendingRevenue = invoices.filter(i => i.status !== "Paid").reduce((acc, i) => acc + i.amount, 0);

  return (
    <div style={{ maxWidth: 1000, margin: "40px auto", padding: "0 20px" }}>
      <PageTitle 
        icon="doc" 
        title="Firm Billing & Invoicing" 
        desc="Manage your law firm's revenue, generate invoices, and track pending payments." 
        t={t} 
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 24, marginBottom: 40 }}>
        <Card t={t}>
          <h3 style={{ fontSize: 14, color: t.sub, margin: "0 0 8px" }}>Total Revenue</h3>
          <div style={{ fontSize: 32, fontWeight: 800, color: t.green }}>₹{totalRevenue.toLocaleString()}</div>
        </Card>
        <Card t={t}>
          <h3 style={{ fontSize: 14, color: t.sub, margin: "0 0 8px" }}>Pending Payments</h3>
          <div style={{ fontSize: 32, fontWeight: 800, color: t.amber }}>₹{pendingRevenue.toLocaleString()}</div>
        </Card>
        <Card t={t}>
          <h3 style={{ fontSize: 14, color: t.sub, margin: "0 0 8px" }}>Total Invoices</h3>
          <div style={{ fontSize: 32, fontWeight: 800 }}>{invoices.length}</div>
        </Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 24 }}>
        <Card t={t}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <h2 style={{ fontSize: 18, fontWeight: 800 }}>Invoice History</h2>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {invoices.length === 0 ? (
              <div style={{ padding: 40, textAlign: "center", color: t.sub }}>No invoices found. Create one.</div>
            ) : (
              invoices.map(inv => (
                <div key={inv.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 16px", background: t.surfaceUp, borderRadius: 8, border: `1px solid ${t.border}` }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 15 }}>{inv.client_name}</div>
                    <div style={{ fontSize: 12, color: t.sub }}>Due: {new Date(inv.due_date).toLocaleDateString()}</div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                    <div style={{ fontWeight: 800 }}>₹{inv.amount.toLocaleString()}</div>
                    <Tag label={inv.status} variant={inv.status === "Paid" ? "success" : "warning"} t={t} />
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        <Card t={t} style={{ height: "fit-content" }}>
          <h3 style={{ fontSize: 16, fontWeight: 800, margin: "0 0 16px" }}>Create Invoice</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <Input value={newInv.client_name} onChange={e => setNewInv({...newInv, client_name: e.target.value})} placeholder="Client Name" t={t} />
            <Input value={newInv.amount} onChange={e => setNewInv({...newInv, amount: e.target.value})} placeholder="Amount (₹)" t={t} />
            <input type="date" value={newInv.due_date} onChange={e => setNewInv({...newInv, due_date: e.target.value})} style={{ background:t.surfaceUp, border:`1.5px solid ${t.border}`, borderRadius:9, padding:"10px 16px", color:t.text, fontFamily:"inherit" }} />
            <Btn onClick={handleCreate} loading={loading} t={t} style={{ width: "100%", justifyContent: "center" }}>Send Invoice</Btn>
          </div>
        </Card>
      </div>
    </div>
  );
}
