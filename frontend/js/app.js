document.addEventListener('DOMContentLoaded', () => {
  // Common JS logic for app initialization, auth state, etc.
  console.log('Maintenance Wizard App Initialized');
});

/**
 * Simulates a login attempt for demonstration purposes
 */
function handleLogin(event) {
  event.preventDefault();
  
  const empId = document.getElementById('empId').value;
  const password = document.getElementById('password').value;
  const loginBtn = document.getElementById('loginBtn');
  const errorMsg = document.getElementById('loginError');
  const btnText = loginBtn.querySelector('.btn-text');
  
  // Reset error
  errorMsg.style.display = 'none';
  document.getElementById('empId').classList.remove('error');
  document.getElementById('password').classList.remove('error');
  
  // Simple validation
  if (!empId || !password) {
    errorMsg.textContent = 'Please enter both Employee ID and Password';
    errorMsg.style.display = 'block';
    if (!empId) document.getElementById('empId').classList.add('error');
    if (!password) document.getElementById('password').classList.add('error');
    return;
  }
  
  // Loading state
  loginBtn.disabled = true;
  btnText.style.display = 'none';
  loginBtn.innerHTML += '<div class="spinner"></div>';
  
  // Call backend API
  fetch('http://127.0.0.1:8000/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ employee_id: empId, password: password })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Invalid Employee ID or Password');
    }
    return response.json();
  })
  .then(data => {
    // Save JWT
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('user_role', data.role);
    localStorage.setItem('user_name', data.name);
    localStorage.setItem('employee_id', data.employee_id);
    
    // Success state
    loginBtn.innerHTML = '<i class="fa-solid fa-check"></i>';
    loginBtn.classList.remove('btn-primary');
    loginBtn.style.backgroundColor = 'var(--status-success)';
    
    // Redirect to role dashboard (absolute path for reliability)
    setTimeout(() => {
      const base = window.location.origin + window.location.pathname.replace(/[^\/]*$/, '');
      if (data.role === 'manager') {
         window.location.href = base + 'home_page_manager.html';
      } else if (data.role === 'supervisor') {
         window.location.href = base + 'home_page_supervisor.html';
      } else {
         window.location.href = base + 'home_page_engineer.html';
      }
    }, 800);
  })
  .catch(error => {
    // Error state
    const spinner = loginBtn.querySelector('.spinner');
    if (spinner) spinner.remove();
    loginBtn.disabled = false;
    btnText.style.display = 'block';
    
    // Distinguish network errors from auth errors
    const msg = error.message.includes('fetch') || error.message.includes('NetworkError')
      ? 'Cannot reach server. Make sure the backend is running on port 8000.'
      : error.message;
    errorMsg.textContent = msg;
    errorMsg.style.display = 'block';
    document.getElementById('empId').classList.add('error');
    document.getElementById('password').classList.add('error');
  });
}

function quickLogin(empId, password) {
  document.getElementById('empId').value = empId;
  document.getElementById('password').value = password;
  const fakeEvent = { preventDefault: () => {} };
  handleLogin(fakeEvent);
}

/**
 * Toggles password visibility
 */
function togglePassword(inputId, iconId) {
  const input = document.getElementById(inputId);
  const icon = document.getElementById(iconId);
  
  if (input.type === 'password') {
    input.type = 'text';
    icon.classList.remove('fa-eye');
    icon.classList.add('fa-eye-slash');
  } else {
    input.type = 'password';
    icon.classList.remove('fa-eye-slash');
    icon.classList.add('fa-eye');
  }
}
