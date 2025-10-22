const API_BASE = "http://localhost:8000";
let sessionId = "session-" + Date.now();
let queryCount = 0;
let latencies = [];

document.getElementById("send-btn").addEventListener("click", sendMessage);
document.getElementById("user-input").addEventListener("keypress", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

async function sendMessage() {
  const input = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const message = input.value.trim();
  if (!message) return;

  input.disabled = true;
  sendBtn.disabled = true;
  addMessage("user", message);
  input.value = "";

  const loadingMsg = addMessage("assistant", '<span class="loading">Thinking...</span>');

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    const data = await response.json();
    removeMessage(loadingMsg);

    let content = `<div class="message-text">${escapeHtml(data.reply)} <span class="latency">${data.latency_ms}ms</span></div>`;

    if (data.citations?.length) {
      content += '<div class="citations">📚 Sources: ';
      data.citations.forEach(c => content += `<span class="citation-badge" title="Score: ${c.score}">${c.id}</span>`);
      content += "</div>";
    }

    if (data.tool_calls?.length) {
      data.tool_calls.forEach(tc => {
        content += `<div class="tool-call"><span class="tool-name">🛠️ ${tc.name}</span><br>→ ${JSON.stringify(tc.result)}</div>`;
      });
    }

    if (data.plan_steps?.length) {
      content += '<div class="plan-steps">';
      data.plan_steps.forEach(step => content += `<span class="plan-step">${step.intent}: ${step.latency_ms}ms</span>`);
      content += "</div>";
    }

    addMessage("assistant", content);

    queryCount++;
    latencies.push(data.latency_ms);
    updateStats();
  } catch (error) {
    removeMessage(loadingMsg);
    addMessage("assistant", `<div class="message-text">❌ Error: ${escapeHtml(error.message)}</div>`);
  } finally {
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
  }
}

function addMessage(role, content) {
  const messagesDiv = document.getElementById("messages");
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${role}`;
  const contentDiv = document.createElement("div");
  contentDiv.className = "message-content";
  contentDiv.innerHTML = content;
  msgDiv.appendChild(contentDiv);
  messagesDiv.appendChild(msgDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
  return msgDiv;
}

function removeMessage(element) {
  element?.parentNode?.removeChild(element);
}

function updateStats() {
  document.getElementById("query-count").textContent = queryCount;
  if (latencies.length) {
    const avg = Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length);
    document.getElementById("avg-latency").textContent = avg + "ms";
    const sorted = [...latencies].sort((a, b) => a - b);
    const p95 = sorted[Math.floor(sorted.length * 0.95)] || sorted[sorted.length - 1];
    document.getElementById("p95-latency").textContent = Math.round(p95) + "ms";
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Quick test functions
async function runTest1() {
  document.getElementById("user-input").value = "What's our late policy and can you book Chen tomorrow at 10:30 in Midtown?";
  await sendMessage();
  setTimeout(() => { document.getElementById("user-input").value = "Make it 11:00 instead"; sendMessage(); }, 2000);
}
function runTest2() { document.getElementById("user-input").value = "Where do patients park?"; sendMessage(); }
function runTest3() { document.getElementById("user-input").value = "Schedule Rivera Monday 9am at Midtown"; sendMessage(); }

// Logging
console.log("%c🚦 FastLane RAG Orchestrator", "font-size: 16px; font-weight: bold; color: #667eea;");
console.log("Test commands: runTest1(), runTest2(), runTest3()");
console.log("Session ID:", sessionId);
