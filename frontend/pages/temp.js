
    const token = localStorage.getItem('access_token') || localStorage.getItem('token');
    
    function showSection(sectionId, element) {
      document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      
      const target = document.getElementById(`section-${sectionId}`);
      if(target) target.classList.add('active');
      if(element) element.classList.add('active');

      if(sectionId === 'dashboard') loadDashboardMetrics();
      if(sectionId === 'equipment') loadMyEquipment();
      if(sectionId === 'work_orders') loadMyWorkOrders();
      if(sectionId === 'inventory') loadInventorySearch();
      if(sectionId === 'maintenance') loadMaintenanceHistory();
      if(sectionId === 'documents') loadDocuments();
      if(sectionId === 'profile') loadProfile();
    }

    async function fetchAPI(url, options = {}) {
      if (!token) { window.location.href = 'index.html'; return null; }
      if (!options.headers) options.headers = {};
      options.headers['Authorization'] = `Bearer ${token}`;
      try {
        const response = await fetch(url.startsWith('http') ? url : 'http://localhost:8000' + url, options);
        if (response.status === 401) window.location.href = 'index.html';
        return await response.json();
      } catch (e) {
        console.error(e);
        return null;
      }
    }

    async function loadProfile() {
      const p = await fetchAPI('/api/profile');
      if(p) {
        document.getElementById('userName').innerText = p.name;
        document.getElementById('headerName').innerText = p.name;
        document.getElementById('headerDept').innerText = `${p.department} | ${p.plant}`;
        
        document.getElementById('profile-container').innerHTML = `
          <div style="margin-bottom:12px"><strong>Name:</strong> ${p.name}</div>
          <div style="margin-bottom:12px"><strong>Employee ID:</strong> ${p.employee_id}</div>
          <div style="margin-bottom:12px"><strong>Email:</strong> ${p.email}</div>
          <div style="margin-bottom:12px"><strong>Phone:</strong> ${p.phone}</div>
          <div style="margin-bottom:12px"><strong>Department:</strong> ${p.department}</div>
          <div style="margin-bottom:12px"><strong>Supervisor:</strong> ${p.supervisor}</div>
          <div style="margin-bottom:12px"><strong>Plant:</strong> ${p.plant}</div>
          <div style="margin-bottom:12px"><strong>Role:</strong> ${p.role}</div>
        `;
      }
    }

    async function loadDashboardMetrics() {
      const data = await fetchAPI('/api/dashboard-metrics');
      if(data) {
          document.getElementById('kpi-eq').innerText = data.assigned_equipment;
          document.getElementById('kpi-wo-open').innerText = data.open_work_orders;
          document.getElementById('kpi-wo-done').innerText = data.completed_work_orders;
          document.getElementById('kpi-req').innerText = data.pending_requests;
      }
    }

    async function loadMyEquipment() {
      const data = await fetchAPI('/api/equipment');
      const tbody = document.getElementById('equipment-table-body');
      if(!data) return;
      tbody.innerHTML = data.map(d => `
        <tr>
          <td>${d.equipment_id}</td><td>${d.equipment_name}</td><td>${d.equipment_type}</td>
          <td>${d.plant}</td><td>${d.block}</td>
          <td><span class="badge ${d.status === 'Running' ? 'badge-success' : (d.status === 'Maintenance' ? 'badge-warning' : 'badge-danger')}">${d.status}</span></td>
          <td>${d.criticality}</td><td>${d.assigned_supervisor}</td><td>${d.last_maintenance}</td>
        </tr>
      `).join('') || '<tr><td colspan="9" style="text-align:center;">No data available</td></tr>';
    }

    async function loadMyWorkOrders() {
      const data = await fetchAPI('/api/work-orders');
      const tbody = document.getElementById('work_orders-table-body');
      if(!data) return;
      tbody.innerHTML = data.map(d => `
        <tr>
          <td>${d.id}</td><td>${d.title}</td><td>${d.equipment_name}</td>
          <td><span class="badge badge-default">${d.priority}</span></td>
          <td><span class="badge ${d.status === 'Open' ? 'badge-warning' : 'badge-success'}">${d.status}</span></td>
          <td>${new Date(typeof d.created_at === 'string' && !d.created_at.endsWith('Z') ? d.created_at + 'Z' : d.created_at).toLocaleDateString()}</td><td>${d.assigned_by}</td>
          <td><button class="btn btn-outline" style="padding: 4px 8px; font-size: 12px;">View</button></td>
        </tr>
      `).join('') || '<tr><td colspan="8" style="text-align:center;">No data available</td></tr>';
    }

    async function loadMaintenanceHistory() {
      const data = await fetchAPI('/api/maintenance');
      const tbody = document.getElementById('maintenance-table-body');
      if(!data) return;
      tbody.innerHTML = data.map(d => `
        <tr>
          <td>${d.id}</td><td>${d.equipment_name}</td><td>${new Date(typeof d.date === 'string' && !d.date.endsWith('Z') ? d.date + 'Z' : d.date).toLocaleDateString()}</td>
          <td>${d.description}</td><td>${d.performed_by}</td>
          <td><span class="badge ${d.status === 'Completed' ? 'badge-success' : 'badge-warning'}">${d.status}</span></td>
        </tr>
      `).join('') || '<tr><td colspan="6" style="text-align:center;">No data available</td></tr>';
    }

    async function loadInventorySearch() {
      const q = document.getElementById('inv-search-input').value;
      const data = await fetchAPI(`/api/inventory/search?part_name=${encodeURIComponent(q)}&part_number=${encodeURIComponent(q)}`);
      const tbody = document.getElementById('inventory-table-body');
      if(!data) return;
      tbody.innerHTML = data.map(d => `
        <tr>
          <td>${d.part_number}</td><td>${d.part_name}</td><td>${d.part_category || 'N/A'}</td>
          <td><span class="${d.stock_qty <= d.minimum_stock ? 'badge badge-danger' : ''}">${d.stock_qty}</span></td>
          <td>${d.minimum_stock}</td><td>${d.warehouse || 'N/A'}</td>
          <td>${d.rack || 'N/A'} / ${d.bin || 'N/A'}</td><td>${d.supplier || 'N/A'}</td>
        </tr>
      `).join('') || '<tr><td colspan="8" style="text-align:center;">No data available</td></tr>';
    }

    async function loadDocuments() {
      const data = await fetchAPI('/api/documents/');
      const tbody = document.getElementById('documents-table-body');
      if(!data) return;
      tbody.innerHTML = data.map(d => `
        <tr>
          <td>${d.filename}</td><td>${d.category || 'Manual'}</td>
          <td>${d.uploaded_by_name}</td><td>${new Date(typeof d.uploaded_at === 'string' && !d.uploaded_at.endsWith('Z') ? d.uploaded_at + 'Z' : d.uploaded_at).toLocaleDateString()}</td>
          <td><button class="btn btn-outline" style="padding: 4px 8px; font-size: 12px;">Download</button></td>
        </tr>
      `).join('') || '<tr><td colspan="5" style="text-align:center;">No documents available</td></tr>';
    }

    async function submitPartRequest(e) {
      e.preventDefault();
      const p = await fetchAPI('/api/profile');
      if(!p) return;
      
      const payload = {
        requested_by: p.id,
        part_number: document.getElementById('req-part').value,
        quantity: parseInt(document.getElementById('req-qty').value),
        equipment_id: document.getElementById('req-eq').value || null,
        reason: document.getElementById('req-reason').value,
        priority: document.getElementById('req-priority').value
      };

      const res = await fetchAPI('/api/part-request/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const msg = document.getElementById('req-msg');
      if(res && res.request_id) {
        msg.style.color = '#10b981';
        msg.innerText = "Request submitted successfully! ID: " + res.request_id;
        document.getElementById('part-request-form').reset();
      } else {
        msg.style.color = '#ef4444';
        msg.innerText = "Failed to submit request.";
      }
    }

    let currentEngImageBase64 = null;
    let engSessionId = localStorage.getItem('engineering_session_id');

async function initEngSession() {
    if (!token) return;
    if (!engSessionId) {
        try {
            const res = await fetchAPI('/api/engineering/session', { method: 'POST' });
            if (res && res.session_id) {
                engSessionId = res.session_id;
                localStorage.setItem('engineering_session_id', engSessionId);
            }
        } catch (e) {
            console.error("Failed to init eng session", e);
        }
    }
}

    let sandSessionId = 'sand-session-' + Date.now();

    function handleEngFileSelect(event) {
      const file = event.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
          const result = e.target.result;
          document.getElementById('engImagePreview').src = result;
          document.getElementById('engImagePreviewContainer').style.display = 'flex';
          currentEngImageBase64 = result.split(',')[1];
        };
        reader.readAsDataURL(file);
      }
    }

    function clearEngImage() {
      currentEngImageBase64 = null;
      document.getElementById('engImagePreviewContainer').style.display = 'none';
      document.getElementById('engImageUpload').value = '';
    }

    async function sendEngMessage() {
      const chatInput = document.getElementById('engChatInput');
      const text = chatInput.value.trim();
      if (!text && !currentEngImageBase64) return;
      
      const chatBox = document.getElementById('engChatBox');
      let userMsgHtml = `<div style="align-self:flex-end; background-color:var(--primary); color:white; padding:16px; border-radius:12px; border-bottom-right-radius:0; max-width:85%; line-height:1.6;">${text}</div>`;
      if (currentEngImageBase64) {
          userMsgHtml = `<div style="align-self:flex-end; background-color:var(--primary); color:white; padding:16px; border-radius:12px; border-bottom-right-radius:0; max-width:85%; line-height:1.6;"><img src="data:image/jpeg;base64,${currentEngImageBase64}" style="max-height: 100px; border-radius:8px; display: block; margin-bottom: 10px;">${text}</div>`;
      }
      chatBox.innerHTML += userMsgHtml;
      
      const bodyPayload = { message: text, session_id: engSessionId };
      if (currentEngImageBase64) {
          bodyPayload.image_base64 = currentEngImageBase64;
          clearEngImage();
      }
      
      chatInput.value = '';
      chatBox.scrollTop = chatBox.scrollHeight;
      
      const typingId = 'typing-' + Date.now();
      chatBox.innerHTML += `<div id="${typingId}" style="align-self:flex-start; background-color:var(--bg-card); border:1px solid var(--border-color); padding:16px; border-radius:12px; border-bottom-left-radius:0; max-width:85%; line-height:1.6;">Analyzing context...</div>`;
      chatBox.scrollTop = chatBox.scrollHeight;
      
      try {
          const res = await fetchAPI('/api/engineering/chat', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(bodyPayload)
          });
          const typingEl = document.getElementById(typingId);
          if(typingEl) typingEl.remove();
          if (res && res.response) {
              chatBox.innerHTML += `<div style="align-self:flex-start; background-color:var(--bg-card); border:1px solid var(--border-color); padding:16px; border-radius:12px; border-bottom-left-radius:0; max-width:85%; line-height:1.6;">${res.response.replace(/\n/g, '<br>')}</div>`;
          } else {
              chatBox.innerHTML += `<div style="align-self:flex-start; background-color:var(--bg-card); border:1px solid var(--border-color); padding:16px; border-radius:12px; border-bottom-left-radius:0; max-width:85%; line-height:1.6; color:var(--badge-danger, #ef4444);">Failed to get response from server.</div>`;
          }
      } catch (e) {
          const typingEl = document.getElementById(typingId);
          if(typingEl) typingEl.remove();
          chatBox.innerHTML += `<div style="align-self:flex-start; background-color:var(--bg-card); border:1px solid var(--border-color); padding:16px; border-radius:12px; border-bottom-left-radius:0; max-width:85%; line-height:1.6; color:var(--badge-danger, #ef4444);">Communication error.</div>`;
      }
      chatBox.scrollTop = chatBox.scrollHeight;
    }

    let sandboxSessionId = localStorage.getItem('sandbox_session_id');
    const API_BASE_SANDBOX = "http://localhost:8000/api/sandbox";

    async function initSandboxSession() {
      if (!token) return;
      if (!sandboxSessionId) {
          try {
              const response = await fetch(`${API_BASE_SANDBOX}/session`, {
                  method: 'POST',
                  headers: { 
        'Authorization': `Bearer ${token}` }
              });
              if (response.ok) {
                  const data = await response.json();
                  sandboxSessionId = data.session_id;
                  localStorage.setItem('sandbox_session_id', sandboxSessionId);
                  loadSessionsList();
              }
          } catch (e) {
              console.error("Failed to init sandbox session", e);
          }
      } else {
          loadSessionsList();
          try {
              const response = await fetch(`${API_BASE_SANDBOX}/history/chat/${sandboxSessionId}`, {
                  headers: { 
        'Authorization': `Bearer ${token}` }
              });
              if (response.ok) {
                  const messages = await response.json();
                  const chatDisplay = document.getElementById('copilot-chat-box');
                  if (messages.length > 0) {
                      chatDisplay.innerHTML = ''; // clear welcome screen
                      messages.forEach(m => {
                          if(m.sender === 'user') {
                              chatDisplay.innerHTML += `<div style="align-self:flex-end; background-color:#2563eb; color:white; padding:12px 16px; border-radius:12px; border-bottom-right-radius:0; max-width:85%; line-height:1.5; font-size:13px; box-shadow:0 2px 4px rgba(37,99,235,0.2);">${m.content}</div>`;
                          } else {
                              chatDisplay.innerHTML += `<div style="align-self:flex-start; background-color:white; border:1px solid var(--border-color); padding:12px 16px; border-radius:12px; border-bottom-left-radius:0; max-width:85%; line-height:1.5; font-size:13px; box-shadow:0 2px 8px rgba(0,0,0,0.05);">${m.content.replace(/\n/g, '<br>')}</div>`;
                          }
                      });
                      chatDisplay.scrollTop = chatDisplay.scrollHeight;
                  }
              }
          } catch (e) {
              console.error("Failed to load chat history", e);
          }
      }
    }

    function toggleCopilot() {
      const panel = document.getElementById('copilot-panel');
      panel.classList.toggle('open');
      if (panel.classList.contains('open') && !sandboxSessionId) {
          initSandboxSession();
      }
    }

    function clearCopilotChat() {
      const welcomeHtml = `<div id="copilot-welcome" style="background:var(--bg-page); border:1px solid var(--border-color); border-radius:12px; padding:16px;">
        <div style="font-weight:600; font-size:14px; margin-bottom:8px; color:var(--text-primary);">Welcome to Sandbox Agent</div>
        <div style="font-size:13px; color:var(--text-secondary); line-height:1.5;">
          Sandbox Agent helps engineers design workflows, generate architectures, create prompts, plan systems, and prototype industrial AI solutions before implementation.
        </div>
        <div style="margin-top:16px;">
          <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:600; margin-bottom:8px; letter-spacing:0.5px;">Quick Actions</div>
          <div style="display:flex; flex-wrap:wrap; gap:8px;">
            <div class="copilot-chip" onclick="sendCopilotChip('Design Database Schema')">Database Schema</div>
            <div class="copilot-chip" onclick="sendCopilotChip('Create Agent Workflow')">Agent Workflow</div>
            <div class="copilot-chip" onclick="sendCopilotChip('Generate Prompt Template')">Prompt Template</div>
            <div class="copilot-chip" onclick="sendCopilotChip('Design API Architecture')">API Architecture</div>
            <div class="copilot-chip" onclick="sendCopilotChip('Build Industrial Dashboard')">Dashboard Design</div>
          </div>
        </div>
      </div>`;
      document.getElementById('copilot-chat-box').innerHTML = welcomeHtml;
    }

    async function sendCopilotChip(text) {
      document.getElementById('copilot-input').value = text;
      await sendCopilotMessage();
    }

    async function sendCopilotMessage() {
      const chatInput = document.getElementById('copilot-input');
      const text = chatInput.value.trim();
      if (!text) return;
      
      if (!sandboxSessionId) await initSandboxSession();

      const chatBox = document.getElementById('copilot-chat-box');
      
      const welcomeMsg = document.getElementById('copilot-welcome');
      if (welcomeMsg) welcomeMsg.remove();

      let userMsgHtml = `<div style="align-self:flex-end; background-color:#2563eb; color:white; padding:12px 16px; border-radius:12px; border-bottom-right-radius:0; max-width:85%; line-height:1.5; font-size:13px; box-shadow:0 2px 4px rgba(37,99,235,0.2);">${text}</div>`;
      chatBox.innerHTML += userMsgHtml;
      chatInput.value = '';
      chatBox.scrollTop = chatBox.scrollHeight;
      
      const typingId = 'typing-copilot-' + Date.now();
      chatBox.innerHTML += `<div id="${typingId}" style="align-self:flex-start; background-color:white; border:1px solid var(--border-color); padding:12px 16px; border-radius:12px; border-bottom-left-radius:0; max-width:85%; line-height:1.5; font-size:13px; box-shadow:0 2px 8px rgba(0,0,0,0.05);"><i class="fa-solid fa-circle-notch fa-spin text-primary" style="margin-right:6px;"></i> Sandbox Agent is thinking...</div>`;
      chatBox.scrollTop = chatBox.scrollHeight;
      
      const agentMessageDiv = document.getElementById(typingId);
      let hasClearedThinking = false;

      try {
          const response = await fetch(`${API_BASE_SANDBOX}/chat`, {
              method: 'POST',
              headers: { 
                  'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
              },
              body: JSON.stringify({ message: text, session_id: sandboxSessionId })
          });

          if (!response.ok) {
              agentMessageDiv.innerHTML = "Error: " + response.statusText;
              agentMessageDiv.style.color = "#ef4444";
              agentMessageDiv.style.borderColor = "#ef4444";
              return;
          }

          // Handle SSE
          const reader = response.body.getReader();
          const decoder = new TextDecoder("utf-8");

          while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              const chunk = decoder.decode(value, { stream: true });
              const lines = chunk.split('\n');

              for (const line of lines) {
                  if (line.startsWith('data: ')) {
                      const dataStr = line.substring(6);
                      if (dataStr === '[DONE]') break;
                      try {
                          const data = JSON.parse(dataStr);
                          if (data.error) {
                              if (!hasClearedThinking) { agentMessageDiv.innerHTML = ''; hasClearedThinking = true; }
                              agentMessageDiv.innerHTML += "Error: " + data.error;
                              agentMessageDiv.style.color = "#ef4444";
                              chatBox.scrollTop = chatBox.scrollHeight;
                          }
                          if (data.token) {
                              if (!hasClearedThinking) { agentMessageDiv.innerHTML = ''; hasClearedThinking = true; }
                              // simplistic replace of \n, full markdown rendering is better but we follow original
                              const tokenHtml = data.token.replace(/\n/g, '<br>');
                              agentMessageDiv.innerHTML += tokenHtml;
                              chatBox.scrollTop = chatBox.scrollHeight;
                          }
                      } catch (e) {
                          console.error("Error parsing JSON line:", dataStr);
                      }
                  }
              }
          }
          agentMessageDiv.id = ''; // remove ID so it stays as a normal message
          loadSessionsList(); // refresh title if generated
      } catch (e) {
          agentMessageDiv.innerHTML = "Communication error. Is the backend running?";
          agentMessageDiv.style.color = "#ef4444";
          agentMessageDiv.style.borderColor = "#ef4444";
      }
      chatBox.scrollTop = chatBox.scrollHeight;
    }

    async function loadSessionsList() {
      if (!token) return;
      try {
          const response = await fetch(`${API_BASE_SANDBOX}/history/list`, {
              headers: { 
        'Authorization': `Bearer ${token}` }
          });
          const res = await response.json();
          const container = document.getElementById('sessionListContainer');
          container.innerHTML = '';
          
          if (!res || res.length === 0) {
              container.innerHTML = '<div style="font-size: 11px; color: var(--text-muted);">No past sessions found.</div>';
              return;
          }

          res.forEach(session => {
              const dateStr = new Date(typeof session.started_at === 'string' && !session.started_at.endsWith('Z') ? session.started_at + 'Z' : session.started_at).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
              const sessionName = session.title || 'Sandbox Session';
              let statusColor = session.status === 'Active' ? '#4da6ff' : '#ffaa00';
              const isActive = session.session_id === sandboxSessionId;
              const borderStyle = isActive ? 'border-left: 3px solid var(--primary); background: white;' : 'border-left: 3px solid transparent; background: rgba(255,255,255,0.4);';
              
              container.insertAdjacentHTML('beforeend', `
                  <div class="session-item" style="padding: 10px; border: 1px solid var(--border-default); border-radius: 6px; cursor: pointer; ${borderStyle}" onclick="switchSession('${session.session_id}')">
                      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                          <strong style="font-size: 11px; display: block; margin-bottom: 4px; color: var(--text-primary); line-height:1.3;">${sessionName}</strong>
                          <button onclick="deleteSession(event, '${session.session_id}')" style="background: none; border: none; color: #ff4d4d; cursor: pointer;" title="Delete Session"><i class="fa-solid fa-trash" style="font-size: 10px;"></i></button>
                      </div>
                      <div style="display: flex; justify-content: space-between; align-items: center; font-size: 9px; margin-top: 6px;">
                          <span style="color: var(--text-muted);">${dateStr}</span>
                          <span style="color: ${statusColor}; font-weight: 600; text-transform: uppercase;">${session.status}</span>
                      </div>
                  </div>
              `);
          });
      } catch(err) {
          console.error("Failed to load session list:", err);
      }
    }

    function switchSession(id) {
      localStorage.setItem('sandbox_session_id', id);
      sandboxSessionId = id;
      initSandboxSession(); // reloads chat history without reloading page
    }

    function createNewSession() {
      localStorage.removeItem('sandbox_session_id');
      sandboxSessionId = null;
      clearCopilotChat();
      initSandboxSession();
    }

    async function deleteSession(e, id) {
      e.stopPropagation();
      if(!confirm("Delete this sandbox session?")) return;
      try {
          const response = await fetch(`${API_BASE_SANDBOX}/session/${id}`, {
              method: 'DELETE',
              headers: { 
        'Authorization': `Bearer ${token}` }
          });
          if(response.ok) {
              if(id === sandboxSessionId) {
                  createNewSession();
              } else {
                  loadSessionsList();
              }
          }
      } catch(e) { console.error(e); }
    }

    function filterSessions() {
      const query = document.getElementById('sessionSearch').value.toLowerCase();
      const items = document.querySelectorAll('.session-item');
      items.forEach(item => {
          const text = item.innerText.toLowerCase();
          item.style.display = text.includes(query) ? 'block' : 'none';
      });
    }

    async function escalateSandbox() {
      if(!sandboxSessionId) {
          alert("No active session to escalate.");
          return;
      }
      try {
          const response = await fetch(`${API_BASE_SANDBOX}/escalate`, {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
              },
              body: JSON.stringify({ sandbox_session_id: sandboxSessionId })
          });
          
          if(response.ok) {
              const data = await response.json();
              alert("Session successfully escalated to Engineering.");
              localStorage.setItem('engineering_session_id', data.engineer_session_id);
              engSessionId = data.engineer_session_id;
              toggleCopilot(); // close copilot
              document.querySelector('.nav-item[onclick*="engineering-agent"]').click();
              
              // Load the escalated chat history if function exists
              const engChatBox = document.getElementById('engChatBox');
              if (engChatBox) engChatBox.innerHTML = '<div class="message agent">Loading escalated context...</div>';
              setTimeout(async () => {
                  try {
                      const histRes = await fetchAPI('/api/engineering/history/chat/' + engSessionId);
                      if (histRes && Array.isArray(histRes)) {
                          engChatBox.innerHTML = '';
                          histRes.forEach(msg => {
                              const isUser = msg.sender === 'user';
                              const bgColor = isUser ? 'var(--primary)' : 'var(--bg-card)';
                              const color = isUser ? 'white' : 'inherit';
                              const alignment = isUser ? 'flex-end' : 'flex-start';
                              engChatBox.innerHTML += `<div style="align-self:${alignment}; background-color:${bgColor}; color:${color}; padding:16px; border-radius:12px; border:1px solid var(--border-color); max-width:85%; line-height:1.6;">${msg.content}</div>`;
                          });
                          engChatBox.scrollTop = engChatBox.scrollHeight;
                      }
                  } catch (e) {}
              }, 1000);
          } else {
              const err = await response.json();
              alert("Escalation failed: " + (err.detail || 'Unknown error'));
          }
      } catch (err) {
          console.error(err);
          alert("Network error during escalation.");
      }
    }

    async function resetSandbox() {
      if (!confirm("Are you sure you want to clear the sandbox knowledge base?")) return;
      try {
          const response = await fetch(`${API_BASE_SANDBOX}/reset`, { 
              method: 'DELETE',
              headers: { 
        'Authorization': `Bearer ${token}` }
          });
          const result = await response.json();
          if (response.ok) {
              alert(result.message);
              clearCopilotChat();
              const chatBox = document.getElementById('copilot-chat-box');
              chatBox.innerHTML += `<div style="align-self:center; background-color:var(--bg-card); color:var(--text-muted); padding:8px 16px; border-radius:12px; font-size:12px; margin-top:16px;">Knowledge base cleared. History reset.</div>`;
          } else {
              alert("Error: " + (result.detail || result.message));
          }
      } catch (error) {
          alert("Connection error.");
      }
    }

    document.addEventListener('DOMContentLoaded', () => {
      loadProfile();
      loadDashboardMetrics();
      initSandboxSession();
      initEngSession(); in background
    });
  