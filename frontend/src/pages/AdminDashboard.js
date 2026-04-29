import React, { useState, useEffect } from 'react';

const AdminDashboard = ({ t }) => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAlerts = async () => {
      const mockData = [
        {
          id: 1,
          date_detected: "2026-03-24",
          title: "Maharashtra Rent Control (Amendment) Notification",
          link: "https://example.com/gazette",
          ai_analysis: "YES. Rent Control. The amendment increases the minimum eviction notice period from 1 month to 45 days in urban areas.",
          status: "PENDING_ADMIN_APPROVAL"
        },
        {
          id: 2,
          date_detected: "2026-03-23",
          title: "Code on Wages - Revised Minimum Floor Wage",
          link: "https://example.com/labour",
          ai_analysis: "YES. Employment. The national floor wage has been adjusted, requiring updates to the basic pay threshold calculations.",
          status: "PENDING_ADMIN_APPROVAL"
        }
      ];
      
      setTimeout(() => {
        setAlerts(mockData);
        setLoading(false);
      }, 800);
    };

    fetchAlerts();
  }, []);

  const handleAction = (id, actionType) => {
    setAlerts(prevAlerts => 
      prevAlerts.map(alert => 
        alert.id === id ? { ...alert, status: actionType } : alert
      )
    );
  };

  // Safe fallback if t is undefined during fast reloads
  const theme = t || { text: '#fff', sub: '#aaa', border: '#333', surfaceUp: '#1a1a1a', blue: '#3b82f6' };

  const styles = {
    container: { padding: '40px', maxWidth: '1000px', margin: '0 auto', color: theme.text },
    header: { borderBottom: `1px solid ${theme.border}`, paddingBottom: '20px', marginBottom: '30px' },
    card: { background: theme.surfaceUp, border: `1px solid ${theme.border}`, borderRadius: '12px', padding: '24px', marginBottom: '20px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' },
    titleRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' },
    title: { margin: 0, fontSize: '1.2rem', fontFamily: '"DM Serif Display", serif', color: theme.text },
    date: { fontSize: '0.9rem', color: theme.sub },
    aiBox: { backgroundColor: `${theme.blue}15`, padding: '16px', borderRadius: '8px', borderLeft: `4px solid ${theme.blue}`, marginBottom: '20px', color: theme.text, lineHeight: '1.6' },
    aiLabel: { fontWeight: '800', color: theme.blue, marginBottom: '8px', display: 'block', fontSize: '0.95rem' },
    buttonRow: { display: 'flex', gap: '12px', alignItems: 'center' },
    btnApprove: { backgroundColor: '#10b981', color: 'white', border: 'none', padding: '10px 20px', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', transition: 'opacity 0.2s' },
    btnReject: { backgroundColor: 'transparent', color: '#ef4444', border: '1px solid #ef4444', padding: '10px 20px', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', transition: 'background 0.2s' },
    link: { marginLeft: 'auto', color: theme.blue, textDecoration: 'none', fontWeight: '600', fontSize: '0.95rem' }
  };

  if (loading) return <div style={{...styles.container, textAlign: 'center', marginTop: '50px'}}>Loading Legislative Alerts...</div>;

  const pendingAlerts = alerts.filter(a => a.status === "PENDING_ADMIN_APPROVAL");

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={{fontFamily: '"DM Serif Display", serif', fontSize: '2.5rem', marginBottom: '10px'}}>Admin Dashboard</h1>
        <p style={{color: theme.sub}}>Human-in-the-loop legislative monitoring system.</p>
      </div>

      <h2 style={{marginBottom: '20px'}}>Pending Approvals ({pendingAlerts.length})</h2>
      
      {pendingAlerts.map(alert => (
        <div key={alert.id} style={styles.card}>
          <div style={styles.titleRow}>
            <h3 style={styles.title}>{alert.title}</h3>
            <span style={styles.date}>Detected: {alert.date_detected}</span>
          </div>
          
          <div style={styles.aiBox}>
            <span style={styles.aiLabel}>Llama-3 Analysis:</span>
            {alert.ai_analysis}
          </div>

          <div style={styles.buttonRow}>
            <button 
              style={styles.btnApprove} 
              onMouseEnter={(e) => e.target.style.opacity = '0.8'}
              onMouseLeave={(e) => e.target.style.opacity = '1'}
              onClick={() => handleAction(alert.id, 'APPROVED_FOR_UPDATE')}
            >
              Approve & Update Matrix
            </button>
            <button 
              style={styles.btnReject} 
              onMouseEnter={(e) => { e.target.style.backgroundColor = '#ef4444'; e.target.style.color = '#fff'; }}
              onMouseLeave={(e) => { e.target.style.backgroundColor = 'transparent'; e.target.style.color = '#ef4444'; }}
              onClick={() => handleAction(alert.id, 'REJECTED')}
            >
              Reject / Ignore
            </button>
            <a href={alert.link} target="_blank" rel="noreferrer" style={styles.link}>
              Read Full Gazette Source →
            </a>
          </div>
        </div>
      ))}
    </div>
  );
};

export default AdminDashboard;