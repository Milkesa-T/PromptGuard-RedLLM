import React, { useState, useEffect } from 'react';
import { Download, Search, RefreshCw, X, Shield, Copy, Check } from 'lucide-react';

export default function AuditLogsView({ autoRefresh = false }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('all');
  const [outcomeFilter, setOutcomeFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [limit, setLimit] = useState(50);
  const [activeModalLog, setActiveModalLog] = useState(null);
  const [copied, setCopied] = useState(false);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/logs?limit=${limit}`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
      }
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    if (autoRefresh) {
      const interval = setInterval(fetchLogs, 5000);
      return () => clearInterval(interval);
    }
  }, [limit, autoRefresh]);

  // Task 4: CSV and JSON Exports via /api/logs/export?format=csv|json
  const exportFile = (format) => {
    const link = document.createElement('a');
    link.href = `/api/logs/export?format=${format}`;
    link.setAttribute('download', `security_audit_logs.${format}`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredLogs = logs.filter((log) => {
    if (actionFilter !== 'all' && (log.guard_action || '').toLowerCase() !== actionFilter) {
      return false;
    }
    if (outcomeFilter === 'defended' && log.is_success) return false;
    if (outcomeFilter === 'jailbreak' && !log.is_success) return false;

    if (search.trim()) {
      const q = search.toLowerCase();
      const haystack = [
        log.attack_id || '',
        log.objective || '',
        log.sent_prompt || '',
        log.guard_reason || '',
        log.target_response || '',
        log.judge_reason || ''
      ].join(' ').toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });

  const copyPrompt = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="card">
      <div className="card-header" style={{ flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h3>Full Security Audit Trail</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Comprehensive forensic archive of all evaluated red-team queries and LLM behaviors.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-secondary" onClick={() => exportFile('csv')}>
            <Download size={14} /> Export CSV
          </button>
          <button className="btn btn-secondary" onClick={() => exportFile('json')}>
            <Download size={14} /> Export JSON
          </button>
          <button className="btn btn-secondary" onClick={fetchLogs} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin-icon' : ''} />
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1.25rem', alignItems: 'center' }}>
        {/* Action pills */}
        <div style={{ display: 'flex', gap: '0.35rem', background: '#0a0e17', padding: '0.25rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          {['all', 'allow', 'block', 'sanitize'].map((act) => (
            <button
              key={act}
              className={`btn btn-xs ${actionFilter === act ? 'btn-primary' : 'btn-secondary'}`}
              style={{ textTransform: 'capitalize' }}
              onClick={() => setActionFilter(act)}
            >
              {act}
            </button>
          ))}
        </div>

        <select
          className="form-control"
          style={{ width: '160px' }}
          value={outcomeFilter}
          onChange={(e) => setOutcomeFilter(e.target.value)}
        >
          <option value="all">All Outcomes</option>
          <option value="defended">🛡️ Defended Only</option>
          <option value="jailbreak">💥 Jailbroken Only</option>
        </select>

        <div style={{ flex: 1, minWidth: '220px', position: 'relative' }}>
          <input
            type="text"
            className="form-control"
            placeholder="Search prompt payload, reasoning, or attack ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          className="form-control"
          style={{ width: '100px' }}
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
        >
          <option value="25">25 rows</option>
          <option value="50">50 rows</option>
          <option value="100">100 rows</option>
        </select>
      </div>

      {/* Audit Logs Table */}
      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: '130px' }}>Time</th>
              <th style={{ width: '140px' }}>Objective</th>
              <th style={{ width: '120px' }}>Action</th>
              <th>Prompt Payload</th>
              <th style={{ width: '130px' }}>Security Verdict</th>
              <th style={{ width: '90px' }}>Latency</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  Loading audit records...
                </td>
              </tr>
            ) : filteredLogs.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  No logs matching current filters.
                </td>
              </tr>
            ) : (
              filteredLogs.map((log, idx) => {
                const action = (log.guard_action || '').toLowerCase();
                const isBlock = action === 'block';
                const isSuccess = Boolean(log.is_success);
                const ts = log.timestamp || '';
                const datePart = ts.split('T')[0] || '';
                const timePart = ts.split('T')[1]?.substring(0, 8) || '—';
                const timeStr = datePart ? `${datePart}\n${timePart}` : timePart;

                return (
                  <tr key={idx} className="clickable" onClick={() => setActiveModalLog(log)}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-muted)', whiteSpace: 'pre' }}>{timeStr}</td>
                    <td>
                      <span className="badge badge-secondary" style={{ fontSize: '0.78rem', maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {log.objective || 'GENERAL'}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${isBlock ? 'badge-danger' : 'badge-success'}`}>
                        {(log.guard_action || 'ALLOW').toUpperCase()}
                      </span>
                    </td>
                    <td style={{ maxWidth: '350px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {log.sent_prompt}
                    </td>
                    <td>
                      {isBlock ? (
                        <span className="badge badge-danger" style={{ fontSize: '0.78rem' }}>🛡️ FW Blocked</span>
                      ) : isSuccess ? (
                        <span className="badge badge-danger" style={{ fontSize: '0.78rem', background: '#f97316' }}>💥 Jailbroken</span>
                      ) : (
                        <span className="badge badge-success" style={{ fontSize: '0.78rem' }}>✅ LLM Refused</span>
                      )}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
                      {(log.execution_time_seconds || 0).toFixed(3)}s
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        💡 <em>Click any row to inspect full prompt payloads, firewall reasonings, and LLM judge traces.</em>
      </div>

      {/* Forensic Inspection Modal */}
      {activeModalLog && (
        <div className="modal-backdrop" onClick={() => setActiveModalLog(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem' }}>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Security Audit Log Forensic Detail</h3>
                <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                  ID: {activeModalLog.attack_id}
                </span>
              </div>
              <button
                className="btn btn-xs btn-secondary"
                onClick={() => setActiveModalLog(null)}
                style={{ padding: '0.2rem 0.5rem' }}
              >
                <X size={16} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem', marginBottom: '1.25rem', background: '#0a0e17', padding: '0.75rem', borderRadius: '8px' }}>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>ACTION</div>
                <span className={`badge ${(activeModalLog.guard_action || '').toLowerCase() === 'block' ? 'badge-danger' : 'badge-success'}`}>
                  {(activeModalLog.guard_action || 'ALLOW').toUpperCase()}
                </span>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>VERDICT</div>
                <span className={`badge ${activeModalLog.is_success ? 'badge-danger' : 'badge-success'}`}>
                  {activeModalLog.is_success ? '💥 Jailbroken' : '🛡️ Defended'}
                </span>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>LATENCY</div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                  {(activeModalLog.execution_time_seconds || 0).toFixed(3)}s
                </span>
              </div>
            </div>

            <div style={{ marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <label style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
                  Adversarial Prompt Sent
                </label>
                <button
                  className="btn btn-xs btn-secondary"
                  onClick={() => copyPrompt(activeModalLog.sent_prompt)}
                >
                  {copied ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
              <pre className="code-box">{activeModalLog.sent_prompt}</pre>
            </div>

            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                Firewall Decision & Reasoning
              </label>
              <div className="card" style={{ background: '#090e1a', padding: '0.85rem', fontSize: '0.85rem', color: 'var(--text-main)' }}>
                {activeModalLog.guard_reason || 'Prompt passed all input firewall inspection tiers.'}
              </div>
            </div>

            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                Target LLM Raw Response
              </label>
              <pre className="code-box">{activeModalLog.target_response || '[NO RESPONSE]'}</pre>
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                Judge Verdict & Reasoning
              </label>
              <div className="card" style={{ background: '#090e1a', padding: '0.85rem', fontSize: '0.85rem', color: 'var(--text-main)' }}>
                {activeModalLog.judge_reason || 'Evaluated.'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
