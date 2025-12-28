// ============================================================================
// SMART ATHLETE HEALTH DASHBOARD - Main JavaScript (COMPLETE REWRITE)
// ============================================================================

const API_URL = window.location.origin + '/api';
const UPDATE_INTERVAL = 5000;
const ABNORMAL_TEMP_THRESHOLD = 36.5;

const getAuthToken = () => localStorage.getItem('auth_token');

async function apiCall(endpoint, options = {}) {
  const token = getAuthToken();
  if (!token) {
    window.location.href = '/';
    return null;
  }
  
  try {
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers
      },
      credentials: 'include'
    });
    
    if (response.status === 401) {
      localStorage.clear();
      window.location.href = '/';
      return null;
    }
    
    return response;
  } catch (error) {
    console.error('API call error:', error);
    return null;
  }
}

let heartRateChart, tempChart, loginHeartRateChart, loginTempChart;
let selectedLoginId = null;
let loginSessions = [];

function initCharts() {
  const hrCtx = document.getElementById('heartRateChart');
  const tempCtx = document.getElementById('tempChart');
  const loginHrCtx = document.getElementById('loginHeartRateChart');
  const loginTempCtx = document.getElementById('loginTempChart');
  
  if (hrCtx) {
    heartRateChart = new Chart(hrCtx.getContext('2d'), {
      type: 'line',
      data: { labels: [], datasets: [{ label: 'Heart Rate (BPM)', data: [], borderColor: '#3b82f6', fill: true, tension: 0.4 }] },
      options: { responsive: true, scales: { y: { min: 40, max: 180 } } }
    });
  }

  if (tempCtx) {
    tempChart = new Chart(tempCtx.getContext('2d'), {
      type: 'line',
      data: { labels: [], datasets: [{ label: 'Temperature (°C)', data: [], borderColor: '#f97316', fill: true, tension: 0.4 }] },
      options: { responsive: true, scales: { y: { min: 35, max: 42 } } }
    });
  }

  if (loginHrCtx) {
    loginHeartRateChart = new Chart(loginHrCtx.getContext('2d'), {
      type: 'line',
      data: { labels: [], datasets: [{ label: 'Heart Rate (BPM)', data: [], borderColor: '#ef4444', fill: true, tension: 0.4, pointRadius: 0 }] },
      options: { responsive: true, scales: { y: { min: 40, max: 180 } } }
    });
  }

  if (loginTempCtx) {
    loginTempChart = new Chart(loginTempCtx.getContext('2d'), {
      type: 'line',
      data: { labels: [], datasets: [{ label: 'Temperature (°C)', data: [], borderColor: '#f97316', fill: true, tension: 0.4, pointRadius: 0 }] },
      options: { responsive: true, scales: { y: { min: 35, max: 40 } } }
    });
  }
}

async function updateDashboard() {
  try {
    const response = await apiCall('/latest-data');
    if (!response || !response.ok) throw new Error('No response');

    const data = await response.json();
    if (!data || !data.heart_rate) throw new Error('Invalid data');
    
    const hrEl = document.getElementById('heartRateValue');
    const tempEl = document.getElementById('tempValue');
    if (hrEl) hrEl.textContent = `${parseFloat(data.heart_rate).toFixed(2)} BPM`;
    if (tempEl) tempEl.textContent = `${parseFloat(data.temperature).toFixed(1)} °C`;

    checkAlert(data);
    await updateCharts();
    await loadLoginSessions();
  } catch (error) {
    console.error("Error updating dashboard:", error);
  }
}

function checkAlert(data) {
  const alertBox = document.getElementById('alertBox');
  const alertMessage = document.getElementById('alertMessage');
  
  if (data.is_abnormal && alertBox) {
    alertBox.classList.remove('hidden');
    if (alertMessage) alertMessage.textContent = data.alert_message || 'Abnormal readings detected!';
  } else if (alertBox) {
    alertBox.classList.add('hidden');
  }
}

async function updateCharts() {
  try {
    const response = await apiCall('/history?hours=24');
    if (!response || !response.ok) return;
    
    const records = await response.json();
    if (!records || records.length === 0) return;

    const labels = records.map(d => {
      const date = new Date(d.timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    });
    
    if (heartRateChart && heartRateChart.data) {
      heartRateChart.data.labels = labels;
      heartRateChart.data.datasets[0].data = records.map(d => parseFloat(d.heart_rate));
      heartRateChart.update();
    }

    if (tempChart && tempChart.data) {
      tempChart.data.labels = labels;
      tempChart.data.datasets[0].data = records.map(d => parseFloat(d.temperature));
      tempChart.update();
    }
  } catch (error) {
    console.error("Error updating charts:", error);
  }
}

async function loadLoginSessions() {
  try {
    const response = await apiCall('/history?hours=168');
    if (!response || !response.ok) return;
    
    const allData = await response.json();
    if (!allData || allData.length === 0) {
      const list = document.getElementById('loginHistoryList');
      if (list) list.innerHTML = '<p class="loading-message">No data available</p>';
      return;
    }

    loginSessions = [{
      id: 1,
      startTime: new Date(allData[0].timestamp),
      data: allData
    }];

    renderLoginHistory();
    if (loginSessions.length > 0) {
      selectedLoginId = loginSessions[0].id;
      updateWaveformCharts(loginSessions[0]);
    }
  } catch (error) {
    console.error('Error loading login sessions:', error);
  }
}

function renderLoginHistory() {
  const list = document.getElementById('loginHistoryList');
  if (!list) return;
  
  list.innerHTML = '';
  loginSessions.forEach(session => {
    const btn = document.createElement('button');
    btn.className = `login-item ${selectedLoginId === session.id ? 'active' : ''}`;
    
    const startTime = new Date(session.startTime);
    const endTime = new Date(session.data[session.data.length - 1].timestamp);
    const duration = Math.round((endTime - startTime) / (1000 * 60));
    
    btn.innerHTML = `
      <p class="login-time">${startTime.toLocaleDateString()}</p>
      <p class="login-info">${startTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
      <p class="login-info">Duration: ${duration} min</p>
    `;
    
    btn.addEventListener('click', () => {
      selectedLoginId = session.id;
      renderLoginHistory();
      updateWaveformCharts(session);
    });
    
    list.appendChild(btn);
  });
}

function updateWaveformCharts(session) {
  if (!session || !session.data || session.data.length === 0) return;

  const labels = session.data.map(d => {
    const date = new Date(d.timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  });
  
  const hrData = session.data.map(d => parseFloat(d.heart_rate));
  const tempData = session.data.map(d => parseFloat(d.temperature));

  if (loginHeartRateChart && loginHeartRateChart.data) {
    loginHeartRateChart.data.labels = labels;
    loginHeartRateChart.data.datasets[0].data = hrData;
    loginHeartRateChart.update('none');
  }

  if (loginTempChart && loginTempChart.data) {
    loginTempChart.data.labels = labels;
    loginTempChart.data.datasets[0].data = tempData;
    loginTempChart.update('none');
  }

  const avgHR = Math.round(hrData.reduce((a, b) => a + b, 0) / hrData.length);
  const maxHR = Math.max(...hrData);
  const avgTemp = (tempData.reduce((a, b) => a + b, 0) / tempData.length).toFixed(1);
  const duration = Math.round((new Date(session.data[session.data.length - 1].timestamp) - new Date(session.startTime)) / (1000 * 60));

  const els = {
    avgHR: document.getElementById('avgHR'),
    maxHR: document.getElementById('maxHR'),
    avgTemp: document.getElementById('avgTemp'),
    duration: document.getElementById('duration')
  };

  if (els.avgHR) els.avgHR.textContent = `${avgHR} BPM`;
  if (els.maxHR) els.maxHR.textContent = `${maxHR} BPM`;
  if (els.avgTemp) els.avgTemp.textContent = `${avgTemp}°C`;
  if (els.duration) els.duration.textContent = `${duration} min`;
}

async function loadSessionAbnormalHistory() {
  try {
    const btn = document.getElementById('refreshSessionHistoryBtn');
    const body = document.getElementById('sessionHistoryTableBody');
    const container = document.getElementById('sessionHistoryTableContainer');
    const noMsg = document.getElementById('noSessionHistoryMessage');
    
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Loading...';
    }

    const response = await apiCall('/history?hours=168');
    if (!response || !response.ok) throw new Error('Failed');
    
    const allRecords = await response.json();
    const abnormalRecords = allRecords.filter(record => {
      const temp = parseFloat(record.temperature);
      const hr = parseFloat(record.heart_rate);
      return temp > ABNORMAL_TEMP_THRESHOLD || hr > 120;
    });

    if (abnormalRecords.length === 0) {
      if (body) body.innerHTML = '';
      if (noMsg) noMsg.classList.remove('hidden');
      if (container) container.classList.add('hidden');
    } else {
      if (noMsg) noMsg.classList.add('hidden');
      if (container) container.classList.remove('hidden');
      if (body) body.innerHTML = '';
      
      abnormalRecords.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
      abnormalRecords.forEach(record => {
        const row = document.createElement('tr');
        const temp = parseFloat(record.temperature);
        const hr = parseFloat(record.heart_rate);
        const date = new Date(record.timestamp);
        
        const tempClass = temp > 38.5 ? 'text-red-600 font-bold' : 'text-orange-600 font-semibold';
        const badge = temp > 38.5 
          ? '<span class="px-2 py-1 bg-red-100 text-red-800 rounded-full text-xs font-bold">🔴 CRITICAL</span>'
          : '<span class="px-2 py-1 bg-orange-100 text-orange-800 rounded-full text-xs font-bold">🟠 WARNING</span>';
        
        row.innerHTML = `
          <td class="px-6 py-4"><div class="text-sm font-medium">${date.toLocaleDateString()}</div></td>
          <td class="px-6 py-4"><div class="text-sm">${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</div></td>
          <td class="px-6 py-4"><div class="text-lg ${tempClass}">${temp.toFixed(1)} °C</div></td>
          <td class="px-6 py-4"><div class="text-sm">${hr.toFixed(0)} BPM</div></td>
          <td class="px-6 py-4">${badge}</td>
        `;
        if (body) body.appendChild(row);
      });
    }
  } catch (error) {
    console.error("Error loading session history:", error);
  } finally {
    const btn = document.getElementById('refreshSessionHistoryBtn');
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Refresh';
    }
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  const token = getAuthToken();
  if (!token) {
    window.location.href = '/';
    return;
  }

  // Set username
  const username = localStorage.getItem('username');
  const usernameEl = document.getElementById('username');
  if (username && usernameEl) {
    usernameEl.textContent = username;
  }
  
  initCharts();
  
  // Verify session and get user ID
  try {
    const verifyResponse = await apiCall('/verify-session');
    if (verifyResponse && verifyResponse.ok) {
      const userData = await verifyResponse.json();
      if (userData.user) {
        localStorage.setItem('user_id', userData.user.id);
        const userIdEl = document.getElementById('userId');
        if (userIdEl) {
          userIdEl.textContent = `(ID: ${userData.user.id})`;
        }
      }
    }
  } catch (error) {
    console.error('Error verifying session:', error);
  }
  
  // Event listeners
  const toggleBtn = document.getElementById('toggleWaveform');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const content = document.getElementById('waveformContent');
      if (content) {
        content.classList.toggle('hidden');
        toggleBtn.textContent = content.classList.contains('hidden') ? 'Show Details' : 'Hide Details';
      }
    });
  }

  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      
      // Create modal overlay
      const modal = document.createElement('div');
      modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 9999; animation: fadeInBackdrop 0.4s cubic-bezier(0.16, 1, 0.3, 1);';
      
      // Create modal content
      const content = document.createElement('div');
      content.style.cssText = 'background: white; padding: 2.5rem; border-radius: 1rem; max-width: 350px; box-shadow: 0 25px 50px rgba(0,0,0,0.2); animation: slideUpScale 0.5s cubic-bezier(0.16, 1, 0.3, 1); text-align: center;';
      content.innerHTML = `
        <div style="width: 60px; height: 60px; margin: 0 auto 1.5rem; border-radius: 50%; border: 3px solid #f59e0b; display: flex; align-items: center; justify-content: center; font-size: 2rem; color: #f59e0b;">!</div>
        <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem; color: #1f2937;">Are you sure?</h2>
        <p style="color: #6b7280; margin-bottom: 2rem; font-size: 0.95rem;">Do you want to logout?</p>
        <div style="display: flex; gap: 1rem; justify-content: center;">
          <button id="cancelBtn" style="padding: 0.75rem 1.5rem; border: none; border-radius: 0.375rem; background: #ef4444; color: white; font-weight: 600; cursor: pointer; transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); font-size: 0.95rem;">
            Cancel
          </button>
          <button id="confirmBtn" style="padding: 0.75rem 1.5rem; border: none; border-radius: 0.375rem; background: #3b82f6; color: white; font-weight: 600; cursor: pointer; transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); font-size: 0.95rem;">
            Yes, logout
          </button>
        </div>
      `;
      
      modal.appendChild(content);
      document.body.appendChild(modal);
      
      // Add animations if not already present
      if (!document.querySelector('style[data-logout-modal]')) {
        const style = document.createElement('style');
        style.setAttribute('data-logout-modal', 'true');
        style.textContent = `
          @keyframes fadeInBackdrop { 
            from { 
              opacity: 0; 
            } 
            to { 
              opacity: 1; 
            } 
          }
          
          @keyframes slideUpScale { 
            0% { 
              opacity: 0; 
              transform: translateY(40px) scale(0.85);
            } 
            50% {
              opacity: 1;
            }
            100% { 
              opacity: 1; 
              transform: translateY(0) scale(1);
            } 
          }
        `;
        document.head.appendChild(style);
      }
      
      // Button handlers
      const cancelBtn = document.getElementById('cancelBtn');
      const confirmBtn = document.getElementById('confirmBtn');
      
      // Add hover effects
      cancelBtn.addEventListener('mouseenter', () => {
        cancelBtn.style.background = '#dc2626';
        cancelBtn.style.transform = 'translateY(-2px)';
      });
      cancelBtn.addEventListener('mouseleave', () => {
        cancelBtn.style.background = '#ef4444';
        cancelBtn.style.transform = 'translateY(0)';
      });
      
      confirmBtn.addEventListener('mouseenter', () => {
        confirmBtn.style.background = '#2563eb';
        confirmBtn.style.transform = 'translateY(-2px)';
      });
      confirmBtn.addEventListener('mouseleave', () => {
        confirmBtn.style.background = '#3b82f6';
        confirmBtn.style.transform = 'translateY(0)';
      });
      
      cancelBtn.addEventListener('click', () => {
        modal.style.animation = 'fadeInBackdrop 0.3s cubic-bezier(0.16, 1, 0.3, 1) reverse';
        setTimeout(() => modal.remove(), 300);
      });
      
      confirmBtn.addEventListener('click', async () => {
        // Show success state
        content.innerHTML = `
          <div style="width: 60px; height: 60px; margin: 0 auto 1.5rem; border-radius: 50%; border: 3px solid #10b981; display: flex; align-items: center; justify-content: center; font-size: 2rem; color: #10b981;">✓</div>
          <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem; color: #1f2937;">Logged Out!</h2>
          <p style="color: #6b7280; margin-bottom: 2rem; font-size: 0.95rem;">You have been successfully logged out.</p>
        `;
        
        setTimeout(async () => {
          await apiCall('/logout', { method: 'POST' });
          localStorage.clear();
          window.location.href = '/';
        }, 1500);
      });
      
      // Close modal when clicking outside
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          modal.style.animation = 'fadeInBackdrop 0.3s cubic-bezier(0.16, 1, 0.3, 1) reverse';
          setTimeout(() => modal.remove(), 300);
        }
      });
    });
  }

  const refreshSessionBtn = document.getElementById('refreshSessionHistoryBtn');
  if (refreshSessionBtn) {
    refreshSessionBtn.addEventListener('click', async () => {
      await loadSessionAbnormalHistory();
    });
  }
  
  // Initial load
  await updateDashboard();
  await loadLoginSessions();
  await loadSessionAbnormalHistory();
  
  // Auto-refresh
  setInterval(updateDashboard, UPDATE_INTERVAL);
});