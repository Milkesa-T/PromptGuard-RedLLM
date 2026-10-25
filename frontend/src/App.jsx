import React, { useState, useEffect } from 'react';
import {
  Shield,
  LayoutDashboard,
  Flame,
  Bot,
  BookOpen,
  FileSpreadsheet,
  Activity
} from 'lucide-react';
import DashboardView from './components/DashboardView';
import PlaygroundView from './components/PlaygroundView';
import AgentSandboxView from './components/AgentSandboxView';
import RAGViewerView from './components/RAGViewerView';
import AuditLogsView from './components/AuditLogsView';

const TABS = [
  {
    id: 'dashboard',
    label: 'Security Dashboard',
    icon: LayoutDashboard,
    title: 'Executive Security Dashboard',
    desc: 'Real-time red-teaming metrics, firewall efficacy & audit telemetry.'
  },
  {
    id: 'playground',
    label: 'Red-Team Launcher',
    icon: Flame,
    title: 'Red-Team Attack Launcher',
    desc: 'Interactive adversarial payload testing against target models and firewalls.'
  },
  {
    id: 'agent-sandbox',
    label: 'AI Agent Sandbox',
    icon: Bot,
    title: 'NovaSupport AI Agent Sandbox',
    desc: 'Test vulnerable tool-calling AI agent for prompt injections and unauthorized tool use.'
  },
  {
    id: 'rag-viewer',
    label: 'RAG Knowledge Base',
    icon: BookOpen,
    title: 'RAG Knowledge & Search Explorer',
    desc: 'Inspect grounded documentation chunks and test live vector similarity retrieval.'
  },
  {
    id: 'audit-logs',
    label: 'Audit Trail',
    icon: FileSpreadsheet,
    title: 'Security Audit Trail',
    desc: 'Comprehensive forensic archive of all processed prompts, firewall triggers, and LLM judge outcomes.'
  }
];

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const currentTabMeta = TABS.find(t => t.id === activeTab) || TABS[0];

  return (
    <div className="app-layout">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">🛡️</div>
          <div>
            <h1 className="brand-title">PromptGuard</h1>
            <span className="brand-subtitle">RedLLM Framework</span>
          </div>
        </div>

        <nav className="nav-menu">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                className={`nav-item ${isActive ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <span className="nav-icon">
                  <Icon size={18} />
                </span>
                {tab.label}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="status-indicator">
            <span className="pulse-dot"></span>
            <span>FastAPI Security Engine Online</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        <header className="topbar">
          <div className="page-title-group">
            <h2>{currentTabMeta.title}</h2>
            <p>{currentTabMeta.desc}</p>
          </div>

          <div className="topbar-actions">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#0a0e17', padding: '0.4rem 0.8rem', borderRadius: '8px', border: '1px solid var(--border-color)', fontSize: '0.8rem' }}>
              <span className={`pulse-dot ${autoRefresh ? '' : 'danger'}`}></span>
              <label style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.4rem', userSelect: 'none' }}>
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                />
                Live Auto-Refresh (5s)
              </label>
            </div>
          </div>
        </header>

        <div className="content-body">
          {activeTab === 'dashboard' && <DashboardView onNavigate={(tab) => setActiveTab(tab)} autoRefresh={autoRefresh} />}
          {activeTab === 'playground' && <PlaygroundView />}
          {activeTab === 'agent-sandbox' && <AgentSandboxView />}
          {activeTab === 'rag-viewer' && <RAGViewerView />}
          {activeTab === 'audit-logs' && <AuditLogsView autoRefresh={autoRefresh} />}
        </div>
      </main>
    </div>
  );
}
