import React, { useState, useRef, useEffect } from 'react';
import { Send, RotateCcw, Wrench, Shield, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

export default function AgentSandboxView() {
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      author: 'NovaSupport Bot',
      text: 'Hello! I am NovaSupport for SecureCorp Cloud Solutions. How may I assist you with your orders or account today?',
      tools: []
    }
  ]);
  const [input, setInput] = useState('');
  const [enableGuard, setEnableGuard] = useState(true);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    // Add user message immediately
    const userMsg = {
      role: 'user',
      author: 'Security Tester',
      text: text,
      tools: []
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          enable_promptguard: enableGuard
        })
      });

      if (res.ok) {
        const data = await res.json();
        const botMsg = {
          role: 'bot',
          author: `NovaSupport ${data.blocked ? '(Blocked by Guard)' : ''}`,
          text: data.response || 'Agent processed request.',
          tools: data.tools_executed || [],
          blocked: data.blocked
        };
        setMessages(prev => [...prev, botMsg]);
      } else {
        throw new Error(`Server returned ${res.status}`);
      }
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: 'bot',
          author: 'System Error',
          text: 'Error communicating with /api/agent/chat: ' + err.message,
          tools: []
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    try {
      await fetch('/api/agent/reset', { method: 'POST' });
      setMessages([
        {
          role: 'bot',
          author: 'NovaSupport Bot',
          text: 'Agent conversation history and mock database successfully reset. How may I assist you?',
          tools: []
        }
      ]);
    } catch (err) {
      alert('Reset failed: ' + err.message);
    }
  };

  return (
    <div className="card" style={{ padding: '1.25rem' }}>
      <div className="card-header" style={{ marginBottom: '1rem' }}>
        <div>
          <h3>NovaSupport Vulnerable AI Agent Sandbox</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Equipped with simulated tools: <code>lookup_customer</code>, <code>lookup_order</code>, <code>process_refund</code>, <code>execute_internal_query</code>
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <label className="toggle-label">
            <div className="toggle-switch">
              <input
                type="checkbox"
                checked={enableGuard}
                onChange={(e) => setEnableGuard(e.target.checked)}
              />
              <span className="slider"></span>
            </div>
            <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>PromptGuard Shield</span>
          </label>
          <button className="btn btn-xs btn-secondary" onClick={handleReset} title="Reset Agent Context">
            <RotateCcw size={13} /> Reset
          </button>
        </div>
      </div>

      <div className="chat-window">
        <div className="chat-messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`chat-bubble-row ${msg.role}`}>
              <div className="chat-author">{msg.author}</div>
              <div className={`chat-bubble ${msg.role}`}>
                {msg.text}

                {/* Render Tool Execution Badges */}
                {msg.tools && msg.tools.length > 0 && (
                  <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                    <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--primary)', fontWeight: 600, letterSpacing: '0.04em' }}>
                      🔧 Tools Executed ({msg.tools.length}):
                    </div>
                    {msg.tools.map((t, tIdx) => {
                      const wasBlocked = t.was_blocked || t.status === 'blocked';
                      return (
                        <div key={tIdx} className="tool-badge-card" style={{ borderLeft: wasBlocked ? '3px solid #ef4444' : '3px solid #10b981' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                            <strong style={{ color: wasBlocked ? '#f87171' : '#38bdf8' }}>
                              {t.tool_name}()
                            </strong>
                            <span className={`badge ${wasBlocked ? 'badge-danger' : 'badge-success'}`} style={{ fontSize: '0.65rem' }}>
                              {wasBlocked ? 'BLOCKED BY POLICY' : 'EXECUTED'}
                            </span>
                          </div>
                          {t.arguments && Object.keys(t.arguments).length > 0 && (
                            <div style={{ color: '#94a3b8', fontSize: '0.7rem' }}>
                              Args: {JSON.stringify(t.arguments)}
                            </div>
                          )}
                          {t.output && (
                            <div style={{ color: '#cbd5e1', fontSize: '0.7rem', marginTop: '0.2rem' }}>
                              Output: {typeof t.output === 'object' ? JSON.stringify(t.output) : String(t.output)}
                            </div>
                          )}
                          {wasBlocked && t.block_reason && (
                            <div style={{ color: '#f87171', fontSize: '0.7rem', marginTop: '0.2rem' }}>
                              Reason: {t.block_reason}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="chat-bubble-row bot">
              <div className="chat-author">NovaSupport Bot</div>
              <div className="chat-bubble bot" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="pulse-dot"></span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Processing message & evaluating tool execution policies...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-bar">
          <input
            type="text"
            placeholder="Test agent with prompt injection, unauthorized refund, or database dump..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            disabled={loading}
          />
          <button className="btn btn-primary" onClick={handleSend} disabled={loading || !input.trim()}>
            <Send size={15} /> Send
          </button>
        </div>
      </div>
    </div>
  );
}
