// Fetches live GPS and order status without refreshing the page
async function fetchLiveData() {
    try {
        const res = await fetch('/api/admin_live_data');
        const orders = await res.json();
        const tbody = document.getElementById('tracking-body');
        tbody.innerHTML = ''; // Clear current rows
        
        if (orders.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="p-4 text-center text-gray-500">No active deliveries.</td></tr>';
            return;
        }

        orders.forEach(o => {
            const latlon = o.lat ? `${o.lat.toFixed(4)}, ${o.lon.toFixed(4)}` : 'Waiting for signal...';
            const statusClass = o.status === 'Pending' ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800';
            
            const row = `<tr class="border-b">
                <td class="p-2 font-mono text-gray-600">#${o.id}</td>
                <td class="p-2 font-bold">Worker ${o.worker_id}</td>
                <td class="p-2">${o.route}</td>
                <td class="p-2"><span class="px-2 py-1 rounded text-xs font-bold ${statusClass}">${o.status}</span></td>
                <td class="p-2 font-mono text-blue-600 font-bold">${latlon}</td>
            </tr>`;
            tbody.innerHTML += row;
        });
    } catch (e) { 
        console.error("Live sync failed.", e); 
    }
}

// Start polling when the script loads
setInterval(fetchLiveData, 1500);
fetchLiveData();