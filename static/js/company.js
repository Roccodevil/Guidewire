// Handles dispatching the order using the selected coordinates
async function dispatch(btnElement) {
    const workerId = btnElement.dataset.workerId;
    const org = document.getElementById('origin').value.split(',');
    const dst = document.getElementById('dest').value.split(',');
    
    const originalText = btnElement.innerText;
    btnElement.innerText = "Dispatching...";
    btnElement.disabled = true;

    try {
        await fetch('/api/dispatch_order', {
            method: 'POST', 
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                worker_id: workerId, 
                origin_lat: parseFloat(org[0]), 
                origin_lon: parseFloat(org[1]), 
                origin_name: org[2],
                dest_lat: parseFloat(dst[0]), 
                dest_lon: parseFloat(dst[1]), 
                dest_name: dst[2]
            })
        });
        alert("Live Route Dispatched! Worker is receiving coordinates.");
        location.reload();
    } catch (e) {
        alert("Failed to dispatch order.");
        btnElement.innerText = originalText;
        btnElement.disabled = false;
    }
}
async function autoDispatch(btnElement) {
    const org = document.getElementById('origin').value.split(',');
    const dst = document.getElementById('dest').value.split(',');
    const terminal = document.getElementById('dispatch-terminal');
    
    btnElement.disabled = true;
    btnElement.innerHTML = "🧠 Analyzing Fleet Variables...";
    terminal.classList.remove('hidden');
    terminal.innerHTML = "> Scanning active fleet...<br>> Evaluating worker insurance profiles...<br>";

    try {
        const res = await fetch('/api/auto_dispatch', {
            method: 'POST', 
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                origin_lat: parseFloat(org[0]), origin_lon: parseFloat(org[1]), origin_name: org[2],
                dest_lat: parseFloat(dst[0]), dest_lon: parseFloat(dst[1]), dest_name: dst[2]
            })
        });
        const data = await res.json();
        
        terminal.innerHTML += `> <span class="text-blue-300">Match Found: Assigned to Worker #${data.assigned_to}</span><br>`;
        terminal.innerHTML += `> <span class="text-yellow-400 font-bold">XAI Audit Trail:</span> ${data.xai_audit}<br>`;
        
        btnElement.innerHTML = "✅ Order Dispatched";
        setTimeout(() => {
            btnElement.innerHTML = "<span class='mr-2'>🧠</span> Auto-Assign via Agentic AI";
            btnElement.disabled = false;
        }, 4000);
        
    } catch (e) {
        terminal.innerHTML += `> <span class="text-red-500">Error computing dispatch.</span>`;
        btnElement.disabled = false;
        btnElement.innerHTML = "Retry Auto-Assign";
    }
}