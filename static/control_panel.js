// TEP Control Panel JavaScript - Safari Compatible
// VERSION: 2025-09-30-22:00 - SAFARI CACHE FIX v2
console.log('🚀 External JavaScript file loading...');
console.log('📦 JavaScript Version: 2025-09-30-22:00 - SAFARI CACHE FIX v2');
console.log('🌐 User Agent:', navigator.userAgent);

// Safari compatibility polyfills
if (!Array.prototype.forEach) {
    Array.prototype.forEach = function(callback, thisArg) {
        for (var i = 0; i < this.length; i++) {
            callback.call(thisArg, this[i], i, this);
        }
    };
}

// Global error handler
window.onerror = function(msg, url, lineNo, columnNo, error) {
    console.error('JavaScript Error:', msg, 'at line', lineNo);
    alert('JavaScript Error: ' + msg);
    return false;
};

// Test functions
function simpleTest() {
    alert('Simple test button clicked!');
    console.log('Simple test button clicked!');
    var statusEl = document.getElementById('status');
    if (statusEl) {
        statusEl.innerHTML = '<div style="background: blue; color: white; padding: 10px;">Button clicked at ' + new Date().toLocaleTimeString() + '</div>';
    }
}

function testFunction() {
    console.log('testFunction() executed');
    alert('Test function works!');
    showMessage('Test function works!', 'success');
}

// Anomaly Detection Stabilization Functions
function checkPCAStatus() {
    console.log('📊 Checking Anomaly Detection status...');
    fetch('/api/pca/status')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            console.log('📊 Anomaly Detection Status:', data);

            var statusText = '📊 Anomaly Detection Status: ';
            var messageType = 'info';

            if (data.training_mode) {
                var progress = Math.round(data.progress);
                statusText += 'Training in Progress (' + data.collected + '/' + data.target + ' = ' + progress + '%)';
                messageType = 'info';

                // Update progress display
                var progressDiv = document.getElementById('training-progress');
                var progressBar = document.getElementById('progress-bar');

                if (progressDiv && progressBar) {
                    progressDiv.style.display = 'block';
                    progressBar.style.width = progress + '%';
                }

                // If training is active, start monitoring (reduced frequency)
                setTimeout(monitorPCAProgress, 10000);

            } else if (data.is_stable) {
                statusText += 'System Stable ✅ - Ready for Retraining';
                messageType = 'success';

                // Hide progress display
                var progressDiv = document.getElementById('training-progress');
                if (progressDiv) {
                    progressDiv.style.display = 'none';
                }

            } else {
                statusText += 'System Stabilizing... ⏳ (Buffer: ' + data.stability_buffer_size + '/20)';
                messageType = 'warning';

                // Hide progress display
                var progressDiv = document.getElementById('training-progress');
                if (progressDiv) {
                    progressDiv.style.display = 'none';
                }
            }

            showMessage(statusText, messageType);
        })
        .catch(function(error) {
            console.error('❌ Anomaly Detection status check failed:', error);
            showMessage('❌ Anomaly Detection status check failed: ' + error.message, 'error');
        });
}

function stabilizePCA() {
    console.log('🎯 Starting Anomaly Detection stabilization...');
    showMessage('🔍 Checking system stability...', 'info');

    fetch('/api/pca/stabilize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        console.log('🎯 Anomaly Detection Stabilization Response:', data);
        if (data.success) {
            showMessage('✅ ' + data.message, 'success');

            // Show progress display immediately
            var progressDiv = document.getElementById('training-progress');
            var progressBar = document.getElementById('progress-bar');

            if (progressDiv && progressBar) {
                progressDiv.style.display = 'block';
                progressBar.style.width = '0%';
            }

            // Start monitoring progress (reduced frequency)
            setTimeout(monitorPCAProgress, 5000);

        } else {
            showMessage('⚠️ ' + data.message, 'warning');

            // Hide progress display if system not stable
            var progressDiv = document.getElementById('training-progress');
            if (progressDiv) {
                progressDiv.style.display = 'none';
            }
        }
    })
    .catch(function(error) {
        console.error('❌ Anomaly Detection stabilization failed:', error);
        showMessage('❌ Anomaly Detection stabilization failed: ' + error.message, 'error');
    });
}

function monitorPCAProgress() {
    fetch('/api/pca/status')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            console.log('📊 PCA Training Status:', data);

            if (data.training_mode) {
                var progress = Math.round(data.progress);

                // Update the progress display in the HTML
                var progressDiv = document.getElementById('training-progress');
                var progressBar = document.getElementById('progress-bar');

                if (progressDiv && progressBar) {
                    progressDiv.style.display = 'block';
                    progressBar.style.width = progress + '%';
                }

                // Show message with progress
                showMessage('📊 Anomaly Detection Training: ' + data.collected + '/' + data.target + ' (' + progress + '%) - ' +
                           (data.target - data.collected) + ' more needed', 'info');

                // Continue monitoring every 10 seconds (reduced from 2s to prevent API spam)
                setTimeout(monitorPCAProgress, 10000);

            } else {
                // Training completed - hide progress display
                var progressDiv = document.getElementById('training-progress');
                if (progressDiv) {
                    progressDiv.style.display = 'none';
                }

                showMessage('✅ Anomaly Detection Training Complete! Model updated and ready.', 'success');
            }
        })
        .catch(function(error) {
            console.error('❌ PCA progress monitoring failed:', error);
            showMessage('PCA progress monitoring failed: ' + error.message, 'error');
        });
}

function showMessage(message, type) {
    console.log('showMessage:', message, type);
    var statusDiv = document.getElementById('status');
    if (!statusDiv) {
        console.error('Status div not found!');
        alert(message);
        return;
    }

    // Clear previous content and set new message
    statusDiv.textContent = message;
    statusDiv.className = type === 'success' ? 'btn-success' :
                         type === 'error' ? 'btn-danger' : 'btn-primary';
    statusDiv.style.display = 'block';
    statusDiv.style.padding = '15px';
    statusDiv.style.borderRadius = '8px';
    statusDiv.style.marginBottom = '20px';
    statusDiv.style.fontWeight = 'bold';
    statusDiv.style.fontSize = '16px';
    statusDiv.style.textAlign = 'center';
    statusDiv.style.border = '2px solid ' + (type === 'success' ? '#4CAF50' :
                                           type === 'error' ? '#f44336' : '#2196F3');

    // Auto-hide after 5 seconds
    setTimeout(function() {
        statusDiv.style.display = 'none';
    }, 5000);
}

// Enhanced button feedback function
function showButtonFeedback(buttons, success) {
    for (var i = 0; i < buttons.length; i++) {
        if (buttons[i]) {
            var btn = buttons[i];
            var originalClass = btn.className;

            if (success) {
                btn.classList.add('btn-success');
                btn.style.transform = 'scale(1.05)';
                btn.style.boxShadow = '0 4px 8px rgba(76, 175, 80, 0.3)';

                (function(button, origClass) {
                    setTimeout(function() {
                        button.classList.remove('btn-success');
                        button.style.transform = '';
                        button.style.boxShadow = '';
                    }, 1200);
                })(btn, originalClass);
            } else {
                btn.classList.add('btn-danger');
                btn.style.transform = 'scale(1.05)';
                btn.style.boxShadow = '0 4px 8px rgba(244, 67, 54, 0.3)';

                (function(button, origClass) {
                    setTimeout(function() {
                        button.classList.remove('btn-danger');
                        button.style.transform = '';
                        button.style.boxShadow = '';
                    }, 1200);
                })(btn, originalClass);
            }
        }
    }
}

function startBackend() {
    console.log('startBackend() called from external JS');
    var btns = document.querySelectorAll("button[onclick*='startBackend']");
    console.log('Found buttons:', btns.length);

    // Disable buttons and show loading state
    for (var i = 0; i < btns.length; i++) {
        if (btns[i]) {
            btns[i].disabled = true;
            btns[i].style.opacity = '0.7';
        }
    }

    fetch('/api/faultexplainer/backend/start', {method: 'POST'})
        .then(function(response) {
            console.log('Backend response:', response.status);
            return response.json();
        })
        .then(function(data) {
            console.log('Backend data:', data);
            showMessage(data.message, data.success ? 'success' : 'error');
            showButtonFeedback(btns, data.success);

            // Force status update after successful start
            if (data.success) {
                setTimeout(updateStatus, 1000);
            }
        })
        .catch(function(e) {
            console.error('Backend error:', e);
            showMessage('Backend start failed: ' + e, 'error');
            showButtonFeedback(btns, false);
        })
        .finally(function() {
            for (var i = 0; i < btns.length; i++) {
                if (btns[i]) {
                    btns[i].disabled = false;
                    btns[i].style.opacity = '1';
                }
            }
        });
}

function stopBackend() {
    console.log('stopBackend() called from external JS');
    var btns = document.querySelectorAll("button[onclick*='stopBackend']");

    for (var i = 0; i < btns.length; i++) {
        if (btns[i]) {
            btns[i].disabled = true;
            btns[i].style.opacity = '0.7';
        }
    }

    fetch('/api/faultexplainer/backend/stop', {method: 'POST'})
        .then(function(response) { return response.json(); })
        .then(function(data) {
            showMessage(data.message, data.success ? 'success' : 'error');
            showButtonFeedback(btns, data.success);
            if (data.success) {
                setTimeout(updateStatus, 1000);
            }
        })
        .catch(function(e) {
            showMessage('Backend stop failed: ' + e, 'error');
            showButtonFeedback(btns, false);
        })
        .finally(function() {
            for (var i = 0; i < btns.length; i++) {
                if (btns[i]) {
                    btns[i].disabled = false;
                    btns[i].style.opacity = '1';
                }
            }
        });
}

function stopFrontend() {
    console.log('stopFrontend() called from external JS');
    var btns = document.querySelectorAll("button[onclick*='stopFrontend']");

    for (var i = 0; i < btns.length; i++) {
        if (btns[i]) btns[i].disabled = true;
    }

    fetch('/api/faultexplainer/frontend/stop', {method: 'POST'})
        .then(function(response) { return response.json(); })
        .then(function(data) {
            showMessage(data.message, data.success ? 'success' : 'error');
            if (data.success) {
                setTimeout(updateStatus, 1000);
            }
        })
        .catch(function(e) {
            showMessage('Frontend stop failed: ' + e, 'error');
        })
        .finally(function() {
            for (var i = 0; i < btns.length; i++) {
                if (btns[i]) btns[i].disabled = false;
            }
        });
}

function startTEP() {
    console.log('startTEP() called from external JS');
    var btns = document.querySelectorAll("button[onclick*='startTEP']");

    // Disable buttons and show loading state
    for (var i = 0; i < btns.length; i++) {
        if (btns[i]) {
            btns[i].disabled = true;
            btns[i].style.opacity = '0.7';
        }
    }

    fetch('/api/tep/start', {method: 'POST'})
        .then(function(response) { return response.json(); })
        .then(function(data) {
            showMessage(data.message, data.success ? 'success' : 'error');
            showButtonFeedback(btns, data.success);

            // Force status update after successful start
            if (data.success) {
                setTimeout(updateStatus, 1000);
            }
        })
        .catch(function(e) {
            showMessage('Start TEP failed: ' + e, 'error');
            showButtonFeedback(btns, false);
        })
        .finally(function() {
            for (var i = 0; i < btns.length; i++) {
                if (btns[i]) {
                    btns[i].disabled = false;
                    btns[i].style.opacity = '1';
                }
            }
        });
}

function startFrontend() {
    console.log('startFrontend() called from external JS');
    var btns = document.querySelectorAll("button[onclick*='startFrontend']");

    for (var i = 0; i < btns.length; i++) {
        if (btns[i]) btns[i].disabled = true;
    }

    fetch('/api/faultexplainer/frontend/start', {method: 'POST'})
        .then(function(response) { return response.json(); })
        .then(function(data) {
            showMessage(data.message, data.success ? 'success' : 'error');
            if (data.success) {
                for (var i = 0; i < btns.length; i++) {
                    btns[i].classList.add('btn-success');
                    (function(btn) {
                        setTimeout(function() { btn.classList.remove('btn-success'); }, 800);
                    })(btns[i]);
                }
            }
        })
        .catch(function(e) { showMessage('Frontend start failed: ' + e, 'error'); })
        .finally(function() {
            for (var i = 0; i < btns.length; i++) {
                if (btns[i]) btns[i].disabled = false;
            }
        });
}

function startBridge() {
    console.log('startBridge() called from external JS');
    fetch('/api/bridge/start', {method: 'POST'})
        .then(function(r) { return r.json(); })
        .then(function(d) { showMessage(d.message, d.success ? 'success' : 'error'); })
        .catch(function(e) { showMessage('Bridge start failed: ' + e, 'error'); });
}

function stopBridge() {
    console.log('stopBridge() called from external JS');
    fetch('/api/bridge/stop', {method: 'POST'})
        .then(function(r) { return r.json(); })
        .then(function(d) { showMessage(d.message, d.success ? 'success' : 'error'); })
        .catch(function(e) { showMessage('Bridge stop failed: ' + e, 'error'); });
}

function setSpeed(mode) {
    console.log('setSpeed() called with mode:', mode);

    // Find the clicked button for feedback
    var clickedBtn = mode === 'demo' ? document.getElementById('btn-speed-demo') :
                     mode === 'real' ? document.getElementById('btn-speed-real') : null;
    var btns = clickedBtn ? [clickedBtn] : [];

    // Show loading state
    if (clickedBtn) {
        clickedBtn.disabled = true;
        clickedBtn.style.opacity = '0.7';
    }

    fetch('/api/speed', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({mode: mode})
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        showMessage('Speed set to ' + data.mode + ' (' + data.step_interval_seconds + 's/step)', 'success');
        showButtonFeedback(btns, true);

        // Update UI elements
        var speedModeEl = document.getElementById('speed-mode');
        if (speedModeEl) {
            speedModeEl.textContent = data.mode === 'demo' ? 'Demo (' + data.step_interval_seconds + 's)' : 'Real (' + data.step_interval_seconds + 's)';
        }
        var di = document.getElementById('demo-interval');
        if (di) di.textContent = data.step_interval_seconds;
        var ds = document.getElementById('demo-interval-slider');
        if (ds && data.mode === 'demo') ds.value = data.step_interval_seconds;

        // Update button active states
        var demoBtn = document.getElementById('btn-speed-demo');
        var realBtn = document.getElementById('btn-speed-real');
        if (demoBtn) demoBtn.classList.toggle('btn-active', data.mode === 'demo');
        if (realBtn) realBtn.classList.toggle('btn-active', data.mode !== 'demo');
    })
    .catch(function(e) {
        showMessage('Speed update failed: ' + e, 'error');
        showButtonFeedback(btns, false);
    })
    .finally(function() {
        if (clickedBtn) {
            clickedBtn.disabled = false;
            clickedBtn.style.opacity = '1';
        }
    });
}

function updateStatus() {
    console.log('updateStatus() called from external JS - timestamp:', new Date().toISOString());
    fetch('/api/status')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            console.log('Status data received:', data);

            // Update TEP status with color change
            var tepStatus = document.getElementById('tep-status');
            var tepStep = document.getElementById('tep-step');
            var tepCard = tepStatus ? tepStatus.closest('.status-card') : null;

            if (tepStatus) tepStatus.textContent = data.tep_running ? 'Running' : 'Stopped';
            if (tepStep) tepStep.textContent = data.current_step;
            if (tepCard) {
                tepCard.className = 'status-card ' + (data.tep_running ? 'status-running' : 'status-stopped');
            }

            // Update backend status with color change
            var backendStatus = document.getElementById('backend-status');
            var backendCard = backendStatus ? backendStatus.closest('.status-card') : null;

            if (backendStatus) backendStatus.textContent = data.backend_running ? 'Running' : 'Stopped';
            if (backendCard) {
                backendCard.className = 'status-card ' + (data.backend_running ? 'status-running' : 'status-stopped');
            }

            // Update frontend status with color change
            var frontendStatus = document.getElementById('frontend-status');
            var frontendCard = frontendStatus ? frontendStatus.closest('.status-card') : null;

            if (frontendStatus) frontendStatus.textContent = data.frontend_running ? 'Running' : 'Stopped';
            if (frontendCard) {
                frontendCard.className = 'status-card ' + (data.frontend_running ? 'status-running' : 'status-stopped');
            }

            // Update data counts
            var rawCount = document.getElementById('raw-count');
            var pcaCount = document.getElementById('pca-count');
            var llmCount = document.getElementById('llm-count');

            if (rawCount) rawCount.textContent = data.raw_data_points || 0;
            if (pcaCount) pcaCount.textContent = data.pca_data_points || 0;
            if (llmCount) llmCount.textContent = data.llm_data_points || 0;

            // Update live connection status
            var liveConnection = document.getElementById('live-connection');
            var liveCount = document.getElementById('live-count');

            if (liveConnection) {
                // Simplified: Connected if TEP is running AND we have data
                var connected = data.tep_running && data.raw_data_points > 0;

                // Debug logging
                console.log('🔴 Live Status Check:', {
                    backend_running: data.backend_running,
                    tep_running: data.tep_running,
                    raw_data_points: data.raw_data_points,
                    connected: connected,
                    element_found: true,
                    current_text: liveConnection.textContent,
                    current_class: liveConnection.className
                });

                // Update text and class
                var newText = connected ? 'Live: Connected' : 'Live: Disconnected';
                var newClass = connected ? 'live-badge live-ok' : 'live-badge live-bad';

                liveConnection.textContent = newText;
                liveConnection.className = newClass;

                console.log('🟢 Live Status Updated:', {
                    new_text: newText,
                    new_class: newClass,
                    actual_text: liveConnection.textContent,
                    actual_class: liveConnection.className
                });
            } else {
                console.error('❌ live-connection element NOT FOUND in DOM!');
            }

            if (liveCount) {
                var totalReceived = (data.raw_data_points || 0);
                liveCount.textContent = 'Received: ' + totalReceived;
            }

            // Update speed display
            var speedModeEl = document.getElementById('speed-mode');
            var speedFactorEl = document.getElementById('speed-factor');
            var speedSlider = document.getElementById('speed-factor-slider');

            if (speedModeEl && data.speed_factor) {
                var speedText = data.speed_factor + 'x (' + data.step_interval_seconds + 's)';
                speedModeEl.textContent = speedText;
            }

            if (speedFactorEl && data.speed_factor) {
                speedFactorEl.textContent = data.speed_factor;
            }

            if (speedSlider && data.speed_factor) {
                speedSlider.value = data.speed_factor;
            }
        })
        .catch(function(error) { console.error('Status update failed:', error); });
}

// Initialize when DOM is ready
function initializeApp() {
    console.log('Initializing app from external JS...');
    try {
        // Update JavaScript status indicator
        var jsStatus = document.getElementById('js-status');
        if (jsStatus) {
            jsStatus.textContent = 'Working ✅';
            jsStatus.style.color = 'green';
        }

        // Test basic functionality
        var statusEl = document.getElementById('status');
        if (statusEl) {
            statusEl.innerHTML = '<div style="background: green; color: white; padding: 10px;">✅ External JavaScript is WORKING!</div>';
        }

        // Initialize dynamic updates
        initializeDynamicUpdates();

        // Test if functions are accessible
        console.log('Testing function availability:');
        console.log('- startTEP:', typeof startTEP);
        console.log('- startBackend:', typeof startBackend);
        console.log('- startFrontend:', typeof startFrontend);
        console.log('- setSpeed:', typeof setSpeed);
        console.log('- startDynamicStatusUpdates:', typeof startDynamicStatusUpdates);

        console.log('✅ External JavaScript initialized successfully');

        // Auto-test backend connection
        autoTestBackend();

    } catch(e) {
        console.error('❌ External JavaScript initialization failed:', e);
        var jsStatus = document.getElementById('js-status');
        if (jsStatus) {
            jsStatus.textContent = 'Error: ' + e.message;
            jsStatus.style.color = 'red';
        }
        alert('Initialization Error: ' + e.message);
    }
}

// GLOBAL SCOPE: Single status update interval management
var statusUpdateInterval = null;
var intervalStarted = false;

function startDynamicStatusUpdates() {
    // Clear any existing interval
    if (statusUpdateInterval) {
        clearInterval(statusUpdateInterval);
        console.log('Cleared existing status update interval:', statusUpdateInterval);
    }

    // Allow global pause from UI
    if (window.globalPauseUpdates) {
        console.log('⏸️ Global pause is ON - not starting status updates');
        return;
    }

    // Fetch backend slider interval to align refresh rate with LLM min interval
    fetch('/api/models/status')
        .then(function(r){ return r.ok ? r.json() : {}; })
        .then(function(cfg){
            var sec = (cfg && cfg.llm_min_interval_seconds) ? cfg.llm_min_interval_seconds : 10;
            // Use at least 10s to avoid UI spam; otherwise follow slider
            var updateRate = Math.max(10000, sec * 1000);
            console.log('Starting status update interval:', updateRate + 'ms (slider=' + sec + 's) at', new Date().toISOString());
            statusUpdateInterval = setInterval(function(){
                if (window.globalPauseUpdates) {
                    console.log('⏸️ Paused - skip this tick');
                    return;
                }
                updateStatus();
            }, updateRate);
            intervalStarted = true;
            console.log('Created new interval with ID:', statusUpdateInterval);
        })
        .catch(function(e){
            console.warn('⚠️ Could not read backend interval, falling back to 10s:', e);
            statusUpdateInterval = setInterval(updateStatus, 10000);
            intervalStarted = true;
        });
}

// Initialize dynamic updates when app starts
function initializeDynamicUpdates() {
    // Start dynamic updates (this will call updateStatus via setInterval)
    startDynamicStatusUpdates();
    // Removed immediate updateStatus() call to prevent duplicate API requests

    // Initialize SSE connection for real-time updates
    initializeSSE();
}

// Global SSE connection
var sseConnection = null;
var sseReconnectAttempts = 0;
var sseMaxReconnectAttempts = 5;

function initializeSSE() {
    console.log('🔌 Initializing SSE connection to /stream');

    try {
        // Close existing connection if any
        if (sseConnection) {
            sseConnection.close();
        }

        // Create new EventSource connection
        sseConnection = new EventSource('/stream');

        // Connection opened
        sseConnection.onopen = function(event) {
            console.log('✅ SSE connection established');
            sseReconnectAttempts = 0;

            // DON'T automatically set "Live: Connected" here!
            // The updateStatus() function will set it based on actual simulation status
            // (TEP running + data points > 0)
            console.log('🔄 SSE connection ready - waiting for status update to determine live status');
        };

        // Receive messages
        sseConnection.onmessage = function(event) {
            try {
                var data = JSON.parse(event.data);
                console.log('📨 SSE event received:', data.event, data.data);

                // Handle different event types
                handleSSEEvent(data);
            } catch (e) {
                console.error('❌ Failed to parse SSE data:', e, event.data);
            }
        };

        // Connection error
        sseConnection.onerror = function(event) {
            console.error('❌ SSE connection error:', event);

            // Update live connection status
            var liveConnection = document.getElementById('live-connection');
            if (liveConnection) {
                liveConnection.textContent = 'Live: Disconnected';
                liveConnection.className = 'live-badge live-bad';
            }

            // Auto-reconnect with exponential backoff
            if (sseReconnectAttempts < sseMaxReconnectAttempts) {
                sseReconnectAttempts++;
                var delay = Math.min(1000 * Math.pow(2, sseReconnectAttempts), 30000);
                console.log('🔄 SSE reconnecting in ' + (delay / 1000) + 's (attempt ' + sseReconnectAttempts + '/' + sseMaxReconnectAttempts + ')');
                setTimeout(initializeSSE, delay);
            } else {
                console.log('❌ SSE max reconnect attempts reached, giving up');
            }
        };

    } catch (e) {
        console.error('❌ Failed to initialize SSE:', e);
    }
}

function handleSSEEvent(data) {
    var eventType = data.event;
    var eventData = data.data;

    console.log('📊 Handling SSE event:', eventType, eventData);

    switch (eventType) {
        case 'connected':
            console.log('✅ SSE stream established:', eventData ? eventData.message || 'connected' : 'connected');
            break;

        case 'llm_started':
            // LLM analysis started
            updateLLMStatus(eventData.model, 'started', eventData);
            break;

        case 'llm_progress':
            // LLM analysis in progress (model loading, thinking, generating)
            updateLLMStatus(eventData.model, 'progress', eventData);
            break;

        case 'llm_completed':
            // LLM analysis completed
            updateLLMStatus(eventData.model, 'completed', eventData);
            break;

        case 'llm_error':
            // LLM analysis error
            updateLLMStatus(eventData.model, 'error', eventData);
            break;

        case 'tep_data':
            // New TEP data point
            updateDataFlowDisplay(eventData);
            break;

        default:
            console.log('⚠️ Unknown SSE event type:', eventType);
    }
}

function updateDataFlowDisplay(eventData) {
    console.log('📊 Updating data flow display:', eventData);

    // Update anomaly detection panel with real-time PCA stats
    if (eventData && eventData.pca_stats) {
        var pcaStatus = document.getElementById('monitor-pca-status');
        var pcaTime = document.getElementById('monitor-pca-time');
        var anomalyScore = document.getElementById('monitor-anomaly-score');

        if (pcaStatus) {
            var isAnomaly = eventData.pca_stats.is_anomaly || false;
            pcaStatus.textContent = isAnomaly ? '🚨 ANOMALY' : '✅ Normal';
            pcaStatus.style.color = isAnomaly ? '#e74c3c' : '#28a745';
        }

        if (pcaTime) {
            pcaTime.textContent = new Date().toLocaleTimeString();
        }

        if (anomalyScore) {
            var t2Score = eventData.pca_stats.t2_stat || 0;
            anomalyScore.textContent = t2Score.toFixed(2);
        }
    }
}

function updateLLMStatus(model, status, data) {
    console.log('🤖 LLM status update:', model, status, data);

    // Update the Multi-LLM panel display
    // This will be implemented to show real-time progress

    // TODO: Add visual indicators in the Multi-LLM Analysis panel
    // For now, just log to console
    if (status === 'started') {
        console.log('🚀 ' + model + ' analysis started');
    } else if (status === 'progress') {
        console.log('⏳ ' + model + ' progress: ' + (data.message || 'Processing...'));
    } else if (status === 'completed') {
        console.log('✅ ' + model + ' completed in ' + data.response_time + 's');
        // Trigger a status update to refresh the display
        setTimeout(updateStatus, 500);
    } else if (status === 'error') {
        console.log('❌ ' + model + ' error: ' + data.error);
    }
}

// Single initialization to prevent duplicate API calls
var appInitialized = false;

function safeInitializeApp() {
    if (appInitialized) {
        console.log('App already initialized, skipping duplicate initialization');
        return;
    }
    appInitialized = true;
    initializeApp();
}

// Multiple initialization methods for Safari compatibility
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', safeInitializeApp);
} else {
    safeInitializeApp();
}

window.onload = function() {
    console.log('Window loaded - checking if initialization needed');
    safeInitializeApp();
};

// Additional missing functions
function stopTEP() {
    console.log('stopTEP() called from external JS');
    var btns = document.querySelectorAll("button[onclick*='stopTEP']");

    for (var i = 0; i < btns.length; i++) {
        if (btns[i]) btns[i].disabled = true;
    }

    // IMMEDIATELY force TEP status card to red (don't wait for API response)
    console.log('✅ Force TEP status card to RED immediately');
    var tepCard = document.querySelector('#tep-status');
    if (tepCard) {
        tepCard.textContent = 'Stopped';
        var tepStatusCard = tepCard.closest('.status-card');
        if (tepStatusCard) {
            tepStatusCard.className = 'status-card status-stopped';
        }
    }

    fetch('/api/tep/stop', {method: 'POST'})
        .then(function(response) { return response.json(); })
        .then(function(data) {
            showMessage(data.message, data.success ? 'success' : 'error');
            if (data.success) {
                for (var i = 0; i < btns.length; i++) {
                    btns[i].classList.add('btn-success');
                    (function(btn) {
                        setTimeout(function() { btn.classList.remove('btn-success'); }, 800);
                    })(btns[i]);
                }

                // ✅ Force status update to show red color immediately (verify)
                setTimeout(updateStatus, 1000);
            }
        })
        .catch(function(e) { showMessage('Stop TEP failed: ' + e, 'error'); })
        .finally(function() {
            for (var i = 0; i < btns.length; i++) {
                if (btns[i]) btns[i].disabled = false;
            }
        });
}

function stopAll() {
    console.log('🛑 EMERGENCY STOP: stopAll() called from external JS');

    // Show immediate feedback
    showMessage('🛑 EMERGENCY STOP: Shutting down all services...', 'warning');

    // Disable the stop button to prevent multiple clicks
    var stopBtn = document.querySelector("button[onclick*='stopAll']");
    if (stopBtn) {
        stopBtn.disabled = true;
        stopBtn.textContent = '🛑 Stopping...';
    }

    // IMMEDIATELY force all status cards to red (don't wait for API response)
    console.log('✅ Force status cards to RED immediately');
    var tepCard = document.querySelector('#tep-status');
    var backendCard = document.querySelector('#backend-status');
    var frontendCard = document.querySelector('#frontend-status');

    if (tepCard) {
        tepCard.textContent = 'Stopped';
        var tepStatusCard = tepCard.closest('.status-card');
        if (tepStatusCard) {
            tepStatusCard.className = 'status-card status-stopped';
        }
    }

    if (backendCard) {
        backendCard.textContent = 'Stopped';
        var backendStatusCard = backendCard.closest('.status-card');
        if (backendStatusCard) {
            backendStatusCard.className = 'status-card status-stopped';
        }
    }

    if (frontendCard) {
        frontendCard.textContent = 'Stopped';
        var frontendStatusCard = frontendCard.closest('.status-card');
        if (frontendStatusCard) {
            frontendStatusCard.className = 'status-card status-stopped';
        }
    }

    // Call the emergency shutdown endpoint (stops EVERYTHING)
    fetch('/api/emergency/shutdown', {method: 'POST'})
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Emergency shutdown failed: HTTP ' + response.status);
            }
            return response.json();
        })
        .then(function(data) {
            console.log('Emergency shutdown result:', data);

            if (data.success) {
                showMessage('✅ Emergency shutdown completed! All processes stopped.', 'success');
            } else {
                showMessage('⚠️ ' + (data.message || 'Shutdown completed with warnings'), 'warning');
            }

            // DON'T call updateStatus() after emergency stop!
            // The backend port 8000 is stopped, so /api/status won't respond correctly
            // Status cards are already set to RED at lines 762-790
            // Let user manually refresh if needed
            console.log('✅ Emergency stop complete - status cards set to STOPPED (RED)');

            // Re-enable button after 5 seconds
            setTimeout(function() {
                if (stopBtn) {
                    stopBtn.disabled = false;
                    stopBtn.textContent = '🛑 Stop Everything';
                }
            }, 5000);
        })
        .catch(function(error) {
            console.error('Emergency stop error:', error);
            showMessage('⚠️ Stop request completed with warnings: ' + error.message, 'warning');

            // DON'T call updateStatus() - backend is stopped!
            // Status cards are already RED (lines 762-790)
            console.log('✅ Emergency stop completed (with error) - status cards remain STOPPED (RED)');

            // Re-enable button
            if (stopBtn) {
                stopBtn.disabled = false;
                stopBtn.textContent = '🛑 Stop Everything';
            }
        });
}

function setLLMInterval(sec) {
    console.log('setLLMInterval() called with:', sec);
    var seconds = parseInt(sec);
    fetch('/api/backend/config/runtime', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ llm_min_interval_seconds: seconds })
    })
    .then(function(r) { return r.json(); })
    .then(function(_) {
        var lab = document.getElementById('llm-interval-label');
        if (lab) lab.textContent = seconds;
        showMessage('LLM refresh interval set to ' + seconds + 's', 'success');
    })
    .catch(function(e) { showMessage('Failed to set LLM interval: ' + e, 'error'); });
}

// Pause/Resume global auto-refresh for unified console
function updatePauseButtonUI() {
    var btn = document.getElementById('btn-pause-refresh');
    if (!btn) return;
    if (window.globalPauseUpdates) {
        btn.textContent = '▶ 恢复更新';
        btn.classList.add('btn-warning');
    } else {
        btn.textContent = '⏸ 暂停更新';
        btn.classList.remove('btn-warning');
    }
}

function toggleGlobalPause() {
    window.globalPauseUpdates = !window.globalPauseUpdates;
    if (window.globalPauseUpdates) {
        if (statusUpdateInterval) {
            clearInterval(statusUpdateInterval);
            statusUpdateInterval = null;
        }
        showMessage('⏸ 已暂停自动刷新', 'info');
    } else {
        startDynamicStatusUpdates();
        showMessage('▶ 已恢复自动刷新', 'success');
    }
    updatePauseButtonUI();
}

// RAG reindex trigger (no upload)
function ragReindex() {
    console.log('ragReindex() called');
    var btn = document.getElementById('btn-rag-reindex');
    if (btn) { btn.disabled = true; btn.classList.add('btn-active'); }
    fetch('/rag/reindex', { method: 'POST' })
        .then(function(r){ return r.json(); })
        .then(function(d){
            if (d.status === 'ok') {
                showMessage('✅ RAG reindexed. Docs: ' + (d.statistics && d.statistics.total_documents), 'success');
            } else {
                showMessage('⚠️ RAG reindex returned non-ok', 'warning');
            }
        })
        .catch(function(e){ showMessage('RAG reindex failed: ' + e, 'error'); })
        .finally(function(){ if (btn) { btn.disabled = false; btn.classList.remove('btn-active'); }});
}

// Initialize pause button label on load
(function(){
    if (typeof window.globalPauseUpdates === 'undefined') {
        window.globalPauseUpdates = false;
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updatePauseButtonUI);
    } else {
        updatePauseButtonUI();
    }
})();


function checkBaselineStatus() {
    console.log('checkBaselineStatus() called from external JS');
    fetch(window.location.protocol + '//' + window.location.hostname + ':8000/metrics')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            showMessage('Backend ok. live_buffer=' + data.live_buffer + ', window=' + data.pca_window + ', baseline_features=' + data.baseline_features, 'success');
        })
        .catch(function(e) {
            showMessage('Metrics check failed: ' + e, 'error');
        });
}

function restartTEP() {
    console.log('restartTEP() called from external JS');
    fetch('/api/tep/restart', {method: 'POST'})
        .then(function(r) { return r.json(); })
        .then(function(d) { showMessage(d.message, d.success ? 'success' : 'error'); })
        .catch(function(e) { showMessage('Restart failed: ' + e, 'error'); });
}

function systemHealthCheck() {
    console.log('systemHealthCheck() called');
    showMessage('Checking system health...', 'info');

    fetch('/api/health')
        .then(function(r) { return r.json(); })
        .then(function(health) {
            var message = '🔍 System Health Check:\n\n';
            message += 'Overall Status: ' + health.overall_status + '\n\n';

            message += 'Components:\n';
            for (var component in health.components) {
                message += '• ' + component + ': ' + health.components[component] + '\n';
            }

            if (health.issues.length > 0) {
                message += '\nIssues Found:\n';
                for (var i = 0; i < health.issues.length; i++) {
                    message += '⚠️ ' + health.issues[i] + '\n';
                }
            }

            if (health.recommendations.length > 0) {
                message += '\nRecommendations:\n';
                for (var i = 0; i < health.recommendations.length; i++) {
                    message += '💡 ' + health.recommendations[i] + '\n';
                }
            }

            var isReady = health.overall_status.indexOf('✅') !== -1;
            showMessage(message, isReady ? 'success' : 'error');

            // Also show in alert for better visibility
            alert(message);
        })
        .catch(function(e) {
            showMessage('Health check failed: ' + e, 'error');
        });
}

function ultraStart() {
    console.log('ultraStart() called - One-click 50x speed startup');
    showMessage('🚀 Starting ultra-fast system (50x speed)...', 'info');

    fetch('/api/ultra_start', {method: 'POST'})
        .then(function(r) { return r.json(); })
        .then(function(data) {
            showMessage(data.message, data.success ? 'success' : 'error');

            if (data.success) {
                // 🔥 CRITICAL FIX: Restart dynamic updates for ultra speed
                console.log('🔄 Restarting dynamic status updates for ultra speed (50x)');
                startDynamicStatusUpdates();

                // Force status update to show new speed
                setTimeout(updateStatus, 1000);

                // Show success alert
                alert('🎉 ULTRA-FAST SYSTEM READY!\n\n' +
                      '⚡ Speed: 50x (data every ' + data.interval_seconds.toFixed(1) + 's)\n' +
                      '📊 Monitor: http://localhost:3000\n' +
                      '🔥 You should see VERY fast updates now!\n' +
                      '📱 Frontend will update every ' + Math.max(1, 5/50).toFixed(1) + 's');
            }
        })
        .catch(function(e) {
            showMessage('Ultra start failed: ' + e, 'error');
        });
}

function loadLog(name) {
    console.log('loadLog() called with:', name);
    fetch('/api/logs/' + name)
        .then(function(r) { return r.json(); })
        .then(function(d) {
            var el = document.getElementById('log-view');
            if (el) {
                el.textContent = (d.lines || []).join('');
                el.scrollTop = el.scrollHeight;
            }
        })
        .catch(function(e) {
            showMessage('Failed to load log: ' + e, 'error');
        });
}

function clearLog() {
    console.log('clearLog() called from external JS');
    var el = document.getElementById('log-view');
    if (el) el.textContent = '';
}

// More missing functions
function reloadBaseline() {
    console.log('reloadBaseline() called from external JS');
    var btn = document.getElementById('btn-reload-baseline');
    if (btn) {
        btn.disabled = true;
        btn.classList.add('btn-active');
    }
    fetch('/api/backend/config/baseline/reload', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({})
    })
    .then(function(r) {
        return r.text().then(function(t) {
            try {
                return JSON.parse(t);
            } catch(e) {
                return {status: 'error', error: 'Non-JSON (' + r.status + '): ' + t.slice(0, 160)};
            }
        });
    })
    .then(function(data) {
        if (data.status === 'ok') {
            showMessage('Baseline reloaded (' + data.features + ' features)', 'success');
            if (btn) {
                btn.classList.add('btn-success');
                setTimeout(function() { btn.classList.remove('btn-success'); }, 1200);
            }
        } else {
            showMessage('Baseline reload error: ' + data.error, 'error');
        }
    })
    .catch(function(e) { showMessage('Baseline reload failed: ' + e, 'error'); })
    .finally(function() {
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('btn-active');
        }
    });
}

function applyStabilityDefaults() {
    console.log('applyStabilityDefaults() called from external JS');
    var payload = {
        llm_min_interval_seconds: 70,
        feature_shift_min_interval_seconds: 999,
        feature_shift_jaccard_threshold: 1.0
    };
    var btn = document.getElementById('btn-stability-defaults');
    if (btn) {
        btn.disabled = true;
        btn.classList.add('btn-active');
    }
    fetch('/api/backend/config/runtime', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    })
    .then(function(r) {
        return r.json().catch(function(e) {
            return r.text().then(function(t) {
                throw new Error('Non-JSON (' + r.status + '): ' + t.slice(0, 160));
            });
        });
    })
    .then(function(_) {
        showMessage('Stability defaults applied', 'success');
        if (btn) {
            btn.classList.add('btn-success');
            setTimeout(function() { btn.classList.remove('btn-success'); }, 1200);
        }
    })
    .catch(function(e) { showMessage('Failed to apply defaults: ' + e, 'error'); })
    .finally(function() {
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('btn-active');
        }
    });
}

function showAnalysisHistory() {
    console.log('showAnalysisHistory() called from external JS');
    var limitSel = document.getElementById('history-limit');
    var limit = limitSel ? parseInt(limitSel.value) : 5;

    showMessage('Loading analysis history...', 'info');

    // Add timestamp to prevent browser caching
    var timestamp = new Date().getTime();
    fetch('/api/backend/analysis/history?limit=' + limit + '&_=' + timestamp)
        .then(function(r) {
            console.log('Analysis history response status:', r.status);
            return r.json();
        })
        .then(function(data) {
            console.log('Analysis history data:', data);
            var box = document.getElementById('analysis-history');
            if (!box) {
                console.error('analysis-history element not found!');
                return;
            }

            if (!data.items || !data.items.length) {
                box.textContent = '(no analysis history yet - try triggering some anomalies first)';
                showMessage('No analysis history found', 'info');
            } else {
                function _esc(s) {
                    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                }
                var lines = data.items.map(function(it, idx) {
                    var ts = it.timestamp || new Date((it.time || 0) * 1000).toLocaleTimeString();
                    var header = '#' + (idx + 1) + ' — ' + ts;
                    var featureAnalysis = it.feature_analysis || '';
                    var summary = it.performance_summary ? JSON.stringify(it.performance_summary) : '';
                    var sid = it.id || '';

                    // Add LLM analysis content
                    var llmContent = '';
                    if (it.llm_analyses) {
                        for (var model in it.llm_analyses) {
                            var analysis = it.llm_analyses[model];
                            if (analysis && analysis.analysis) {
                                llmContent += '\n\n=== ' + model.toUpperCase() + ' ANALYSIS ===\n';
                                llmContent += analysis.analysis;
                                if (analysis.response_time) {
                                    llmContent += '\n(Response time: ' + analysis.response_time + 's)';
                                }
                            }
                        }
                    }

                    var apiHost = window.location.protocol + '//' + window.location.hostname + ':8000';
                    // ✅ Fixed: Use React Interactive RCA Assistant (port 5173) with analysis_id parameter
                    var discussUrl = window.location.protocol + '//' + window.location.hostname + ':5173/assistant?analysis_id=' + encodeURIComponent(sid);
                    var block = '' +
                        '<div class="analysis-entry">' +
                        '<div><strong>' + _esc(header) + '</strong></div>' +
                        (featureAnalysis ? ('<pre>' + _esc(featureAnalysis) + '</pre>') : '') +
                        (llmContent ? ('<pre>' + _esc(llmContent) + '</pre>') : '') +
                        (summary ? ('<pre>' + _esc(summary) + '</pre>') : '') +
                        '<div><a href="' + discussUrl + '" target="_blank" rel="noopener">💬 Discuss this analysis in Fault Analysis →</a></div>' +
                        '</div>';
                    return block;
                });
                box.innerHTML = lines.join('<hr/>');
                showMessage('Loaded ' + data.items.length + ' analysis entries with LLM content', 'success');
            }
            box.style.display = 'block';
        })
        .catch(function(e) {
            console.error('Analysis history error:', e);
            showMessage('Failed to load analysis history: ' + e, 'error');
            var box = document.getElementById('analysis-history');
            if (box) {
                box.textContent = 'Error loading analysis history. Make sure backend is running on port 8000.';
                box.style.display = 'block';
            }
        });
}



function downloadAnalysis(fmt) {
    console.log('downloadAnalysis() called with format:', fmt);
    showMessage('Preparing download...', 'info');

    // Get analysis history and create download
    var limitSel = document.getElementById('history-limit');
    var limit = limitSel ? parseInt(limitSel.value) : 5;

    fetch('/api/backend/analysis/history?limit=' + limit)
        .then(function(r) {
            if (!r.ok) throw new Error('Backend not available (port 8000)');
            return r.json();
        })
        .then(function(data) {
            if (!data.items || !data.items.length) {
                showMessage('No analysis data to download', 'error');
                return;
            }

            var content = '';
            var filename = '';

            if (fmt === 'json') {
                // JSON format - single JSON array
                content = JSON.stringify(data.items, null, 2);
                filename = 'tep_analysis_history.json';
            } else if (fmt === 'md') {
                // Markdown format
                var lines = ['# TEP Analysis History\n'];
                data.items.forEach(function(item, i) {
                    var ts = item.timestamp || 'Unknown time';
                    lines.push('## Analysis #' + (i + 1) + ' - ' + ts + '\n');
                    lines.push('**Feature Analysis:**\n```\n' + (item.feature_analysis || 'N/A') + '\n```\n');

                    if (item.llm_analyses) {
                        lines.push('**LLM Analysis Results:**\n');
                        for (var model in item.llm_analyses) {
                            var analysis = item.llm_analyses[model];
                            if (analysis && analysis.analysis) {
                                lines.push('### ' + model.toUpperCase() + '\n');
                                lines.push(analysis.analysis + '\n');
                                if (analysis.response_time) {
                                    lines.push('*Response time: ' + analysis.response_time + 's*\n');
                                }
                            }
                        }
                    }

                    if (item.performance_summary) {
                        lines.push('**Performance Summary:**\n');
                        for (var model in item.performance_summary) {
                            var perf = item.performance_summary[model];
                            lines.push('- ' + model + ': ' + (perf.response_time || 0) + 's, ' + (perf.word_count || 0) + ' words\n');
                        }
                    }
                    lines.push('\n---\n');
                });
                content = lines.join('\n');
                filename = 'tep_analysis_history.md';
            } else {
                showMessage('Invalid format: ' + fmt, 'error');
                return;
            }

            // Create and trigger download
            var blob = new Blob([content], { type: 'text/plain' });
            var url = window.URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            showMessage('Downloaded ' + filename + ' with ' + data.items.length + ' analysis entries', 'success');
        })
        .catch(function(e) {
            showMessage('Download failed: ' + e + '. Make sure FaultExplainer backend is running on port 8000, or try copying the displayed analysis instead.', 'error');
        });
}

function downloadAnalysisByDate() {
    console.log('downloadAnalysisByDate() called from external JS');
    var inp = document.getElementById('history-date');
    if (!inp || !inp.value) {
        showMessage('Please select a date', 'error');
        return;
    }
    var ds = inp.value; // YYYY-MM-DD
    window.location = '/api/analysis/history/download/bydate/' + ds;
}

// Missing slider and preset functions
function setDemoInterval(sec) {
    console.log('setDemoInterval() called with:', sec);
    var seconds = parseInt(sec);
    fetch('/api/speed', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({mode: 'demo', seconds: seconds})
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
        var intervalEl = document.getElementById('demo-interval');
        var speedModeEl = document.getElementById('speed-mode');
        if (intervalEl) intervalEl.textContent = d.step_interval_seconds;
        if (speedModeEl) speedModeEl.textContent = 'Demo (' + d.step_interval_seconds + 's)';
        showMessage('Demo interval set to ' + d.step_interval_seconds + 's', 'success');
    })
    .catch(function(e) { showMessage('Failed to set interval: ' + e, 'error'); });
}

// New speed factor control function
function setSpeedFactor(factor) {
    console.log('setSpeedFactor() called with:', factor);
    var speedFactor = parseFloat(factor);

    // Update display
    var label = document.getElementById('speed-factor');
    if (label) {
        var description = speedFactor < 1.0 ? (speedFactor + 'x (Slower)') :
                         speedFactor === 1.0 ? '1.0x (Normal)' :
                         speedFactor + 'x (Faster)';
        label.textContent = description;
    }

    // Send to backend (will need new API endpoint)
    fetch('/api/speed/factor', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({speed_factor: speedFactor})
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
        console.log('setSpeedFactor response:', d);
        showMessage('Speed factor set to ' + speedFactor + 'x (interval: ' + d.step_interval_seconds + 's)', 'success');

        // 🔥 CRITICAL FIX: Restart dynamic updates with new speed
        console.log('🔄 Restarting dynamic status updates for new speed factor:', speedFactor);
        startDynamicStatusUpdates();

        // Force immediate status update
        setTimeout(updateStatus, 500);
    })
    .catch(function(e) {
        console.error('setSpeedFactor error:', e);
        showMessage('Failed to set speed factor: ' + e, 'error');
    });
}

function setPreset(mode) {
    console.log('setPreset() called with mode:', mode);
    var demo = {
        pca_window_size: 8,
        fault_trigger_consecutive_step: 3,
        decimation_N: 1,
        llm_min_interval_seconds: 0
    };
    var balanced = {
        decimation_N: 4,
        pca_window_size: 12,
        fault_trigger_consecutive_step: 2,
        llm_min_interval_seconds: 20,
        feature_shift_min_interval_seconds: 60,
        feature_shift_jaccard_threshold: 0.8
    };
    var real = {
        pca_window_size: 20,
        fault_trigger_consecutive_step: 6,
        decimation_N: 1,
        llm_min_interval_seconds: 300
    };
    var cfg = mode === 'demo' ? demo : (mode === 'balanced' ? balanced : real);
    cfg.preset = mode;

    fetch('/api/backend/config/runtime', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(cfg)
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        showMessage('Backend runtime config updated: ' + JSON.stringify(data.updated), 'success');
        var label = mode === 'demo' ? 'Demo' : (mode === 'balanced' ? 'Balanced' : 'Realistic');
        var presetModeEl = document.getElementById('preset-mode');
        if (presetModeEl) presetModeEl.textContent = label;

        var demoBtn = document.getElementById('btn-preset-demo');
        var balancedBtn = document.getElementById('btn-preset-balanced');
        var realBtn = document.getElementById('btn-preset-real');

        if (demoBtn) demoBtn.classList.toggle('btn-active', mode === 'demo');
        if (balancedBtn) balancedBtn.classList.toggle('btn-active', mode === 'balanced');
        if (realBtn) realBtn.classList.toggle('btn-active', mode === 'real');
    })
    .catch(function(e) { showMessage('Config update failed: ' + e, 'error'); });
}

function setIngestion(mode) {
    console.log('setIngestion() called with mode:', mode);
    var internal = mode === 'internal';
    var internalBtn = document.getElementById('btn-ingest-internal');
    var csvBtn = document.getElementById('btn-ingest-csv');

    if (internalBtn) internalBtn.classList.toggle('btn-active', internal);
    if (csvBtn) csvBtn.classList.toggle('btn-active', !internal);

    var hint = document.getElementById('ingest-hint');
    if (hint) {
        hint.textContent = internal ?
            'Using Internal Simulator. Bridge controls disabled.' :
            'Using CSV Bridge. Internal Simulator controls disabled.';
    }

    // Enable/disable relevant buttons
    var simButtons = document.querySelectorAll("button[onclick*='startTEP'], button[onclick*='stopTEP']");
    var bridgeButtons = [
        document.getElementById('btn-bridge-start'),
        document.querySelectorAll("button[onclick*='stopBridge']")
    ];

    for (var i = 0; i < simButtons.length; i++) {
        if (simButtons[i]) simButtons[i].disabled = !internal;
    }

    if (bridgeButtons[0]) bridgeButtons[0].disabled = internal;
    if (bridgeButtons[1]) {
        for (var j = 0; j < bridgeButtons[1].length; j++) {
            if (bridgeButtons[1][j]) bridgeButtons[1][j].disabled = internal;
        }
    }
}

function setXMV(xmvNum, value) {
    console.log('setXMV() called with:', xmvNum, value);
    var floatValue = parseFloat(value);  // Convert to float (0.0-100.0)
    var valueSpan = document.getElementById('xmv' + xmvNum + '-value');
    if (valueSpan) valueSpan.textContent = floatValue.toFixed(1);

    fetch('/api/xmv/set', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            xmv_num: xmvNum,
            value: floatValue
        })
    })
    .then(function(response) {
        return response.json();
    })
    .then(function(data) {
        console.log('XMV set response:', data);
        if (!data.success) {
            console.error('Failed to set XMV:', data.message);
            showMessage('Failed to set XMV_' + xmvNum + ': ' + data.message, 'error');
        } else {
            console.log('XMV_' + xmvNum + ' set to ' + floatValue + '%');
        }
    })
    .catch(function(error) {
        console.error('Error setting XMV:', error);
        showMessage('Error setting XMV_' + xmvNum + ': ' + error.message, 'error');
    });
}

function setIDV(idvNum, value) {
    console.log('setIDV() called with:', idvNum, value);
    var percentValue = parseInt(value);  // Convert to percentage
    var valueSpan = document.getElementById('idv' + idvNum + '-value');

    // Update display with percentage and activation status
    if (valueSpan) {
        if (percentValue < 50) {
            valueSpan.textContent = percentValue + '%';
            valueSpan.style.color = '#007bff';  // Blue for inactive
        } else {
            valueSpan.textContent = percentValue + '%';
            valueSpan.style.color = '#e74c3c';  // Red for active
        }
    }

    // Convert percentage to binary for Fortran (0-49% = 0, 50-100% = 1)
    var fortranValue = percentValue >= 50 ? 1 : 0;

    fetch('/api/idv/set', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({idv_num: idvNum, value: fortranValue})  // Send binary 0/1 to Fortran
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        if (data.success) {
            showMessage('IDV_' + idvNum + ' set to ' + percentValue + '% (' + (fortranValue ? 'ACTIVE' : 'OFF') + ')', 'success');
        }
    })
    .catch(function(e) { showMessage('IDV update failed: ' + e, 'error'); });
}

// Test IDV impact function
function testIDVImpact() {
    console.log('testIDVImpact() called');
    showMessage('Testing IDV impact...', 'info');

    fetch('/api/idv/test', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({})
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
        console.log('IDV test response:', d);
        if (d.test_successful) {
            var message = 'IDV Test Results:\n';
            message += 'Baseline Reactor Temp: ' + d.baseline_reactor_temp + '\n';
            message += 'Fault Reactor Temp: ' + d.fault_reactor_temp + '\n';
            message += 'Difference Detected: ' + d.difference_detected;
            alert(message);
            showMessage('IDV test completed - check console for details', 'success');
        } else {
            showMessage('IDV test failed: ' + (d.error || 'Unknown error'), 'error');
        }
    })
    .catch(function(e) {
        console.error('IDV test error:', e);
        showMessage('IDV test failed: ' + e, 'error');
    });
}

// Test functions for emergency fallback
function simpleTest() {
    console.log('simpleTest() called from external JS');
    alert('Simple test button clicked!');
    var statusEl = document.getElementById('status');
    if (statusEl) {
        statusEl.innerHTML = '<div style="background: blue; color: white; padding: 10px;">Button clicked at ' + new Date().toLocaleTimeString() + '</div>';
    }
}

function testFunction() {
    console.log('testFunction() called from external JS');
    alert('Test function executed!');
}

// Backend connectivity test
function testBackendConnection() {
    console.log('Testing backend connection...');
    showMessage('Testing backend connection...', 'info');

    // Test multiple endpoints
    var tests = [
        {name: 'Status', url: window.location.protocol + '//' + window.location.hostname + ':8000/status'},
        {name: 'Metrics', url: window.location.protocol + '//' + window.location.hostname + ':8000/metrics'},
        {name: 'Analysis History', url: '/api/backend/analysis/history?limit=1'}
    ];

    var results = [];
    var completed = 0;

    tests.forEach(function(test) {
        fetch(test.url)
            .then(function(r) {
                results.push(test.name + ': ✅ OK (' + r.status + ')');
                return r.json();
            })
            .then(function(data) {
                console.log(test.name + ' data:', data);
            })
            .catch(function(e) {
                results.push(test.name + ': ❌ FAILED (' + e + ')');
            })
            .finally(function() {
                completed++;
                if (completed === tests.length) {
                    var message = 'Backend Test Results:\n' + results.join('\n');
                    showMessage(message, results.some(function(r) { return r.includes('❌'); }) ? 'error' : 'success');
                }
            });
    });
}

// Auto-test backend connection on load
function autoTestBackend() {
    setTimeout(function() {
        console.log('Auto-testing backend connection...');
        // Use /health for MultiLLM backend (no /status)
        fetch(window.location.protocol + '//' + window.location.hostname + ':8000/health')
            .then(function(r) {
                if (!r.ok) throw new Error('Backend not healthy (' + r.status + ')');
                console.log('✅ Backend health OK on port 8000');
                var liveConnection = document.getElementById('live-connection');
                if (liveConnection && liveConnection.textContent.toLowerCase().indexOf('disconnected') !== -1) {
                    // Update connection status if backend is reachable
                    liveConnection.textContent = 'Live: Backend OK';
                    liveConnection.className = 'live-badge live-ok';
                }
            })
            .catch(function(e) {
                console.log('❌ Backend not reachable on port 8000:', e);
                var liveConnection = document.getElementById('live-connection');
                if (liveConnection) {
                    liveConnection.textContent = 'Live: Backend Down';
                    liveConnection.className = 'live-badge live-bad';
                }
            });
    }, 2000);
}

// ========== SNAPSHOT MANAGER FUNCTIONS ==========

function loadSnapshotManager() {
    console.log('loadSnapshotManager() called');
    showMessage('Loading snapshots...', 'info');

    fetch('/api/snapshots/list?limit=50')
        .then(function(r) {
            if (!r.ok) throw new Error('Failed to load snapshots');
            return r.json();
        })
        .then(function(data) {
            displaySnapshotList(data.snapshots);
            showMessage('Loaded ' + data.total + ' snapshots', 'success');
        })
        .catch(function(e) {
            console.error('Error loading snapshots:', e);
            showMessage('Failed to load snapshots: ' + e.message, 'error');
        });
}

function displaySnapshotList(snapshots) {
    var container = document.getElementById('snapshot-list-container');
    if (!container) {
        console.error('snapshot-list-container not found');
        return;
    }

    if (!snapshots || snapshots.length === 0) {
        container.innerHTML = '<p style="color: #888;">No snapshots available yet. Run some simulations to create snapshots.</p>';
        return;
    }

    snapshots.sort(function(a, b) { return b.id - a.id; });

    var html = '<table class="snapshot-table">';
    html += '<thead><tr><th>Time</th><th>Name</th><th>LLM Models</th><th>Features</th><th>Actions</th></tr></thead><tbody>';

    snapshots.forEach(function(snap) {
        var timestamp = snap.timestamp || 'Unknown';
        var name = snap.name || ('Analysis ' + snap.id);
        var models = snap.llm_models.join(', ') || 'None';
        var featureCount = snap.feature_count || 0;
        var hasEnhancement = snap.has_ai_enhancement ? '✨' : '';

        html += '<tr>';
        html += '<td>' + timestamp + '</td>';
        html += '<td>' + name + ' ' + hasEnhancement + '</td>';
        html += '<td>' + models + '</td>';
        html += '<td>' + featureCount + '</td>';
        html += '<td>';
        html += '<button class="btn-small" onclick="openSnapshotChat(' + snap.id + ')">💬 Chat</button> ';
        html += '<button class="btn-small" onclick="renameSnapshotPrompt(' + snap.id + ', \'' + name.replace(/'/g, "\\'") + '\')">✏️ Rename</button> ';
        html += '<button class="btn-small" onclick="viewSnapshotDetails(' + snap.id + ')">👁️ View</button>';
        html += '</td></tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

function openSnapshotChat(snapshotId) {
    console.log('openSnapshotChat() called with ID:', snapshotId);
    showMessage('Opening chat for snapshot ' + snapshotId + '...', 'info');
    // 🔧 FIX: Use React frontend (port 5173) with /assistant route
    var chatUrl = window.location.protocol + '//' + window.location.hostname + ':5173/assistant?analysis_id=' + encodeURIComponent(snapshotId);
    window.open(chatUrl, '_blank', 'noopener,noreferrer');
}

function viewSnapshotDetails(snapshotId) {
    console.log('viewSnapshotDetails() called with ID:', snapshotId);
    showMessage('Loading snapshot details...', 'info');

    fetch('/api/snapshots/get/' + snapshotId)
        .then(function(r) {
            if (!r.ok) throw new Error('Failed to load snapshot');
            return r.json();
        })
        .then(function(data) {
            displaySnapshotDetailsModal(data.snapshot);
        })
        .catch(function(e) {
            console.error('Error loading snapshot:', e);
            showMessage('Failed to load snapshot: ' + e.message, 'error');
        });
}

function displaySnapshotDetailsModal(snapshot) {
    var modal = document.getElementById('snapshot-details-modal');
    var content = document.getElementById('snapshot-details-content');

    if (!modal || !content) {
        alert('Modal elements not found. Displaying in console.');
        console.log('Snapshot Details:', snapshot);
        return;
    }

    var html = '<h3>Snapshot: ' + (snapshot.name || snapshot.id) + '</h3>';
    html += '<p><strong>Timestamp:</strong> ' + snapshot.timestamp + '</p>';
    html += '<p><strong>ID:</strong> ' + snapshot.id + '</p>';

    if (snapshot.feature_analysis) {
        html += '<h4>Feature Analysis:</h4><pre>' + snapshot.feature_analysis + '</pre>';
    }

    if (snapshot.llm_analyses) {
        html += '<h4>LLM Analysis Results:</h4>';
        for (var model in snapshot.llm_analyses) {
            var analysis = snapshot.llm_analyses[model];
            if (analysis && analysis.analysis) {
                html += '<div class="llm-result-box"><h5>' + model.toUpperCase() + '</h5>';
                html += '<p>' + analysis.analysis.replace(/\n/g, '<br>') + '</p>';
                if (analysis.response_time) {
                    html += '<p><em>Response time: ' + analysis.response_time + 's</em></p>';
                }
                html += '</div>';
            }
        }
    }

    if (snapshot.ai_agent_enhancement) {
        html += '<h4>AI Agent Enhancement:</h4><div class="enhancement-box">';
        html += '<p>' + snapshot.ai_agent_enhancement.enhanced_analysis.replace(/\n/g, '<br>') + '</p>';
        html += '<p><em>Sources: ' + snapshot.ai_agent_enhancement.knowledge_sources.join(', ') + '</em></p>';
        html += '</div>';
    }

    content.innerHTML = html;
    modal.style.display = 'block';
}

function closeSnapshotDetailsModal() {
    var modal = document.getElementById('snapshot-details-modal');
    if (modal) modal.style.display = 'none';
}

function renameSnapshotPrompt(snapshotId, currentName) {
    var newName = prompt('Enter new name for this snapshot:', currentName);
    if (newName && newName.trim() !== '' && newName !== currentName) {
        renameSnapshot(snapshotId, newName.trim());
    }
}

function renameSnapshot(snapshotId, newName) {
    console.log('renameSnapshot() called:', snapshotId, newName);
    showMessage('Renaming snapshot...', 'info');

    fetch('/api/snapshots/rename', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: snapshotId, name: newName, tags: []})
    })
    .then(function(r) {
        if (!r.ok) throw new Error('Failed to rename snapshot');
        return r.json();
    })
    .then(function(data) {
        showMessage('Snapshot renamed successfully', 'success');
        loadSnapshotManager();
    })
    .catch(function(e) {
        console.error('Error renaming snapshot:', e);
        showMessage('Failed to rename snapshot: ' + e.message, 'error');
    });
}

console.log('✅ External JavaScript file loaded completely');
