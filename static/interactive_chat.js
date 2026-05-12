// Interactive RCA Chat JavaScript

let currentSnapshotId = null;
let currentSnapshot = null;
let chatHistory = [];
let ruledOutHypotheses = [];

// Load snapshot on page load
window.onload = function() {
    const urlParams = new URLSearchParams(window.location.search);
    currentSnapshotId = urlParams.get('snapshot_id');
    
    if (currentSnapshotId) {
        loadSnapshot(currentSnapshotId);
    } else {
        alert('No snapshot ID provided');
        window.close();
    }
};

function loadSnapshot(snapshotId) {
    console.log('Loading snapshot:', snapshotId);
    
    fetch('/api/snapshots/get/' + snapshotId)
        .then(r => {
            if (!r.ok) throw new Error('Failed to load snapshot');
            return r.json();
        })
        .then(data => {
            currentSnapshot = data.snapshot;
            displaySnapshotContext(currentSnapshot);
            displayLLMResults(currentSnapshot);
        })
        .catch(e => {
            alert('Failed to load snapshot: ' + e.message);
            console.error(e);
        });
}

function displaySnapshotContext(snapshot) {
    document.getElementById('snapshot-id').textContent = snapshot.id;
    document.getElementById('snapshot-time').textContent = snapshot.timestamp || 'Unknown';
    document.getElementById('snapshot-name').textContent = snapshot.name || ('Analysis ' + snapshot.id);
    document.getElementById('feature-analysis').textContent = snapshot.feature_analysis || 'No feature analysis available';
}

function displayLLMResults(snapshot) {
    const container = document.getElementById('root-causes-container');
    
    if (!snapshot.llm_analyses || Object.keys(snapshot.llm_analyses).length === 0) {
        container.innerHTML = '<p style="color: #888;">No LLM analysis results available</p>';
        return;
    }
    
    let html = '';
    
    for (const model in snapshot.llm_analyses) {
        const analysis = snapshot.llm_analyses[model];
        if (!analysis || !analysis.analysis) continue;
        
        const isRuledOut = ruledOutHypotheses.some(h => h.model === model);
        
        html += '<div class="root-cause-item' + (isRuledOut ? ' ruled-out' : '') + '" id="llm-' + model + '">';
        html += '<h4>' + model.toUpperCase();
        if (isRuledOut) {
            html += '<span class="ruled-out-badge">RULED OUT</span>';
        }
        html += '</h4>';
        html += '<div class="analysis-text">' + formatAnalysisText(analysis.analysis) + '</div>';
        
        if (analysis.response_time) {
            html += '<div style="font-size: 11px; color: #888; margin-top: 5px;">Response time: ' + analysis.response_time + 's</div>';
        }
        
        if (!isRuledOut) {
            html += '<div class="root-cause-buttons">';
            html += '<button class="btn btn-danger" onclick="ruleOutHypothesis(\'' + model + '\', \'entire\')">❌ Rule Out This Analysis</button>';
            html += '</div>';
        }
        html += '</div>';
    }
    
    // Add AI Agent Enhancement if available
    if (snapshot.ai_agent_enhancement && snapshot.ai_agent_enhancement.enhanced_analysis) {
        html += '<div class="root-cause-item" style="border-left-color: #ffaa00;">';
        html += '<h4 style="color: #ffaa00;">✨ AI AGENT ENHANCEMENT</h4>';
        html += '<div class="analysis-text">' + formatAnalysisText(snapshot.ai_agent_enhancement.enhanced_analysis) + '</div>';
        if (snapshot.ai_agent_enhancement.knowledge_sources) {
            html += '<div style="font-size: 11px; color: #888; margin-top: 5px;">📚 Sources: ' + snapshot.ai_agent_enhancement.knowledge_sources.join(', ') + '</div>';
        }
        html += '</div>';
    }
    
    container.innerHTML = html;
}

function formatAnalysisText(text) {
    // Convert newlines to <br>
    return text.replace(/\n/g, '<br>');
}

function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addChatMessage('user', message);
    input.value = '';
    
    // Show loading
    document.getElementById('loading').classList.add('active');
    
    // Send to backend
    fetch('/api/chat/enhanced', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            analysis_id: currentSnapshotId,
            query: message,
            history: chatHistory,
            ruled_out: ruledOutHypotheses
        })
    })
    .then(r => {
        if (!r.ok) throw new Error('Chat request failed');
        return r.json();
    })
    .then(data => {
        document.getElementById('loading').classList.remove('active');
        addChatMessage('assistant', data.answer, data.knowledge_used);
        chatHistory.push({role: 'user', content: message});
        chatHistory.push({role: 'assistant', content: data.answer});
    })
    .catch(e => {
        document.getElementById('loading').classList.remove('active');
        addChatMessage('error', 'Failed to get response: ' + e.message);
        console.error(e);
    });
}

function addChatMessage(role, content, sources) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    
    let className = 'chat-message ';
    let roleLabel = '';
    
    if (role === 'user') {
        className += 'user-message';
        roleLabel = 'You:';
    } else if (role === 'assistant') {
        className += 'ai-message';
        roleLabel = 'AI Assistant:';
    } else if (role === 'error') {
        className += 'error-message';
        roleLabel = 'Error:';
    }
    
    div.className = className;
    
    let html = '<div class="message-role">' + roleLabel + '</div>';
    html += '<div class="message-content">' + content.replace(/\n/g, '<br>') + '</div>';
    
    if (sources && sources.length > 0) {
        html += '<div class="knowledge-sources">';
        html += '📚 Knowledge sources: ';
        sources.forEach((src, i) => {
            if (i > 0) html += ', ';
            html += src.source + ' (p.' + src.page + ')';
        });
        html += '</div>';
    }
    
    div.innerHTML = html;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function ruleOutHypothesis(model, rcNumber) {
    const reason = prompt('Why are you ruling out this ' + model.toUpperCase() + ' analysis?\n\nPlease provide your reasoning:');
    
    if (!reason || reason.trim() === '') {
        return;
    }
    
    // Add to ruled-out list
    ruledOutHypotheses.push({
        model: model,
        rc_number: rcNumber,
        reason: reason.trim(),
        timestamp: new Date().toISOString()
    });
    
    // Update UI
    const element = document.getElementById('llm-' + model);
    if (element) {
        element.classList.add('ruled-out');
        const h4 = element.querySelector('h4');
        if (h4 && !h4.querySelector('.ruled-out-badge')) {
            h4.innerHTML += '<span class="ruled-out-badge">RULED OUT</span>';
        }
        const buttons = element.querySelector('.root-cause-buttons');
        if (buttons) {
            buttons.style.display = 'none';
        }
    }
    
    // Send to backend
    fetch('/api/context/ruled_out', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            analysis_id: currentSnapshotId,
            hypothesis_id: model + '_' + rcNumber,
            reason: reason.trim(),
            operator: 'User'
        })
    })
    .then(r => r.json())
    .then(data => {
        console.log('Ruled out saved:', data);
        // Automatically ask AI for alternatives
        const autoMessage = 'I ruled out the ' + model.toUpperCase() + ' analysis because: ' + reason.trim() + '. What are the alternative explanations?';
        document.getElementById('chat-input').value = autoMessage;
        sendMessage();
    })
    .catch(e => {
        console.error('Failed to save ruled-out:', e);
    });
}

function generateReport() {
    if (chatHistory.length === 0) {
        alert('Please have a conversation first before generating a report.');
        return;
    }
    
    const conclusion = prompt('Please provide your final conclusion for this root cause analysis:');
    
    if (!conclusion || conclusion.trim() === '') {
        return;
    }
    
    const email = prompt('Enter email address to send the report:', 'tep-rca-system@example.com');
    
    if (!email || email.trim() === '') {
        return;
    }
    
    // Show loading
    addChatMessage('assistant', '📄 Generating report and sending to ' + email + '...');
    
    fetch('/api/report/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            snapshot_id: currentSnapshotId,
            conclusion: conclusion.trim(),
            email: email.trim(),
            chat_history: chatHistory,
            ruled_out: ruledOutHypotheses
        })
    })
    .then(r => {
        if (!r.ok) throw new Error('Report generation failed');
        return r.json();
    })
    .then(data => {
        addChatMessage('assistant', '✅ Report generated successfully!\n\n📧 Sent to: ' + data.recipient + '\n📄 File: ' + data.filename);
    })
    .catch(e => {
        addChatMessage('error', 'Failed to generate report: ' + e.message);
        console.error(e);
    });
}

console.log('✅ Interactive Chat JavaScript loaded');

