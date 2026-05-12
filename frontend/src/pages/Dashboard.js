import { useState, useEffect } from "react";
import { PageTitle, Card, Btn, Input, Ic, ICONS, Tag, ErrBox, Spinner } from "../components/UI";

export default function Dashboard({ t, toast }) {
  const [token, setToken] = useState(localStorage.getItem("ns_token"));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [cases, setCases] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [hearings, setHearings] = useState([]);
  
  const [newCase, setNewCase] = useState({ title: "", cnr_number: "", court_name: "", client_name: "" });
  const [newTask, setNewTask] = useState({ title: "", description: "", due_date: "", case_id: "" });
  const [newHearing, setNewHearing] = useState({ purpose: "", hearing_date: "", case_id: "", notes: "" });

  useEffect(() => {
    if (token) fetchUser();
  }, [token]);

  const fetchUser = async () => {
    try {
      const res = await fetch("http://localhost:8001/api/auth/me", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        setUser(await res.json());
        fetchData();
      } else {
        localStorage.removeItem("ns_token");
        setToken(null);
      }
    } catch (e) {
      toast("Connection error", "error");
    }
  };

  const fetchData = async () => {
    try {
      const headers = { "Authorization": `Bearer ${token}` };
      const [cRes, tRes, hRes] = await Promise.all([
        fetch("http://localhost:8001/api/cases", { headers }),
        fetch("http://localhost:8001/api/tasks", { headers }),
        fetch("http://localhost:8001/api/hearings", { headers })
      ]);
      if (cRes.ok) setCases(await cRes.json());
      if (tRes.ok) setTasks(await tRes.json());
      if (hRes.ok) setHearings(await hRes.json());
    } catch (e) {
      console.log(e);
    }
  };

  const handleAuth = async () => {
    setLoading(true);
    const url = isRegister ? "http://localhost:8001/api/auth/register" : "http://localhost:8001/api/auth/login";
    const body = isRegister 
      ? JSON.stringify({ email, password, full_name: email.split("@")[0], phone: "0000000000" })
      : JSON.stringify({ email, password });
      
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body
      });
      const data = await res.json();
      if (res.ok) {
        if (isRegister) {
          toast("Registration successful. Please log in.", "success");
          setIsRegister(false);
        } else {
          localStorage.setItem("ns_token", data.access_token);
          setToken(data.access_token);
          toast("Logged in successfully", "success");
        }
      } else {
        toast(data.detail || "Authentication failed", "error");
      }
    } catch (e) {
      toast("Server error", "error");
    }
    setLoading(false);
  };

  const handleCreateCase = async () => {
    if (!newCase.title) return toast("Case title is required", "error");
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8001/api/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify(newCase)
      });
      if (res.ok) {
        toast("Case created", "success");
        setNewCase({ title: "", cnr_number: "", court_name: "", client_name: "" });
        fetchData();
      }
    } catch (e) {
      toast("Error creating case", "error");
    }
    setLoading(false);
  };

  const handleCreateTask = async () => {
    if (!newTask.title || !newTask.due_date) return toast("Title and Due Date required", "error");
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8001/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ ...newTask, due_date: new Date(newTask.due_date).toISOString() })
      });
      if (res.ok) {
        toast("Task created", "success");
        setNewTask({ title: "", description: "", due_date: "", case_id: "" });
        fetchData();
      }
    } catch (e) {
      toast("Error creating task", "error");
    }
    setLoading(false);
  };

  const handleCreateHearing = async () => {
    if (!newHearing.purpose || !newHearing.hearing_date || !newHearing.case_id) return toast("Purpose, Date, and Case required", "error");
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8001/api/hearings", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ ...newHearing, hearing_date: new Date(newHearing.hearing_date).toISOString() })
      });
      if (res.ok) {
        toast("Hearing added", "success");
        setNewHearing({ purpose: "", hearing_date: "", case_id: "", notes: "" });
        fetchData();
      } else {
        toast("Error: Not authorized for this case", "error");
      }
    } catch (e) {
      toast("Error creating hearing", "error");
    }
    setLoading(false);
  };

  if (!token || !user) {
    return (
      <div style={{ maxWidth: 400, margin: "80px auto", padding: "0 20px" }}>
        <Card t={t}>
          <div style={{ textAlign: "center", marginBottom: 24 }}>
            <div style={{ width: 48, height: 48, background: `${t.blue}22`, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
              <Ic d={ICONS.grid} size={24} color={t.blue} />
            </div>
            <h2 style={{ fontSize: 22, fontWeight: 800, margin: "0 0 8px" }}>{isRegister ? "Create Account" : "Lawyer Login"}</h2>
            <p style={{ fontSize: 14, color: t.sub }}>Access your firm dashboard</p>
          </div>
          
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email address" t={t} />
            <Input value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" t={t} />
            <Btn onClick={handleAuth} loading={loading} t={t} style={{ width: "100%", justifyContent: "center" }}>
              {isRegister ? "Register" : "Sign In"}
            </Btn>
            <button onClick={() => setIsRegister(!isRegister)} style={{ background: "none", border: "none", color: t.blue, cursor: "pointer", fontSize: 13, marginTop: 8 }}>
              {isRegister ? "Already have an account? Sign in" : "Need an account? Register"}
            </button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1000, margin: "40px auto", padding: "0 20px" }}>
      <PageTitle 
        icon="grid" 
        title={`Welcome back, ${user.full_name}`} 
        desc="Manage your cases, hearings, and daily tasks in one centralized dashboard." 
        badge={user.role.toUpperCase()}
        t={t} 
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 24, marginBottom: 40 }}>
        <Card t={t}>
          <h3 style={{ fontSize: 14, color: t.sub, margin: "0 0 8px" }}>Active Cases</h3>
          <div style={{ fontSize: 32, fontWeight: 800 }}>{cases.length}</div>
        </Card>
        <Card t={t}>
          <h3 style={{ fontSize: 14, color: t.sub, margin: "0 0 8px" }}>Upcoming Hearings</h3>
          <div style={{ fontSize: 32, fontWeight: 800 }}>{hearings.length}</div>
        </Card>
        <Card t={t}>
          <h3 style={{ fontSize: 14, color: t.sub, margin: "0 0 8px" }}>Pending Tasks</h3>
          <div style={{ fontSize: 32, fontWeight: 800 }}>{tasks.filter(t => !t.is_completed).length}</div>
        </Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 24 }}>
        {/* Main Content Area */}
        <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
          {/* Cases */}
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
              <h2 style={{ fontSize: 18, fontWeight: 800 }}>My Cases</h2>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {cases.length === 0 ? (
                <div style={{ padding: 40, textAlign: "center", border: `1px dashed ${t.border}`, borderRadius: 12, color: t.sub }}>
                  No active cases. Create one from the sidebar.
                </div>
              ) : (
                cases.map(c => (
                  <Card key={c.id} t={t} style={{ padding: "16px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }} hover>
                    <div>
                      <h4 style={{ margin: "0 0 4px", fontSize: 15, fontWeight: 700 }}>{c.title}</h4>
                      <div style={{ fontSize: 12, color: t.sub, display: "flex", gap: 12 }}>
                        {c.cnr_number && <span>CNR: {c.cnr_number}</span>}
                        {c.court_name && <span>Court: {c.court_name}</span>}
                      </div>
                    </div>
                    <Tag label={c.status} variant="info" t={t} />
                  </Card>
                ))
              )}
            </div>
          </div>

          {/* Tasks & Hearings */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>Tasks</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {tasks.length === 0 ? <div style={{ color: t.sub, fontSize: 14 }}>No tasks</div> : tasks.map(t => (
                  <div key={t.id} style={{ padding: 12, background: t.surfaceUp, borderRadius: 8, border: `1px solid ${t.border}` }}>
                    <div style={{ fontWeight: 700, fontSize: 14 }}>{t.title}</div>
                    <div style={{ fontSize: 12, color: t.sub }}>Due: {new Date(t.due_date).toLocaleDateString()}</div>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 800, marginBottom: 16 }}>Hearings</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {hearings.length === 0 ? <div style={{ color: t.sub, fontSize: 14 }}>No hearings</div> : hearings.map(h => (
                  <div key={h.id} style={{ padding: 12, background: t.surfaceUp, borderRadius: 8, border: `1px solid ${t.border}` }}>
                    <div style={{ fontWeight: 700, fontSize: 14 }}>{h.purpose}</div>
                    <div style={{ fontSize: 12, color: t.sub }}>{new Date(h.hearing_date).toLocaleDateString()}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Add Case */}
          <Card t={t}>
            <h3 style={{ fontSize: 16, fontWeight: 800, margin: "0 0 16px" }}>Add New Case</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <Input value={newCase.title} onChange={e => setNewCase({...newCase, title: e.target.value})} placeholder="Case Title (e.g. State vs John)" t={t} />
              <Input value={newCase.cnr_number} onChange={e => setNewCase({...newCase, cnr_number: e.target.value})} placeholder="CNR Number (Optional)" t={t} />
              <Input value={newCase.court_name} onChange={e => setNewCase({...newCase, court_name: e.target.value})} placeholder="Court Name" t={t} />
              <Btn onClick={handleCreateCase} loading={loading} t={t} style={{ width: "100%", justifyContent: "center" }}>Create Case</Btn>
            </div>
          </Card>

          {/* Add Task */}
          <Card t={t}>
            <h3 style={{ fontSize: 16, fontWeight: 800, margin: "0 0 16px" }}>Add Task</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <Input value={newTask.title} onChange={e => setNewTask({...newTask, title: e.target.value})} placeholder="Task title" t={t} />
              <input type="date" value={newTask.due_date} onChange={e => setNewTask({...newTask, due_date: e.target.value})} style={{ background:t.surfaceUp, border:`1.5px solid ${t.border}`, borderRadius:9, padding:"10px 16px", color:t.text, fontFamily:"inherit" }} />
              <select value={newTask.case_id} onChange={e => setNewTask({...newTask, case_id: e.target.value})} style={{ background:t.surfaceUp, border:`1.5px solid ${t.border}`, borderRadius:9, padding:"10px 16px", color:t.text, fontFamily:"inherit" }}>
                <option value="">Select Case (Optional)</option>
                {cases.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
              </select>
              <Btn onClick={handleCreateTask} loading={loading} t={t} style={{ width: "100%", justifyContent: "center" }}>Add Task</Btn>
            </div>
          </Card>

          {/* Add Hearing */}
          <Card t={t}>
            <h3 style={{ fontSize: 16, fontWeight: 800, margin: "0 0 16px" }}>Schedule Hearing</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <Input value={newHearing.purpose} onChange={e => setNewHearing({...newHearing, purpose: e.target.value})} placeholder="Purpose" t={t} />
              <input type="date" value={newHearing.hearing_date} onChange={e => setNewHearing({...newHearing, hearing_date: e.target.value})} style={{ background:t.surfaceUp, border:`1.5px solid ${t.border}`, borderRadius:9, padding:"10px 16px", color:t.text, fontFamily:"inherit" }} />
              <select value={newHearing.case_id} onChange={e => setNewHearing({...newHearing, case_id: e.target.value})} style={{ background:t.surfaceUp, border:`1.5px solid ${t.border}`, borderRadius:9, padding:"10px 16px", color:t.text, fontFamily:"inherit" }}>
                <option value="">Select Case</option>
                {cases.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
              </select>
              <Btn onClick={handleCreateHearing} loading={loading} t={t} style={{ width: "100%", justifyContent: "center" }}>Schedule</Btn>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
