const token = localStorage.getItem('access_token');
if (!token) {
    window.location.href = 'index.html';
}

async function fetchAPI(endpoint) {
    const res = await fetch(`http://127.0.0.1:8000${endpoint}`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) {
        if (res.status === 401 || res.status === 403) {
            localStorage.removeItem('access_token');
            window.location.href = 'index.html';
        }
        throw new Error(await res.text());
    }
    return res.json();
}

async function loadDashboard() {
    try {
        // Fetch User Info
        const userName = localStorage.getItem('user_name') || 'Engineer';
        const userRole = localStorage.getItem('user_role') || 'engineer';
        const empId = localStorage.getItem('employee_id') || 'N/A';
        
        document.getElementById('userName').innerText = userName;
        document.getElementById('userAvatar').innerText = userName.substring(0,2).toUpperCase();
        document.getElementById('navAvatar').innerText = userName.substring(0,2).toUpperCase();
        document.getElementById('userId').innerText = `ID: ${empId}`;
        
        if(document.getElementById('userRole')) {
            document.getElementById('userRole').innerText = userRole.charAt(0).toUpperCase() + userRole.slice(1);
        }

        // Fetch Stats
        const stats = await fetchAPI('/api/engineer/dashboard');
        if (document.getElementById('statActiveSessions')) document.getElementById('statActiveSessions').innerText = stats.active_sessions;
        if (document.getElementById('statOpenAlerts')) document.getElementById('statOpenAlerts').innerText = stats.open_alerts;
        if (document.getElementById('statEscalations')) document.getElementById('statEscalations').innerText = stats.pending_escalations;
        // document.getElementById('statCompletedTasks').innerText = stats.completed_tasks; // Optional

        // Fetch Recent Sessions
        const sessions = await fetchAPI('/api/engineer/recent-sessions');
        const sessionContainer = document.getElementById('recent-sessions-container');
        if (sessionContainer) {
            sessionContainer.innerHTML = '';
            if (sessions.length === 0) {
                sessionContainer.innerHTML = '<div style="padding: 10px; color: var(--text-muted); font-size: 14px;">No recent sessions found.</div>';
        } else {
            sessions.forEach(session => {
                const statusClass = session.status === 'active' ? 'status-info' : (session.status === 'resolved' ? 'status-success' : 'status-warning');
                const statusLabel = session.status === 'active' ? 'In Progress' : (session.status.charAt(0).toUpperCase() + session.status.slice(1));
                const actionText = session.status === 'active' 
                    ? `<a href="engineering_agent.html?session_id=${session.session_id}" style="font-weight: 500; font-size: 13px;" onclick="localStorage.setItem('engineering_session_id', '${session.session_id}')">Resume</a>` 
                    : '<a href="history.html" class="text-muted" style="font-size: 13px;">View Log</a>';
                
                sessionContainer.innerHTML += `
                  <div class="list-row">
                    <div class="row-main">
                      <div class="row-title">${session.equipment_name}</div>
                      <div class="row-meta">${session.engineer} &middot; ${new Date(typeof session.started_at === 'string' && !session.started_at.endsWith('Z') ? session.started_at + 'Z' : session.started_at).toLocaleString()}</div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px;">
                      <span class="badge ${statusClass}">${statusLabel}</span>
                      ${actionText}
                    </div>
                  </div>
                `;
            });
        }
        }

        // Fetch Alerts
        const alerts = await fetchAPI('/api/engineer/alerts');
        const alertsContainer = document.getElementById('active-alerts-container');
        if (alertsContainer) {
            alertsContainer.innerHTML = '';
            if (alerts.length === 0) {
                alertsContainer.innerHTML = '<div style="padding: 10px; color: var(--text-muted); font-size: 14px;">No active alerts.</div>';
        } else {
            alerts.forEach(alert => {
                const badgeClass = alert.severity === 'critical' ? 'status-critical' : 'status-warning';
                alertsContainer.innerHTML += `
                  <div class="list-row">
                    <div class="row-main">
                      <div class="row-title">${alert.description}</div>
                      <div class="row-meta">Equipment ${alert.equipment_id} &middot; ${new Date(typeof alert.timestamp === 'string' && !alert.timestamp.endsWith('Z') ? alert.timestamp + 'Z' : alert.timestamp).toLocaleString()}</div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px;">
                      <span class="badge ${badgeClass}">${alert.severity.charAt(0).toUpperCase() + alert.severity.slice(1)}</span>
                      <a href="#" style="font-weight: 500; font-size: 13px;" onclick="event.preventDefault(); startSessionForEquipment(${alert.equipment_id})">Open Agent</a>
                    </div>
                  </div>
                `;
            });
        }
        }

        // Fetch Equipment Health
        const health = await fetchAPI('/api/engineer/equipment-health');
        if (document.getElementById('healthHealthy')) document.getElementById('healthHealthy').innerText = health.healthy_assets;
        if (document.getElementById('healthWarning')) document.getElementById('healthWarning').innerText = health.warning_assets;
        if (document.getElementById('healthCritical')) document.getElementById('healthCritical').innerText = health.critical_assets;

        // Fetch Escalations
        const escalations = await fetchAPI('/api/engineer/escalations');
        const escContainer = document.getElementById('escalations-container');
        if (escContainer) {
            escContainer.innerHTML = '';
            if (escalations.length === 0) {
                escContainer.innerHTML = '<div style="padding: 10px; color: var(--text-muted); font-size: 14px;">No pending escalations.</div>';
        } else {
            escalations.forEach(esc => {
                escContainer.innerHTML += `
                  <div class="list-row">
                    <div class="row-main">
                      <div class="row-title">${esc.escalation_id} - ${esc.equipment}</div>
                      <div class="row-meta">Assigned to: ${esc.assigned_supervisor}</div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 12px;">
                      <span class="badge status-warning">${esc.status}</span>
                    </div>
                  </div>
                `;
            });
        }
        }
        
    } catch (e) {
        console.error("Dashboard Load Error:", e);
    }
}

async function startNewEngineeringSession() {
    try {
        const response = await fetch('http://127.0.0.1:8000/api/sessions/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ equipment_id: 1, task_domain: "Mechanical" })
        });
        if (!response.ok) throw new Error("Failed to create session");
        const data = await response.json();
        localStorage.setItem('engineering_session_id', data.id);
        console.log("Opening Engineering Agent");
        console.log("Session ID:", data.id);
        window.location.href = `engineering_agent.html?session_id=${data.id}`;
    } catch (e) { 
        alert("Failed to start session: " + e.message); 
    }
}

async function startSessionForEquipment(equipmentId) {
    try {
        const response = await fetch('http://127.0.0.1:8000/api/sessions/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ equipment_id: equipmentId, task_domain: "General" })
        });
        if (!response.ok) throw new Error("Failed to create session");
        const data = await response.json();
        localStorage.setItem('engineering_session_id', data.id);
        console.log("Opening Engineering Agent");
        console.log("Session ID:", data.id);
        window.location.href = `engineering_agent.html?session_id=${data.id}`;
    } catch (e) { 
        alert("Failed to start session: " + e.message); 
    }
}

document.addEventListener('DOMContentLoaded', loadDashboard);
