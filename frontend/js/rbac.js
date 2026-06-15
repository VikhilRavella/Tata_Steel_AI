/**
 * Role-Based Access Control (RBAC) & Dynamic Profile Rendering
 * This script must be included on all protected HTML pages.
 */

(function enforceRBAC() {
  const token = localStorage.getItem('access_token');
  const role = localStorage.getItem('user_role');
  
  if (!token || !role) {
    console.warn("RBAC: Unauthenticated access attempt. Redirecting to login.");
    window.location.replace('index.html');
    return;
  }
  
  const currentPath = window.location.pathname;
  let currentPage = currentPath.substring(currentPath.lastIndexOf('/') + 1) || 'index.html';
  
  // Strip query parameters or hashes (crucial for local file:// execution where ? is part of pathname)
  if (currentPage.includes('?')) currentPage = currentPage.split('?')[0];
  if (currentPage.includes('#')) currentPage = currentPage.split('#')[0];
  
  // Define Role-to-Page mappings (whitelist)
  const allowedPages = {
    'manager': ['home_page_manager.html', 'manager_audit_log.html', 'manager_documents.html', 'manager_asset_health.html', 'manager_users.html', 'upload.html', 'engineering_agent.html', 'agent_sandbox.html', 'documents.html', 'profile.html', 'chat.html', 'equipment.html', 'history.html', 'safety.html'],
    'supervisor': ['home_page_supervisor.html', 'supervisor_escalations.html', 'supervisor_documents.html', 'supervisor_plant_health.html', 'upload.html', 'engineering_agent.html', 'agent_sandbox.html', 'documents.html', 'profile.html', 'chat.html', 'equipment.html', 'history.html', 'safety.html'],
    'engineer': ['home_page_engineer.html', 'chat.html', 'equipment.html', 'history.html', 'safety.html', 'upload.html', 'engineering_agent.html', 'agent_sandbox.html', 'documents.html', 'profile.html']
  };
  
  // If the page is not in their whitelist (and it's not index.html)
  if (currentPage !== 'index.html' && allowedPages[role] && !allowedPages[role].includes(currentPage)) {
    console.error(`RBAC: Access Denied. User role '${role}' is not permitted to access '${currentPage}'.`);
    
    // Redirect to their default dashboard
    if (role === 'manager') window.location.replace('home_page_manager.html');
    else if (role === 'supervisor') window.location.replace('home_page_supervisor.html');
    else window.location.replace('home_page_engineer.html');
  }
})();

document.addEventListener('DOMContentLoaded', () => {
  // Dynamically render user profile information from localStorage
  const userName = localStorage.getItem('user_name');
  const userRole = localStorage.getItem('user_role');
  
  if (userName && userRole) {
    // Determine Initials (e.g., Rajesh Kumar -> RK)
    const initials = userName.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    
    // Capitalize role display
    const roleDisplay = userRole.charAt(0).toUpperCase() + userRole.slice(1);
    
    // 1. Update large sidebar profile names (used in manager.html / home_page_engineer.html)
    // Find all elements that look like they hold the profile name
    document.querySelectorAll('.sidebar, .topbar').forEach(container => {
      // Typically the name is in an element with class ending in -name or just inside a profile block
      const nameElements = container.querySelectorAll('h3, .profile-name, .user-name, div[style*="font-weight: 600"]');
      nameElements.forEach(el => {
        // Simple heuristic: if it currently says Manish Kumar or Rahul Agarwal or similar, replace it
        if (el.textContent.includes('Kumar') || el.textContent.includes('Agarwal') || el.textContent.includes('Jenkins')) {
           el.textContent = userName;
        } else if (el.classList.contains('profile-name') || el.tagName === 'H3') {
           el.textContent = userName;
        }
      });
      
      // Update Role Badges
      const badgeElements = container.querySelectorAll('.badge, .profile-role, .user-role');
      badgeElements.forEach(el => {
        if (el.textContent.includes('Manager') || el.textContent.includes('L2') || el.textContent.includes('Sup') || el.textContent.includes('Engineer')) {
           if (roleDisplay === 'Engineer') {
               el.textContent = 'L2 Engineer'; // Keeping the L2 flavor for engineers
           } else {
               el.textContent = roleDisplay;
           }
        }
      });
      
      // Update Avatars/Initials
      const avatarElements = container.querySelectorAll('.avatar, .profile-icon, .user-initials');
      avatarElements.forEach(el => {
        if (el.textContent.trim().length <= 2 && el.textContent.trim().length > 0) {
           el.textContent = initials;
        }
      });
    });
  }
  
  // Setup logout buttons
  document.querySelectorAll('a[href="index.html"], .logout-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      if (btn.tagName === 'A' && btn.getAttribute('href') === 'index.html') {
         localStorage.removeItem('access_token');
         localStorage.removeItem('user_role');
         localStorage.removeItem('user_name');
         localStorage.removeItem('employee_id');
      }
    });
  });

  // Global Search Bar Handler (Top Nav)
  const globalSearchInput = document.querySelector('.search-bar .search-input');
  if (globalSearchInput && !globalSearchInput.id.includes('sessionSearch')) {
      globalSearchInput.addEventListener('keypress', function (e) {
          if (e.key === 'Enter') {
              const query = this.value.trim();
              if (query) {
                  window.location.href = `engineering_agent.html?q=${encodeURIComponent(query)}`;
              }
          }
      });
  }
});
