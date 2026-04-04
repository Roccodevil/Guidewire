const { useEffect, useMemo, useRef, useState } = React;

const DELHI_CENTER = { lat: 28.6139, lon: 77.2090 };

function toLabel(point, fallback) {
    if (!point) {
        return fallback;
    }
    return `${fallback} (${point.lat.toFixed(4)}, ${point.lon.toFixed(4)})`;
}

function describeAvailability(status) {
    if (status === "Pending") {
        return "Awaiting acceptance";
    }
    return "No active delivery";
}

function CompanyApp() {
    const initial = window.__COMPANY_DATA__ || { workers: [], orders: [] };
    const [originPoint, setOriginPoint] = useState(null);
    const [destPoint, setDestPoint] = useState(null);
    const [selecting, setSelecting] = useState("origin");
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedWorkerId, setSelectedWorkerId] = useState("");
    const [terminalLines, setTerminalLines] = useState([]);
    const [dispatchingWorker, setDispatchingWorker] = useState(null);
    const [autoLoading, setAutoLoading] = useState(false);
    const [mapReady, setMapReady] = useState(false);

    const mapRef = useRef(null);
    const originMarkerRef = useRef(null);
    const destMarkerRef = useRef(null);
    const routeLineRef = useRef(null);
    const selectingRef = useRef("origin");

    useEffect(() => {
        selectingRef.current = selecting;
    }, [selecting]);

    useEffect(() => {
        gsap.from(".panel", { y: 24, opacity: 0, duration: 0.8, stagger: 0.1, ease: "power2.out" });
    }, []);

    useEffect(() => {
        if (mapRef.current) {
            return;
        }

        const map = L.map("dispatch-map", { zoomControl: true }).setView([DELHI_CENTER.lat, DELHI_CENTER.lon], 11);

        L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
            attribution: "&copy; OpenStreetMap contributors"
        }).addTo(map);

        map.on("click", (event) => {
            const point = { lat: event.latlng.lat, lon: event.latlng.lng };
            if (selectingRef.current === "origin") {
                setOriginPoint(point);
            } else {
                setDestPoint(point);
            }
        });

        mapRef.current = map;
        setMapReady(true);
    }, []);

    useEffect(() => {
        if (!mapRef.current || !mapReady) {
            return;
        }

        const originIcon = L.divIcon({
            className: "custom-pin pin-origin",
            html: '<span class="pin-label">O</span>',
            iconSize: [32, 46],
            iconAnchor: [16, 44],
            popupAnchor: [0, -40]
        });
        const destIcon = L.divIcon({
            className: "custom-pin pin-destination",
            html: '<span class="pin-label">D</span>',
            iconSize: [32, 46],
            iconAnchor: [16, 44],
            popupAnchor: [0, -40]
        });

        if (originMarkerRef.current) {
            mapRef.current.removeLayer(originMarkerRef.current);
        }
        if (originPoint) {
            originMarkerRef.current = L.marker([originPoint.lat, originPoint.lon])
                .addTo(mapRef.current)
                .setIcon(originIcon)
                .bindPopup("Origin");
        }

        if (destMarkerRef.current) {
            mapRef.current.removeLayer(destMarkerRef.current);
        }
        if (destPoint) {
            destMarkerRef.current = L.marker([destPoint.lat, destPoint.lon])
                .addTo(mapRef.current)
                .setIcon(destIcon)
                .bindPopup("Destination");
        }

        if (routeLineRef.current) {
            mapRef.current.removeLayer(routeLineRef.current);
        }

        if (originPoint && destPoint) {
            routeLineRef.current = L.polyline(
                [
                    [originPoint.lat, originPoint.lon],
                    [destPoint.lat, destPoint.lon]
                ],
                {
                    color: "#0f6bff",
                    weight: 4,
                    dashArray: "8 8",
                    opacity: 0.8
                }
            ).addTo(mapRef.current);

            const bounds = L.latLngBounds(
                [originPoint.lat, originPoint.lon],
                [destPoint.lat, destPoint.lon]
            );
            mapRef.current.fitBounds(bounds.pad(0.25));
        }
    }, [originPoint, destPoint, mapReady]);

    const appendTerminal = (line) => setTerminalLines((prev) => [...prev, line]);

    const workerStatus = useMemo(() => {
        const map = new Map();
        const openOrders = initial.orders.filter((order) => order.status === "Pending" || order.status === "Active");

        openOrders.forEach((order) => {
            const existing = map.get(order.worker_id);
            if (order.status === "Active" || !existing) {
                map.set(order.worker_id, order.status);
            }
        });
        return map;
    }, [initial.orders]);

    const availableWorkers = useMemo(() => {
        return initial.workers.filter((worker) => {
            const status = workerStatus.get(worker.id);
            return !status || status === "Pending";
        });
    }, [initial.workers, workerStatus]);

    const filteredWorkers = useMemo(() => {
        const q = searchTerm.trim().toLowerCase();
        if (!q) {
            return availableWorkers;
        }
        return availableWorkers.filter((worker) => {
            return String(worker.id).includes(q) || worker.username.toLowerCase().includes(q);
        });
    }, [availableWorkers, searchTerm]);

    useEffect(() => {
        if (!selectedWorkerId && filteredWorkers.length > 0) {
            setSelectedWorkerId(String(filteredWorkers[0].id));
            return;
        }
        if (selectedWorkerId && !filteredWorkers.some((worker) => String(worker.id) === String(selectedWorkerId))) {
            setSelectedWorkerId(filteredWorkers.length > 0 ? String(filteredWorkers[0].id) : "");
        }
    }, [filteredWorkers, selectedWorkerId]);

    const dispatch = async (workerId) => {
        if (!originPoint || !destPoint) {
            window.alert("Select both origin and destination from the map first.");
            return;
        }

        setDispatchingWorker(workerId);
        try {
            await fetch("/api/dispatch_order", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    worker_id: workerId,
                    origin_lat: originPoint.lat,
                    origin_lon: originPoint.lon,
                    origin_name: toLabel(originPoint, "Pinned Origin"),
                    dest_lat: destPoint.lat,
                    dest_lon: destPoint.lon,
                    dest_name: toLabel(destPoint, "Pinned Destination")
                })
            });
            window.alert("Route dispatched. Worker is receiving coordinates.");
            window.location.reload();
        } catch (error) {
            window.alert("Failed to dispatch order.");
            setDispatchingWorker(null);
        }
    };

    const autoDispatch = async () => {
        if (!originPoint || !destPoint) {
            window.alert("Select both origin and destination from the map first.");
            return;
        }

        setAutoLoading(true);
        setTerminalLines([
            "Scanning active fleet.",
            "Evaluating worker insurance profiles."
        ]);

        try {
            const res = await fetch("/api/auto_dispatch", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    origin_lat: originPoint.lat,
                    origin_lon: originPoint.lon,
                    origin_name: toLabel(originPoint, "Pinned Origin"),
                    dest_lat: destPoint.lat,
                    dest_lon: destPoint.lon,
                    dest_name: toLabel(destPoint, "Pinned Destination")
                })
            });
            const data = await res.json();
            appendTerminal(`Match found: assigned to worker #${data.assigned_to}`);
            appendTerminal(`XAI audit trail: ${data.xai_audit}`);
            setTimeout(() => window.location.reload(), 1200);
        } catch (error) {
            appendTerminal("Error computing dispatch.");
            setAutoLoading(false);
        }
    };

    return (
        <main className="app-layout page-width company-shell">
            <section className="panel">
                <div className="company-hero">
                    <div>
                        <span className="eyebrow">Dispatch Studio</span>
                        <h1>Platform Dispatcher</h1>
                        <p className="subtitle">Pick origin and destination directly on map, then dispatch to an available worker.</p>
                    </div>
                    <div className="company-metrics">
                        <div>
                            <strong>{availableWorkers.length}</strong>
                            <span>Available workers</span>
                        </div>
                        <div>
                            <strong>{initial.orders.length}</strong>
                            <span>Open orders</span>
                        </div>
                    </div>
                </div>

                <div className="map-hero-overlay">
                    <strong>Smart Route Picker</strong>
                    <span>Choose pin mode, click map, and dispatch instantly.</span>
                </div>

                <div className="pick-mode-row">
                    <button
                        className={`btn ${selecting === "origin" ? "btn-primary" : "btn-ghost"}`}
                        onClick={() => setSelecting("origin")}
                    >
                        Set Origin Pin
                    </button>
                    <button
                        className={`btn ${selecting === "destination" ? "btn-primary" : "btn-ghost"}`}
                        onClick={() => setSelecting("destination")}
                    >
                        Set Destination Pin
                    </button>
                </div>

                <div id="dispatch-map" className="map-canvas"></div>

                <div className="dispatch-config">
                    <label>
                        Origin Selected
                        <input
                            value={originPoint ? `${originPoint.lat.toFixed(5)}, ${originPoint.lon.toFixed(5)}` : "Click map in Origin mode"}
                            readOnly
                        />
                    </label>
                    <label>
                        Destination Selected
                        <input
                            value={destPoint ? `${destPoint.lat.toFixed(5)}, ${destPoint.lon.toFixed(5)}` : "Click map in Destination mode"}
                            readOnly
                        />
                    </label>
                </div>

                <button className="btn btn-accent" disabled={autoLoading} onClick={autoDispatch}>
                    {autoLoading ? "Analyzing fleet..." : "Auto-Assign via Agentic AI"}
                </button>

                {terminalLines.length > 0 && (
                    <div className="panel terminal compact-terminal">
                        {terminalLines.map((line, idx) => <p key={idx}>{"> " + line}</p>)}
                    </div>
                )}
            </section>

            <section className="panel">
                <h2>Available Workers</h2>
                <p className="subtitle">Use search and dropdown to quickly find and dispatch a specific worker.</p>

                <div className="dispatch-toolbar">
                    <input
                        type="text"
                        placeholder="Search by worker ID or username"
                        value={searchTerm}
                        onChange={(event) => setSearchTerm(event.target.value)}
                    />
                    <select
                        value={selectedWorkerId}
                        onChange={(event) => setSelectedWorkerId(event.target.value)}
                        disabled={filteredWorkers.length === 0}
                    >
                        {filteredWorkers.length === 0 ? (
                            <option value="">No matching worker</option>
                        ) : (
                            filteredWorkers.map((worker) => (
                                <option value={worker.id} key={worker.id}>
                                    #{worker.id} ({worker.username})
                                </option>
                            ))
                        )}
                    </select>
                    <button
                        className="btn btn-primary"
                        disabled={!selectedWorkerId || dispatchingWorker === Number(selectedWorkerId)}
                        onClick={() => dispatch(Number(selectedWorkerId))}
                    >
                        {dispatchingWorker === Number(selectedWorkerId) ? "Dispatching..." : "Dispatch Selected"}
                    </button>
                </div>

                <div className="stack-list">
                    {filteredWorkers.length === 0 ? (
                        <div className="empty-state">No workers match your search right now.</div>
                    ) : (
                        filteredWorkers.map((worker) => {
                            const status = workerStatus.get(worker.id);
                            return (
                                <article className="worker-row" key={worker.id}>
                                    <div>
                                        <h3>Worker #{worker.id} ({worker.username})</h3>
                                        <p>{describeAvailability(status)}</p>
                                    </div>
                                    <button
                                        className="btn btn-primary"
                                        disabled={dispatchingWorker === worker.id}
                                        onClick={() => dispatch(worker.id)}
                                    >
                                        {dispatchingWorker === worker.id ? "Dispatching..." : "Send Delivery"}
                                    </button>
                                </article>
                            );
                        })
                    )}
                </div>
            </section>
        </main>
    );
}

ReactDOM.createRoot(document.getElementById("react-root")).render(<CompanyApp />);
