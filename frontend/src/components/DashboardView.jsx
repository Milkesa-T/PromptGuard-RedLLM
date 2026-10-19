import React, { useEffect, useRef, useState } from 'react';
import { drawBenchmarkCharts } from './dashboard_charts';
import KPICards from './KPICards';
import { RefreshCw, Play, ShieldAlert, Award } from 'lucide-react';

export default function DashboardView({ onNavigate, autoRefresh = false }) {
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [benchmarkLoading, setBenchmarkLoading] = useState(false);
  const [benchmarkResult, setBenchmarkResult] = useState(null);
  const [baselineResult, setBaselineResult] = useState(null);
  const [benchmarkRows, setBenchmarkRows] = useState([]);
  const chartRef = useRef(null);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Error fetching stats:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    if (autoRefresh) {
      const interval = setInterval(fetchStats, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const runBenchmark = async (enableGuard = true) => {
    try {
      setBenchmarkLoading(true);
      const res = await fetch(`/api/benchmark/run?enable_guard=${enableGuard}`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (enableGuard) setBenchmarkResult(data);
      else setBaselineResult(data);

      const resultsRes = await fetch('/api/benchmark/results');
      if (resultsRes.ok) {
        const resultsData = await resultsRes.json();
        setBenchmarkRows(resultsData.results || []);
      }
      fetchStats();
    } catch (err) {
      alert('Benchmark execution failed: ' + err.message);
    } finally {
      setBenchmarkLoading(false);
    }
  };

  const exportResults = async (format) => {
    try {
      const response = await fetch(`/api/benchmark/export?format=${format}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `benchmark_results.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert('Export failed: ' + err.message);
    }
  };

  useEffect(() => {
    if (chartRef.current) {
      drawBenchmarkCharts(chartRef.current, {
        baseline: baselineResult,
        protectedRun: benchmarkResult,
        results: benchmarkRows,
      });
    }
  }, [baselineResult, benchmarkResult, benchmarkRows]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f1f5f9' }}>Real-time Security Telemetry</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Continuous monitoring of prompt injections, guardrail enforcement, and latency overhead.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn btn-secondary" onClick={fetchStats} disabled={loading}>
            <RefreshCw size={15} className={loading ? 'spin-icon' : ''} />
            Refresh Metrics
          </button>
          <button className="btn btn-secondary" onClick={() => runBenchmark(false)} disabled={benchmarkLoading}>
            <Play size={15} />
            Run Baseline
          </button>
          <button className="btn btn-primary" onClick={() => runBenchmark(true)} disabled={benchmarkLoading}>
            <Play size={15} />
            {benchmarkLoading ? 'Running Benchmark...' : 'Run Protected'}
          </button>
        </div>
      </div>

      {/* 4 Dark-Mode KPI Cards */}
      <KPICards stats={stats} />

      {benchmarkResult && (
        <div className="card" style={{ marginBottom: '1.5rem', borderLeft: '4px solid var(--primary)', background: '#0b1324' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Award size={24} color="#38bdf8" />
              <div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Automated Benchmark Complete</h4>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Campaign ID: <code>{benchmarkResult.campaign_id?.slice(0, 8)}</code> | Tested <strong>{benchmarkResult.total_attacks}</strong> attack vectors.
                </p>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <span className="badge badge-success">Blocked: {benchmarkResult.blocked_by_guard}</span>
              <span className="badge badge-danger">ASR: {benchmarkResult.attack_success_rate}%</span>
              <span className="badge badge-primary">{benchmarkResult.avg_latency_ms}ms avg</span>
            </div>
          </div>
        </div>
      )}

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: '0.75rem', alignItems: 'center' }}>
          <div>
            <h3>Benchmark Analysis</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              Compare baseline and protected runs. Run both configurations for a meaningful comparison.
            </p>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            <button className="btn btn-secondary" onClick={() => exportResults('json')}>Export JSON</button>
            <button className="btn btn-secondary" onClick={() => exportResults('csv')}>Export CSV</button>
          </div>
        </div>
        <canvas ref={chartRef} aria-label="Benchmark ASR comparison and attack category charts" role="img" />
      </div>

      {/* Quick Action Launchers */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.25rem' }}>
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '1.5rem' }}>🔴</span>
              <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>Red-Team Attack Launcher</h4>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Simulate direct jailbreaks, Base64/ROT13 obfuscation, and system prompt exfiltration probes against models protected by PromptGuard.
            </p>
          </div>
          <button className="btn btn-secondary" style={{ marginTop: '1.25rem' }} onClick={() => onNavigate('playground')}>
            Open Attack Launcher &rarr;
          </button>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '1.5rem' }}>🤖</span>
              <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>NovaSupport AI Agent Sandbox</h4>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Interactive customer support agent equipped with multi-step tool-calling capabilities and RAG knowledge retrieval.
            </p>
          </div>
          <button className="btn btn-secondary" style={{ marginTop: '1.25rem' }} onClick={() => onNavigate('agent-sandbox')}>
            Launch Agent Sandbox &rarr;
          </button>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '1.5rem' }}>📚</span>
              <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>RAG Knowledge Base & Search</h4>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Inspect indexed grounding documents and test live vector semantic similarity retrieval against corporate policies.
            </p>
          </div>
          <button className="btn btn-secondary" style={{ marginTop: '1.25rem' }} onClick={() => onNavigate('rag-viewer')}>
            Explore Knowledge Base &rarr;
          </button>
        </div>
      </div>
    </div>
  );
}
