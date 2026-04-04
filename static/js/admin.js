const { useEffect, useMemo, useRef, useState } = React;

function money(value) {
    return `Rs ${Number(value || 0).toFixed(2)}`;
}

function makeChart(ctx, config) {
    if (!ctx || typeof Chart === "undefined") {
        return null;
    }
    return new Chart(ctx, config);
}

function AdminApp() {
    const initial = window.__ADMIN_DATA__;
    const analytics = initial.analytics || {
        total_coverage_limit: 0,
        total_coverage_used: 0,
        coverage_utilization_pct: 0,
        total_claim_count: 0,
        average_claim_amount: 0,
        loss_ratio_pct: 0,
        worker_coverage_usage: [],
        tier_performance: [],
        claims_trend: []
    };

    const [liveOrders, setLiveOrders] = useState([]);
    const [trendWindow, setTrendWindow] = useState("30");
    const [activeTab, setActiveTab] = useState("operations");
    const [hoveredLabel, setHoveredLabel] = useState("");
    const [liveSearch, setLiveSearch] = useState("");

    const coverageChartRef = useRef(null);
    const workerChartRef = useRef(null);
    const tierChartRef = useRef(null);
    const tierUsageChartRef = useRef(null);
    const trendChartRef = useRef(null);

    const coverageChartInstance = useRef(null);
    const workerChartInstance = useRef(null);
    const tierChartInstance = useRef(null);
    const tierUsageChartInstance = useRef(null);
    const trendChartInstance = useRef(null);

    useEffect(() => {
        gsap.from(".panel", { y: 20, opacity: 0, duration: 0.75, stagger: 0.06, ease: "power2.out" });
    }, []);

    useEffect(() => {
        let active = true;

        const fetchLiveData = async () => {
            try {
                const res = await fetch("/api/admin_live_data");
                const orders = await res.json();
                if (active) {
                    setLiveOrders(orders);
                }
            } catch (error) {
                console.error("Live sync failed", error);
            }
        };

        fetchLiveData();
        const timerId = setInterval(fetchLiveData, 1500);
        return () => {
            active = false;
            clearInterval(timerId);
        };
    }, []);

    const netClass = useMemo(() => (Number(initial.net_profit) >= 0 ? "positive" : "negative"), [initial.net_profit]);

    const filteredTrend = useMemo(() => {
        if (trendWindow === "all") {
            return analytics.claims_trend;
        }
        const days = Number(trendWindow);
        const cutoff = new Date();
        cutoff.setDate(cutoff.getDate() - days);
        return analytics.claims_trend.filter((row) => new Date(row.date) >= cutoff);
    }, [analytics.claims_trend, trendWindow]);

    const utilizationBuckets = useMemo(
        () => analytics.worker_utilization_buckets || [],
        [analytics.worker_utilization_buckets]
    );

    const filteredLiveOrders = useMemo(() => {
        const query = liveSearch.trim().toLowerCase();
        if (!query) {
            return liveOrders;
        }
        return liveOrders.filter((order) => {
            return String(order.id).includes(query) || String(order.worker_id).includes(query) || order.route.toLowerCase().includes(query);
        });
    }, [liveOrders, liveSearch]);

    useEffect(() => {
        if (activeTab !== "analytics") {
            return;
        }
        if (coverageChartInstance.current) {
            coverageChartInstance.current.destroy();
        }
        const used = Number(analytics.total_coverage_used || 0);
        const remaining = Math.max(0, Number(analytics.total_coverage_limit || 0) - used);

        coverageChartInstance.current = makeChart(coverageChartRef.current, {
            type: "doughnut",
            data: {
                labels: ["Coverage Used", "Coverage Remaining"],
                datasets: [{
                    data: [used, remaining],
                    backgroundColor: ["#4d8dff", "#d9e7ff"],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: "bottom", labels: { boxWidth: 12, color: "#4e5f80" } }
                },
                cutout: "68%"
            }
        });

        return () => {
            if (coverageChartInstance.current) {
                coverageChartInstance.current.destroy();
            }
        };
    }, [activeTab, analytics.total_coverage_limit, analytics.total_coverage_used]);

    useEffect(() => {
        if (activeTab !== "analytics") {
            return;
        }
        if (workerChartInstance.current) {
            workerChartInstance.current.destroy();
        }

        const labels = utilizationBuckets.map((row) => row.bucket);
        const data = utilizationBuckets.map((row) => Number(row.count || 0));

        workerChartInstance.current = makeChart(workerChartRef.current, {
            type: "bar",
            data: {
                labels,
                datasets: [{
                    label: "Workers",
                    data,
                    borderRadius: 8,
                    backgroundColor: "rgba(77, 141, 255, 0.72)",
                    borderColor: "#4d8dff",
                    borderWidth: 1
                }]
            },
            options: {
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: "#60708f" } },
                    y: { grid: { color: "#e6eefc" }, ticks: { color: "#60708f" } }
                }
            }
        });

        return () => {
            if (workerChartInstance.current) {
                workerChartInstance.current.destroy();
            }
        };
    }, [activeTab, utilizationBuckets]);

    useEffect(() => {
        if (activeTab !== "analytics") {
            return;
        }
        if (tierChartInstance.current) {
            tierChartInstance.current.destroy();
        }

        const labels = analytics.tier_performance.map((t) => t.tier);
        const premiumData = analytics.tier_performance.map((t) => Number(t.premium_collected || 0));
        const payoutData = analytics.tier_performance.map((t) => Number(t.claim_paid || 0));

        tierChartInstance.current = makeChart(tierChartRef.current, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: "Premium Collected",
                        data: premiumData,
                        backgroundColor: "rgba(10, 155, 140, 0.62)",
                        borderRadius: 8
                    },
                    {
                        label: "Claim Paid",
                        data: payoutData,
                        backgroundColor: "rgba(77, 141, 255, 0.64)",
                        borderRadius: 8
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: "bottom", labels: { boxWidth: 12, color: "#4e5f80" } }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: "#60708f" } },
                    y: { grid: { color: "#e6eefc" }, ticks: { color: "#60708f" } }
                }
            }
        });

        return () => {
            if (tierChartInstance.current) {
                tierChartInstance.current.destroy();
            }
        };
    }, [activeTab, analytics.tier_performance]);

    useEffect(() => {
        if (activeTab !== "analytics") {
            return;
        }
        if (tierUsageChartInstance.current) {
            tierUsageChartInstance.current.destroy();
        }

        const labels = analytics.tier_performance.map((t) => t.tier);
        const used = analytics.tier_performance.map((t) => Number(t.coverage_used || 0));

        tierUsageChartInstance.current = makeChart(tierUsageChartRef.current, {
            type: "doughnut",
            data: {
                labels,
                datasets: [{
                    data: used,
                    backgroundColor: ["#4d8dff", "#0a9b8c", "#7ba8ff", "#8dcfc4", "#5f87d8", "#8ea9d8"],
                    borderWidth: 0
                }]
            },
            options: {
                plugins: {
                    legend: { position: "bottom", labels: { boxWidth: 12, color: "#4e5f80" } }
                },
                cutout: "58%"
            }
        });

        return () => {
            if (tierUsageChartInstance.current) {
                tierUsageChartInstance.current.destroy();
            }
        };
    }, [activeTab, analytics.tier_performance]);

    useEffect(() => {
        if (activeTab !== "analytics") {
            return;
        }
        if (trendChartInstance.current) {
            trendChartInstance.current.destroy();
        }

        trendChartInstance.current = makeChart(trendChartRef.current, {
            type: "line",
            data: {
                labels: filteredTrend.map((row) => row.date),
                datasets: [{
                    label: "Claims Paid",
                    data: filteredTrend.map((row) => Number(row.amount || 0)),
                    borderColor: "#0b63f6",
                    pointRadius: 3,
                    pointBackgroundColor: "#0b63f6",
                    tension: 0.32,
                    fill: true,
                    backgroundColor: "rgba(11, 99, 246, 0.12)"
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: "#60708f" } },
                    y: { grid: { color: "#e6eefc" }, ticks: { color: "#60708f" } }
                }
            }
        });

        return () => {
            if (trendChartInstance.current) {
                trendChartInstance.current.destroy();
            }
        };
    }, [activeTab, filteredTrend]);

    return (
        <main className="app-layout page-width admin-shell">
            <h1>System Admin Console</h1>

            <section className="admin-tab-strip">
                <button
                    className={`tab-btn ${activeTab === "operations" ? "active" : ""}`}
                    onClick={() => setActiveTab("operations")}
                >
                    Operations
                </button>
                <button
                    className={`tab-btn ${activeTab === "analytics" ? "active" : ""}`}
                    onClick={() => setActiveTab("analytics")}
                >
                    Analytics
                </button>
            </section>

            {activeTab === "operations" && (
                <>
                    <section className="stats-grid">
                        <article className="panel metric-card">
                            <p>Total Premiums Collected</p>
                            <strong>{money(initial.total_premiums)}</strong>
                        </article>
                        <article className="panel metric-card">
                            <p>Parametric Claims Paid</p>
                            <strong>{money(initial.total_payouts)}</strong>
                        </article>
                        <article className={`panel metric-card ${netClass}`}>
                            <p>Platform Net Risk Balance</p>
                            <strong>{money(initial.net_profit)}</strong>
                        </article>
                    </section>

                    <section className="split-grid">
                        <article className="panel">
                            <h2>Fleet Management</h2>
                            <form className="inline-form" action="/admin/add_worker" method="POST">
                                <input name="username" placeholder="Worker username" required />
                                <input name="password" type="password" placeholder="Password" required />
                                <button className="btn btn-primary" type="submit">Add</button>
                            </form>

                            <table className="table">
                                <thead>
                                    <tr><th>ID</th><th>Username</th><th>Wallet</th><th>Action</th></tr>
                                </thead>
                                <tbody>
                                    {initial.workers.map((worker) => (
                                        <tr
                                            key={worker.id}
                                            className={`admin-hover-row ${hoveredLabel === `Worker #${worker.id} (${worker.username})` ? "active" : ""}`}
                                            onMouseEnter={() => setHoveredLabel(`Worker #${worker.id} (${worker.username})`)}
                                            onMouseLeave={() => setHoveredLabel("")}
                                        >
                                            <td>#{worker.id}</td>
                                            <td>{worker.username}</td>
                                            <td>{money(worker.wallet_balance)}</td>
                                            <td>
                                                <form action={`/admin/delete_worker/${worker.id}`} method="POST">
                                                    <button className="btn btn-danger" type="submit">Delete</button>
                                                </form>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </article>

                        <article className="panel">
                            <div className="row space-between align-center">
                                <h2>Policy Marketplace</h2>
                                <form action="/api/generate_tiers" method="POST">
                                    <button className="btn btn-accent" type="submit">Auto-Gen (XAI)</button>
                                </form>
                            </div>

                            <form action="/admin/add_policy" method="POST" className="stack-form">
                                <div className="inline-form">
                                    <input name="tier" placeholder="Tier" required />
                                    <input name="premium" placeholder="Premium" type="number" required />
                                    <input name="coverage" placeholder="Coverage" type="number" required />
                                </div>
                                <div className="inline-form">
                                    <input name="description" placeholder="Description / XAI reasoning" required />
                                    <button className="btn btn-primary" type="submit">Create</button>
                                </div>
                            </form>

                            <div className="stack-list scroll-panel policy-scroll">
                                {initial.policy_options.map((opt) => (
                                    <div
                                        className={`policy-option admin-policy-hover ${hoveredLabel === `Policy ${opt.tier}` ? "hovered" : ""}`}
                                        key={opt.id}
                                        onMouseEnter={() => setHoveredLabel(`Policy ${opt.tier}`)}
                                        onMouseLeave={() => setHoveredLabel("")}
                                    >
                                        <h3>{opt.tier}</h3>
                                        <p>{money(opt.premium)} / week | cover {money(opt.coverage_limit)}</p>
                                        <small>{opt.xai_description}</small>
                                        <p><strong>Terms:</strong> {opt.terms_text}</p>
                                        <p><strong>Rules:</strong> {opt.rules_text}</p>
                                        <form action={`/admin/delete_policy_option/${opt.id}`} method="POST">
                                            <button className="btn btn-danger" type="submit">Remove</button>
                                        </form>
                                    </div>
                                ))}
                            </div>
                        </article>
                    </section>

                    <section className="panel">
                        <h2>Historical Claim Ledger</h2>
                        <div className="scroll-panel table-scroll">
                            <table className="table">
                                <thead>
                                    <tr><th>Type</th><th>Details</th><th>Amount Paid</th><th>Time</th></tr>
                                </thead>
                                <tbody>
                                    {initial.claims.map((claim, idx) => (
                                        <tr key={idx}>
                                            <td>Auto-Claim</td>
                                            <td>{claim.reason}</td>
                                            <td>{money(claim.payout_amount)} paid</td>
                                            <td>{claim.timestamp}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </section>

                    <section className="panel">
                        <div className="row space-between align-center">
                            <h2>Live Telemetry Monitor</h2>
                            <div className="row align-center">
                                <input
                                    className="telemetry-search"
                                    type="text"
                                    placeholder="Search worker/order ID"
                                    value={liveSearch}
                                    onChange={(e) => setLiveSearch(e.target.value)}
                                />
                                <span className="pill">Live sync active</span>
                            </div>
                        </div>
                        <div className="scroll-panel table-scroll">
                            <table className="table">
                                <thead>
                                    <tr><th>Order ID</th><th>Worker ID</th><th>Route</th><th>Status</th><th>Live GPS</th></tr>
                                </thead>
                                <tbody>
                                    {filteredLiveOrders.length === 0 ? (
                                        <tr><td colSpan="5">No active deliveries.</td></tr>
                                    ) : (
                                        filteredLiveOrders.map((order) => (
                                            <tr
                                                key={order.id}
                                                className={`admin-hover-row ${hoveredLabel === `Live Order #${order.id}` ? "active" : ""}`}
                                                onMouseEnter={() => setHoveredLabel(`Live Order #${order.id}`)}
                                                onMouseLeave={() => setHoveredLabel("")}
                                            >
                                                <td>#{order.id}</td>
                                                <td>Worker {order.worker_id}</td>
                                                <td>{order.route}</td>
                                                <td>{order.status}</td>
                                                <td>{order.lat ? `${order.lat.toFixed(4)}, ${order.lon.toFixed(4)}` : "Waiting for signal"}</td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </section>

                </>
            )}

            {activeTab === "analytics" && (
                <>
                    <section className="analytics-kpi-grid">
                        <article className="panel analytics-kpi">
                            <p>Coverage Utilization</p>
                            <strong>{analytics.coverage_utilization_pct}%</strong>
                            <small>{money(analytics.total_coverage_used)} used of {money(analytics.total_coverage_limit)}</small>
                        </article>
                        <article className="panel analytics-kpi">
                            <p>Total Claim Events</p>
                            <strong>{analytics.total_claim_count}</strong>
                            <small>Average payout {money(analytics.average_claim_amount)}</small>
                        </article>
                        <article className="panel analytics-kpi">
                            <p>Loss Ratio</p>
                            <strong>{analytics.loss_ratio_pct}%</strong>
                            <small>Payouts as a percent of collected premiums</small>
                        </article>
                    </section>

                    <section className="analytics-chart-grid">
                        <article className="panel chart-card">
                            <div className="row space-between align-center">
                                <h2>Coverage Pool Mix</h2>
                                <span className="chip">Portfolio Risk</span>
                            </div>
                            <canvas ref={coverageChartRef} height="180"></canvas>
                        </article>

                        <article className="panel chart-card">
                            <div className="row space-between align-center">
                                <h2>Worker Utilization Distribution</h2>
                                <span className="chip">Scales to large worker counts</span>
                            </div>
                            <canvas ref={workerChartRef} height="180"></canvas>
                        </article>

                        <article className="panel chart-card">
                            <div className="row space-between align-center">
                                <h2>Tier Premium vs Claims</h2>
                                <span className="chip">Tier Comparison</span>
                            </div>
                            <canvas ref={tierChartRef} height="180"></canvas>
                        </article>

                        <article className="panel chart-card">
                            <div className="row space-between align-center">
                                <h2>Coverage Usage by Tier</h2>
                                <span className="chip">Coverage Type Consumption</span>
                            </div>
                            <canvas ref={tierUsageChartRef} height="180"></canvas>
                        </article>

                        <article className="panel chart-card full-width">
                            <div className="row space-between align-center">
                                <h2>Claims Trend</h2>
                                <select value={trendWindow} onChange={(e) => setTrendWindow(e.target.value)}>
                                    <option value="7">Last 7 days</option>
                                    <option value="30">Last 30 days</option>
                                    <option value="90">Last 90 days</option>
                                    <option value="all">All</option>
                                </select>
                            </div>
                            <canvas ref={trendChartRef} height="160"></canvas>
                        </article>
                    </section>

                    <section className="panel">
                        <h2>Worker Coverage Usage Details</h2>
                        <table className="table">
                            <thead>
                                <tr><th>Worker</th><th>Tier</th><th>Used</th><th>Limit</th><th>Utilization</th><th>Claims</th><th>Claim Paid</th></tr>
                            </thead>
                            <tbody>
                                {analytics.worker_coverage_usage.length === 0 ? (
                                    <tr><td colSpan="7">No active worker policy analytics available.</td></tr>
                                ) : (
                                    analytics.worker_coverage_usage.map((row) => (
                                        <tr key={row.worker_id}>
                                            <td>#{row.worker_id} {row.username}</td>
                                            <td>{row.tier}</td>
                                            <td>{money(row.coverage_used)}</td>
                                            <td>{money(row.coverage_limit)}</td>
                                            <td>{row.utilization_pct}%</td>
                                            <td>{row.claim_count}</td>
                                            <td>{money(row.claim_amount)}</td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </section>
                </>
            )}
        </main>
    );
}

ReactDOM.createRoot(document.getElementById("react-root")).render(<AdminApp />);
