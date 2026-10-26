import React, { useState, useEffect } from 'react';
import { Send, Shield, Zap, AlertTriangle, CheckCircle, Terminal, RefreshCw } from 'lucide-react';

export default function PlaygroundView() {
  const [presets, setPresets] = useState([]);
  const [loadingPresets, setLoadingPresets] = useState(true);
  const [prompt, setPrompt] = useState('');
  const [objective, setObjective] = useState('');
  const [attackType, setAttackType] = useState('direct_injection');
  const [enableGuard, setEnableGuard] = useState(true);
  const [useVulnerableTarget, setUseVulnerableTarget] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  // Dynamically fetch attack presets from backend datasets
  const fetchPresets = async () => {
    try {
      setLoadingPresets(true);
      const res = await fetch('/api/attack/presets');
      if (res.ok) {
        const data = await res.json();
        const list = data.presets || [];
        setPresets(list);
        if (list.length > 0 && !prompt) {
          setPrompt(list[0].prompt || '');
          setObjective(list[0].objective || 'PWNED_SYSTEM_OVERRIDE');
          setAttackType(list[0].attack_type || 'direct_injection');
        }
      }
    } catch (err) {
      console.error('Failed to load attack presets:', err);
    } finally {
      setLoadingPresets(false);
    }
  };

  useEffect(() => {
    fetchPresets();
  }, []);

  const handleSend = async () => {
    if (!prompt.trim()) return;

    try {
      setLoading(true);
      setResult(null);

      const res = await fetch('/api/attack/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          objective: objective.trim() || 'PWNED_SYSTEM_OVERRIDE',
          enable_promptguard: enableGuard,
          attack_type: attackType,
          use_vulnerable_target: useVulnerableTarget
        })
      });

      if (res.ok) {
        const data = await res.json();
        setResult(data);
      } else {
        throw new Error(`Server returned ${res.status}`);
      }
    } catch (err) {
      alert('Attack failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadPreset = (e) => {
    const val = e.target.value;
    if (!val) {
      setPrompt('');
      setObjective('');
      return;
    }
    const selected = presets.find(p => (p.id || p.prompt) === val);
    if (selected) {
      setPrompt(selected.prompt || '');
      setObjective(selected.objective || 'PWNED_SYSTEM_OVERRIDE');
      setAttackType(selected.attack_type || 'direct_injection');
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem' }}>
      {/* Attack Generator Form */}
      <div className="card">
        <div className="card-header">
          <h3>Adversarial Attack Generator</h3>
          <button className="btn btn-xs btn-secondary" onClick={fetchPresets} disabled={loadingPresets} title="Reload attack seeds from dataset">
            <RefreshCw size={12} className={loadingPresets ? 'spin-icon' : ''} /> Refresh Seeds
          </button>
        </div>

        <div className="form-group">
          <label>Curated Attack Seeds ({presets.length})</label>
          <select className="form-control" onChange={loadPreset} disabled={loadingPresets}>
            <option value="">-- Select from Curated Datasets or Custom --</option>
            {presets.map((p, idx) => {
              const label = `[${p.id || p.attack_type || 'Attack'}] ${p.prompt?.slice(0, 60)}...`;
              return (
                <option key={idx} value={p.id || p.prompt}>
                  {label}
                </option>
              );
            })}
          </select>
        </div>

        <div className="form-group">
          <label>Attack Objective</label>
          <input
            type="text"
            className="form-control"
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            placeholder="Target exfiltration or override goal..."
          />
        </div>

        <div className="form-group">
          <label>Adversarial Prompt Payload</label>
          <textarea
            className="form-control"
            rows="5"
            placeholder="Enter adversarial injection, cipher payload, or jailbreak prompt..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label className="toggle-label">
            <div className="toggle-switch">
              <input
                type="checkbox"
                checked={enableGuard}
                onChange={(e) => setEnableGuard(e.target.checked)}
              />
              <span className="slider"></span>
            </div>
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>
              Enable <strong>PromptGuard Defense Firewall</strong>
            </span>
          </label>
        </div>

        {/* Vulnerable Target Demo Toggle */}
        <div className="form-group" style={{ background: useVulnerableTarget ? 'rgba(249,115,22,0.08)' : 'transparent', border: useVulnerableTarget ? '1px solid #f9731640' : '1px solid transparent', borderRadius: '8px', padding: '0.75rem', transition: 'all 0.3s' }}>
          <label className="toggle-label">
            <div className="toggle-switch">
              <input
                type="checkbox"
                checked={useVulnerableTarget}
                onChange={(e) => setUseVulnerableTarget(e.target.checked)}
              />
              <span className="slider" style={useVulnerableTarget ? { background: '#f97316' } : {}}></span>
            </div>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: useVulnerableTarget ? '#f97316' : 'inherit' }}>
              🎯 <strong>Simulate Vulnerable LLM Target</strong>
              <span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 400, color: 'var(--text-muted)', marginTop: '2px' }}>
                Demo mode: routes to unaligned model that complies with attacks
              </span>
            </span>
          </label>
          {useVulnerableTarget && (
            <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#f97316', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              ⚠️ Guard OFF + Vulnerable Target = <strong>💥 JAILBROKEN scenario</strong> &nbsp;|&nbsp; Guard ON = <strong>🛡️ FIREWALL BLOCKED</strong>
            </div>
          )}
        </div>

        <button
          className="btn btn-primary"
          style={{ width: '100%', marginTop: '0.5rem' }}
          onClick={handleSend}
          disabled={loading || !prompt.trim()}
        >
          <Send size={15} />
          {loading ? 'Testing Target & Firewall...' : 'Send Adversarial Attack'}
        </button>
      </div>

      {/* Live Trace & Result View */}
      <div className="card">
        <div className="card-header">
          <h3>Live Inspection & Response Trace</h3>
          {result && (() => {
            const firewallBlocked = result.guard_result?.action === 'block';
            const attackSuccess = result.is_success;
            if (firewallBlocked) {
              return <span className="badge badge-danger">🛡️ FIREWALL BLOCKED</span>;
            } else if (attackSuccess) {
              return <span className="badge" style={{background:'#f97316', color:'#fff', fontWeight:700, fontSize:'0.8rem', padding:'0.35rem 0.75rem'}}>💥 ATTACK SUCCESS — JAILBROKEN</span>;
            } else {
              return <span className="badge badge-success">✅ LLM REFUSED — NOT JAILBROKEN</span>;
            }
          })()}
        </div>

        {!result ? (
          <div className="text-center text-muted" style={{ padding: '3rem 1rem' }}>
            <Terminal size={36} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
            <p>Launch an adversarial payload to inspect the live multi-tier firewall analysis, cipher decoders, and LLM behavior.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Firewall Decision Box */}
            <div className="card" style={{
              background: '#090e1a', padding: '1rem',
              borderLeft: !enableGuard
                ? '3px solid #f97316'
                : result.guard_result?.action === 'block'
                  ? '3px solid #ef4444'
                  : '3px solid #10b981'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <strong style={{ fontSize: '0.85rem', color: '#38bdf8' }}>PromptGuard Firewall Decision:</strong>
                {!enableGuard ? (
                  <span className="badge" style={{ background: '#f97316', color: '#fff' }}>GUARD OFF</span>
                ) : (
                  <span className={`badge ${result.guard_result?.action === 'block' ? 'badge-danger' : 'badge-success'}`}>
                    {(result.guard_result?.action || 'ALLOW').toUpperCase()}
                  </span>
                )}
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0 }}>
                {!enableGuard
                  ? '⚠️ Guard disabled — Prompt sent directly to LLM with NO firewall inspection.'
                  : result.guard_result?.reason || 'Prompt passed all input firewall inspection tiers.'}
              </p>
              {enableGuard && result.guard_result?.detected_ciphers && result.guard_result.detected_ciphers.length > 0 && (
                <div style={{ marginTop: '0.5rem' }}>
                  <span className="badge badge-warning">
                    Decoded Ciphers: {result.guard_result.detected_ciphers.join(', ')}
                  </span>
                </div>
              )}
            </div>

            {/* Target Response Box */}
            <div className="card" style={{ background: '#090e1a', padding: '1rem' }}>
              <div style={{ marginBottom: '0.5rem' }}>
                <strong style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Target LLM Response:</strong>
              </div>
              <pre className="code-box" style={{ margin: 0, whiteSpace: 'pre-wrap', maxHeight: '180px' }}>
                {result.target_response || '[NO RESPONSE]'}
              </pre>
            </div>

            {/* Judge Evaluation */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <span>Judge Verdict: <strong>{result.judge_reason || 'Evaluated'}</strong></span>
              <span>Execution: <strong>{(result.execution_time_seconds || 0).toFixed(3)}s</strong></span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
