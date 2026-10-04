document.addEventListener('DOMContentLoaded', () => {
  // --- Tab Navigation ---
  const navItems = document.querySelectorAll('.nav-item');
  const tabPanes = document.querySelectorAll('.tab-pane');
  const pageTitle = document.getElementById('page-title');
  const pageDesc = document.getElementById('page-desc');

  const tabMeta = {
    'dashboard': { title: 'Executive Security Dashboard', desc: 'Real-time red-teaming metrics, firewall efficacy & audit telemetry.' },
    'playground': { title: 'Red-Team Attack Launcher', desc: 'Interactive adversarial payload testing against target models and firewalls.' },
    'agent-sandbox': { title: 'NovaSupport AI Agent Sandbox', desc: 'Test vulnerable tool-calling AI agent for prompt injections and unauthorized tool use.' },
    'audit-logs': { title: 'Security Audit Trail', desc: 'Comprehensive audit history of all processed prompts, firewall triggers, and LLM judge outcomes.' }
  };

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const tabKey = item.getAttribute('data-tab');
      navItems.forEach(i => i.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      item.classList.add('active');
      const targetPane = document.getElementById(`tab-${tabKey}`);
      if (targetPane) targetPane.classList.add('active');

      if (tabMeta[tabKey]) {
        pageTitle.innerText = tabMeta[tabKey].title;
        pageDesc.innerText = tabMeta[tabKey].desc;
      }

      if (tabKey === 'dashboard' || tabKey === 'audit-logs') {
        loadStats();
        loadLogs();
      }
    });
  });

  // --- API Handlers ---
  async function loadStats() {
    try {
      const res = await fetch('/api/stats');
      if (!res.ok) return;
      const data = await res.json();

      document.getElementById('kpi-total').innerText = data.total_attacks || 0;
      document.getElementById('kpi-blocked').innerText = data.blocked_attacks || 0;
      document.getElementById('kpi-block-rate').innerText = `${data.block_rate || 0}% Block Rate`;
      document.getElementById('kpi-success').innerText = data.successful_attacks || 0;
      document.getElementById('kpi-asr').innerText = `${data.attack_success_rate || 0}% ASR`;
      document.getElementById('kpi-latency').innerText = `${data.avg_response_time_seconds || 0}s`;
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }

  async function loadLogs() {
    try {
      const res = await fetch('/api/logs?limit=50');
      if (!res.ok) return;
      const data = await res.json();
      const logs = data.logs || [];

      // Render Dashboard Table (Top 5)
      const dashBody = document.getElementById('dashboard-logs-body');
      if (dashBody) {
        if (logs.length === 0) {
          dashBody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No audit logs found. Run a benchmark or attack test!</td></tr>`;
        } else {
          dashBody.innerHTML = logs.slice(0, 5).map(log => `
            <tr>
              <td class="text-muted" style="font-size:0.8rem;">${(log.timestamp || '').substring(11, 19)}</td>
              <td><strong>${escapeHtml(log.objective || 'Unknown')}</strong></td>
              <td>
                <span class="badge ${log.guard_action === 'block' ? 'badge-danger' : 'badge-success'}">
                  ${(log.guard_action || 'allow').toUpperCase()}
                </span>
              </td>
              <td style="max-width:250px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                ${escapeHtml(log.target_response || '')}
              </td>
              <td>
                <span class="badge ${log.is_success ? 'badge-danger' : 'badge-success'}">
                  ${log.is_success ? '💥 Jailbreak Success' : '🛡️ Defended'}
                </span>
              </td>
            </tr>
          `).join('');
        }
      }

      // Render Full Logs Table
      const fullBody = document.getElementById('full-logs-body');
      if (fullBody) {
        if (logs.length === 0) {
          fullBody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">No logs recorded yet.</td></tr>`;
        } else {
          fullBody.innerHTML = logs.map(log => `
            <tr>
              <td style="font-family:monospace; font-size:0.8rem;">${(log.attack_id || '').substring(0, 8)}...</td>
              <td class="text-muted" style="font-size:0.8rem;">${log.timestamp}</td>
              <td style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(log.sent_prompt)}</td>
              <td><span class="badge ${log.guard_action === 'block' ? 'badge-danger' : 'badge-success'}">${(log.guard_action || '').toUpperCase()}</span></td>
              <td style="font-size:0.8rem;">${escapeHtml(log.guard_reason || 'N/A')}</td>
              <td style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(log.target_response)}</td>
              <td><span class="badge ${log.is_success ? 'badge-danger' : 'badge-success'}">${log.is_success ? 'FAIL (Jailbroken)' : 'PASS (Defended)'}</span></td>
            </tr>
          `).join('');
        }
      }
    } catch (err) {
      console.error('Failed to load logs:', err);
    }
  }

  // Preset Attack Selector
  const presetSelect = document.getElementById('preset-attack-select');
  const promptInput = document.getElementById('attack-prompt');
  if (presetSelect && promptInput) {
    presetSelect.addEventListener('change', () => {
      if (presetSelect.value) {
        promptInput.value = presetSelect.value;
      }
    });
  }

  // Send Single Attack
  const btnSendAttack = document.getElementById('btn-send-attack');
  const resultView = document.getElementById('attack-result-view');
  if (btnSendAttack) {
    btnSendAttack.addEventListener('click', async () => {
      const prompt = promptInput.value.trim();
      const objective = document.getElementById('attack-objective').value.trim();
      const enableGuard = document.getElementById('toggle-promptguard').checked;

      if (!prompt) {
        alert('Please enter an attack prompt.');
        return;
      }

      btnSendAttack.disabled = true;
      btnSendAttack.innerText = '⏳ Testing Target & Firewall...';
      resultView.innerHTML = '<div class="text-center text-muted">Running firewall inspection and evaluating model behavior...</div>';

      try {
        const res = await fetch('/api/attack/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt: prompt,
            objective: objective,
            enable_promptguard: enableGuard
          })
        });
        const data = await res.json();

        resultView.innerHTML = `
          <div style="display:flex; flex-direction:column; gap:1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <strong>Outcome:</strong>
              <span class="badge ${data.is_success ? 'badge-danger' : 'badge-success'}" style="font-size:0.9rem;">
                ${data.is_success ? '💥 ATTACK SUCCESS (JAILBROKEN)' : '🛡️ ATTACK BLOCKED / DEFENDED'}
              </span>
            </div>
            
            <div class="card" style="background:#090e1a; padding:1rem;">
              <h4 style="font-size:0.85rem; color:var(--primary); margin-bottom:0.5rem;">PromptGuard Firewall Decision:</h4>
              <p><strong>Action:</strong> <span class="badge ${data.guard_result.action === 'block' ? 'badge-danger' : 'badge-success'}">${(data.guard_result.action || '').toUpperCase()}</span></p>
              <p class="text-muted" style="font-size:0.85rem; margin-top:0.25rem;">${escapeHtml(data.guard_result.reason || 'None')}</p>
              ${data.guard_result.detected_ciphers && data.guard_result.detected_ciphers.length > 0 ? 
                `<p style="margin-top:0.25rem;"><span class="badge badge-warning">Decoded Ciphers: ${data.guard_result.detected_ciphers.join(', ')}</span></p>` : ''}
            </div>

            <div class="card" style="background:#090e1a; padding:1rem;">
              <h4 style="font-size:0.85rem; color:var(--text-muted); margin-bottom:0.5rem;">Target Response:</h4>
              <p style="white-space:pre-wrap; font-size:0.9rem;">${escapeHtml(data.target_response || '')}</p>
            </div>

            <div style="font-size:0.8rem; color:var(--text-muted); text-align:right;">
              Judge Verdict: ${escapeHtml(data.judge_reason || 'Evaluated')} | Execution: ${(data.execution_time_seconds || 0).toFixed(3)}s
            </div>
          </div>
        `;
        loadStats();
      } catch (err) {
        resultView.innerHTML = `<div class="badge badge-danger">Error: ${escapeHtml(err.message)}</div>`;
      } finally {
        btnSendAttack.disabled = false;
        btnSendAttack.innerText = '🚀 Send Adversarial Attack';
      }
    });
  }

  // Agent Chat
  const btnSendAgent = document.getElementById('btn-send-agent-msg');
  const agentInput = document.getElementById('agent-user-input');
  const chatMessages = document.getElementById('agent-chat-messages');

  async function sendAgentMessage() {
    const text = agentInput.value.trim();
    if (!text) return;
    const enableGuard = document.getElementById('toggle-agent-guard').checked;

    // Append user message
    chatMessages.innerHTML += `
      <div class="chat-msg user">
        <div class="msg-author">Security Tester</div>
        <div class="msg-bubble">${escapeHtml(text)}</div>
      </div>
    `;
    agentInput.value = '';
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
      const res = await fetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, enable_promptguard: enableGuard })
      });
      const data = await res.json();

      let toolsHtml = '';
      if (data.tools_executed && data.tools_executed.length > 0) {
        toolsHtml = `<div style="margin-top:0.5rem; font-size:0.75rem; color:var(--warning);">🔧 Tools Executed: ${data.tools_executed.map(t => t.tool_name).join(', ')}</div>`;
      }

      chatMessages.innerHTML += `
        <div class="chat-msg bot">
          <div class="msg-author">NovaSupport ${data.blocked ? '<span class="badge badge-danger">Blocked by Guard</span>' : ''}</div>
          <div class="msg-bubble">${escapeHtml(data.response || '')}${toolsHtml}</div>
        </div>
      `;
      chatMessages.scrollTop = chatMessages.scrollHeight;
    } catch (err) {
      chatMessages.innerHTML += `
        <div class="chat-msg bot">
          <div class="msg-bubble badge badge-danger">Error: ${escapeHtml(err.message)}</div>
        </div>
      `;
    }
  }

  if (btnSendAgent && agentInput) {
    btnSendAgent.addEventListener('click', sendAgentMessage);
    agentInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') sendAgentMessage();
    });
  }

  // Run Benchmark Button
  const btnRunBenchmark = document.getElementById('btn-run-benchmark');
  if (btnRunBenchmark) {
    btnRunBenchmark.addEventListener('click', async () => {
      btnRunBenchmark.disabled = true;
      btnRunBenchmark.innerText = '⚡ Running Benchmark Suite...';
      try {
        const res = await fetch('/api/benchmark/run?enable_guard=true', { method: 'POST' });
        const summary = await res.json();
        alert(`Benchmark Completed!\nTotal Attacks: ${summary.total_attacks}\nBlocked: ${summary.blocked_by_guard}\nASR: ${summary.attack_success_rate}%\nAvg Latency: ${summary.avg_latency_ms}ms`);
        loadStats();
        loadLogs();
      } catch (err) {
        alert('Benchmark failed: ' + err.message);
      } finally {
        btnRunBenchmark.disabled = false;
        btnRunBenchmark.innerText = '⚡ Run Full Benchmark';
      }
    });
  }

  // Refresh Button
  const btnRefresh = document.getElementById('btn-refresh-stats');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', () => {
      loadStats();
      loadLogs();
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // Initial Data Load
  loadStats();
  loadLogs();
});
