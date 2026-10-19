/**
 * PromptGuard / RedLLM — Security Telemetry & Dashboard Controller
 * Member 6 (Evaluation, Telemetry & UI)
 * 
 * Features:
 *  1. 4 Dark-Mode KPI Cards with live metric updates & visual progress bars
 *  2. Filterable Audit Table with rich security badges, live search & inspection modal
 *  3. Live Refresh button with auto-refresh interval & CSV export integration
 */

class DashboardController {
  constructor() {
    this.logs = [];
    this.stats = {};
    this.currentActionFilter = 'all';
    this.currentOutcomeFilter = 'all';
    this.searchQuery = '';
    this.currentLimit = 50;
    this.autoRefreshTimer = null;
    this.isAutoRefreshActive = false;

    this.init();
  }

  init() {
    this.bindEvents();
    this.loadStats();
    this.loadLogs();
  }

  bindEvents() {
    // 1. Live Refresh Button (Topbar & Dashboard)
    const refreshBtn = document.getElementById('btn-refresh-stats');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.refreshAll(true));
    }

    const tableRefreshBtn = document.getElementById('btn-refresh-table');
    if (tableRefreshBtn) {
      tableRefreshBtn.addEventListener('click', () => this.refreshAll(true));
    }

    // 2. Auto-Refresh Toggle
    const autoRefreshToggle = document.getElementById('toggle-auto-refresh');
    if (autoRefreshToggle) {
      autoRefreshToggle.addEventListener('change', (e) => {
        this.toggleAutoRefresh(e.target.checked);
      });
    }

    // 3. CSV Download Buttons
    const csvBtn = document.getElementById('btn-download-csv');
    if (csvBtn) {
      csvBtn.addEventListener('click', () => this.downloadCSV());
    }

    const exportBtn = document.getElementById('btn-export-logs');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => this.downloadCSV());
    }

    const exportJsonBtn = document.getElementById('btn-export-json');
    if (exportJsonBtn) {
      exportJsonBtn.addEventListener('click', () => this.downloadJSON());
    }

    // 4. Action Filter Pills
    const filterPills = document.querySelectorAll('.action-filter-pill');
    filterPills.forEach(pill => {
      pill.addEventListener('click', () => {
        filterPills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        this.currentActionFilter = pill.getAttribute('data-action') || 'all';
        this.renderFilteredLogs();
      });
    });

    // 5. Outcome Filter Dropdown
    const outcomeSelect = document.getElementById('filter-outcome-select');
    if (outcomeSelect) {
      outcomeSelect.addEventListener('change', (e) => {
        this.currentOutcomeFilter = e.target.value;
        this.renderFilteredLogs();
      });
    }

    // 6. Real-time Search Input
    const searchInput = document.getElementById('search-audit-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.trim().toLowerCase();
        this.renderFilteredLogs();
      });
    }

    // 7. Limit Selector
    const limitSelect = document.getElementById('audit-limit-select');
    if (limitSelect) {
      limitSelect.addEventListener('change', (e) => {
        this.currentLimit = parseInt(e.target.value, 10) || 50;
        this.loadLogs();
      });
    }

    // 8. Modal Close Handling
    const modalClose = document.getElementById('modal-close-btn');
    const modalBackdrop = document.getElementById('audit-detail-modal');
    if (modalClose && modalBackdrop) {
      modalClose.addEventListener('click', () => this.closeModal());
      modalBackdrop.addEventListener('click', (e) => {
        if (e.target === modalBackdrop) this.closeModal();
      });
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') this.closeModal();
      });
    }
  }

  // --- API Fetch Methods ---

  async loadStats() {
    try {
      const res = await fetch('/api/stats');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      this.stats = data;
      this.renderKPICards(data);
    } catch (err) {
      console.error('Failed to load telemetry stats:', err);
    }
  }

  async loadLogs() {
    try {
      const url = `/api/logs?limit=${this.currentLimit}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      this.logs = data.logs || [];
      this.renderFilteredLogs();
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    }
  }

  async refreshAll(showAnimation = false) {
    const refreshBtn = document.getElementById('btn-refresh-stats');
    const tableRefreshBtn = document.getElementById('btn-refresh-table');

    if (showAnimation) {
      if (refreshBtn) refreshBtn.classList.add('spin-icon');
      if (tableRefreshBtn) tableRefreshBtn.classList.add('spin-icon');
    }

    try {
      await Promise.all([this.loadStats(), this.loadLogs()]);
    } finally {
      if (showAnimation) {
        setTimeout(() => {
          if (refreshBtn) refreshBtn.classList.remove('spin-icon');
          if (tableRefreshBtn) tableRefreshBtn.classList.remove('spin-icon');
        }, 500);
      }
    }
  }

  toggleAutoRefresh(enable) {
    this.isAutoRefreshActive = enable;
    const pulseIndicator = document.getElementById('live-stream-pulse');

    if (enable) {
      if (pulseIndicator) pulseIndicator.classList.add('active');
      this.autoRefreshTimer = setInterval(() => {
        this.refreshAll(false);
      }, 5000);
    } else {
      if (pulseIndicator) pulseIndicator.classList.remove('active');
      if (this.autoRefreshTimer) {
        clearInterval(this.autoRefreshTimer);
        this.autoRefreshTimer = null;
      }
    }
  }

  // --- KPI Cards Rendering ---

  renderKPICards(stats) {
    const total = stats.total_attacks || 0;
    const blocked = stats.blocked_attacks || 0;
    const success = stats.successful_attacks || 0;
    const blockRate = stats.block_rate || 0;
    const asr = stats.attack_success_rate || 0;
    const latency = stats.avg_response_time_seconds || 0;
    const agentInteractions = stats.total_agent_interactions || 0;

    // Card 1: Total Attacks Tested
    const totalEl = document.getElementById('kpi-total');
    if (totalEl) totalEl.innerText = total.toLocaleString();
    const totalSub = document.getElementById('kpi-total-sub');
    if (totalSub) totalSub.innerText = `${agentInteractions} agent interactions`;

    // Card 2: Firewall Interventions (Block Rate)
    const blockedEl = document.getElementById('kpi-blocked');
    if (blockedEl) blockedEl.innerText = blocked.toLocaleString();
    const blockRateEl = document.getElementById('kpi-block-rate');
    if (blockRateEl) blockRateEl.innerText = `${blockRate}% Block Rate`;
    const blockBar = document.getElementById('kpi-block-bar');
    if (blockBar) blockBar.style.width = `${Math.min(blockRate, 100)}%`;

    // Card 3: Successful Jailbreaks (ASR)
    const successEl = document.getElementById('kpi-success');
    if (successEl) successEl.innerText = success.toLocaleString();
    const asrEl = document.getElementById('kpi-asr');
    if (asrEl) asrEl.innerText = `${asr}% ASR`;
    const asrBar = document.getElementById('kpi-asr-bar');
    if (asrBar) asrBar.style.width = `${Math.min(asr, 100)}%`;

    // Card 4: Average Defense Latency
    const latencyEl = document.getElementById('kpi-latency');
    if (latencyEl) latencyEl.innerText = `${latency.toFixed(3)}s`;
    const latencySub = document.getElementById('kpi-latency-sub');
    if (latencySub) {
      const ms = Math.round(latency * 1000);
      latencySub.innerText = `~${ms}ms inspection + LLM`;
    }
  }

  // --- Audit Table & Filtering ---

  getFilteredLogs() {
    return this.logs.filter(log => {
      // 1. Action filter
      if (this.currentActionFilter !== 'all') {
        const action = (log.guard_action || '').toLowerCase();
        if (action !== this.currentActionFilter) return false;
      }

      // 2. Outcome filter
      if (this.currentOutcomeFilter !== 'all') {
        const isSuccess = Boolean(log.is_success);
        if (this.currentOutcomeFilter === 'defended' && isSuccess) return false;
        if (this.currentOutcomeFilter === 'jailbreak' && !isSuccess) return false;
      }

      // 3. Search query
      if (this.searchQuery) {
        const haystack = [
          log.attack_id || '',
          log.objective || '',
          log.sent_prompt || '',
          log.guard_reason || '',
          log.target_response || '',
          log.judge_reason || ''
        ].join(' ').toLowerCase();

        if (!haystack.includes(this.searchQuery)) return false;
      }

      return true;
    });
  }

  renderFilteredLogs() {
    const filtered = this.getFilteredLogs();

    // 1. Render Dashboard Table (recent view)
    const dashBody = document.getElementById('dashboard-logs-body');
    if (dashBody) {
      if (filtered.length === 0) {
        dashBody.innerHTML = `
          <tr>
            <td colspan="6" class="text-center text-muted py-4">
              <div style="font-size:1.5rem; margin-bottom:0.5rem;">🔍</div>
              No audit records match the current filters.
            </td>
          </tr>
        `;
      } else {
        dashBody.innerHTML = filtered.slice(0, 10).map(log => this.buildTableRow(log, false)).join('');
      }
    }

    // 2. Render Full Logs Table (Tab 4)
    const fullBody = document.getElementById('full-logs-body');
    if (fullBody) {
      if (filtered.length === 0) {
        fullBody.innerHTML = `
          <tr>
            <td colspan="7" class="text-center text-muted py-4">
              <div style="font-size:1.5rem; margin-bottom:0.5rem;">📂</div>
              No security audit logs found for the applied filter criteria.
            </td>
          </tr>
        `;
      } else {
        fullBody.innerHTML = filtered.map(log => this.buildTableRow(log, true)).join('');
      }
    }

    // Update result counts badge
    const countBadge = document.getElementById('audit-count-badge');
    if (countBadge) {
      countBadge.innerText = `${filtered.length} / ${this.logs.length} records`;
    }

    // Attach row click listeners for inspection modal
    this.attachRowClickEvents();
  }

  buildTableRow(log, isFullView = false) {
    const action = (log.guard_action || 'allow').toLowerCase();
    const actionBadge = this.getActionBadge(action);
    const outcomeBadge = this.getOutcomeBadge(Boolean(log.is_success));
    const timeFormatted = this.formatTimestamp(log.timestamp);
    const latencyVal = log.execution_time_seconds ? `${Number(log.execution_time_seconds).toFixed(3)}s` : '—';

    if (!isFullView) {
      return `
        <tr class="audit-row" data-id="${this.escapeHtml(log.attack_id || '')}">
          <td class="text-muted font-mono" style="font-size:0.8rem;">${timeFormatted}</td>
          <td><span class="badge-objective">${this.escapeHtml(log.objective || 'Default')}</span></td>
          <td>${actionBadge}</td>
          <td class="truncate-cell">${this.escapeHtml(log.sent_prompt || '')}</td>
          <td>${outcomeBadge}</td>
          <td><span class="badge-latency">⚡ ${latencyVal}</span></td>
        </tr>
      `;
    }

    return `
      <tr class="audit-row" data-id="${this.escapeHtml(log.attack_id || '')}">
        <td class="font-mono text-muted" style="font-size:0.75rem;">${(log.attack_id || '').substring(0, 8)}...</td>
        <td class="text-muted font-mono" style="font-size:0.8rem;">${timeFormatted}</td>
        <td><span class="badge-objective">${this.escapeHtml(log.objective || 'N/A')}</span></td>
        <td>${actionBadge}</td>
        <td class="truncate-cell">${this.escapeHtml(log.sent_prompt || '')}</td>
        <td>${outcomeBadge}</td>
        <td><span class="badge-latency">⚡ ${latencyVal}</span></td>
      </tr>
    `;
  }

  getActionBadge(action) {
    switch (action) {
      case 'block':
        return `<span class="badge badge-action-block"><span class="badge-dot"></span>🛡️ BLOCKED</span>`;
      case 'sanitize':
        return `<span class="badge badge-action-sanitize"><span class="badge-dot"></span>🧹 SANITIZED</span>`;
      case 'allow':
      default:
        return `<span class="badge badge-action-allow"><span class="badge-dot"></span>✅ ALLOWED</span>`;
    }
  }

  getOutcomeBadge(isSuccess) {
    if (isSuccess) {
      return `<span class="badge badge-outcome-jailbreak">💥 JAILBROKEN</span>`;
    }
    return `<span class="badge badge-outcome-defended">🛡️ DEFENDED</span>`;
  }

  formatTimestamp(ts) {
    if (!ts) return 'N/A';
    try {
      const date = new Date(ts);
      if (!isNaN(date.getTime())) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      }
    } catch {
      // fallback
    }
    return ts.length > 8 ? ts.substring(11, 19) : ts;
  }

  attachRowClickEvents() {
    const rows = document.querySelectorAll('.audit-row');
    rows.forEach(row => {
      row.addEventListener('click', () => {
        const attackId = row.getAttribute('data-id');
        const record = this.logs.find(l => l.attack_id === attackId);
        if (record) {
          this.openModal(record);
        }
      });
    });
  }

  // --- Inspection Modal ---

  openModal(log) {
    const modal = document.getElementById('audit-detail-modal');
    if (!modal) return;

    const action = (log.guard_action || 'allow').toLowerCase();
    const isSuccess = Boolean(log.is_success);

    document.getElementById('modal-attack-id').innerText = log.attack_id || 'N/A';
    document.getElementById('modal-timestamp').innerText = log.timestamp || 'N/A';
    document.getElementById('modal-objective').innerText = log.objective || 'N/A';
    document.getElementById('modal-action-badge').innerHTML = this.getActionBadge(action);
    document.getElementById('modal-outcome-badge').innerHTML = this.getOutcomeBadge(isSuccess);
    document.getElementById('modal-latency').innerText = `${Number(log.execution_time_seconds || 0).toFixed(3)}s`;

    document.getElementById('modal-sent-prompt').innerText = log.sent_prompt || '—';
    document.getElementById('modal-guard-reason').innerText = log.guard_reason || 'No firewall intervention triggered (traffic deemed safe).';
    document.getElementById('modal-target-response').innerText = log.target_response || '—';
    document.getElementById('modal-judge-reason').innerText = log.judge_reason || '—';

    // Copy prompt button handler
    const copyBtn = document.getElementById('modal-copy-prompt');
    if (copyBtn) {
      copyBtn.onclick = () => {
        navigator.clipboard.writeText(log.sent_prompt || '');
        copyBtn.innerText = '✅ Copied!';
        setTimeout(() => { copyBtn.innerText = '📋 Copy Prompt'; }, 2000);
      };
    }

    modal.classList.add('active');
  }

  closeModal() {
    const modal = document.getElementById('audit-detail-modal');
    if (modal) modal.classList.remove('active');
  }

  // --- Export Functionality ---

  downloadCSV() {
    // Direct link trigger to /api/logs/export
    const link = document.createElement('a');
    link.href = '/api/logs/export';
    link.setAttribute('download', 'security_audit_logs.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  downloadJSON() {
    const filtered = this.getFilteredLogs();
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(filtered, null, 2));
    const link = document.createElement('a');
    link.href = dataStr;
    link.setAttribute('download', `security_audit_logs_${new Date().toISOString().substring(0, 10)}.json`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

// Instantiate on DOM load
let dashboardManager = null;
document.addEventListener('DOMContentLoaded', () => {
  dashboardManager = new DashboardController();
  window.dashboardManager = dashboardManager;
});
