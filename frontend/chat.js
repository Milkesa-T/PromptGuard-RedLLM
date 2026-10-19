// frontend/chat.js

document.addEventListener("DOMContentLoaded", () => {
  const chatContainer = document.getElementById("agent-chat-messages");
  const userInput = document.getElementById("agent-user-input");
  const sendBtn = document.getElementById("btn-send-agent-msg");
  const guardToggle = document.getElementById("toggle-agent-guard");

  if (!chatContainer || !userInput || !sendBtn) {
    console.warn("Chat elements not found on the page.");
    return;
  }

  // =========================================================================
  // TASK 1: Chat layout with placeholder messages
  // =========================================================================
  const placeholderMessages = [
    {
      role: "bot",
      author: "NovaSupport Bot",
      text: "Hello! I am NovaSupport for SecureCorp Cloud Solutions. How may I assist you with your orders or account today?",
      tools: []
    },
    {
      role: "user",
      author: "You",
      text: "Can you check order #98421 and its shipping status?",
      tools: []
    },
    {
      role: "bot",
      author: "NovaSupport Bot",
      text: "Order #98421 has been located. It was fulfilled yesterday and is currently in transit with Priority Air.",
      tools: [
        {
          name: "lookup_order",
          status: "success",
          args: { order_id: "98421" },
          result: "Status: In Transit | Carrier: Priority Air"
        }
      ]
    }
  ];

  function renderPlaceholders() {
    chatContainer.innerHTML = "";
    placeholderMessages.forEach((msg) => {
      appendChatMessage(msg.role, msg.author, msg.text, msg.tools);
    });
  }

  // =========================================================================
  // TASK 3: Visual badge cards for tool executions
  // =========================================================================
  function createToolBadgeCard(tool) {
    const card = document.createElement("div");
    card.className = "tool-badge-card";

    const isSuccess = tool.status === "success" || tool.status === "executed" || !tool.status;
    const isBlocked = tool.status === "blocked" || tool.status === "intervened";

    // Styling to match existing dark/modern theme
    card.style.display = "flex";
    card.style.flexDirection = "column";
    card.style.gap = "4px";
    card.style.margin = "6px 0";
    card.style.padding = "6px 10px";
    card.style.borderRadius = "6px";
    card.style.fontSize = "12px";
    card.style.fontFamily = "'JetBrains Mono', monospace";
    card.style.border = isBlocked
      ? "1px solid rgba(239, 68, 68, 0.4)"
      : "1px solid rgba(59, 130, 246, 0.3)";
    card.style.backgroundColor = isBlocked
      ? "rgba(239, 68, 68, 0.1)"
      : "rgba(15, 23, 42, 0.6)";

    const header = document.createElement("div");
    header.style.display = "flex";
    header.style.alignItems = "center";
    header.style.justifyContent = "space-between";
    header.style.gap = "8px";

    const titleSpan = document.createElement("span");
    titleSpan.innerHTML = `⚙️ <strong>${escapeHtml(tool.name || "tool_call")}</strong>`;
    titleSpan.style.color = "#93c5fd";

    const statusBadge = document.createElement("span");
    statusBadge.textContent = (tool.status || "executed").toUpperCase();
    statusBadge.style.fontSize = "10px";
    statusBadge.style.padding = "2px 6px";
    statusBadge.style.borderRadius = "4px";
    statusBadge.style.fontWeight = "600";
    statusBadge.style.backgroundColor = isBlocked ? "#dc2626" : "#2563eb";
    statusBadge.style.color = "#ffffff";

    header.appendChild(titleSpan);
    header.appendChild(statusBadge);
    card.appendChild(header);

    // Detail or payload breakdown
    if (tool.args || tool.result || tool.detail) {
      const detailBody = document.createElement("div");
      detailBody.style.color = "#cbd5e1";
      detailBody.style.fontSize = "11px";
      detailBody.style.wordBreak = "break-word";

      let detailContent = "";
      if (tool.args) {
        detailContent += `<strong>Input:</strong> ${JSON.stringify(tool.args)} `;
      }
      if (tool.result) {
        detailContent += `<strong>Output:</strong> ${escapeHtml(typeof tool.result === "string" ? tool.result : JSON.stringify(tool.result))}`;
      }
      if (!tool.args && !tool.result && tool.detail) {
        detailContent += escapeHtml(tool.detail);
      }

      detailBody.innerHTML = detailContent;
      card.appendChild(detailBody);
    }

    return card;
  }

  function appendChatMessage(role, author, text, tools = []) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-msg ${role}`;

    const authorDiv = document.createElement("div");
    authorDiv.className = "msg-author";
    authorDiv.textContent = author;
    msgDiv.appendChild(authorDiv);

    const bubbleDiv = document.createElement("div");
    bubbleDiv.className = "msg-bubble";
    bubbleDiv.textContent = text;
    msgDiv.appendChild(bubbleDiv);

    // Render tool cards if present
    if (tools && tools.length > 0) {
      const toolContainer = document.createElement("div");
      toolContainer.className = "msg-tool-badges";
      toolContainer.style.marginTop = "6px";

      tools.forEach((tool) => {
        toolContainer.appendChild(createToolBadgeCard(tool));
      });

      msgDiv.appendChild(toolContainer);
    }

    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  // =========================================================================
  // TASK 2: Send button fetch logic to /api/agent/chat
  // =========================================================================
  async function handleSend() {
    const message = userInput.value.trim();
    if (!message) return;

    // Render user message immediately
    appendChatMessage("user", "You", message, []);
    userInput.value = "";
    sendBtn.disabled = true;
    sendBtn.textContent = "Sending...";

    const payload = {
      message: message,
      guard_enabled: guardToggle ? guardToggle.checked : true
    };

    try {
      const response = await fetch("/api/agent/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // Normalize standard response structures
      const reply = data.reply || data.response || data.message || "Agent processed request.";
      const tools = data.tools || data.tool_executions || data.tool_calls || [];

      appendChatMessage("bot", "NovaSupport Bot", reply, tools);

    } catch (err) {
      console.error("Chat API error:", err);
      appendChatMessage(
        "bot",
        "System Error",
        "Unable to reach /api/agent/chat. Ensure the backend server is running.",
        [{ name: "NetworkRequest", status: "blocked", detail: err.message }]
      );
    } finally {
      sendBtn.disabled = false;
      sendBtn.textContent = "Send";
      userInput.focus();
    }
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Bind click & Enter key
  sendBtn.addEventListener("click", handleSend);
  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSend();
    }
  });

  // Load initial placeholder layout
  renderPlaceholders();
});