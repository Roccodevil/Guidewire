// Handles rejecting an order
async function rejectOrder(orderId) {
    await fetch('/api/reject_order', {
        method: 'POST', 
        body: JSON.stringify({order_id: orderId}),
        headers: {'Content-Type': 'application/json'}
    });
    location.reload();
}

// Handles accepting an order, hitting the AI, and simulating live GPS
async function startSimulatedTrip(btnElement, orderId) {
    const terminal = document.getElementById('terminal');
    btnElement.disabled = true;
    btnElement.innerText = "Tracking...";
    terminal.innerHTML += `<br>> Order #${orderId} Accepted. Fetching Polyline...<br>`;

    const res = await fetch('/api/start_delivery', {
        method: 'POST', 
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({order_id: orderId})
    });
    const data = await res.json();
    
    terminal.innerHTML += `> <span class="text-yellow-400">Risk Assessment: ${data.suggested_action}</span><br>`;
    if(data.parametric_triggered) {
        terminal.innerHTML += `> <span class='text-red-400 font-bold bg-red-900/30 px-1'>TRIGGER: Claim Auto-Filed & Paid.</span><br>`;
    }

    const pathPoints = data.route_data.path || [];
    if(pathPoints.length > 0) {
        terminal.innerHTML += `> <span class='text-blue-300'>Initiating Live GPS Telemetry...</span><br>`;
        for(let i = 0; i < pathPoints.length; i += Math.max(1, Math.floor(pathPoints.length / 5))) {
            const pt = pathPoints[i];
            terminal.innerHTML += `> GPS Ping: ${pt.latitude.toFixed(4)}, ${pt.longitude.toFixed(4)}<br>`;
            terminal.scrollTop = terminal.scrollHeight;
            
            await fetch('/api/update_gps', {
                method: 'POST', 
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({order_id: orderId, lat: pt.latitude, lon: pt.longitude})
            });
            await new Promise(r => setTimeout(r, 800));
        }
    } else {
        terminal.innerHTML += `> Error: Could not retrieve polyline from API.<br>`;
    }
    
    terminal.innerHTML += `> <span class="text-green-400 font-bold">Route #${orderId} Complete.</span><br>`;
    setTimeout(() => location.reload(), 2000);
}

// Toggle Policy Documents visibility
function toggleDocs() {
    document.getElementById('policy-docs').classList.toggle('hidden');
}