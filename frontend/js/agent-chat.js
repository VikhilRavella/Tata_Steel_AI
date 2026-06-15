document.addEventListener('DOMContentLoaded', () => {
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const chatMessages = document.getElementById('chatMessages');

  if (chatForm) {
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const text = chatInput.value.trim();
      if (!text) return;
      
      // Append User Message
      appendUserMessage(text);
      chatInput.value = '';
      
      // Show typing indicator
      const typingId = appendTypingIndicator();
      
      // Get JWT and Active Session
      const token = localStorage.getItem('access_token') || 'mock_token';
      const sessionId = localStorage.getItem('active_session_id') || 'MW-1000';
      
      try {
        const response = await fetch('http://localhost:8000/api/agent/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            message: text,
            session_id: sessionId
          })
        });

        removeElement(typingId);
        
        if (!response.ok) {
           appendAgentMessage("Error: Could not reach the agent service.");
           return;
        }

        // Setup streaming message container
        const msgId = 'msg-' + Date.now();
        createEmptyAgentMessage(msgId);
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let fullMessageText = "";
        let done = false;

        while (!done) {
          const { value, done: readerDone } = await reader.read();
          done = readerDone;
          if (value) {
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const dataStr = line.replace('data: ', '').trim();
                if (dataStr === '[DONE]') {
                   finalizeMessage(msgId, fullMessageText);
                   break;
                }
                try {
                  const data = JSON.parse(dataStr);
                  if (data.token) {
                    fullMessageText += data.token;
                    appendTokenToMessage(msgId, data.token);
                  }
                  if (data.error) {
                    fullMessageText += `\n**Error:** ${data.error}`;
                    appendTokenToMessage(msgId, `\n**Error:** ${data.error}`);
                  }
                } catch (e) {
                  // Incomplete JSON chunk, skip
                }
              }
            }
          }
        }
      } catch (error) {
        removeElement(typingId);
        appendAgentMessage("Network Error: Could not connect to backend.");
      }
    });
  }
});

function createEmptyAgentMessage(id) {
  const msgHTML = `
    <div class="message agent-message">
      <div id="${id}-content" class="message-content"></div>
      <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
        <span class="badge status-info" style="font-size: 10px;">Live Stream</span>
        <div class="message-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
      </div>
    </div>
  `;
  document.getElementById('chatMessages').insertAdjacentHTML('beforeend', msgHTML);
  scrollToBottom();
}

function appendTokenToMessage(id, token) {
  const contentEl = document.getElementById(`${id}-content`);
  if (contentEl) {
    // Basic formatting replacement to handle newlines
    const formattedToken = token.replace(/\n/g, '<br>');
    contentEl.innerHTML += formattedToken;
    scrollToBottom();
  }
}

function finalizeMessage(id, fullText) {
  const contentEl = document.getElementById(`${id}-content`);
  if (!contentEl) return;
  
  const cardRegex = /\[INSTRUCTION_CARD\]\s*(\{[\s\S]*?\})/i;
  const match = fullText.match(cardRegex);
  
  if (match) {
    try {
      const cardData = JSON.parse(match[1]);
      const cardHTML = `
        <div style="margin-top: 12px; background-color: var(--bg-page); border: 1px solid var(--border-strong); border-radius: 8px; padding: 12px;">
          <h4 style="margin: 0 0 8px 0; color: var(--primary);"><i class="fa-solid fa-clipboard-list"></i> ${cardData.issue_summary || 'Instruction Card'}</h4>
          <div style="font-size: 12px; margin-bottom: 8px;"><strong>Tools Required:</strong> ${cardData.required_tools ? cardData.required_tools.join(', ') : 'None'}</div>
          ${cardData.safety_warnings && cardData.safety_warnings.length > 0 ? `<div style="font-size: 12px; color: var(--status-critical); margin-bottom: 8px;"><i class="fa-solid fa-triangle-exclamation"></i> <strong>Safety:</strong> ${cardData.safety_warnings.join(', ')}</div>` : ''}
          <div style="font-size: 13px; font-weight: bold; margin-bottom: 4px;">Steps:</div>
          <ul style="font-size: 13px; margin: 0 0 12px 16px; padding: 0;">
            ${cardData.steps ? cardData.steps.map(s => `<li>${s}</li>`).join('') : ''}
          </ul>
          <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">Ref: ${cardData.sop_reference || 'N/A'}</div>
          
          <div id="${id}-ack-area" style="border-top: 1px solid var(--border-default); padding-top: 12px;">
            <div style="font-size: 12px; margin-bottom: 8px; font-weight: bold;">Do you understand and agree to follow these instructions?</div>
            <div style="display: flex; gap: 8px;" id="${id}-btn-group">
              <button class="btn btn-primary" style="height: 28px; padding: 0 12px; font-size: 12px; background-color: var(--status-success); border: none;" onclick="showSignatureBox('${id}', '${cardData.issue_summary}')">Yes, I agree</button>
              <button class="btn btn-secondary" style="height: 28px; padding: 0 12px; font-size: 12px;" onclick="submitInstructionAck('${id}', '${cardData.issue_summary}', 'No')">No, need clarification</button>
            </div>
            <div id="${id}-sig-box" style="display: none; margin-top: 12px;">
              <input type="text" id="${id}-sig-input" class="input-field" placeholder="Type your name to digitally sign" style="height: 32px; font-size: 12px; margin-bottom: 8px;">
              <button class="btn btn-primary" style="height: 28px; width: 100%; font-size: 12px;" onclick="submitInstructionAck('${id}', '${cardData.issue_summary}', 'Yes')">Sign & Acknowledge</button>
            </div>
          </div>
        </div>
      `;
      fullText = fullText.replace(match[0], cardHTML);
    } catch(e) {
      console.error("Failed to parse instruction card", e);
    }
  }
  
  fullText = fullText.replace(/\n/g, '<br>');
  contentEl.innerHTML = fullText;
  scrollToBottom();
}

window.showSignatureBox = function(id, summary) {
  document.getElementById(`${id}-btn-group`).style.display = 'none';
  document.getElementById(`${id}-sig-box`).style.display = 'block';
};

window.submitInstructionAck = async function(id, summary, status) {
  const sessionId = localStorage.getItem('active_session_id') || 'MW-1000';
  const token = localStorage.getItem('access_token') || 'mock_token';
  const sigInput = document.getElementById(`${id}-sig-input`);
  const signature = sigInput ? sigInput.value : '';
  
  if (status === 'Yes' && !signature) {
    alert('Digital signature required to acknowledge.');
    return;
  }
  
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/sessions/${sessionId}/acknowledge`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        instruction_summary: summary,
        status: status,
        signature: signature
      })
    });
    
    if (res.ok) {
      const ackArea = document.getElementById(`${id}-ack-area`);
      if (status === 'Yes') {
         ackArea.innerHTML = `<div style="color: var(--status-success); font-size: 12px; font-weight: bold;"><i class="fa-solid fa-check"></i> Instruction Acknowledged and Signed by ${signature}</div>`;
         appendUserMessage("I understand and will proceed with the instructions.");
      } else {
         ackArea.innerHTML = `<div style="color: var(--status-warning); font-size: 12px; font-weight: bold;"><i class="fa-solid fa-circle-question"></i> Clarification Requested</div>`;
         appendUserMessage("I need clarification on the previous instructions. Can you explain in more detail?");
      }
      
      // Auto-submit the user message to the agent
      const chatForm = document.getElementById('chatForm');
      if (chatForm) {
         chatForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
      }
    }
  } catch (e) {
    alert("Network error submitting acknowledgment");
  }
}

function appendUserMessage(text) {
  const msgHTML = `
    <div class="message user-message">
      <div class="message-content">${text}</div>
      <div class="message-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
    </div>
  `;
  document.getElementById('chatMessages').insertAdjacentHTML('beforeend', msgHTML);
  scrollToBottom();
}

function appendAgentMessage(text) {
  const msgHTML = `
    <div class="message agent-message">
      <div class="message-content">
        ${text}
        <div style="margin-top: 12px; display: flex; gap: 8px;">
          <button class="btn btn-secondary" style="height: 28px; padding: 0 12px; font-size: 12px;">Show Diagram</button>
          <button class="btn btn-secondary" style="height: 28px; padding: 0 12px; font-size: 12px;">Acknowledge</button>
        </div>
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
        <span class="badge status-info" style="font-size: 10px;">SOP-04 &middot; Page 12</span>
        <div class="message-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
      </div>
    </div>
  `;
  document.getElementById('chatMessages').insertAdjacentHTML('beforeend', msgHTML);
  scrollToBottom();
}

function appendTypingIndicator() {
  const id = 'typing-' + Date.now();
  const typingHTML = `
    <div id="${id}" class="message agent-message" style="width: 60px; display: flex; justify-content: center; gap: 4px;">
      <div class="typing-dot"></div>
      <div class="typing-dot" style="animation-delay: 0.2s"></div>
      <div class="typing-dot" style="animation-delay: 0.4s"></div>
    </div>
  `;
  document.getElementById('chatMessages').insertAdjacentHTML('beforeend', typingHTML);
  scrollToBottom();
  return id;
}

function removeElement(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function scrollToBottom() {
  const container = document.getElementById('chatMessages');
  container.scrollTop = container.scrollHeight;
}
