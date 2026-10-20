import React, { useState, useRef, useEffect } from 'react';
import { Send, RotateCcw, Wrench, Shield, CheckCircle2, XCircle, AlertTriangle, RefreshCw, Radio } from 'lucide-react';

export default function AgentSandboxView() {
  const [messages, setMessages] = useState([]);
  const [availableTools, setAvailableTools] = useState([]);
  const [securityPolicy, setSecurityPolicy] = useState(null);
  const [input, setInput] = useState('');
  const [enableGuard, setEnableGuard] = useState(true);
  const [enableStreaming, setEnableStreaming] = useState(true);
  const [loading, setLoading] = useState(false);
  const [streamingStatus, setStreamingStatus] = useState('');
  const [loadingHistory, setLoadingHistory] = useState(true);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, streamingStatus]);

  // Dynamically load tools schema and past interactions on mount
  useEffect(() => {
    const initData = async () => {
      try {
        setLoadingHistory(true);
        // 1. Fetch available tools dynamically
        const toolsRes = await fetch('/api/agent/tools');
        let toolNames = [];
        if (toolsRes.ok) {
          const toolsData = await toolsRes.json();
          setAvailableTools(toolsData.tools || []);
          setSecurityPolicy(toolsData.security_policy || null);
          toolNames = (toolsData.tools || []).map(t => t.function?.name || t.name);
        }

        // 2. Fetch past real interaction logs from database
        const historyRes = await fetch('/api/agent/interactions?limit=15');
        if (historyRes.ok) {
          const historyData = await historyRes.json();
          const records = historyData.interactions || [];

          if (records.length > 0) {
            // Reconstruct chat from real SQLite interaction history
            const loadedMessages = [];
            records.reverse().forEach((r) => {
              if (r.user_prompt) {
                loadedMessages.push({
                  role: 'user',
                  author: 'Security Tester',
                  text: r.user_prompt,
                  tools: []
                });
              }
              if (r.bot_response) {
                let parsedTools = [];
                try {
                  parsedTools = typeof r.tools_executed === 'string' ? JSON.parse(r.tools_executed) : (r.tools_executed || []);
                } catch (e) {
                  parsedTools = [];
                }

                loadedMessages.push({
                  role: 'bot',
                  author: `NovaSupport ${r.guard_blocked ? '(Blocked by Guard)' : ''}`,
                  text: r.bot_response,
                  tools: parsedTools,
                  blocked: Boolean(r.guard_blocked)
                });
              }
            });
            setMessages(loadedMessages);
          } else {
            setMessages([
              {
                role: 'bot',
                author: 'NovaSupport Bot',
                text: `NovaSupport AI Agent online. Ready to assist with tools: ${toolNames.join(', ')}.`,
                tools: []
              }
            ]);
          }
        }
      } catch (err) {
        console.error('Failed to initialize Agent Sandbox:', err);
      } finally {
        setLoadingHistory(false);
      }
    };

    initData();
  }, []);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = {
      role: 'user',
      author: 'Security Tester',
      text: text,
      tools: []
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    setStreamingStatus('Initializing connection...');

    // If SSE streaming is enabled
    if (enableStreaming) {
      try {
        const response = await fetch('/api/agent/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            enable_promptguard: enableGuard
          })
        });

        if (!response.ok) {
          throw new Error(`Server returned HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let botText = '';
        let toolsCollected = [];
        let isBlocked = false;

        // Placeholder bot message that streams in real time
        const botMsgIndex = messages.length + 1;
        setMessages(prev => [
          ...prev,
          {
            role: 'bot',
            author: 'NovaSupport Bot (Streaming...)',
            text: '',
            tools: [],
            blocked: false
          }
        ]);

        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split('\n\n');
          buffer = parts.pop() || '';

          for (const block of parts) {
            if (!block.trim()) continue;
            const lines = block.split('\n');
            let event = 'message';
            let dataStr = '';

            for (const line of lines) {
              if (line.startsWith('event: ')) {
                event = line.replace('event: ', '').trim();
              } else if (line.startsWith('data: ')) {
                dataStr = line.replace('data: ', '').trim();
              }
            }

            if (!dataStr) continue;
            try {
              const data = JSON.parse(dataStr);

              if (event === 'status') {
                setStreamingStatus(data.message || 'Processing...');
              } else if (event === 'guard_decision') {
                if (data.blocked) {
                  isBlocked = true;
                  setStreamingStatus(`🛑 Blocked by Guard: ${data.reason}`);
                } else {
                  setStreamingStatus('✅ Guard check passed');
                }
              } else if (event === 'tool_event') {
                toolsCollected.push(data);
                setMessages(prev => {
                  const updated = [...prev];
                  const currentBot = updated[updated.length - 1];
                  if (currentBot && currentBot.role === 'bot') {
                    currentBot.tools = [...toolsCollected];
                  }
                  return updated;
                });
              } else if (event === 'token') {
                botText += data.chunk || '';
                setMessages(prev => {
                  const updated = [...prev];
                  const currentBot = updated[updated.length - 1];
                  if (currentBot && currentBot.role === 'bot') {
                    currentBot.text = botText;
                  }
                  return updated;
                });
              } else if (event === 'done') {
                isBlocked = data.blocked;
                botText = data.response || botText;
                setMessages(prev => {
                  const updated = [...prev];
                  const currentBot = updated[updated.length - 1];
                  if (currentBot && currentBot.role === 'bot') {
                    currentBot.author = `NovaSupport ${isBlocked ? '(Blocked by Guard)' : ''}`;
                    currentBot.text = botText;
                    currentBot.tools = data.tools_executed || toolsCollected;
                    currentBot.blocked = isBlocked;
                  }
                  return updated;
                });
              }
            } catch (jsonErr) {
              // Ignore partial frames
            }
          }
        }
      } catch (err) {
        setMessages(prev => [
          ...prev,
          {
            role: 'bot',
            author: 'Stream Error',
            text: 'Error in live streaming: ' + err.message,
            tools: []
          }
        ]);
      } finally {
        setLoading(false);
        setStreamingStatus('');
      }
      return;
    }

    // Fallback: Synchronous REST turn
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
      setStreamingStatus('');
    }
  };

  const handleReset = async () => {
    try {
      await fetch('/api/agent/reset', { method: 'POST' });
      const toolNames = availableTools.map(t => t.function?.name || t.name);
      setMessages([
        {
          role: 'bot',
          author: 'NovaSupport Bot',
          text: `Conversation context and database reset. Ready to test: ${toolNames.join(', ')}.`,
          tools: []
        }
      ]);
    } catch (err) {
      alert('Reset failed: ' + err.message);
    }
  };

  return (
    <div className="card" style={{ padding: '1.25rem' }}>
      <div className="card-header" style={{ marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h3>NovaSupport Vulnerable AI Agent Sandbox</h3>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', gap: '0.4rem', flexWrap: 'wrap', alignItems: 'center', marginTop: '0.25rem' }}>
            <span>Active Tools ({availableTools.length}):</span>
            {availableTools.map((t, idx) => {
              const name = t.function?.name || t.name;
              const isPrivileged = securityPolicy?.privileged_tools?.includes(name);
              return (
                <code key={idx} style={{ color: isPrivileged ? '#f87171' : '#38bdf8' }}>
                  {name}
                </code>
              );
            })}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          {/* Live Streaming Toggle */}
          <label className="toggle-label" title="Enable real-time SSE token & tool streaming">
            <div className="toggle-switch">
              <input
                type="checkbox"
                checked={enableStreaming}
                onChange={(e) => setEnableStreaming(e.target.checked)}
              />
              <span className="slider"></span>
            </div>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <Radio size={12} color={enableStreaming ? '#38bdf8' : 'var(--text-muted)'} />
              Live SSE Stream
            </span>
          </label>

          {/* PromptGuard Toggle */}
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
          {loadingHistory ? (
            <div className="text-center text-muted py-4">Loading real session history...</div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className={`chat-bubble-row ${msg.role}`}>
                <div className="chat-author">{msg.author}</div>
                <div className={`chat-bubble ${msg.role}`}>
                  {msg.text || (loading && idx === messages.length - 1 ? '...' : '')}

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
                                {t.tool_name || t.name}()
                              </strong>
                              <span className={`badge ${wasBlocked ? 'badge-danger' : 'badge-success'}`} style={{ fontSize: '0.65rem' }}>
                                {wasBlocked ? 'BLOCKED BY POLICY' : 'EXECUTED'}
                              </span>
                            </div>
                            {t.parameters && Object.keys(t.parameters).length > 0 && (
                              <div style={{ color: '#94a3b8', fontSize: '0.7rem' }}>
                                Args: {JSON.stringify(t.parameters)}
                              </div>
                            )}
                            {t.result && (
                              <div style={{ color: '#cbd5e1', fontSize: '0.7rem', marginTop: '0.2rem' }}>
                                Output: {typeof t.result === 'object' ? JSON.stringify(t.result) : String(t.result)}
                              </div>
                            )}
                            {wasBlocked && (t.policy_violation || t.block_reason) && (
                              <div style={{ color: '#f87171', fontSize: '0.7rem', marginTop: '0.2rem' }}>
                                Reason: {t.policy_violation || t.block_reason}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {loading && (
            <div className="chat-bubble-row bot">
              <div className="chat-author">NovaSupport Bot</div>
              <div className="chat-bubble bot" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="pulse-dot"></span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  {streamingStatus || 'Processing message & evaluating tool execution policies...'}
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-bar">
          <input
            type="text"
            placeholder="Test agent with prompt injection, unauthorized refund, or database query..."
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
