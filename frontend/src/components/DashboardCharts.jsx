import React, { useState, useEffect } from 'react';
import { TrendingDown, ShieldCheck, Zap, RefreshCw, BarChart2, CheckCircle2, AlertOctagon } from 'lucide-react';

export default function DashboardCharts({ onEvaluationComplete }) {
  const [exemplarStats, setExemplarStats] = useState({ seed_count: 32, dynamic_count: 0, total_active_vectors: 32 });
  const [loading, setLoading] = useState(false);
  const [adaptiveRunning, setAdaptiveRunning] = useState(false);
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [adaptiveComparison, setAdaptiveComparison] = useState(null);

  const fetchExemplarStats = async () => {
    try {
      const res = await fetch('/api/guard/exemplars');
      if (res.ok) {
        const data = await res.json();
        setExemplarStats(data);
      }
    } catch (e) {
      console.error('Failed to fetch exemplar stats:', e);
    }
  };

  useEffect(() => {
    fetchExemplarStats();
  }, []);

  // Run Standard Held-Out Dual-Split Benchmark (ASR + FPR)
  const runHeldOutEval = async () => {
    setLoading(true);
    setAdaptiveComparison(null);
    try {
      const res = await fetch('/api/benchmark/held-out?enable_guard=true&max_attacks=20&max_benign=20', {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        setEvaluationResult(data);
        if (onEvaluationComplete) onEvaluationComplete(data);
      }
    } catch (e) {
      alert('Evaluation failed: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  // Run Closed-Loop 2-Round Adaptive Benchmark
  const runAdaptiveBenchmark = async () => {
    setAdaptiveRunning(true);
    setEvaluationResult(null);
    try {
      const res = await fetch('/api/benchmark/adaptive-rounds?max_samples=15', {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        setAdaptiveComparison(data);
        fetchExemplarStats();
        if (onEvaluationComplete) onEvaluationComplete(data.round_2_adapted);
      }
    } catch (e) {
      alert('Adaptive benchmark failed: ' + e.message);
    } finally {
      setAdaptiveRunning(false);
    }
  };

  // Trigger Closed-Loop Auto-Adapt from recent audit log evasions
  const handleAutoAdapt = async () => {
    try {
      const res = await fetch('/api/guard/exemplars/adapt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: 'audit_log_feedback' })
      });
      if (res.ok) {
        const data = await res.json();
        alert(data.message);
        fetchExemplarStats();
      }
    } catch (e) {
      alert('Auto-adapt failed: ' + e.message);
    }
  };

  const handleResetExemplars = async () => {
    if (!confirm('Reset all dynamic learned exemplars back to baseline 32 seeds?')) return;
    try {
      const res = await fetch('/api/guard/exemplars/reset', { method: 'POST' });
      if (res.ok) {
        fetchExemplarStats();
        setAdaptiveComparison(null);
        setEvaluationResult(null);
      }
    } catch (e) {
      alert('Reset failed: ' + e.message);
    }
  };

  return (
    <div style={{ marginBottom: '2rem' }}>
      {/* Top Banner: Closed-Loop Adaptive Control Panel */}
      <div style={{
        background: 'linear-gradient(135deg, #0b1329 0%, #111d40 100%)',
        borderRadius: '12px',
        border: '1px solid #1e293b',
        padding: '1.25rem 1.5rem',
        marginBottom: '1.5rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Zap size={22} color="#a855f7" />
            <h4 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc' }}>
              Adaptive Defense Feedback Loop
            </h4>
            <span className="badge" style={{ background: '#7e22ce', color: '#fff', fontSize: '0.75rem' }}>
              Self-Learning
            </span>
          </div>
          <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.82rem', color: '#94a3b8' }}>
            Current Vector Index: <strong>32 baseline seeds</strong> + <strong style={{ color: '#a855f7' }}>{exemplarStats.dynamic_count || 0} dynamic exemplars</strong> ({exemplarStats.total_active_vectors || 32} total active)
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
          <button
            className="btn btn-secondary"
            onClick={runHeldOutEval}
            disabled={loading || adaptiveRunning}
            style={{ fontSize: '0.82rem' }}
          >
            <BarChart2 size={14} />
            {loading ? 'Evaluating Held-Out...' : 'Run Held-Out Dual-Split'}
          </button>
          <button
            className="btn btn-primary"
            onClick={runAdaptiveBenchmark}
            disabled={loading || adaptiveRunning}
            style={{ fontSize: '0.82rem', background: '#9333ea', borderColor: '#9333ea' }}
          >
            <TrendingDown size={14} />
            {adaptiveRunning ? 'Running 2-Round Adaptation...' : 'Run Adaptive 2-Round Comparison'}
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleAutoAdapt}
            style={{ fontSize: '0.82rem' }}
            title="Auto-ingest unblocked prompts from recent audit logs"
          >
            <Zap size={14} /> Auto-Adapt
          </button>
          {exemplarStats.dynamic_count > 0 && (
            <button
              className="btn btn-secondary"
              onClick={handleResetExemplars}
              style={{ fontSize: '0.82rem', color: '#ef4444' }}
            >
              Reset Seeds
            </button>
          )}
        </div>
      </div>

      {/* Before / After Progression Display (When Adaptive Comparison is available) */}
      {adaptiveComparison && (
        <div className="card" style={{ background: '#090e1a', border: '1px solid #7e22ce', marginBottom: '1.5rem', padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <div>
              <h4 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f1f5f9', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <TrendingDown color="#10b981" size={22} />
                Closed-Loop Adaptation Results: Before vs. After
              </h4>
              <p style={{ color: '#94a3b8', fontSize: '0.82rem', margin: '0.2rem 0 0 0' }}>
                Quantifying attack neutralization before and after dynamic vector exemplar ingestion.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <span className="badge badge-success" style={{ fontSize: '0.85rem' }}>
                -{adaptiveComparison.comparison.asr_reduction_percentage}% ASR Reduction
              </span>
              <span className="badge badge-primary" style={{ fontSize: '0.85rem' }}>
                +{adaptiveComparison.comparison.exemplars_learned} Exemplars Synthesized
              </span>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
            {/* Round 1 Card */}
            <div style={{ background: '#0f172a', padding: '1.25rem', borderRadius: '8px', border: '1px solid #334155' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 700, color: '#f8fafc', fontSize: '0.9rem' }}>Round 1: Baseline Defense</span>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>32 Seeds</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#f87171' }}>
                  {adaptiveComparison.comparison.round_1_asr}%
                </div>
                <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Attack Success Rate (ASR)</span>
              </div>
              <div style={{ width: '100%', height: '12px', background: '#1e293b', borderRadius: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${adaptiveComparison.comparison.round_1_asr}%`, height: '100%', background: '#ef4444' }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', fontSize: '0.78rem', color: '#94a3b8' }}>
                <span>False Positive Rate: {adaptiveComparison.comparison.round_1_fpr}%</span>
                <span>Blocked: {adaptiveComparison.round_1_baseline.blocked_attacks} / {adaptiveComparison.round_1_baseline.total_attacks}</span>
              </div>
            </div>

            {/* Round 2 Card */}
            <div style={{ background: '#0f172a', padding: '1.25rem', borderRadius: '8px', border: '1px solid #10b981' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 700, color: '#10b981', fontSize: '0.9rem' }}>Round 2: Adapted Defense</span>
                <span style={{ fontSize: '0.75rem', color: '#a855f7' }}>{adaptiveComparison.comparison.total_active_vectors} Active Vectors</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: '#10b981' }}>
                  {adaptiveComparison.comparison.round_2_asr}%
                </div>
                <span style={{ fontSize: '0.8rem', color: '#10b981' }}>Attack Success Rate (ASR)</span>
              </div>
              <div style={{ width: '100%', height: '12px', background: '#1e293b', borderRadius: '6px', overflow: 'hidden' }}>
                <div style={{ width: `${adaptiveComparison.comparison.round_2_asr}%`, height: '100%', background: '#10b981' }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', fontSize: '0.78rem', color: '#94a3b8' }}>
                <span>False Positive Rate: {adaptiveComparison.comparison.round_2_fpr}%</span>
                <span>Blocked: {adaptiveComparison.round_2_adapted.blocked_attacks} / {adaptiveComparison.round_2_adapted.total_attacks}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Held-Out Metrics & Threat Category Breakdown (When Single Eval is available) */}
      {evaluationResult && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
          {/* Dual-Split Security vs Usability Card */}
          <div className="card" style={{ background: '#0b1324' }}>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem', color: '#f1f5f9' }}>
              Security vs. Usability Tradeoff (Held-Out Dual Split)
            </h4>

            {/* ASR Bar */}
            <div style={{ marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '0.35rem' }}>
                <span style={{ color: '#cbd5e1' }}>Attack Success Rate (ASR) — [Lower is Better]</span>
                <span style={{ fontWeight: 700, color: evaluationResult.attack_success_rate < 20 ? '#10b981' : '#ef4444' }}>
                  {evaluationResult.attack_success_rate}%
                </span>
              </div>
              <div style={{ width: '100%', height: '10px', background: '#1e293b', borderRadius: '5px', overflow: 'hidden' }}>
                <div style={{
                  width: `${evaluationResult.attack_success_rate}%`,
                  height: '100%',
                  background: evaluationResult.attack_success_rate < 20 ? '#10b981' : '#ef4444'
                }} />
              </div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
                Blocked {evaluationResult.blocked_attacks} of {evaluationResult.total_attacks} hostile attacks.
              </div>
            </div>

            {/* FPR Bar */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '0.35rem' }}>
                <span style={{ color: '#cbd5e1' }}>False Positive Rate (FPR) — [Usability Preservation]</span>
                <span style={{ fontWeight: 700, color: evaluationResult.false_positive_rate < 5 ? '#10b981' : '#f59e0b' }}>
                  {evaluationResult.false_positive_rate}%
                </span>
              </div>
              <div style={{ width: '100%', height: '10px', background: '#1e293b', borderRadius: '5px', overflow: 'hidden' }}>
                <div style={{
                  width: `${evaluationResult.false_positive_rate}%`,
                  height: '100%',
                  background: evaluationResult.false_positive_rate < 5 ? '#10b981' : '#f59e0b'
                }} />
              </div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
                Accurately passed {evaluationResult.total_benign - evaluationResult.false_positives} of {evaluationResult.total_benign} legitimate customer queries.
              </div>
            </div>
          </div>

          {/* Per-Category Threat Breakdown */}
          <div className="card" style={{ background: '#0b1324' }}>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem', color: '#f1f5f9' }}>
              Threat Category Efficacy Breakdown
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              {Object.entries(evaluationResult.per_category || {}).map(([cat, data]) => (
                <div key={cat} style={{ fontSize: '0.8rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                    <span style={{ color: '#94a3b8', textTransform: 'capitalize' }}>
                      {cat.replace(/_/g, ' ')}
                    </span>
                    <span style={{ fontWeight: 600, color: data.asr === 0 ? '#10b981' : (data.asr < 30 ? '#f59e0b' : '#ef4444') }}>
                      ASR: {data.asr}% ({data.blocked}/{data.total} blocked)
                    </span>
                  </div>
                  <div style={{ width: '100%', height: '6px', background: '#1e293b', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{
                      width: `${100 - data.asr}%`,
                      height: '100%',
                      background: data.asr === 0 ? '#10b981' : '#38bdf8'
                    }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
