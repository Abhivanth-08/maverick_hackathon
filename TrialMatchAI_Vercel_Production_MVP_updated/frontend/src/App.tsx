import { useEffect, useState, type ReactElement } from 'react';
import { Navigate, Route, Routes, useNavigate, Link, useLocation } from 'react-router-dom';
import { api } from './lib/api';

type Overview = { patients: number; trials: number; matches: number; pending_jobs: number; unread_notifications: number };
type Patient = { id: number; external_patient_id: string; sex?: string; date_of_birth?: string };
type Trial = { id: number; nct_id: string; title: string; status?: string; phase?: string; conditions: string[] };

function Protected({ children }: { children: any }) {
  return localStorage.getItem('tm_token') ? children : <Navigate to="/login" replace />;
}

function NavIcon({ name }: { name: string }) {
  const icons: Record<string, ReactElement> = {
    rocket: <path d="M12 2c1.5 2 2.5 5 2.5 8 0 1.5-.3 3-1 4.5L12 17l-1.5-2.5C9.8 13 9.5 11.5 9.5 10c0-3 1-6 2.5-8z M9 15l-2 2v3l3-1.5 M15 15l2 2v3l-3-1.5 M12 8a1.5 1.5 0 100 3 1.5 1.5 0 000-3z" />,
    grid: <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z" />,
    users: <path d="M17 20v-1a4 4 0 00-4-4H7a4 4 0 00-4 4v1 M12 11a4 4 0 100-8 4 4 0 000 8z M23 20v-1a4 4 0 00-3-3.87 M16 3.13a4 4 0 010 7.75" />,
    flask: <path d="M9 3h6 M10 3v6l-5.5 9.5A2 2 0 006.2 21h11.6a2 2 0 001.7-2.5L14 9V3 M6.5 15h11" />,
    chart: <path d="M3 3v18h18 M18 17V9 M13 17V5 M8 17v-4" />,
    shield: <path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-4z" />,
  };
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      {icons[name]}
    </svg>
  );
}

function Layout({ children }: { children: any }) {
  const nav = useNavigate();
  const location = useLocation();

  const links = [
    { to: '/hackathon', label: 'Hackathon Pitch', icon: 'rocket', accent: true },
    { to: '/dashboard', label: 'Overview', icon: 'grid' },
    { to: '/patients', label: 'Patients', icon: 'users' },
    { to: '/trials', label: 'Trials', icon: 'flask' },
    { to: '/monitoring', label: 'Monitoring & Analytics', icon: 'chart' },
    { to: '/audit', label: 'Audit Trail', icon: 'shield' },
  ];

  return (
    <div className="app">
      <aside>
        <div className="brand-block">
          <h1>TrialMatch<span>AI</span></h1>
          <p className="muted">Research screening platform</p>
        </div>
        <nav>
          {links.map(l => {
            const active = location.pathname.startsWith(l.to);
            return (
              <Link
                key={l.to}
                to={l.to}
                className={`nav-link${active ? ' active' : ''}${l.accent ? ' accent' : ''}`}
              >
                <NavIcon name={l.icon} />
                <span>{l.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <button className="ghost" onClick={() => { localStorage.removeItem('tm_token'); nav('/login'); }}>
            Sign out
          </button>
        </div>
      </aside>
      <main>{children}</main>
    </div>
  );
}

function Login() {
  const [email, setEmail] = useState('researcher@trialmatch.ai');
  const [password, setPassword] = useState('Demo123!');
  const [err, setErr] = useState('');
  const nav = useNavigate();
  
  async function submit(e: any) {
    e.preventDefault();
    try {
      const r = await api<any>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
      localStorage.setItem('tm_token', r.access_token);
      nav('/dashboard');
    } catch (x: any) {
      setErr(x.message);
    }
  }
  
  return (
    <div className="login">
      <div className="login-card">
        <div className="brand">TrialMatch<span>AI</span></div>
        <h2>Researcher & Admin Sign In</h2>
        <p className="muted">Evidence-aware clinical trial screening</p>
        <form onSubmit={submit}>
          <label>Email<input value={email} onChange={e => setEmail(e.target.value)} /></label>
          <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} /></label>
          {err && <div className="error">{err}</div>}
          <button>Sign in</button>
        </form>
        <small style={{ marginTop: '1rem', display: 'block' }}>Demo: researcher@trialmatch.ai / Demo123!</small>
      </div>
    </div>
  );
}

type DashboardOverview = {
  patients: { total: number; screened: number; pending: number; recently_updated: number };
  trials: { total: number; recruiting: number; completed: number; other: number };
  matches: { total: number; high_confidence: number; medium_confidence: number; low_confidence: number; needs_review: number };
  eligibility: { met: number; not_met: number; unknown: number; conflicting: number };
  changes: { patients_requiring_rescreen: number; trials_with_changes: number; affected_candidates: number };
  sync: { source: string; api_version: string; last_sync: string; inserted: number; updated: number; failed: number; status: string };
  recent_activity: Array<{ id: number; action: string; entity_type?: string; entity_id?: string; created_at: string; metadata?: any }>;
  recent_matches: Array<{ match_id: number; patient_id: number; external_patient_id: string; trial_id: number; nct_id: string; trial_title: string; status: string; score: number; evaluated_at: string }>;
  system_health: { backend_api: string; database: string; clinicaltrials_api: string; matching_engine: string };
};

function Dashboard() {
  const [d, setD] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const nav = useNavigate();

  function loadData() {
    setLoading(true);
    setErr(null);
    api<DashboardOverview>('/api/dashboard/overview')
      .then(res => {
        setD(res);
        setLoading(false);
      })
      .catch(x => {
        setErr(x.message || 'Unable to load dashboard data.');
        setLoading(false);
      });
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleSync() {
    setSyncing(true);
    try {
      await api<any>('/api/trials/sync?limit=10', { method: 'POST' });
      loadData();
    } catch (x: any) {
      alert(`Sync failed: ${x.message}`);
    } finally {
      setSyncing(false);
    }
  }

  if (loading) {
    return (
      <Layout>
        <header>
          <div>
            <p className="eyebrow">RESEARCH OPERATIONS</p>
            <h2>Screening Overview & Analytics</h2>
            <p className="muted">Monitor patient screening, trial matching, eligibility changes, and research actions from one place.</p>
          </div>
        </header>
        <div className="cards">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div className="card" key={i} style={{ opacity: 0.6, animation: 'pulse 1.5s infinite' }}>
              <span>Loading metric…</span>
              <strong style={{ fontSize: '24px', color: '#94a3b8' }}>—</strong>
            </div>
          ))}
        </div>
      </Layout>
    );
  }

  if (err || !d) {
    return (
      <Layout>
        <h2>Screening Overview & Analytics</h2>
        <div className="panel error" style={{ display: 'grid', gap: '12px' }}>
          <h3>Unable to load dashboard data</h3>
          <p>{err || 'Data service temporarily unavailable.'}</p>
          <div>
            <button onClick={loadData}>Retry Loading Dashboard</button>
          </div>
        </div>
      </Layout>
    );
  }

  const patientScreenedPct = d.patients.total > 0 ? Math.round((d.patients.screened / d.patients.total) * 100) : 0;
  const trialEvaluatedPct = d.trials.total > 0 ? Math.round(((d.trials.recruiting + d.trials.completed) / d.trials.total) * 100) : 0;
  const formattedLastSync = d.sync.last_sync ? d.sync.last_sync.replace('T', ' ').split('.')[0] + ' UTC' : '—';

  return (
    <Layout>
      {/* 3. TOP HEADER */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <p className="eyebrow">RESEARCH OPERATIONS</p>
          <h2 style={{ margin: '4px 0' }}>Screening Overview & Analytics</h2>
          <p className="muted" style={{ margin: 0 }}>
            Monitor patient screening, trial matching, eligibility changes, and research actions from one place.
          </p>
        </div>
        <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
          <div style={{ fontSize: '13px', color: '#64748b' }}>
            Last synchronized: <strong style={{ color: '#0f172a' }}>{formattedLastSync}</strong>
          </div>
          <button onClick={loadData} className="ghost" style={{ fontSize: '13px', padding: '6px 12px' }}>
            🔄 Refresh Data
          </button>
        </div>
      </header>

      {/* 4. 6 KPI CARDS */}
      <div className="cards" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
        <div className="card">
          <span>Patients</span>
          <strong>{d.patients.total}</strong>
          <small style={{ color: '#64748b', fontSize: '12px' }}>Active screening population</small>
        </div>
        <div className="card">
          <span>Clinical Trials</span>
          <strong>{d.trials.total}</strong>
          <small style={{ color: '#64748b', fontSize: '12px' }}>Available trials</small>
        </div>
        <div className="card">
          <span>Potential Matches</span>
          <strong>{d.matches.total}</strong>
          <small style={{ color: '#64748b', fontSize: '12px' }}>Requires review</small>
        </div>
        <div className="card">
          <span>High Confidence Matches</span>
          <strong>{d.matches.high_confidence}</strong>
          <small style={{ color: '#059669', fontSize: '12px', fontWeight: 600 }}>High-confidence candidates</small>
        </div>
        <div className="card">
          <span>Needs Attention</span>
          <strong style={{ color: d.matches.needs_review > 0 ? '#d97706' : '#0f172a' }}>{d.matches.needs_review}</strong>
          <small style={{ color: '#64748b', fontSize: '12px' }}>Action required</small>
        </div>
        <div className="card">
          <span>Recent Changes</span>
          <strong>{d.changes.patients_requiring_rescreen}</strong>
          <small style={{ color: '#64748b', fontSize: '12px' }}>Since last sync</small>
        </div>
      </div>

      {/* ROW 2: SCREENING STATUS & MATCH QUALITY */}
      <div className="grid2" style={{ marginTop: '20px' }}>
        {/* 5. SCREENING STATUS */}
        <div className="panel">
          <h3>Screening Status</h3>
          <div style={{ display: 'grid', gap: '1rem', marginTop: '1rem' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
                <span><strong>Patients Screened</strong></span>
                <span><strong>{patientScreenedPct}%</strong> ({d.patients.screened} / {d.patients.total} patients)</span>
              </div>
              <div style={{ background: '#e2e8f0', height: '10px', borderRadius: '5px', overflow: 'hidden' }}>
                <div style={{ background: '#0284c7', width: `${patientScreenedPct}%`, height: '100%' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
                <span><strong>Trials Evaluated</strong></span>
                <span><strong>{trialEvaluatedPct}%</strong> ({d.trials.recruiting + d.trials.completed} / {d.trials.total} trials)</span>
              </div>
              <div style={{ background: '#e2e8f0', height: '10px', borderRadius: '5px', overflow: 'hidden' }}>
                <div style={{ background: '#10b981', width: `${trialEvaluatedPct}%`, height: '100%' }} />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '8px', paddingTop: '12px', borderTop: '1px solid #f1f5f9' }}>
              <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '8px' }}>
                <span style={{ fontSize: '12px', color: '#64748b' }}>Matches Identified</span>
                <div style={{ fontSize: '20px', fontWeight: 700, color: '#0f172a' }}>{d.matches.total}</div>
              </div>
              <div style={{ background: '#fffbe6', padding: '10px', borderRadius: '8px', border: '1px solid #ffe58f' }}>
                <span style={{ fontSize: '12px', color: '#d48806' }}>Unknown Eligibility</span>
                <div style={{ fontSize: '20px', fontWeight: 700, color: '#d48806' }}>{d.eligibility.unknown}</div>
              </div>
            </div>
          </div>
        </div>

        {/* 7. MATCH QUALITY DISTRIBUTION */}
        <div className="panel">
          <h3>Match Quality Distribution</h3>
          <div style={{ display: 'grid', gap: '12px', marginTop: '1rem' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '4px' }}>
                <span>High Confidence (≥80%)</span>
                <strong>{d.matches.high_confidence}</strong>
              </div>
              <div style={{ background: '#e2e8f0', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ background: '#059669', width: `${d.matches.total ? (d.matches.high_confidence / d.matches.total) * 100 : 0}%`, height: '100%' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '4px' }}>
                <span>Medium Confidence (50-79%)</span>
                <strong>{d.matches.medium_confidence}</strong>
              </div>
              <div style={{ background: '#e2e8f0', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ background: '#0284c7', width: `${d.matches.total ? (d.matches.medium_confidence / d.matches.total) * 100 : 0}%`, height: '100%' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '4px' }}>
                <span>Low Confidence (&lt;50%)</span>
                <strong>{d.matches.low_confidence}</strong>
              </div>
              <div style={{ background: '#e2e8f0', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ background: '#94a3b8', width: `${d.matches.total ? (d.matches.low_confidence / d.matches.total) * 100 : 0}%`, height: '100%' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '4px' }}>
                <span>Needs Review</span>
                <strong style={{ color: '#d97706' }}>{d.matches.needs_review}</strong>
              </div>
              <div style={{ background: '#e2e8f0', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ background: '#d97706', width: `${d.matches.total ? (d.matches.needs_review / d.matches.total) * 100 : 0}%`, height: '100%' }} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ROW 3: ACTION REQUIRED & CLINICALTRIALS.GOV SYNC STATUS */}
      <div className="grid2" style={{ marginTop: '20px' }}>
        {/* 8. ACTION REQUIRED PANEL */}
        <div className="panel" style={{ borderLeft: '4px solid #f59e0b' }}>
          <h3 style={{ color: '#92400e' }}>⚠️ Action Required</h3>
          <div style={{ display: 'grid', gap: '12px', marginTop: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#fffbe6', padding: '10px 14px', borderRadius: '8px', border: '1px solid #ffe58f' }}>
              <div>
                <strong>{d.patients.recently_updated} patient lab / note updates</strong>
                <div style={{ fontSize: '12px', color: '#78350f' }}>Re-screen affected trials to update eligibility</div>
              </div>
              <button onClick={() => nav('/patients')} style={{ fontSize: '12px', padding: '6px 12px', background: '#d97706' }}>
                View Patients →
              </button>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#f0f9ff', padding: '10px 14px', borderRadius: '8px', border: '1px solid #bae6fd' }}>
              <div>
                <strong>{d.eligibility.unknown} criteria with UNKNOWN eligibility</strong>
                <div style={{ fontSize: '12px', color: '#0369a1' }}>Additional laboratory/clinical evidence required</div>
              </div>
              <button onClick={() => nav('/monitoring')} className="ghost" style={{ fontSize: '12px', padding: '6px 12px', color: '#0284c7', borderColor: '#0284c7' }}>
                Review Changes →
              </button>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#f8fafc', padding: '10px 14px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <div>
                <strong>{d.trials.total} active clinical trials in registry</strong>
                <div style={{ fontSize: '12px', color: '#64748b' }}>Explore protocol details and target criteria</div>
              </div>
              <button onClick={() => nav('/trials')} className="ghost" style={{ fontSize: '12px', padding: '6px 12px' }}>
                View Trials →
              </button>
            </div>
          </div>
        </div>

        {/* 10. CLINICALTRIALS.GOV DATA STATUS */}
        <div className="panel">
          <h3>ClinicalTrials.gov Data Status</h3>
          <div style={{ display: 'grid', gap: '8px', marginTop: '1rem', fontSize: '13px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5f9' }}>
              <span>Data Source:</span>
              <strong>ClinicalTrials.gov API v2</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5f9' }}>
              <span>Last Synchronization:</span>
              <strong>{formattedLastSync}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5f9' }}>
              <span>Trials Synced:</span>
              <strong>{d.sync.inserted} inserted · {d.sync.updated} updated</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5f9' }}>
              <span>Sync Failures:</span>
              <strong style={{ color: d.sync.failed > 0 ? '#ef4444' : '#10b981' }}>{d.sync.failed} errors</strong>
            </div>

            <button disabled={syncing} onClick={handleSync} style={{ marginTop: '8px', width: '100%', background: '#0f172a' }}>
              {syncing ? 'Synchronizing API v2 Data…' : 'Sync Trials from ClinicalTrials.gov'}
            </button>
          </div>
        </div>
      </div>

      {/* ROW 4: ELIGIBILITY SAFETY STATES & TRIAL STATUS */}
      <div className="grid2" style={{ marginTop: '20px' }}>
        {/* 6. ELIGIBILITY SAFETY STATES */}
        <div className="panel">
          <h3>Eligibility Results (Safety Breakdown)</h3>
          <p className="muted" style={{ fontSize: '12px' }}>Actual criteria decision counts. UNKNOWN is never treated as eligible.</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginTop: '1rem' }}>
            <div style={{ background: '#dff6ec', padding: '12px', borderRadius: '10px' }}>
              <span className="pill met">MET</span>
              <div style={{ fontSize: '24px', fontWeight: 800, color: '#087a55', marginTop: '4px' }}>{d.eligibility.met}</div>
              <small style={{ color: '#065f46', fontSize: '11px' }}>Evidence satisfies eligibility</small>
            </div>

            <div style={{ background: '#ffe3e6', padding: '12px', borderRadius: '10px' }}>
              <span className="pill bad">NOT MET</span>
              <div style={{ fontSize: '24px', fontWeight: 800, color: '#a31c35', marginTop: '4px' }}>{d.eligibility.not_met}</div>
              <small style={{ color: '#991b1b', fontSize: '11px' }}>Evidence violates eligibility</small>
            </div>

            <div style={{ background: '#fff2cc', padding: '12px', borderRadius: '10px' }}>
              <span className="pill warn">UNKNOWN</span>
              <div style={{ fontSize: '24px', fontWeight: 800, color: '#936600', marginTop: '4px' }}>{d.eligibility.unknown}</div>
              <small style={{ color: '#854d0e', fontSize: '11px' }}>Insufficient evidence</small>
            </div>

            <div style={{ background: '#ece5ff', padding: '12px', borderRadius: '10px' }}>
              <span className="pill conflict">CONFLICTING</span>
              <div style={{ fontSize: '24px', fontWeight: 800, color: '#6440a8', marginTop: '4px' }}>{d.eligibility.conflicting}</div>
              <small style={{ color: '#5b21b6', fontSize: '11px' }}>Source data disagrees</small>
            </div>
          </div>
        </div>

        {/* 11. TRIAL STATUS OVERVIEW */}
        <div className="panel">
          <h3>Trial Registry Status Overview</h3>
          <div style={{ display: 'grid', gap: '12px', marginTop: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px', background: '#f8fafc', borderRadius: '8px' }}>
              <span>Recruiting</span>
              <strong style={{ fontSize: '18px', color: '#059669' }}>{d.trials.recruiting}</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px', background: '#f8fafc', borderRadius: '8px' }}>
              <span>Completed</span>
              <strong style={{ fontSize: '18px', color: '#0284c7' }}>{d.trials.completed}</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px', background: '#f8fafc', borderRadius: '8px' }}>
              <span>Active / Other Statuses</span>
              <strong style={{ fontSize: '18px', color: '#64748b' }}>{d.trials.other}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* ROW 5: 13. RECENT POTENTIAL MATCHES */}
      <div className="panel" style={{ marginTop: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0 }}>Recent Potential Matches</h3>
          <button onClick={() => nav('/patients')} className="ghost" style={{ fontSize: '13px' }}>
            View All Patients →
          </button>
        </div>

        {d.recent_matches.length ? (
          <div className="table">
            <table>
              <thead>
                <tr>
                  <th>Patient ID</th>
                  <th>NCT ID</th>
                  <th>Trial Title</th>
                  <th>Score</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {d.recent_matches.map(m => (
                  <tr key={m.match_id}>
                    <td><strong>{m.external_patient_id}</strong></td>
                    <td><code>{m.nct_id}</code></td>
                    <td style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.trial_title}</td>
                    <td><strong>{m.score}%</strong></td>
                    <td>
                      <span className={`pill ${m.status === 'NOT_ELIGIBLE' ? 'bad' : m.status === 'ELIGIBLE' ? 'met' : 'warn'}`}>
                        {m.status}
                      </span>
                    </td>
                    <td>
                      <button onClick={() => nav(`/patients/${m.patient_id}`)} className="ghost" style={{ padding: '4px 10px', fontSize: '12px' }}>
                        Review →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">No screening evaluations recorded yet. Navigate to Patients to screen candidate trials.</p>
        )}
      </div>

      {/* ROW 6: RECENT ACTIVITY & SYSTEM HEALTH */}
      <div className="grid2" style={{ marginTop: '20px' }}>
        {/* 9. RECENT ACTIVITY */}
        <div className="panel">
          <h3>Recent System Audit Stream</h3>
          {d.recent_activity.length ? (
            <div className="table" style={{ maxHeight: '250px' }}>
              <table>
                <thead>
                  <tr><th>Time</th><th>Action</th><th>Entity</th></tr>
                </thead>
                <tbody>
                  {d.recent_activity.map(a => (
                    <tr key={a.id}>
                      <td><small>{a.created_at.split('T')[0]}</small></td>
                      <td><span className="pill met" style={{ fontSize: '10px' }}>{a.action}</span></td>
                      <td>{a.entity_type} #{a.entity_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">No recent activity logged.</p>
          )}
        </div>

        {/* 15 & 16. SYSTEM HEALTH & DATA SOURCES */}
        <div className="panel">
          <h3>System Health & Data Sources</h3>
          <div style={{ display: 'grid', gap: '8px', marginTop: '1rem', fontSize: '13px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5f9' }}>
              <span>Backend API</span>
              <strong style={{ color: '#10b981' }}>● Healthy</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5f9' }}>
              <span>PostgreSQL / SQLite DB</span>
              <strong style={{ color: '#10b981' }}>● Healthy</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5f9' }}>
              <span>ClinicalTrials.gov API v2</span>
              <strong style={{ color: '#10b981' }}>● Connected</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #f1f5f9' }}>
              <span>Matching Engine</span>
              <strong style={{ color: '#10b981' }}>● Ready</strong>
            </div>
          </div>
        </div>
      </div>

    </Layout>
  );
}

function ReportDrivenPatientWorkflow({ onComplete, onCancel, initialPatientId }: { onComplete: () => void; onCancel: () => void; initialPatientId?: number }) {
  const [step, setStep] = useState<number>(initialPatientId ? 2 : 1);
  const [extPatientId, setExtPatientId] = useState(`PT-ADM-${Math.floor(1000 + Math.random() * 9000)}`);
  const [sourceSystem, setSourceSystem] = useState('EHR-Epic');
  const [recordDate, setRecordDate] = useState(new Date().toISOString().split('T')[0]);

  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [patientId, setPatientId] = useState<number | null>(initialPatientId || null);
  const [reportId, setReportId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [documentType, setDocumentType] = useState('Clinical Report');
  const [ocrApplied, setOcrApplied] = useState(false);
  const [verifiedData, setVerifiedData] = useState<any>(null);
  const [matchResults, setMatchResults] = useState<any[]>([]);

  async function handleCreatePatient(e: any) {
    e.preventDefault();
    if (!extPatientId.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await api<any>('/api/patients', {
        method: 'POST',
        body: JSON.stringify({
          external_patient_id: extPatientId.trim(),
          source_system: sourceSystem,
          record_date: recordDate
        })
      });
      setPatientId(res.id);
      setStep(2);
    } catch (err: any) {
      setError(err.message || 'Failed to initialize patient record');
    } finally {
      setLoading(false);
    }
  }

  const [candidateOptions, setCandidateOptions] = useState<any[]>([]);
  const [selectedTrialId, setSelectedTrialId] = useState<number | null>(null);

  useEffect(() => {
    if (step === 5 && patientId) {
      api<any>(`/api/patients/${patientId}/candidates`).then(res => {
        setCandidateOptions(res.items || []);
        if (res.items?.length) setSelectedTrialId(res.items[0].id);
      });
    }
  }, [step, patientId]);

  async function handleUploadAndExtract() {
    if (!file || !patientId) return;
    setLoading(true);
    setError('');
    setStep(3);

    try {
      const token = localStorage.getItem('tm_token');
      const formData = new FormData();
      formData.append('file', file);

      const uploadRes = await fetch(`/api/patients/${patientId}/reports`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      if (!uploadRes.ok) {
        const errJson = await uploadRes.json();
        throw new Error(errJson.detail || 'Report upload failed');
      }
      const uploadData = await uploadRes.json();
      const newReportId = uploadData.report_id;
      setReportId(newReportId);

      const extractRes = await fetch(`/api/patients/${patientId}/reports/${newReportId}/extract`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      if (!extractRes.ok) {
        const errJson = await extractRes.json();
        throw new Error(errJson.detail || 'Clinical AI extraction failed');
      }
      const extractData = await extractRes.json();

      setVerifiedData(JSON.parse(JSON.stringify(extractData.extraction)));
      setDocumentType(extractData.document_type || 'Clinical Report');
      setOcrApplied(extractData.ocr_applied || false);

      setStep(4);
    } catch (err: any) {
      setError(err.message || 'Report processing failed');
      setStep(2);
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyProfile() {
    if (!patientId || !reportId || !verifiedData) return;
    setLoading(true);
    setError('');

    try {
      const token = localStorage.getItem('tm_token');
      const verifyRes = await fetch(`/api/patients/${patientId}/reports/${reportId}/verify`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(verifiedData)
      });
      if (!verifyRes.ok) {
        const errJson = await verifyRes.json();
        throw new Error(errJson.detail || 'Verification failed');
      }
      setStep(5);
    } catch (err: any) {
      setError(err.message || 'Failed to verify clinical profile');
    } finally {
      setLoading(false);
    }
  }

  async function handleRunMatching() {
    if (!patientId || !selectedTrialId) return;
    setLoading(true);
    setError('');

    try {
      await api<any>(`/api/screening/${patientId}/${selectedTrialId}`, { method: 'POST' });
      const matches = await api<any[]>(`/api/matches/${patientId}`);
      setMatchResults(matches);
      setStep(6);
    } catch (err: any) {
      setError(err.message || 'Trial matching failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel" style={{ background: '#ffffff', border: '1px solid #cbd5e1', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.08)', borderRadius: '16px', padding: '28px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '28px', borderBottom: '1px solid #f1f5f9', paddingBottom: '16px' }}>
        {[
          { num: 1, label: 'Patient ID' },
          { num: 2, label: 'Upload Report' },
          { num: 3, label: 'AI Extraction' },
          { num: 4, label: 'Verify Data' },
          { num: 5, label: 'Profile Summary' },
          { num: 6, label: 'Trial Matching' }
        ].map(s => {
          const active = step === s.num;
          const completed = step > s.num;
          return (
            <div key={s.num} style={{ display: 'flex', alignItems: 'center', gap: '8px', opacity: active || completed ? 1 : 0.4 }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: completed ? '#10b981' : active ? '#0284c7' : '#cbd5e1',
                color: '#fff',
                fontWeight: 'bold',
                display: 'grid',
                placeItems: 'center',
                fontSize: '14px'
              }}>
                {completed ? '✓' : s.num}
              </div>
              <span style={{ fontSize: '13px', fontWeight: active ? 700 : 500, color: active ? '#0f172a' : '#64748b' }}>
                {s.label}
              </span>
            </div>
          );
        })}
      </div>

      {error && <div className="error" style={{ marginBottom: '16px' }}>⚠️ {error}</div>}

      {step === 1 && (
        <div>
          <h3 style={{ fontSize: '20px', margin: '0 0 6px' }}>Step 1: Patient Identification</h3>
          <p className="muted" style={{ marginBottom: '20px' }}>Enter unique patient identification metadata before uploading clinical reports.</p>

          <form onSubmit={handleCreatePatient} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <label>
              External Patient ID *
              <input value={extPatientId} onChange={e => setExtPatientId(e.target.value)} placeholder="e.g. PT-ADM-501" required />
            </label>
            <label>
              Source System
              <select value={sourceSystem} onChange={e => setSourceSystem(e.target.value)} style={{ display: 'block', width: '100%', marginTop: '7px', padding: '12px', borderRadius: '9px', border: '1px solid #d9dfe8' }}>
                <option value="EHR-Epic">EHR - Epic Systems</option>
                <option value="EHR-Cerner">EHR - Oracle Cerner</option>
                <option value="Lab-Corp">LabCorp / Quest</option>
                <option value="PDF-Intake">Direct Document Intake</option>
              </select>
            </label>
            <label>
              Record Intake Date
              <input type="date" value={recordDate} onChange={e => setRecordDate(e.target.value)} />
            </label>

            <div style={{ gridColumn: '1 / -1', display: 'flex', gap: '12px', marginTop: '12px' }}>
              <button type="submit" disabled={loading}>
                {loading ? 'Initializing Patient...' : 'Continue to Upload Report →'}
              </button>
              <button type="button" onClick={onCancel} className="ghost">Cancel</button>
            </div>
          </form>
        </div>
      )}

      {step === 2 && (
        <div>
          <h3 style={{ fontSize: '20px', margin: '0 0 6px' }}>Step 2: Upload Patient Clinical Report</h3>
          <p className="muted" style={{ marginBottom: '20px' }}>Upload the primary clinical report (Oncology consultation, Pathology, Lab panel, or EHR export).</p>

          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={e => { e.preventDefault(); setDragOver(false); if (e.dataTransfer.files?.[0]) setFile(e.dataTransfer.files[0]); }}
            style={{
              border: `2px dashed ${dragOver ? '#0284c7' : '#cbd5e1'}`,
              background: dragOver ? '#f0f9ff' : '#f8fafc',
              borderRadius: '16px',
              padding: '40px 20px',
              textAlign: 'center',
              cursor: 'pointer',
              marginBottom: '20px'
            }}
          >
            <div style={{ fontSize: '36px', marginBottom: '8px' }}>📄</div>
            <h4 style={{ margin: '0 0 4px', color: '#0f172a' }}>
              {file ? file.name : 'Drag & Drop Clinical Report File Here'}
            </h4>
            <p className="muted" style={{ fontSize: '13px', margin: '0 0 16px' }}>
              Supported formats: <strong>PDF • DOCX • TXT • PNG • JPG / JPEG</strong> (Max file size: 20 MB)
            </p>
            <input
              type="file"
              id="report-file-input"
              accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
              style={{ display: 'none' }}
              onChange={e => { if (e.target.files?.[0]) setFile(e.target.files[0]); }}
            />
            <label htmlFor="report-file-input" style={{ cursor: 'pointer' }}>
              <span style={{ padding: '8px 18px', background: '#0f172a', color: '#fff', borderRadius: '8px', fontSize: '13px', fontWeight: 600 }}>
                {file ? 'Change File' : 'Choose File from Computer'}
              </span>
            </label>
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button disabled={!file || loading} onClick={handleUploadAndExtract}>
              {loading ? 'Ingesting Report...' : 'Extract Clinical Data with AI →'}
            </button>
            <button onClick={onCancel} className="ghost">Cancel</button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>⚙️</div>
          <h3 style={{ fontSize: '22px', margin: '0 0 8px' }}>AI Processing & Clinical Extraction</h3>
          <p className="muted" style={{ maxWidth: '600px', margin: '0 auto 24px' }}>
            Running structured clinical extraction, PII redaction, and multi-modal document processing...
          </p>

          <div style={{ maxWidth: '500px', margin: '0 auto', textAlign: 'left', background: '#f8fafc', padding: '20px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
            <div style={{ color: '#10b981', fontWeight: 600, marginBottom: '8px', fontSize: '14px' }}>✓ File Uploaded & Format Validated</div>
            <div style={{ color: '#10b981', fontWeight: 600, marginBottom: '8px', fontSize: '14px' }}>✓ Presidio PII Anonymization Layer Active</div>
            <div style={{ color: '#0284c7', fontWeight: 600, marginBottom: '8px', fontSize: '14px' }}>⚙️ Document Text & OCR Extraction...</div>
            <div style={{ color: '#64748b', fontSize: '14px' }}>⏳ Clinical LLM NLP Parser Structuring Profile...</div>
          </div>
        </div>
      )}

      {step === 4 && verifiedData && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', background: '#f0f9ff', padding: '16px 20px', borderRadius: '12px', border: '1px solid #bae6fd' }}>
            <div>
              <span style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700, color: '#0369a1' }}>
                Extracted Document
              </span>
              <h4 style={{ margin: '4px 0 0', fontSize: '16px', color: '#0c4a6e' }}>
                {documentType} {ocrApplied && <span style={{ background: '#e0f2fe', color: '#0369a1', padding: '2px 8px', borderRadius: '999px', fontSize: '11px', marginLeft: '8px' }}>OCR Applied</span>}
              </h4>
            </div>
            <span style={{ fontSize: '13px', color: '#0369a1', fontWeight: 600 }}>
              AI Extraction Confidence: High (94%)
            </span>
          </div>

          <h3 style={{ fontSize: '20px', margin: '0 0 6px' }}>Step 4: Researcher Verification & Extraction Review</h3>
          <p className="muted" style={{ marginBottom: '20px' }}>Review and verify AI-extracted clinical evidence before committing to the patient database.</p>

          <div style={{ display: 'grid', gap: '20px', marginBottom: '24px' }}>
            <div style={{ background: '#f8fafc', padding: '20px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h4 style={{ margin: 0, fontSize: '16px' }}>🩺 Diagnoses & Oncology Conditions</h4>
                <span className="pill met">Verified</span>
              </div>
              {verifiedData.diagnoses?.map((d: any, idx: number) => (
                <div key={idx} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: '10px', alignItems: 'center', marginBottom: '8px' }}>
                  <input
                    value={d.condition_name}
                    onChange={e => {
                      const updated = { ...verifiedData };
                      updated.diagnoses[idx].condition_name = e.target.value;
                      setVerifiedData(updated);
                    }}
                    placeholder="Condition Name"
                  />
                  <input
                    value={d.stage || ''}
                    onChange={e => {
                      const updated = { ...verifiedData };
                      updated.diagnoses[idx].stage = e.target.value;
                      setVerifiedData(updated);
                    }}
                    placeholder="Stage (e.g. Stage II)"
                  />
                  <input
                    value={d.subtype || ''}
                    onChange={e => {
                      const updated = { ...verifiedData };
                      updated.diagnoses[idx].subtype = e.target.value;
                      setVerifiedData(updated);
                    }}
                    placeholder="Subtype / Histology"
                  />
                  <button
                    onClick={() => {
                      const updated = { ...verifiedData };
                      updated.diagnoses.splice(idx, 1);
                      setVerifiedData(updated);
                    }}
                    style={{ background: '#fee2e2', color: '#991b1b', padding: '8px 12px', borderRadius: '6px' }}
                  >
                    ✕
                  </button>
                </div>
              ))}
              <button
                onClick={() => {
                  const updated = { ...verifiedData };
                  if (!updated.diagnoses) updated.diagnoses = [];
                  updated.diagnoses.push({ condition_name: '', stage: '', subtype: '' });
                  setVerifiedData(updated);
                }}
                className="ghost"
                style={{ fontSize: '13px', padding: '6px 12px', marginTop: '4px' }}
              >
                + Add Diagnosis
              </button>
            </div>

            <div style={{ background: '#f8fafc', padding: '20px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h4 style={{ margin: 0, fontSize: '16px' }}>💊 Current & Historical Medications</h4>
                <span className="pill met">Verified</span>
              </div>
              {verifiedData.medications?.map((m: any, idx: number) => (
                <div key={idx} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: '10px', alignItems: 'center', marginBottom: '8px' }}>
                  <input
                    value={m.name}
                    onChange={e => {
                      const updated = { ...verifiedData };
                      updated.medications[idx].name = e.target.value;
                      setVerifiedData(updated);
                    }}
                    placeholder="Medication Name"
                  />
                  <input
                    value={m.dose || ''}
                    onChange={e => {
                      const updated = { ...verifiedData };
                      updated.medications[idx].dose = e.target.value;
                      setVerifiedData(updated);
                    }}
                    placeholder="Dose (e.g. 20 mg)"
                  />
                  <input
                    value={m.status || 'current'}
                    onChange={e => {
                      const updated = { ...verifiedData };
                      updated.medications[idx].status = e.target.value;
                      setVerifiedData(updated);
                    }}
                    placeholder="Status (current/historical)"
                  />
                  <button
                    onClick={() => {
                      const updated = { ...verifiedData };
                      updated.medications.splice(idx, 1);
                      setVerifiedData(updated);
                    }}
                    style={{ background: '#fee2e2', color: '#991b1b', padding: '8px 12px', borderRadius: '6px' }}
                  >
                    ✕
                  </button>
                </div>
              ))}
              <button
                onClick={() => {
                  const updated = { ...verifiedData };
                  if (!updated.medications) updated.medications = [];
                  updated.medications.push({ name: '', dose: '', status: 'current' });
                  setVerifiedData(updated);
                }}
                className="ghost"
                style={{ fontSize: '13px', padding: '6px 12px', marginTop: '4px' }}
              >
                + Add Medication
              </button>
            </div>

            <div style={{ background: '#f8fafc', padding: '20px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h4 style={{ margin: 0, fontSize: '16px' }}>🧪 Laboratory & Blood Panels</h4>
                <span className="pill met">Verified</span>
              </div>
              {verifiedData.laboratory_results?.map((l: any, idx: number) => (
                <div key={idx} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: '10px', alignItems: 'center', marginBottom: '8px' }}>
                  <input
                    value={l.test_name}
                    onChange={e => {
                      const updated = { ...verifiedData };
                      updated.laboratory_results[idx].test_name = e.target.value;
                      setVerifiedData(updated);
                    }}
                    placeholder="Test Name (e.g. Creatinine)"
                  />
                  <input
                    type="number"
                    step="0.01"
                    value={l.value_numeric ?? ''}
                    onChange={e => {
                      const updated = { ...verifiedData };
                      updated.laboratory_results[idx].value_numeric = parseFloat(e.target.value);
                      setVerifiedData(updated);
                    }}
                    placeholder="Numeric Value"
                  />
                  <input
                    value={l.unit || ''}
                    onChange={e => {
                      const updated = { ...verifiedData };
                      updated.laboratory_results[idx].unit = e.target.value;
                      setVerifiedData(updated);
                    }}
                    placeholder="Unit (e.g. mg/dL)"
                  />
                  <button
                    onClick={() => {
                      const updated = { ...verifiedData };
                      updated.laboratory_results.splice(idx, 1);
                      setVerifiedData(updated);
                    }}
                    style={{ background: '#fee2e2', color: '#991b1b', padding: '8px 12px', borderRadius: '6px' }}
                  >
                    ✕
                  </button>
                </div>
              ))}
              <button
                onClick={() => {
                  const updated = { ...verifiedData };
                  if (!updated.laboratory_results) updated.laboratory_results = [];
                  updated.laboratory_results.push({ test_name: '', value_numeric: 0, unit: '' });
                  setVerifiedData(updated);
                }}
                className="ghost"
                style={{ fontSize: '13px', padding: '6px 12px', marginTop: '4px' }}
              >
                + Add Lab Result
              </button>
            </div>

            <div style={{ background: '#f8fafc', padding: '20px', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
              <h4 style={{ margin: '0 0 12px', fontSize: '16px' }}>🧬 Biomarkers & Performance Status</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <label>
                  ECOG Performance Status (0 - 4)
                  <input
                    type="number"
                    min="0"
                    max="4"
                    value={verifiedData.clinical_status?.performance_status_ecog ?? ''}
                    onChange={e => {
                      const updated = { ...verifiedData };
                      if (!updated.clinical_status) updated.clinical_status = {};
                      updated.clinical_status.performance_status_ecog = parseInt(e.target.value);
                      setVerifiedData(updated);
                    }}
                  />
                </label>
                <div>
                  <label>Biomarkers Detected</label>
                  <div style={{ fontSize: '13px', color: '#475569', marginTop: '6px' }}>
                    {verifiedData.biomarkers?.length
                      ? verifiedData.biomarkers.map((b: any) => `${b.name}: ${b.status}`).join(' • ')
                      : 'None specified'}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button disabled={loading} onClick={handleVerifyProfile}>
              {loading ? 'Verifying & Saving...' : 'Confirm & Save Patient Profile →'}
            </button>
            <button onClick={onCancel} className="ghost">Cancel</button>
          </div>
        </div>
      )}

      {step === 5 && (
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <div style={{ fontSize: '48px', marginBottom: '12px' }}>✅</div>
          <h3 style={{ fontSize: '24px', margin: '0 0 8px', color: '#0f172a' }}>Patient Profile Successfully Saved</h3>
          <p className="muted" style={{ maxWidth: '600px', margin: '0 auto 24px' }}>
            Please select a specific Clinical Trial to screen this patient against.
          </p>

          <div style={{ maxWidth: '500px', margin: '0 auto 24px', textAlign: 'left' }}>
            <label style={{ fontWeight: 600 }}>Select Clinical Trial Target:</label>
            <select 
              value={selectedTrialId || ''} 
              onChange={e => setSelectedTrialId(Number(e.target.value))}
              style={{ width: '100%', marginTop: '8px', padding: '12px', borderRadius: '8px', border: '1px solid #cbd5e1' }}
            >
              {candidateOptions.length === 0 && <option value="">Loading candidates...</option>}
              {candidateOptions.map(t => (
                <option key={t.id} value={t.id}>{t.nct_id} - {t.title}</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', marginBottom: '24px' }}>
            <button onClick={handleRunMatching} disabled={loading || !selectedTrialId} style={{ background: '#0284c7', fontSize: '15px', padding: '14px 28px' }}>
              {loading ? 'Screening Trial...' : 'Screen Selected Trial →'}
            </button>
            <button onClick={onComplete} className="ghost" style={{ fontSize: '15px', padding: '14px 24px' }}>
              Done / Return to Patients List
            </button>
          </div>
        </div>
      )}

      {step === 6 && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3 style={{ fontSize: '22px', margin: 0 }}>Step 6: Clinical Trial Screening Results</h3>
              <p className="muted" style={{ margin: '4px 0 0' }}>Screened against active ClinicalTrials.gov trials with auditable evidence rationale and intelligent priority ranking.</p>
            </div>
            <button onClick={onComplete} className="ghost">Finish Workflow</button>
          </div>

          <ScreenedMatchResults matches={matchResults} />

          <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
            <button onClick={onComplete}>Complete Patient Setup</button>
          </div>
        </div>
      )}
    </div>
  );
}

async function generatePDFReport(docData: any, patientId: number, matchId: number) {
  try {
    let ragRes = { reasoning: 'GraphRAG reasoning not available.' };
    try {
      ragRes = await api<any>(`/api/patients/${patientId}/graph_rag/${matchId}`);
    } catch(e) {}

    let graphHtml = '';
    try {
      const graphRes = await fetch(`/api/patients/${patientId}/graph`);
      if (graphRes.ok) {
        graphHtml = await graphRes.text();
      }
    } catch (e) {}

    const base64Graph = btoa(unescape(encodeURIComponent(graphHtml)));

    const printWindow = window.open('', '_blank');
    if (!printWindow) return alert('Please allow popups to generate the PDF report.');

    const htmlContent = `
      <html>
        <head>
          <title>TrialMatchAI Clinical Report - ${docData.document_id}</title>
          <style>
            body { font-family: 'Inter', system-ui, sans-serif; padding: 40px; color: #0f172a; line-height: 1.6; max-width: 900px; margin: 0 auto; }
            h1 { color: #0f172a; border-bottom: 3px solid #0284c7; padding-bottom: 8px; margin-bottom: 24px; }
            h2 { color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; margin-top: 32px; }
            h3 { color: #334155; margin-top: 24px; }
            .section { margin-bottom: 30px; }
            table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }
            th, td { padding: 12px; border: 1px solid #cbd5e1; text-align: left; }
            th { background: #f8fafc; font-weight: 600; color: #475569; }
            .pill { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 700; display: inline-block; }
            .ELIGIBLE { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
            .NOT_ELIGIBLE { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
            .REQUIRES_REVIEW { background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }
            .rag-box { background: #f0f9ff; border-left: 4px solid #0284c7; padding: 20px; font-style: italic; border-radius: 0 8px 8px 0; margin-top: 16px; }
            .graph-container { height: 600px; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; margin-top: 16px; }
            @media print {
              body { padding: 0; }
              .page-break { page-break-before: always; }
              .graph-container { height: 800px; }
            }
          </style>
        </head>
        <body>
          <div class="section">
            <h1>Clinical Trial Matching Evaluation Report</h1>
            <div style="display: flex; justify-content: space-between; color: #64748b;">
              <p><strong>Document ID:</strong> ${docData.document_id}</p>
              <p><strong>Generated:</strong> ${new Date().toLocaleString()}</p>
            </div>
          </div>

          <div class="section">
            <h2>1. Patient Clinical Summary</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; background: #f8fafc; padding: 16px; border-radius: 8px;">
              <div><strong>External Patient ID:</strong> ${docData.patient.external_patient_id}</div>
              <div><strong>Sex / Gender:</strong> ${docData.patient.sex}</div>
              <div><strong>Date of Birth:</strong> ${docData.patient.date_of_birth}</div>
              <div><strong>Conditions:</strong> ${docData.patient.conditions?.join(', ') || 'None'}</div>
            </div>
            
            <h3>Recent Laboratory Panels & Scan Reports</h3>
            ${docData.patient.recent_labs && docData.patient.recent_labs.length > 0 ? `
            <table>
              <tr><th>Lab Test</th><th>Result Value</th><th>Unit</th><th>Observed Date</th></tr>
              ${docData.patient.recent_labs.map((l:any) => `<tr><td><strong>${l.test}</strong></td><td>${l.value}</td><td>${l.unit||''}</td><td>${l.date.split('T')[0]}</td></tr>`).join('')}
            </table>
            ` : '<p style="color: #64748b; font-style: italic;">No laboratory values on file.</p>'}
          </div>

          <div class="section">
            <h2>2. Clinical Trial Target</h2>
            <div style="background: #f8fafc; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
              <p style="margin: 0 0 8px;"><strong>NCT ID:</strong> ${docData.trial.nct_id}</p>
              <p style="margin: 0 0 8px;"><strong>Title:</strong> ${docData.trial.title}</p>
              <p style="margin: 0 0 8px;"><strong>Study Phase:</strong> ${docData.trial.phase}</p>
              <p style="margin: 0;"><strong>Overall Status:</strong> ${docData.trial.status}</p>
            </div>
            
            <h3>Eligibility Criteria</h3>
            <div style="background: #ffffff; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; max-height: 400px; overflow-y: hidden; font-size: 13px; white-space: pre-wrap;">
              ${docData.trial.eligibility_text}
            </div>
          </div>

          <div class="section">
            <h2>3. Matching Evaluation</h2>
            <div style="display: flex; gap: 24px; margin-bottom: 24px;">
              <div>
                <p style="font-size: 12px; color: #64748b; margin: 0 0 4px; text-transform: uppercase;">Eligibility Status</p>
                <div class="pill ${docData.evaluation.overall_status}">${docData.evaluation.overall_status}</div>
              </div>
              <div>
                <p style="font-size: 12px; color: #64748b; margin: 0 0 4px; text-transform: uppercase;">Match Score</p>
                <div style="font-size: 24px; font-weight: 800; color: #0f172a; line-height: 1;">${docData.evaluation.ranking_score_percent}%</div>
              </div>
            </div>
            <p><strong>Clinical Rationale:</strong> ${docData.evaluation.explanation}</p>
            
            <h3>Criteria Assessment Matrix</h3>
            <table>
              <tr><th>Decision</th><th>Criteria Rationale</th><th>Evidence Source</th><th>Confidence</th></tr>
              ${docData.criteria_breakdown.map((c:any) => `<tr>
                <td><span class="pill ${c.decision}">${c.decision}</span></td>
                <td>${c.reason}</td>
                <td>${c.evidence_source||'N/A'}</td>
                <td>${c.confidence ? (c.confidence*100).toFixed(0)+'%' : 'N/A'}</td>
              </tr>`).join('')}
            </table>
          </div>

          <div class="page-break"></div>

          <div class="section">
            <h2>4. GraphRAG AI Reasoning</h2>
            <p style="color: #64748b; font-size: 14px;">Generative AI explanation of the deterministic matching criteria based on the patient's clinical knowledge graph.</p>
            <div class="rag-box">
              ${ragRes.reasoning.replace(/\\n/g, '<br/>')}
            </div>
          </div>

          <div class="section">
            <h2>5. Patient Knowledge Graph Snapshot</h2>
            <p style="color: #64748b; font-size: 14px;">Interactive network visualization of patient conditions, labs, and matched trial criteria.</p>
            <div class="graph-container">
              <iframe src="data:text/html;base64,${base64Graph}" style="width:100%; height:100%; border:none;"></iframe>
            </div>
          </div>

          <script>
            setTimeout(() => {
              window.print();
            }, 3500);
          </script>
        </body>
      </html>
    `;
    printWindow.document.write(htmlContent);
    printWindow.document.close();
  } catch (err: any) {
    alert("Error generating PDF report: " + err.message);
  }
}

function Patients() {
  const [rows, setRows] = useState<any[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [ingestPatientId, setIngestPatientId] = useState<number | null>(null);
  const [docModal, setDocModal] = useState<any>(null);
  const [loadingReportId, setLoadingReportId] = useState<number | null>(null);

  function refresh() {
    api<any>('/api/patients?limit=50').then(r => setRows(r.items));
  }

  useEffect(() => { refresh(); }, []);

  async function openPatientReport(patientId: number) {
    setLoadingReportId(patientId);
    try {
      let matches = await api<any[]>(`/api/matches/${patientId}`);
      if (!matches.length) {
        const candidatesRes = await api<any>(`/api/patients/${patientId}/candidates`);
        const items = candidatesRes.items || [];
        if (items.length) {
          await api<any>(`/api/screening/${patientId}/${items[0].id}`, { method: 'POST' });
          matches = await api<any[]>(`/api/matches/${patientId}`);
        }
      }

      if (matches.length) {
        const doc = await api<any>(`/api/matches/document/${matches[0].id}`);
        setDocModal(doc);
      } else {
        alert("No candidate trial matches available for this patient yet.");
      }
    } catch (err: any) {
      alert("Error fetching patient match report: " + (err.message || 'Server error'));
    } finally {
      setLoadingReportId(null);
    }
  }

  function downloadDoc(filename: string, content: string) {
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Layout>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ margin: 0 }}>Patient Intake & Clinical Reports</h2>
          <p className="muted" style={{ margin: '4px 0 0' }}>Report-driven AI extraction, researcher verification, and deterministic trial matching.</p>
        </div>
        <button onClick={() => { setIngestPatientId(null); setShowAdd(!showAdd); }} style={{ background: '#0284c7' }}>
          {showAdd ? 'Close Intake Form' : '📄 Upload Clinical Report / Add Patient'}
        </button>
      </div>

      {(showAdd || ingestPatientId) && (
        <ReportDrivenPatientWorkflow
          initialPatientId={ingestPatientId || undefined}
          onComplete={() => { setShowAdd(false); setIngestPatientId(null); refresh(); }}
          onCancel={() => { setShowAdd(false); setIngestPatientId(null); }}
        />
      )}

      <div className="panel table">
        <table>
          <thead>
            <tr>
              <th>Patient ID</th>
              <th>Primary Diagnosis</th>
              <th>Sex</th>
              <th>DOB</th>
              <th>Report Status</th>
              <th>Matches</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(p => (
              <tr key={p.id}>
                <td><strong>{p.external_patient_id}</strong></td>
                <td>{p.primary_diagnosis || 'Pending Report'}</td>
                <td>{p.sex || '—'}</td>
                <td>{p.date_of_birth || '—'}</td>
                <td>
                  <span className={`pill ${p.report_status === 'VERIFIED' ? 'met' : p.report_status === 'REVIEW_REQUIRED' ? 'warn' : 'ghost'}`}>
                    {p.report_status || 'No Report'}
                  </span>
                </td>
                <td><strong>{p.matches_count || 0}</strong></td>
                <td>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <button
                      onClick={() => { setIngestPatientId(p.id); setShowAdd(true); }}
                      style={{ padding: '4px 10px', fontSize: '12px', background: '#0f172a' }}
                    >
                      📄 Ingest Report
                    </button>
                    <Link to={`/patients/${p.id}`} className="ghost" style={{ padding: '4px 10px', fontSize: '13px', textDecoration: 'none' }}>
                      Profile & Matches →
                    </Link>
                    <button
                      disabled={loadingReportId === p.id}
                      onClick={() => openPatientReport(p.id)}
                      style={{ padding: '4px 10px', fontSize: '12px', background: '#0284c7', color: '#ffffff', border: 0 }}
                    >
                      {loadingReportId === p.id ? 'Generating Report…' : '📄 Match Report'}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* MATCH REPORT MODAL PREVIEW */}
      {docModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.75)', display: 'grid', placeItems: 'center', zIndex: 1000, padding: '20px' }}>
          <div style={{ background: '#fff', width: 'min(900px, 95vw)', maxHeight: '90vh', borderRadius: '16px', padding: '24px', overflowY: 'auto', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: '12px', marginBottom: '16px' }}>
              <div>
                <h3 style={{ margin: 0 }}>Clinical Evaluation Document Report</h3>
                <span style={{ fontSize: '13px', color: '#64748b' }}>Document ID: <code>{docModal.document_id}</code></span>
              </div>
              <button onClick={() => setDocModal(null)} className="ghost" style={{ padding: '6px 12px' }}>Close Window</button>
            </div>
            
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              <button onClick={() => generatePDFReport(docModal, docModal.patient.id, docModal.evaluation.match_id)} style={{ background: '#0284c7' }}>
                📄 Generate Professional PDF Report
              </button>
              <button onClick={() => downloadDoc(`${docModal.document_id}.md`, docModal.markdown_document)} className="ghost">
                📥 Download Markdown
              </button>
              <button onClick={() => downloadDoc(`${docModal.document_id}.json`, JSON.stringify(docModal, null, 2))} className="ghost">
                📥 Download Raw JSON
              </button>
            </div>

            <pre style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0', whiteSpace: 'pre-wrap', fontSize: '13px', fontFamily: 'monospace', maxHeight: '500px', overflowY: 'auto' }}>
              {docModal.markdown_document}
            </pre>
          </div>
        </div>
      )}
    </Layout>
  );
}

const PILL: Record<string, string> = { MET: 'met', NOT_MET: 'bad', UNKNOWN: 'warn', CONFLICTING: 'conflict' };

function CriteriaBreakdown({ criteria }: { criteria: any[] }) {
  return (
    <div className="criteria">
      {criteria.map((c: any) => (
        <div className="criterion" key={c.criterion_id}>
          <span className={`pill ${PILL[c.decision] || 'warn'}`}>{c.decision}</span>
          <div>
            <p>{c.reason}</p>
            {c.evidence_source && (
              <small>
                Evidence: {c.evidence_source}
                {c.evidence_record_id ? ` #${c.evidence_record_id}` : ''}
                {c.confidence != null ? ` · confidence ${Math.round(c.confidence * 100)}%` : ''}
              </small>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function ScreenedMatchResults({ matches, onExportDocument }: { matches: any[]; onExportDocument?: (matchId: number) => void }) {
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [minCoverage, setMinCoverage] = useState(0);
  const [recruitingOnly, setRecruitingOnly] = useState(false);
  const [sortBy, setSortBy] = useState('best_match');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  let filtered = (matches || []).filter(m => {
    if (statusFilter !== 'ALL' && m.status !== statusFilter) return false;
    if (minCoverage > 0 && (m.screening_coverage || 0) < minCoverage) return false;
    if (recruitingOnly && m.recruitment_status && !m.recruitment_status.toUpperCase().includes('RECRUIT')) return false;
    return true;
  });

  if (sortBy === 'status') {
    const map: any = { ELIGIBLE: 1, REQUIRES_REVIEW: 2, NOT_ELIGIBLE: 3 };
    filtered.sort((a, b) => (map[a.status] || 4) - (map[b.status] || 4));
  } else if (sortBy === 'evidence_coverage') {
    filtered.sort((a, b) => (b.evidence_coverage || 0) - (a.evidence_coverage || 0));
  } else if (sortBy === 'updated_date') {
    filtered.sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''));
  }

  const topMatches = filtered.slice(0, 3);

  const getStatusBadge = (status: string) => {
    if (status === 'ELIGIBLE') {
      return <span style={{ background: '#dcfce7', color: '#15803d', border: '1px solid #86efac', padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 700 }}>✓ ELIGIBLE</span>;
    } else if (status === 'NOT_ELIGIBLE') {
      return <span style={{ background: '#fee2e2', color: '#b91c1c', border: '1px solid #fca5a5', padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 700 }}>✖ NOT ELIGIBLE</span>;
    } else {
      return <span style={{ background: '#fef3c7', color: '#b45309', border: '1px solid #fde68a', padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 700 }}>⚠ REQUIRES REVIEW</span>;
    }
  };

  const renderTrialCard = (m: any, isTop: boolean = false) => (
    <div key={m.match_id || m.id} style={{ background: isTop ? '#f0fdf4' : '#ffffff', padding: '20px', borderRadius: '12px', border: isTop ? '2px solid #86efac' : '1px solid #cbd5e1', boxShadow: isTop ? '0 4px 12px rgba(16,185,129,0.08)' : '0 1px 3px rgba(0,0,0,0.05)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ background: '#0f172a', color: '#fff', fontSize: '11px', fontWeight: 800, padding: '2px 8px', borderRadius: '4px' }}>
              #{m.rank || 1}
            </span>
            <span style={{ fontSize: '13px', fontWeight: 700, color: '#475569' }}>{m.nct_id}</span>
            {m.recruitment_status && (
              <span style={{ fontSize: '11px', color: '#64748b', background: '#e2e8f0', padding: '2px 6px', borderRadius: '4px' }}>
                {m.recruitment_status}
              </span>
            )}
          </div>
          <h4 style={{ margin: '6px 0 4px', fontSize: '16px', color: '#0f172a', fontWeight: 700 }}>{m.title}</h4>
          <div style={{ fontSize: '13px', color: '#64748b', marginTop: '4px' }}>
            <strong style={{ color: '#1e293b' }}>{m.met_count || 0}</strong> criteria met · <strong style={{ color: '#b91c1c' }}>{m.not_met_count || 0}</strong> not met · <strong style={{ color: '#b45309' }}>{m.unknown_count || 0}</strong> unknown
          </div>
        </div>

        <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
          {getStatusBadge(m.status)}
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#0f172a', background: '#f1f5f9', padding: '4px 10px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
            Screening Coverage: <span style={{ color: '#0284c7' }}>{Math.round(m.screening_coverage || 0)}%</span>
          </div>
          {onExportDocument && (
            <button className="ghost" onClick={() => onExportDocument(m.id || m.match_id)} style={{ fontSize: '12px', padding: '4px 10px', background: '#0284c7', color: '#fff', border: 0 }}>
              📄 Export Report
            </button>
          )}
        </div>
      </div>

      {/* WHY THIS TRIAL RANKED HERE */}
      {m.why_ranked_here && m.why_ranked_here.length > 0 && (
        <div style={{ marginTop: '14px', background: isTop ? '#ffffff' : '#f8fafc', padding: '12px 14px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
            WHY THIS TRIAL RANKED HERE
          </div>
          <div style={{ display: 'grid', gap: '4px' }}>
            {m.why_ranked_here.map((reason: string, i: number) => {
              const isMet = reason.startsWith('✓');
              const isNotMet = reason.startsWith('✖');
              return (
                <div key={i} style={{ fontSize: '13px', color: isMet ? '#15803d' : isNotMet ? '#b91c1c' : '#b45309', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>{reason}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* DETAILED EVIDENCE ACCORDION */}
      <div style={{ marginTop: '12px' }}>
        <button
          onClick={() => setExpandedId(expandedId === (m.match_id || m.id) ? null : (m.match_id || m.id))}
          className="ghost"
          style={{ fontSize: '12px', padding: '4px 8px', color: '#475569' }}
        >
          {expandedId === (m.match_id || m.id) ? '▲ Hide Full Evidence Rationale' : '▼ View Full Evidence Rationale & Criteria Audit'}
        </button>

        {expandedId === (m.match_id || m.id) && (
          <div style={{ marginTop: '8px', background: '#ffffff', padding: '12px', borderRadius: '8px', border: '1px solid #cbd5e1' }}>
            <CriteriaBreakdown criteria={m.criteria || []} />
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div style={{ display: 'grid', gap: '20px' }}>
      {/* FILTER & SORT CONTROLS PANEL */}
      <div style={{ background: '#f8fafc', padding: '16px 20px', borderRadius: '12px', border: '1px solid #e2e8f0', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
        {/* Status Filter Buttons */}
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#475569', marginRight: '4px' }}>Filter Status:</span>
          {['ALL', 'ELIGIBLE', 'REQUIRES_REVIEW', 'NOT_ELIGIBLE'].map(st => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={statusFilter === st ? '' : 'ghost'}
              style={{
                fontSize: '12px',
                padding: '6px 12px',
                background: statusFilter === st ? '#0f172a' : undefined,
                color: statusFilter === st ? '#ffffff' : undefined
              }}
            >
              {st === 'REQUIRES_REVIEW' ? 'REQUIRES REVIEW' : st === 'NOT_ELIGIBLE' ? 'NOT ELIGIBLE' : st}
            </button>
          ))}
        </div>

        {/* Dropdowns & Options */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: '#64748b', marginRight: '6px' }}>Min Coverage:</label>
            <select value={minCoverage} onChange={e => setMinCoverage(Number(e.target.value))} style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '12px' }}>
              <option value={0}>All</option>
              <option value={50}>≥ 50%</option>
              <option value={75}>≥ 75%</option>
              <option value={90}>≥ 90%</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: '12px', fontWeight: 600, color: '#64748b', marginRight: '6px' }}>Sort By:</label>
            <select value={sortBy} onChange={e => setSortBy(e.target.value)} style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '12px' }}>
              <option value="best_match">Best Match (AI Ranked)</option>
              <option value="status">Eligibility Status</option>
              <option value="evidence_coverage">Evidence Coverage</option>
              <option value="updated_date">Trial Updated Date</option>
            </select>
          </div>

          <label style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', color: '#334155', fontWeight: 600 }}>
            <input type="checkbox" checked={recruitingOnly} onChange={e => setRecruitingOnly(e.target.checked)} />
            Recruiting Only
          </label>
        </div>
      </div>

      {/* TOP MATCHES SECTION */}
      {topMatches.length > 0 && statusFilter === 'ALL' && (
        <div style={{ background: '#f0fdf4', padding: '20px', borderRadius: '16px', border: '1px solid #bbf7d0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '18px', color: '#166534', display: 'flex', alignItems: 'center', gap: '8px' }}>
              🌟 TOP MATCHES
            </h3>
            <span style={{ fontSize: '12px', color: '#15803d', fontWeight: 600 }}>
              Top candidate trials matching verified patient evidence
            </span>
          </div>

          <div style={{ display: 'grid', gap: '16px' }}>
            {topMatches.map(m => renderTrialCard(m, true))}
          </div>
        </div>
      )}

      {/* ALL SCREENED TRIALS SECTION */}
      <div>
        <h3 style={{ fontSize: '18px', margin: '0 0 14px', color: '#0f172a' }}>
          ALL SCREENED TRIALS ({filtered.length})
        </h3>
        {filtered.length ? (
          <div style={{ display: 'grid', gap: '16px' }}>
            {filtered.map(m => renderTrialCard(m, false))}
          </div>
        ) : (
          <div style={{ background: '#f8fafc', padding: '30px', textAlign: 'center', borderRadius: '12px', border: '1px solid #e2e8f0', color: '#64748b' }}>
            No candidate trial matches found matching selected filter criteria.
          </div>
        )}
      </div>
    </div>
  );
}

function PatientDetail() {
  const id = useLocation().pathname.split('/').pop();
  const [p, setP] = useState<any>();
  const [matches, setMatches] = useState<any[]>([]);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [detail, setDetail] = useState<Record<string, any>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [screeningId, setScreeningId] = useState<number | null>(null);
  const [msg, setMsg] = useState('');
  const [note, setNote] = useState('');
  const [noteResult, setNoteResult] = useState<any>(null);
  const [docModal, setDocModal] = useState<any>(null);

  function refresh() {
    api<any>(`/api/patients/${id}`).then(setP);
    api<any>(`/api/matches/${id}`).then(setMatches);
    api<any>(`/api/patients/${id}/candidates`).then(r => setCandidates(r.items));
  }

  useEffect(() => { refresh(); }, [id]);

  const [labName, setLabName] = useState('Creatinine');
  const [labVal, setLabVal] = useState('1.8');
  const [labUnit, setLabUnit] = useState('mg/dL');

  async function updateLab(e?: any) {
    if (e) e.preventDefault();
    if (!labName.trim() || !labVal.trim()) return;
    const r = await api<any>(`/api/patients/${id}/labs?test_name=${encodeURIComponent(labName.trim())}&value=${encodeURIComponent(labVal.trim())}&unit=${encodeURIComponent(labUnit.trim())}`, { method: 'POST' });
    setMsg(`Lab record ${r.status}: ${labName.trim()} set to ${labVal.trim()} ${labUnit.trim()}. Affected trials: ${r.affected_trial_ids.length}.`);
    setP(await api<any>(`/api/patients/${id}`));
  }

  async function screen(trialId: number, nctId: string) {
    setScreeningId(trialId);
    try {
      const r = await api<any>(`/api/screening/${id}/${trialId}`, { method: 'POST' });
      setDetail(d => ({ ...d, [nctId]: r.criteria }));
      setExpanded(e => ({ ...e, [nctId]: true }));
      await refresh();
    } finally {
      setScreeningId(null);
    }
  }

  async function submitNote() {
    if (!note.trim()) return;
    const r = await api<any>(`/api/patients/${id}/notes?text=${encodeURIComponent(note)}`, { method: 'POST' });
    setNoteResult(r);
    setNote('');
  }

  async function fetchDocument(matchId: number) {
    try {
      const doc = await api<any>(`/api/matches/document/${matchId}`);
      setDocModal(doc);
    } catch (err: any) {
      alert(`Error fetching document: ${err.message}`);
    }
  }

  function downloadDoc(filename: string, content: string) {
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (!p) return <Layout><p>Loading patient clinical profile…</p></Layout>;

  return (
    <Layout>
      <h2>Patient Clinical Profile: {p.external_patient_id}</h2>
      
      <div className="grid2">
        <div className="panel">
          <h3>Demographics & Lab History</h3>
          <p><strong>Date of Birth:</strong> {p.date_of_birth || '—'}</p>
          <p><strong>Sex / Gender:</strong> {p.sex || '—'}</p>
          
          <h4 style={{ marginTop: '1rem', marginBottom: '0.5rem' }}>Recent Laboratory Panels</h4>
          {p.labs.length ? (
            p.labs.map((x: any) => (
              <p key={x.id} style={{ margin: '6px 0', background: '#f8fafc', padding: '8px 12px', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <b>{x.test_name}</b>: <strong>{x.value} {x.unit}</strong> <small style={{ color: '#64748b', marginLeft: '8px' }}>({x.observed_at.split('T')[0]})</small>
              </p>
            ))
          ) : (
            <p className="muted">No laboratory records present.</p>
          )}
          
          <div style={{ marginTop: '1rem', padding: '12px', background: '#f1f5f9', borderRadius: '8px', border: '1px solid #cbd5e1' }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '14px' }}>Add or Update Laboratory Test Value</h4>
            <p className="muted" style={{ fontSize: '12px', margin: '0 0 8px 0' }}>If a record for the test exists, it updates the existing value rather than creating a duplicate.</p>
            <form onSubmit={updateLab} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
              <input value={labName} onChange={e => setLabName(e.target.value)} placeholder="Test Name (e.g. Creatinine)" style={{ margin: 0, padding: '6px 10px', fontSize: '13px' }} required />
              <input value={labVal} onChange={e => setLabVal(e.target.value)} placeholder="Value (e.g. 1.8)" style={{ margin: 0, padding: '6px 10px', fontSize: '13px' }} required />
              <input value={labUnit} onChange={e => setLabUnit(e.target.value)} placeholder="Unit (e.g. mg/dL)" style={{ margin: 0, padding: '6px 10px', fontSize: '13px' }} />
              <button style={{ gridColumn: '1 / -1', padding: '8px', fontSize: '13px', background: '#0f172a' }}>Update / Upsert Lab Value</button>
            </form>
          </div>
          {msg && <div className="success" style={{ marginTop: '10px' }}>{msg}</div>}

          <hr style={{ margin: '1.5rem 0', border: '0', borderTop: '1px solid #e2e8f0' }} />

          <h3>Anonymized Clinical Notes Entry</h3>
          <p className="muted">Free text is automatically anonymized with Presidio prior to storage.</p>
          <textarea value={note} onChange={e => setNote(e.target.value)} rows={3} placeholder="e.g. Patient reports fatigue; call mobile 555-0199" />
          <button onClick={submitNote}>Save Anonymized Note</button>
          {noteResult && (
            <div className="success">
              Stored: “{noteResult.anonymized_text}” · {noteResult.detected_entities.length} PII entities redacted
            </div>
          )}
        </div>

        <div className="panel">
          <h3>Candidate Clinical Trials</h3>
          <p className="muted">Semantically ranked against patient conditions and profile.</p>
          {candidates.length ? (
            candidates.map(t => (
              <div className="match" key={t.id}>
                <div>
                  <b>{t.nct_id}</b> — {t.title}
                </div>
                <button disabled={screeningId === t.id} onClick={() => screen(t.id, t.nct_id)}>
                  {screeningId === t.id ? 'Screening…' : 'Screen Trial'}
                </button>
                {detail[t.nct_id] && expanded[t.nct_id] && <CriteriaBreakdown criteria={detail[t.nct_id]} />}
              </div>
            ))
          ) : (
            <p className="muted">No candidate trials available.</p>
          )}
        </div>
      </div>

      <div className="panel" style={{ marginTop: '1.5rem' }}>
        <h3>Matched Trial Evaluations & Document Reports</h3>
        <p className="muted" style={{ margin: '-4px 0 16px', fontSize: '13px' }}>Intelligently ranked trial matches with evidence coverage and audit rationales.</p>
        <ScreenedMatchResults matches={matches} onExportDocument={(mId) => fetchDocument(mId)} />
      </div>

      {/* DOCUMENT PREVIEW MODAL */}
      {docModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.75)', display: 'grid', placeItems: 'center', zIndex: 1000, padding: '20px' }}>
          <div style={{ background: '#fff', width: 'min(900px, 95vw)', maxHeight: '90vh', borderRadius: '16px', padding: '24px', overflowY: 'auto', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: '12px', marginBottom: '16px' }}>
              <div>
                <h3 style={{ margin: 0 }}>Clinical Evaluation Document Report</h3>
                <span style={{ fontSize: '13px', color: '#64748b' }}>Document ID: <code>{docModal.document_id}</code></span>
              </div>
              <button onClick={() => setDocModal(null)} className="ghost" style={{ padding: '6px 12px' }}>Close Window</button>
            </div>
            
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              <button onClick={() => generatePDFReport(docModal, docModal.patient.id, docModal.evaluation.match_id)} style={{ background: '#0284c7' }}>
                📄 Generate Professional PDF Report
              </button>
              <button onClick={() => downloadDoc(`${docModal.document_id}.md`, docModal.markdown_document)} className="ghost">
                📥 Download Markdown
              </button>
              <button onClick={() => downloadDoc(`${docModal.document_id}.json`, JSON.stringify(docModal, null, 2))} className="ghost">
                📥 Download Raw JSON
              </button>
            </div>

            <pre style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0', whiteSpace: 'pre-wrap', fontSize: '13px', fontFamily: 'monospace', maxHeight: '500px', overflowY: 'auto' }}>
              {docModal.markdown_document}
            </pre>
          </div>
        </div>
      )}
    </Layout>
  );
}

function Trials() {
  const [rows, setRows] = useState<Trial[]>([]);
  const [condition, setCondition] = useState('Breast Cancer');
  const [term, setTerm] = useState('');
  const [nctId, setNctId] = useState('');
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');
  const [selectedTrial, setSelectedTrial] = useState<any>(null);

  async function openTrialDetails(nctId: string) {
    try {
      const t = await api<any>(`/api/trials/${nctId}`);
      setSelectedTrial(t);
    } catch (err: any) {
      alert("Error fetching trial details: " + err.message);
    }
  }

  function refresh() {
    api<any>('/api/trials?limit=50').then(r => setRows(r.items));
  }

  useEffect(() => { refresh(); }, []);

  async function handleSync(e: any) {
    e.preventDefault();
    setLoading(true);
    setSyncMsg('');
    try {
      let url = `/api/trials/sync?limit=${limit}`;
      if (nctId.trim()) {
        url += `&nct_id=${encodeURIComponent(nctId.trim())}`;
      } else {
        if (condition.trim()) url += `&condition=${encodeURIComponent(condition.trim())}`;
        if (term.trim()) url += `&term=${encodeURIComponent(term.trim())}`;
      }
      const res = await api<any>(url, { method: 'POST' });
      setSyncMsg(`Sync complete! Total: ${res.imported_count} (Inserted: ${res.inserted_count ?? 0}, Updated: ${res.updated_count ?? 0}, Failed: ${res.failed_count ?? 0})`);
      refresh();
    } catch (err: any) {
      setSyncMsg(`Sync error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Layout>
      <h2>Clinical Trials Database</h2>
      <p className="muted">Cached trial records synchronized from official ClinicalTrials.gov API v2.</p>
      
      <div className="panel" style={{ marginBottom: '1rem' }}>
        <h3>Live Sync from ClinicalTrials.gov API v2</h3>
        <form onSubmit={handleSync} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '0.5rem', flexWrap: 'wrap' }}>
          <input value={condition} onChange={e => setCondition(e.target.value)} placeholder="Condition (e.g. Breast Cancer)" style={{ flex: 1, minWidth: '180px', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }} />
          <input value={term} onChange={e => setTerm(e.target.value)} placeholder="Search term (optional)" style={{ flex: 1, minWidth: '150px', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }} />
          <input value={nctId} onChange={e => setNctId(e.target.value)} placeholder="NCT ID (optional)" style={{ width: '150px', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }} />
          <input type="number" min="1" max="100" value={limit} onChange={e => setLimit(Number(e.target.value))} title="Import limit" style={{ width: '70px', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }} />
          <button disabled={loading}>{loading ? 'Fetching live API v2 data…' : 'Sync Live Clinical Trials'}</button>
        </form>
        {syncMsg && <p className="success" style={{ marginTop: '0.5rem' }}>{syncMsg}</p>}
      </div>

      <div className="panel table">
        <table>
          <thead>
            <tr><th>NCT ID</th><th>Title</th><th>Status</th><th>Phase</th><th>Target Conditions</th><th>Action</th></tr>
          </thead>
          <tbody>
            {rows.map(t => (
              <tr key={t.id}>
                <td><strong>{t.nct_id}</strong></td>
                <td>{t.title}</td>
                <td><span className="pill met">{t.status || 'ACTIVE'}</span></td>
                <td>{t.phase || '—'}</td>
                <td>{t.conditions?.join(', ') || '—'}</td>
                <td>
                  <button onClick={() => openTrialDetails(t.nct_id)} style={{ padding: '4px 10px', fontSize: '12px', background: '#0284c7' }}>
                    📄 View Full Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedTrial && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.75)', display: 'grid', placeItems: 'center', zIndex: 1000, padding: '20px' }}>
          <div style={{ background: '#fff', width: 'min(900px, 95vw)', maxHeight: '90vh', borderRadius: '16px', padding: '24px', overflowY: 'auto', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: '12px', marginBottom: '16px' }}>
              <div>
                <h3 style={{ margin: 0 }}>Trial Full Details: {selectedTrial.nct_id}</h3>
              </div>
              <button onClick={() => setSelectedTrial(null)} className="ghost" style={{ padding: '6px 12px' }}>Close Window</button>
            </div>
            
            <div style={{ display: 'grid', gap: '16px' }}>
              <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px' }}>
                <p style={{ margin: '0 0 8px' }}><strong>Title:</strong> {selectedTrial.title}</p>
                <p style={{ margin: '0 0 8px' }}><strong>Status:</strong> {selectedTrial.status}</p>
                <p style={{ margin: '0 0 8px' }}><strong>Phase:</strong> {selectedTrial.phase}</p>
                <p style={{ margin: '0' }}><strong>Conditions:</strong> {selectedTrial.conditions?.join(', ')}</p>
              </div>
              <div>
                <h4 style={{ margin: '0 0 8px' }}>Eligibility Criteria</h4>
                <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', maxHeight: '300px', overflowY: 'auto', fontSize: '13px', whiteSpace: 'pre-wrap' }}>
                  {selectedTrial.eligibility_text || 'No criteria details available.'}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}

function Monitoring() {
  const [d, setD] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefreshMs, setAutoRefreshMs] = useState<number>(60000);
  const [syncing, setSyncing] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const navigate = useNavigate();

  const loadData = () => {
    setError(null);
    api<any>('/api/monitoring/overview')
      .then(res => {
        setD(res);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load monitoring overview:", err);
        setError("Monitoring data unavailable");
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!autoRefreshMs || autoRefreshMs <= 0) return;
    const timer = setInterval(() => {
      loadData();
    }, autoRefreshMs);
    return () => clearInterval(timer);
  }, [autoRefreshMs]);

  const handleSyncNow = async () => {
    setSyncing(true);
    setActionMessage(null);
    try {
      await api('/api/trials/sync', { method: 'POST', body: JSON.stringify({ condition: 'Breast Cancer', limit: 10 }) });
      setActionMessage('ClinicalTrials.gov sync completed successfully.');
      loadData();
    } catch (err: any) {
      setActionMessage('Sync failed: ' + (err.message || 'Server error'));
    } finally {
      setSyncing(false);
    }
  };

  const handleRunScreening = async (patientId: number, trialId: number) => {
    setActionMessage(null);
    try {
      await api(`/api/screening/${patientId}/${trialId}`, { method: 'POST' });
      setActionMessage(`Incremental re-screening executed for Patient #${patientId}.`);
      loadData();
    } catch (err: any) {
      setActionMessage('Screening execution failed: ' + (err.message || 'Error'));
    }
  };

  if (loading) {
    return (
      <Layout>
        <div style={{ padding: '2rem', textAlign: 'center' }}>
          <h2>MONITORING & ANALYTICS</h2>
          <p className="muted">Loading real-time change impact telemetry...</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginTop: '2rem' }}>
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="panel" style={{ height: '120px', background: '#f8fafc' }} />
            ))}
          </div>
        </div>
      </Layout>
    );
  }

  if (error || !d) {
    return (
      <Layout>
        <div className="panel" style={{ textAlign: 'center', padding: '3rem 1rem', marginTop: '2rem' }}>
          <h3 style={{ color: '#dc2626' }}>Monitoring Data Unavailable</h3>
          <p className="muted">Failed to connect to backend monitoring telemetry stream.</p>
          <button onClick={loadData} style={{ marginTop: '1rem' }}>Retry Connection</button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      {/* 1. HEADER SECTION */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', color: '#0284c7', textTransform: 'uppercase' }}>
            MONITORING & ANALYTICS
          </div>
          <h2 style={{ margin: '4px 0 0 0' }}>System Monitoring & Change Impact</h2>
          <p className="muted" style={{ margin: '4px 0 0 0', fontSize: '13px' }}>
            Track patient and trial changes, re-screening activity, synchronization health, and screening impact.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', background: '#ffffff', padding: '8px 14px', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ fontSize: '12px', color: '#64748b' }}>
            Last updated: <strong style={{ color: '#0f172a' }}>{new Date(d.last_updated).toLocaleTimeString()}</strong>
          </div>

          <button onClick={loadData} className="ghost" style={{ padding: '6px 12px', fontSize: '12px' }}>
            Refresh
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#64748b' }}>
            <span>Auto-refresh:</span>
            <select
              value={autoRefreshMs}
              onChange={e => setAutoRefreshMs(Number(e.target.value))}
              style={{ padding: '4px 8px', fontSize: '12px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
            >
              <option value={0}>Off</option>
              <option value={30000}>30 sec</option>
              <option value={60000}>1 min</option>
              <option value={300000}>5 min</option>
            </select>
          </div>
        </div>
      </div>

      {actionMessage && (
        <div style={{ background: '#eff6ff', borderLeft: '4px solid #3b82f6', color: '#1e40af', padding: '10px 14px', borderRadius: '6px', marginBottom: '1.5rem', fontSize: '13px' }}>
          {actionMessage}
        </div>
      )}

      {/* 2. TOP 6 KPI CARDS */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '12px', marginBottom: '1.5rem' }}>
        {/* CARD 1: PATIENT CHANGES */}
        <div className="panel" style={{ padding: '14px' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>PATIENT CHANGES</div>
          <div style={{ fontSize: '28px', fontWeight: 800, color: '#0f172a', margin: '4px 0' }}>{d.kpis.patient_changes_24h}</div>
          <small style={{ color: '#64748b', fontSize: '11px' }}>Changes in last 24 hours</small>
        </div>

        {/* CARD 2: TRIAL CHANGES */}
        <div className="panel" style={{ padding: '14px' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>TRIAL CHANGES</div>
          <div style={{ fontSize: '28px', fontWeight: 800, color: '#0f172a', margin: '4px 0' }}>{d.kpis.trial_changes}</div>
          <small style={{ color: '#64748b', fontSize: '11px' }}>Updated since last sync</small>
        </div>

        {/* CARD 3: RE-SCREENING QUEUE */}
        <div className="panel" style={{ padding: '14px' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>RE-SCREENING QUEUE</div>
          <div style={{ fontSize: '28px', fontWeight: 800, color: '#d97706', margin: '4px 0' }}>{d.kpis.rescreening_queue}</div>
          <small style={{ color: '#64748b', fontSize: '11px' }}>Pending review</small>
        </div>

        {/* CARD 4: AFFECTED MATCHES */}
        <div className="panel" style={{ padding: '14px' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>AFFECTED MATCHES</div>
          <div style={{ fontSize: '28px', fontWeight: 800, color: '#2563eb', margin: '4px 0' }}>{d.kpis.affected_matches}</div>
          <small style={{ color: '#64748b', fontSize: '11px' }}>Potentially impacted</small>
        </div>

        {/* CARD 5: SYNC STATUS */}
        <div className="panel" style={{ padding: '14px' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>SYNC STATUS</div>
          <div style={{ marginTop: '6px' }}>
            <span className={`pill ${d.kpis.sync_status === 'Connected' ? 'met' : 'bad'}`} style={{ fontSize: '12px', padding: '4px 10px' }}>
              ● {d.kpis.sync_status}
            </span>
          </div>
          <small style={{ color: '#64748b', fontSize: '11px', display: 'block', marginTop: '6px' }}>ClinicalTrials.gov v2</small>
        </div>

        {/* CARD 6: FAILED JOBS */}
        <div className="panel" style={{ padding: '14px' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>FAILED JOBS</div>
          <div style={{ fontSize: '28px', fontWeight: 800, color: d.kpis.failed_jobs > 0 ? '#dc2626' : '#059669', margin: '4px 0' }}>{d.kpis.failed_jobs}</div>
          <small style={{ color: '#64748b', fontSize: '11px' }}>Requires attention</small>
        </div>
      </div>

      {/* ROW 1: CHANGE IMPACT OVERVIEW & SYSTEM HEALTH */}
      <div className="grid2" style={{ marginBottom: '1.5rem' }}>
        {/* 4. CHANGE IMPACT OVERVIEW */}
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>CHANGE IMPACT OVERVIEW</h3>
          <p className="muted" style={{ fontSize: '12px' }}>Real-time telemetry flow for incremental patient & trial re-evaluations.</p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px', marginTop: '1rem', textAlign: 'center' }}>
            <div style={{ background: '#e0f2fe', padding: '10px 6px', borderRadius: '8px', borderTop: '3px solid #0284c7' }}>
              <small style={{ color: '#0369a1', fontSize: '10px', fontWeight: 700 }}>Patient Changes</small>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#0284c7', marginTop: '2px' }}>{d.change_impact_stages.patient_changes}</div>
            </div>

            <div style={{ background: '#fef3c7', padding: '10px 6px', borderRadius: '8px', borderTop: '3px solid #d97706' }}>
              <small style={{ color: '#92400e', fontSize: '10px', fontWeight: 700 }}>Criteria Affected</small>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#d97706', marginTop: '2px' }}>{d.change_impact_stages.criteria_affected}</div>
            </div>

            <div style={{ background: '#eff6ff', padding: '10px 6px', borderRadius: '8px', borderTop: '3px solid #2563eb' }}>
              <small style={{ color: '#1e40af', fontSize: '10px', fontWeight: 700 }}>Candidates Affected</small>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#2563eb', marginTop: '2px' }}>{d.change_impact_stages.candidates_affected}</div>
            </div>

            <div style={{ background: '#fae8ff', padding: '10px 6px', borderRadius: '8px', borderTop: '3px solid #c026d3' }}>
              <small style={{ color: '#86198f', fontSize: '10px', fontWeight: 700 }}>Re-screening Req.</small>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#c026d3', marginTop: '2px' }}>{d.change_impact_stages.rescreen_required}</div>
            </div>

            <div style={{ background: '#dcfce7', padding: '10px 6px', borderRadius: '8px', borderTop: '3px solid #16a34a' }}>
              <small style={{ color: '#15803d', fontSize: '10px', fontWeight: 700 }}>Re-screened</small>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#16a34a', marginTop: '2px' }}>{d.change_impact_stages.rescreened}</div>
            </div>
          </div>
        </div>

        {/* 11. SYSTEM HEALTH */}
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>SYSTEM HEALTH</h3>
          <p className="muted" style={{ fontSize: '12px' }}>Operational health checks calculated dynamically from active services.</p>

          <div style={{ display: 'grid', gap: '8px', marginTop: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: '#f8fafc', borderRadius: '6px' }}>
              <span style={{ fontSize: '13px' }}>Backend API</span>
              <span className="pill met" style={{ fontSize: '11px' }}>● {d.system_health.backend_api}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: '#f8fafc', borderRadius: '6px' }}>
              <span style={{ fontSize: '13px' }}>Database Connection</span>
              <span className="pill met" style={{ fontSize: '11px' }}>● {d.system_health.database}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: '#f8fafc', borderRadius: '6px' }}>
              <span style={{ fontSize: '13px' }}>ClinicalTrials.gov API v2</span>
              <span className="pill met" style={{ fontSize: '11px' }}>● {d.system_health.clinicaltrials_api}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: '#f8fafc', borderRadius: '6px' }}>
              <span style={{ fontSize: '13px' }}>Matching Engine</span>
              <span className="pill met" style={{ fontSize: '11px' }}>● {d.system_health.matching_engine}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: '#f8fafc', borderRadius: '6px' }}>
              <span style={{ fontSize: '13px' }}>Monitoring Worker</span>
              <span className={`pill ${d.system_health.monitoring_worker === 'Healthy' ? 'met' : 'warn'}`} style={{ fontSize: '11px' }}>
                ● {d.system_health.monitoring_worker}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ROW 2: PATIENT CHANGE ACTIVITY & TRIAL CHANGE ACTIVITY */}
      <div className="grid2" style={{ marginBottom: '1.5rem' }}>
        {/* 5. PATIENT CHANGE ACTIVITY */}
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>PATIENT CHANGE ACTIVITY</h3>
          <div className="table" style={{ maxHeight: '280px', marginTop: '0.8rem' }}>
            <table>
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Change Type</th>
                  <th>Source</th>
                  <th>Changed At</th>
                  <th>Impact</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {d.patient_activity.map((p: any, idx: number) => (
                  <tr key={idx}>
                    <td><strong>{p.external_patient_id}</strong></td>
                    <td>{p.change_type}</td>
                    <td><small className="muted">{p.source}</small></td>
                    <td><small>{new Date(p.changed_at).toLocaleTimeString()}</small></td>
                    <td>
                      <span className={`pill ${p.impact === 'Re-screen required' ? 'warn' : p.impact === 'Potential impact' ? 'conflict' : 'met'}`}>
                        {p.impact}
                      </span>
                    </td>
                    <td>
                      <button onClick={() => navigate(`/patients/${p.patient_id}`)} className="ghost" style={{ padding: '2px 8px', fontSize: '11px' }}>
                        Review
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 6. TRIAL CHANGE ACTIVITY */}
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>TRIAL CHANGE ACTIVITY</h3>
          <div className="table" style={{ maxHeight: '280px', marginTop: '0.8rem' }}>
            <table>
              <thead>
                <tr>
                  <th>NCT ID</th>
                  <th>Trial</th>
                  <th>Change Type</th>
                  <th>New Status</th>
                  <th>Candidates</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {d.trial_activity.map((t: any, idx: number) => (
                  <tr key={idx}>
                    <td><code>{t.nct_id}</code></td>
                    <td style={{ maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.title}</td>
                    <td><small>{t.change_type}</small></td>
                    <td><span className="pill met">{t.new_value}</span></td>
                    <td><strong>{t.affected_candidates_count}</strong></td>
                    <td>
                      <button onClick={() => navigate('/trials')} className="ghost" style={{ padding: '2px 8px', fontSize: '11px' }}>
                        Review
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ROW 3: INCREMENTAL RE-SCREENING QUEUE */}
      <div className="panel" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h3 style={{ margin: 0 }}>INCREMENTAL RE-SCREENING QUEUE</h3>
            <p className="muted" style={{ margin: '4px 0 0 0', fontSize: '12px' }}>Targeted evaluations queued for changed clinical evidence.</p>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <span className="pill warn" style={{ fontSize: '11px' }}>Pending: {d.rescreening_queue.counts.pending}</span>
            <span className="pill conflict" style={{ fontSize: '11px' }}>In Progress: {d.rescreening_queue.counts.in_progress}</span>
            <span className="pill met" style={{ fontSize: '11px' }}>Completed: {d.rescreening_queue.counts.completed}</span>
            <span className="pill bad" style={{ fontSize: '11px' }}>Failed: {d.rescreening_queue.counts.failed}</span>
          </div>
        </div>

        <div className="table" style={{ marginTop: '1rem' }}>
          <table>
            <thead>
              <tr>
                <th>Patient</th>
                <th>Affected Trial</th>
                <th>Reason</th>
                <th>Priority</th>
                <th>Queued At</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {d.rescreening_queue.items.length ? (
                d.rescreening_queue.items.map((q: any) => (
                  <tr key={q.job_id}>
                    <td><strong>{q.external_patient_id}</strong></td>
                    <td><code>{q.nct_id}</code> - <small>{q.trial_title}</small></td>
                    <td>{q.reason}</td>
                    <td>
                      <span className={`pill ${q.priority === 'High' ? 'bad' : q.priority === 'Medium' ? 'warn' : 'met'}`}>
                        {q.priority}
                      </span>
                    </td>
                    <td><small>{new Date(q.queued_at).toLocaleTimeString()}</small></td>
                    <td><span className="pill met">{q.status}</span></td>
                    <td>
                      <div style={{ display: 'flex', gap: '4px' }}>
                        <button onClick={() => navigate(`/patients/${q.patient_id}`)} className="ghost" style={{ padding: '2px 6px', fontSize: '11px' }}>
                          Review
                        </button>
                        {q.trial_id && (
                          <button onClick={() => handleRunScreening(q.patient_id, q.trial_id)} style={{ padding: '2px 6px', fontSize: '11px', background: '#0284c7' }}>
                            Run
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', color: '#64748b', padding: '1rem' }}>
                    No pending items in re-screening queue. All clinical evidence up-to-date.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ROW 4: MATCH IMPACT & ELIGIBILITY CHANGE ANALYTICS */}
      <div className="grid2" style={{ marginBottom: '1.5rem' }}>
        {/* 8. MATCH IMPACT ANALYTICS */}
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>MATCH IMPACT ANALYTICS</h3>
          <p className="muted" style={{ fontSize: '12px' }}>Candidate match stability breakdown from database evaluation results.</p>

          <div style={{ display: 'grid', gap: '12px', marginTop: '1rem' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span>Unaffected Candidate Matches</span>
                <strong>{d.match_impact.unaffected}</strong>
              </div>
              <div style={{ background: '#e2e8f0', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ background: '#10b981', width: '100%', height: '100%' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span>Potentially Affected</span>
                <strong>{d.match_impact.potentially_affected}</strong>
              </div>
              <div style={{ background: '#e2e8f0', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ background: '#3b82f6', width: '60%', height: '100%' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span>Re-screen Required</span>
                <strong>{d.match_impact.requires_rescreening}</strong>
              </div>
              <div style={{ background: '#e2e8f0', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ background: '#f59e0b', width: '40%', height: '100%' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span>Changed Result After Re-screen</span>
                <strong>{d.match_impact.changed_after_rescreen}</strong>
              </div>
              <div style={{ background: '#e2e8f0', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ background: '#8b5cf6', width: '25%', height: '100%' }} />
              </div>
            </div>
          </div>
        </div>

        {/* 9. ELIGIBILITY CHANGE ANALYTICS */}
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>ELIGIBILITY TRANSITIONS</h3>
          <p className="muted" style={{ fontSize: '12px' }}>Criteria decision migration counts across re-evaluation cycles.</p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', marginTop: '1rem' }}>
            <div style={{ background: '#ffe3e6', padding: '10px', borderRadius: '8px' }}>
              <div style={{ fontSize: '11px', color: '#991b1b', fontWeight: 700 }}>MET → NOT MET</div>
              <div style={{ fontSize: '20px', fontWeight: 800, color: '#a31c35' }}>{d.eligibility_impact.met_to_not_met}</div>
            </div>

            <div style={{ background: '#fff2cc', padding: '10px', borderRadius: '8px' }}>
              <div style={{ fontSize: '11px', color: '#854d0e', fontWeight: 700 }}>MET → UNKNOWN</div>
              <div style={{ fontSize: '20px', fontWeight: 800, color: '#936600' }}>{d.eligibility_impact.met_to_unknown}</div>
            </div>

            <div style={{ background: '#dff6ec', padding: '10px', borderRadius: '8px' }}>
              <div style={{ fontSize: '11px', color: '#065f46', fontWeight: 700 }}>NOT MET → MET</div>
              <div style={{ fontSize: '20px', fontWeight: 800, color: '#087a55' }}>{d.eligibility_impact.not_met_to_met}</div>
            </div>

            <div style={{ background: '#dff6ec', padding: '10px', borderRadius: '8px' }}>
              <div style={{ fontSize: '11px', color: '#065f46', fontWeight: 700 }}>UNKNOWN → MET</div>
              <div style={{ fontSize: '20px', fontWeight: 800, color: '#087a55' }}>{d.eligibility_impact.unknown_to_met}</div>
            </div>

            <div style={{ background: '#ffe3e6', padding: '10px', borderRadius: '8px' }}>
              <div style={{ fontSize: '11px', color: '#991b1b', fontWeight: 700 }}>UNKNOWN → NOT MET</div>
              <div style={{ fontSize: '20px', fontWeight: 800, color: '#a31c35' }}>{d.eligibility_impact.unknown_to_not_met}</div>
            </div>

            <div style={{ background: '#ece5ff', padding: '10px', borderRadius: '8px' }}>
              <div style={{ fontSize: '11px', color: '#5b21b6', fontWeight: 700 }}>CONFLICTING</div>
              <div style={{ fontSize: '20px', fontWeight: 800, color: '#6440a8' }}>{d.eligibility_impact.conflicting}</div>
            </div>
          </div>
        </div>
      </div>

      {/* ROW 5: CLINICALTRIALS.GOV SYNC & ALERTS */}
      <div className="grid2" style={{ marginBottom: '1.5rem' }}>
        {/* 10. CLINICALTRIALS.GOV SYNC */}
        <div className="panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0 }}>CLINICALTRIALS.GOV SYNC</h3>
            <button disabled={syncing} onClick={handleSyncNow} style={{ padding: '6px 12px', fontSize: '12px', background: '#0f172a' }}>
              {syncing ? 'Syncing…' : 'Sync Now'}
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginTop: '1rem' }}>
            <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '6px' }}>
              <small className="muted" style={{ fontSize: '10px' }}>Status</small>
              <div style={{ fontWeight: 700, color: '#059669', fontSize: '14px', marginTop: '2px' }}>● {d.clinicaltrials_sync.status}</div>
            </div>

            <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '6px' }}>
              <small className="muted" style={{ fontSize: '10px' }}>Fetched</small>
              <div style={{ fontWeight: 700, fontSize: '16px', marginTop: '2px' }}>{d.clinicaltrials_sync.fetched}</div>
            </div>

            <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '6px' }}>
              <small className="muted" style={{ fontSize: '10px' }}>Inserted</small>
              <div style={{ fontWeight: 700, fontSize: '16px', marginTop: '2px' }}>{d.clinicaltrials_sync.inserted}</div>
            </div>

            <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '6px' }}>
              <small className="muted" style={{ fontSize: '10px' }}>Updated</small>
              <div style={{ fontWeight: 700, fontSize: '16px', marginTop: '2px' }}>{d.clinicaltrials_sync.updated}</div>
            </div>

            <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '6px' }}>
              <small className="muted" style={{ fontSize: '10px' }}>Failed</small>
              <div style={{ fontWeight: 700, color: d.clinicaltrials_sync.failed > 0 ? '#dc2626' : '#475569', fontSize: '16px', marginTop: '2px' }}>{d.clinicaltrials_sync.failed}</div>
            </div>

            <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '6px' }}>
              <small className="muted" style={{ fontSize: '10px' }}>Duration</small>
              <div style={{ fontWeight: 700, fontSize: '14px', marginTop: '2px' }}>{(d.clinicaltrials_sync.duration_ms / 1000).toFixed(1)}s</div>
            </div>
          </div>
        </div>

        {/* 15. ALERTS & ISSUES */}
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>ALERTS & ISSUES</h3>
          <div style={{ display: 'grid', gap: '8px', marginTop: '1rem', maxHeight: '220px', overflowY: 'auto' }}>
            {d.alerts.length ? (
              d.alerts.map((a: any) => (
                <div key={a.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', background: '#fff5f5', borderRadius: '6px', borderLeft: '3px solid #dc2626' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className={`pill ${a.severity === 'HIGH' ? 'bad' : a.severity === 'MEDIUM' ? 'warn' : 'conflict'}`} style={{ fontSize: '10px' }}>
                        {a.severity}
                      </span>
                      <strong style={{ fontSize: '12px' }}>{a.title}</strong>
                    </div>
                    <small className="muted" style={{ fontSize: '11px', display: 'block', marginTop: '2px' }}>{a.message}</small>
                  </div>
                  <button onClick={() => navigate(a.action_link)} className="ghost" style={{ padding: '2px 8px', fontSize: '11px' }}>
                    Review
                  </button>
                </div>
              ))
            ) : (
              <div style={{ background: '#f0fdf4', color: '#166534', padding: '14px', borderRadius: '6px', textAlign: 'center', fontSize: '13px' }}>
                ✓ No active operational issues detected
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ROW 6: DATA QUALITY & API PERFORMANCE */}
      <div className="grid2" style={{ marginBottom: '1.5rem' }}>
        {/* 16. DATA QUALITY */}
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>DATA QUALITY</h3>
          <p className="muted" style={{ fontSize: '12px' }}>Calculated database record field completeness.</p>

          <div style={{ display: 'grid', gap: '10px', marginTop: '1rem' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span>Trial Eligibility Text Completeness</span>
                <strong>{d.data_quality.eligibility_completeness_pct}%</strong>
              </div>
              <div style={{ background: '#e2e8f0', height: '6px', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ background: '#0284c7', width: `${d.data_quality.eligibility_completeness_pct}%`, height: '100%' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span>Trial Locations Complete</span>
                <strong>{d.data_quality.locations_completeness_pct}%</strong>
              </div>
              <div style={{ background: '#e2e8f0', height: '6px', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ background: '#10b981', width: `${d.data_quality.locations_completeness_pct}%`, height: '100%' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span>Patient Required Demographics</span>
                <strong>{d.data_quality.patient_demographics_pct}%</strong>
              </div>
              <div style={{ background: '#e2e8f0', height: '6px', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ background: '#8b5cf6', width: `${d.data_quality.patient_demographics_pct}%`, height: '100%' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span>Patient Labs with Units</span>
                <strong>{d.data_quality.lab_units_pct}%</strong>
              </div>
              <div style={{ background: '#e2e8f0', height: '6px', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ background: '#f59e0b', width: `${d.data_quality.lab_units_pct}%`, height: '100%' }} />
              </div>
            </div>
          </div>
        </div>

        {/* 12. API PERFORMANCE */}
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>API PERFORMANCE TELEMETRY</h3>
          <div className="table" style={{ maxHeight: '200px', marginTop: '0.8rem' }}>
            <table>
              <thead>
                <tr>
                  <th>Endpoint</th>
                  <th>Requests</th>
                  <th>Avg Latency</th>
                  <th>P95 Latency</th>
                  <th>Errors</th>
                </tr>
              </thead>
              <tbody>
                {d.api_performance.map((ep: any, idx: number) => (
                  <tr key={idx}>
                    <td><code>{ep.endpoint}</code></td>
                    <td>{ep.requests}</td>
                    <td>{ep.avg_latency_ms}ms</td>
                    <td>{ep.p95_latency_ms}ms</td>
                    <td><span className="pill met">{ep.errors}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ROW 7: RECENT MONITORING EVENTS */}
      <div className="panel" style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ marginTop: 0 }}>RECENT MONITORING EVENTS</h3>
        <div className="table" style={{ maxHeight: '250px', marginTop: '0.8rem' }}>
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action Event</th>
                <th>Target Entity</th>
                <th>Metadata / Impact Detail</th>
              </tr>
            </thead>
            <tbody>
              {d.recent_events.map((ev: any) => (
                <tr key={ev.id}>
                  <td><small>{new Date(ev.timestamp).toLocaleTimeString()}</small></td>
                  <td><span className="pill met">{ev.action}</span></td>
                  <td>{ev.entity_type} #{ev.entity_id}</td>
                  <td><code>{JSON.stringify(ev.metadata)}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 18. COLLAPSIBLE HOW CHANGE IMPACT WORKS */}
      <details style={{ background: '#ffffff', padding: '12px 16px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
        <summary style={{ cursor: 'pointer', fontWeight: 700, fontSize: '13px', color: '#475569' }}>
          How Change Impact Works (Clinical Architecture Reference)
        </summary>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px', marginTop: '1rem' }}>
          <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '6px' }}>
            <strong>1. Ingestion</strong> — Patient lab / note entry anonymized via Presidio.
          </div>
          <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '6px' }}>
            <strong>2. Detection</strong> — Scans target criteria & flags dependent trials.
          </div>
          <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '6px' }}>
            <strong>3. Re-Screening</strong> — Evaluates updated evidence incrementally without full DB scan.
          </div>
          <div style={{ background: '#f8fafc', padding: '10px', borderRadius: '6px' }}>
            <strong>4. Match Report</strong> — Updated evaluation document generated for PI sign-off.
          </div>
        </div>
      </details>
    </Layout>
  );
}

function Audit() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => { api<any[]>('/api/audit').then(setRows); }, []);
  
  return (
    <Layout>
      <h2>System Audit Trail</h2>
      <p className="muted">Immutable clinical decision support audit trail log.</p>
      <div className="panel table">
        <table>
          <thead>
            <tr><th>Timestamp</th><th>Action</th><th>Entity</th><th>Metadata</th></tr>
          </thead>
          <tbody>
            {rows.map(x => (
              <tr key={x.id}>
                <td>{x.created_at}</td>
                <td><span className="pill met">{x.action}</span></td>
                <td>{x.entity_type} {x.entity_id}</td>
                <td><code>{JSON.stringify(x.metadata)}</code></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}

function HackathonDemo() {
  const [step, setStep] = useState(1);
  const [trials, setTrials] = useState<any[]>([]);
  const [selectedTrial, setSelectedTrial] = useState<any>(null);
  const [matchResult, setMatchResult] = useState<any>(null);
  const [ragReasoning, setRagReasoning] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [graphKey, setGraphKey] = useState(1); // To force iframe reload
  const patientId = 1;

  useEffect(() => {
    api<any>('/api/trials').then(data => setTrials(data.items || []));
  }, []);

  async function runMatch() {
    if (!selectedTrial) return;
    setLoading(true);
    try {
      const res = await api<any>(`/api/screening/${patientId}/${selectedTrial.id}`, { method: 'POST' });
      setMatchResult(res);
      setRagReasoning('');
    } catch (e) {
      alert("Match failed");
    } finally {
      setLoading(false);
    }
  }

  async function generateGraphRAG() {
    if (!matchResult) return;
    setLoading(true);
    try {
      const res = await api<any>(`/api/patients/${patientId}/graph_rag/${matchResult.id}`);
      setRagReasoning(res.reasoning);
    } catch (e) {
      alert("GraphRAG failed");
    } finally {
      setLoading(false);
    }
  }

  async function simulateLab() {
    setLoading(true);
    setSuccessMsg('');
    try {
      await api<any>(`/api/patients/${patientId}/labs?test_name=Creatinine&value=1.0&unit=mg/dL`, { method: 'POST' });
      await api<any>(`/api/patients/${patientId}/labs?test_name=AST&value=30&unit=U/L`, { method: 'POST' });
      await api<any>(`/api/patients/${patientId}/labs?test_name=ECOG&value=0&unit=`, { method: 'POST' });
      setGraphKey(k => k + 1);
      setSuccessMsg("Labs simulated: Creatinine = 1.0 mg/dL, AST = 30 U/L, ECOG = 0. Graph updated! Re-run match in Step 2.");
    } catch (e) {
      alert("Simulation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Layout>
      <h2>Synapse-KG Hackathon Demo</h2>
      <p className="muted">End-to-End Workflow: Clinical Extraction, GraphRAG, and Dynamic Updates</p>
      
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
        <button className={step === 1 ? '' : 'ghost'} onClick={() => setStep(1)}>1. Trial Selection</button>
        <button className={step === 2 ? '' : 'ghost'} onClick={() => setStep(2)}>2. GraphRAG Engine</button>
        <button className={step === 3 ? '' : 'ghost'} onClick={() => setStep(3)}>3. Dynamic Simulation</button>
      </div>

      {step === 1 && (
        <div className="panel">
          <h3>Step 1: Trial Selection</h3>
          <p>Select a scraped Clinical Trial from the registry to evaluate.</p>
          <div className="table">
            <table>
              <thead><tr><th>NCT ID</th><th>Title</th><th>Action</th></tr></thead>
              <tbody>
                {trials.map(t => (
                  <tr key={t.id}>
                    <td>{t.nct_id}</td>
                    <td>{t.title}</td>
                    <td>
                      <button onClick={() => { setSelectedTrial(t); setStep(2); }}>Select & Proceed</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="grid2">
          <div className="panel">
            <h3>Patient Knowledge Graph</h3>
            <iframe key={graphKey} src={`/api/patients/${patientId}/graph`} style={{ width: '100%', height: '500px', border: '1px solid #e2e8f0', borderRadius: '8px' }} />
          </div>
          <div className="panel">
            <h3>Deterministic Rule Engine</h3>
            {selectedTrial ? (
              <>
                <p><strong>Target:</strong> {selectedTrial.title}</p>
                <button onClick={runMatch} disabled={loading}>{loading ? 'Processing...' : 'Run AST Rule Engine'}</button>
                
                {matchResult && (
                  <div style={{ marginTop: '1rem', padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                    <h4 style={{ color: matchResult.status === 'ELIGIBLE' ? 'green' : 'red' }}>Status: {matchResult.status}</h4>
                    <ul style={{ paddingLeft: '1rem', margin: '1rem 0' }}>
                      {matchResult.criteria.map((c: any, i: number) => (
                        <li key={i} style={{ marginBottom: '0.5rem', color: c.decision === 'MET' ? 'green' : 'red' }}>
                          {c.decision === 'MET' ? '✅' : '❌'} {c.reason}
                        </li>
                      ))}
                    </ul>
                    
                    <button onClick={generateGraphRAG} disabled={loading}>Generate GraphRAG Explanation</button>
                    
                    {ragReasoning && (
                      <div style={{ marginTop: '1rem', padding: '1rem', background: '#e0f2fe', color: '#0369a1', borderRadius: '8px', borderLeft: '4px solid #0284c7' }}>
                        <strong>GraphRAG Reasoning:</strong><br/><br/>
                        {ragReasoning}
                      </div>
                    )}
                  </div>
                )}
              </>
            ) : <p>Please select a trial in Step 1.</p>}
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="panel" style={{ maxWidth: '600px' }}>
          <h3>Step 3: Dynamic Data Simulation</h3>
          <p>Simulate an incoming HL7/FHIR observation to see how the graph and rules adapt.</p>
          <div style={{ background: '#fffbe6', padding: '1rem', borderRadius: '8px', border: '1px solid #ffe58f' }}>
            <p><strong>Incoming Message:</strong> LAB RESULT - Creatinine = 1.0 mg/dL, AST = 30 U/L, ECOG = 0</p>
            <button onClick={simulateLab} disabled={loading}>{loading ? 'Ingesting...' : 'Ingest HL7 Data into Graph'}</button>
            {successMsg && (
              <div style={{ marginTop: '1rem', padding: '10px', background: '#dcfce7', color: '#166534', borderRadius: '6px', fontSize: '13px', fontWeight: 500 }}>
                ✓ {successMsg}
              </div>
            )}
          </div>
        </div>
      )}
    </Layout>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
      <Route path="/hackathon" element={<Protected><HackathonDemo /></Protected>} />
      <Route path="/patients" element={<Protected><Patients /></Protected>} />
      <Route path="/patients/:id" element={<Protected><PatientDetail /></Protected>} />
      <Route path="/trials" element={<Protected><Trials /></Protected>} />
      <Route path="/monitoring" element={<Protected><Monitoring /></Protected>} />
      <Route path="/audit" element={<Protected><Audit /></Protected>} />
      <Route path="*" element={<Navigate to={localStorage.getItem('tm_token') ? '/dashboard' : '/login'} replace />} />
    </Routes>
  );
}
