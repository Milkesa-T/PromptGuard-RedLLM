import React from 'react';
import { Target, ShieldCheck, Flame, Zap } from 'lucide-react';

export default function KPICards({ stats = {} }) {
  const total = stats.total_attacks || 0;
  const blocked = stats.blocked_attacks || 0;
  const success = stats.successful_attacks || 0;
  const blockRate = stats.block_rate || 0;
  const asr = stats.attack_success_rate || 0;
  const latency = stats.avg_response_time_seconds || 0;
  const agentInteractions = stats.total_agent_interactions || 0;

  return (
    <div className="kpi-grid">
      {/* KPI 1: Total Attacks Tested */}
      <div className="kpi-card">
        <div className="kpi-card-header">
          <span className="kpi-label">Total Attacks Tested</span>
          <div className="kpi-icon-wrap" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
            <Target size={20} />
          </div>
        </div>
        <div className="kpi-value">{total.toLocaleString()}</div>
        <div className="kpi-footer">
          <span style={{ color: 'var(--text-muted)' }}>{agentInteractions} agent interactions</span>
        </div>
      </div>

      {/* KPI 2: Firewall Interventions */}
      <div className="kpi-card">
        <div className="kpi-card-header">
          <span className="kpi-label">Firewall Interventions</span>
          <div className="kpi-icon-wrap" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>
            <ShieldCheck size={20} />
          </div>
        </div>
        <div className="kpi-value" style={{ color: '#34d399' }}>{blocked.toLocaleString()}</div>
        <div className="kpi-progress-bar">
          <div
            className="kpi-progress-fill"
            style={{ width: `${Math.min(blockRate, 100)}%`, background: 'linear-gradient(90deg, #059669, #10b981)' }}
          />
        </div>
        <div className="kpi-footer">
          <span style={{ color: '#34d399', fontWeight: 600 }}>{blockRate}% Block Rate</span>
        </div>
      </div>

      {/* KPI 3: Successful Jailbreaks */}
      <div className="kpi-card">
        <div className="kpi-card-header">
          <span className="kpi-label">Successful Jailbreaks</span>
          <div className="kpi-icon-wrap" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444' }}>
            <Flame size={20} />
          </div>
        </div>
        <div className="kpi-value" style={{ color: '#f87171' }}>{success.toLocaleString()}</div>
        <div className="kpi-progress-bar">
          <div
            className="kpi-progress-fill"
            style={{ width: `${Math.min(asr, 100)}%`, background: 'linear-gradient(90deg, #dc2626, #ef4444)' }}
          />
        </div>
        <div className="kpi-footer">
          <span style={{ color: '#f87171', fontWeight: 600 }}>{asr}% Attack Success Rate (ASR)</span>
        </div>
      </div>

      {/* KPI 4: Average Defense Latency */}
      <div className="kpi-card">
        <div className="kpi-card-header">
          <span className="kpi-label">Average Latency</span>
          <div className="kpi-icon-wrap" style={{ background: 'rgba(129, 140, 248, 0.15)', color: '#818cf8' }}>
            <Zap size={20} />
          </div>
        </div>
        <div className="kpi-value">{latency.toFixed(3)}s</div>
        <div className="kpi-footer">
          <span style={{ color: 'var(--text-muted)' }}>
            ~{Math.round(latency * 1000)}ms inspection + inference
          </span>
        </div>
      </div>
    </div>
  );
}
