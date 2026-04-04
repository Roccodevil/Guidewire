const { useEffect, useMemo, useRef, useState } = React;

function formatMoney(value) {
    return `Rs ${Number(value || 0).toFixed(2)}`;
}

function DashboardApp() {
    const initial = window.__DASHBOARD_DATA__;
    const [pendingOrders, setPendingOrders] = useState(initial.pending_orders || []);
    const [docsOpen, setDocsOpen] = useState(false);
    const [runningOrderId, setRunningOrderId] = useState(null);
    const [buyingTier, setBuyingTier] = useState("");
    const [hoveredTier, setHoveredTier] = useState("");
    const [paymentTarget, setPaymentTarget] = useState(null);
    const [paymentMethod, setPaymentMethod] = useState("card");
    const [showExpiryPicker, setShowExpiryPicker] = useState(false);
    const [paymentForm, setPaymentForm] = useState({
        cardHolder: "",
        cardNumber: "",
        expiry: "",
        cvv: ""
    });
    const [terminalLines, setTerminalLines] = useState([
        "System online. Weather and traffic APIs connected.",
        "Awaiting route execution."
    ]);

    const terminalRef = useRef(null);
    const monthPickerRef = useRef(null);
    const knownOrderIdsRef = useRef(new Set((initial.pending_orders || []).map((order) => order.id)));

    const coveragePercent = useMemo(() => {
        if (!initial.policy || Number(initial.policy.coverage_limit) === 0) {
            return 0;
        }
        return Math.min(100, (Number(initial.policy.coverage_used) / Number(initial.policy.coverage_limit)) * 100);
    }, [initial.policy]);

    useEffect(() => {
        gsap.from(".panel", { y: 24, opacity: 0, duration: 0.8, stagger: 0.08, ease: "power2.out" });
    }, []);

    useEffect(() => {
        if (terminalRef.current) {
            terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
        }
    }, [terminalLines]);

    useEffect(() => {
        let active = true;

        const pollPendingOrders = async () => {
            try {
                const res = await fetch("/api/worker_pending_orders");
                if (!res.ok) {
                    return;
                }

                const latestOrders = await res.json();
                if (!active) {
                    return;
                }

                const incoming = latestOrders.filter((order) => !knownOrderIdsRef.current.has(order.id));
                if (incoming.length > 0) {
                    setTerminalLines((prev) => [
                        ...prev,
                        `${incoming.length} new order${incoming.length > 1 ? "s" : ""} received in queue.`
                    ]);

                    if ("Notification" in window) {
                        if (Notification.permission === "granted") {
                            new Notification("Guidewire Worker Hub", {
                                body: `${incoming.length} new order${incoming.length > 1 ? "s" : ""} waiting in queue.`
                            });
                        } else if (Notification.permission === "default") {
                            Notification.requestPermission();
                        }
                    }

                }

                setPendingOrders(latestOrders);
                knownOrderIdsRef.current = new Set(latestOrders.map((order) => order.id));
            } catch (error) {
                console.error("Failed to poll worker queue", error);
            }
        };

        pollPendingOrders();
        const intervalId = setInterval(pollPendingOrders, 5000);

        return () => {
            active = false;
            clearInterval(intervalId);
        };
    }, []);

    const appendLine = (line) => {
        setTerminalLines((prev) => [...prev, line]);
    };

    const rejectOrder = async (orderId) => {
        await fetch("/api/reject_order", {
            method: "POST",
            body: JSON.stringify({ order_id: orderId }),
            headers: { "Content-Type": "application/json" }
        });
        setPendingOrders((prev) => prev.filter((order) => order.id !== orderId));
        appendLine(`Order #${orderId} rejected by worker.`);
    };

    const buyPolicy = async (tier, premium) => {
        setBuyingTier(tier);
        const body = new URLSearchParams({ tier, premium: String(premium) });
        await fetch("/buy_policy", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: body.toString()
        });
        window.location.reload();
    };

    const startPayment = (opt) => {
        setPaymentTarget(opt);
        setPaymentMethod("card");
        setShowExpiryPicker(false);
        setPaymentForm({ cardHolder: "", cardNumber: "", expiry: "", cvv: "" });
    };

    const closePayment = () => {
        if (buyingTier) {
            return;
        }
        setShowExpiryPicker(false);
        setPaymentTarget(null);
    };

    const openExpiryPicker = () => {
        setShowExpiryPicker((prev) => !prev);
        setTimeout(() => {
            if (monthPickerRef.current && typeof monthPickerRef.current.showPicker === "function") {
                monthPickerRef.current.showPicker();
            }
        }, 0);
    };

    const handleMonthPick = (value) => {
        if (!value) {
            return;
        }
        const [year, month] = value.split("-");
        const shortYear = year.slice(-2);
        setPaymentForm((prev) => ({ ...prev, expiry: `${month}/${shortYear}` }));
        setShowExpiryPicker(false);
    };

    const handlePaymentConfirm = async () => {
        if (!paymentTarget) {
            return;
        }

        if (paymentMethod === "card") {
            const { cardHolder, cardNumber, expiry, cvv } = paymentForm;
            const cardDigits = cardNumber.replace(/\D/g, "");
            const cvvDigits = cvv.replace(/\D/g, "");

            if (!cardHolder.trim() || cardDigits.length < 12 || !expiry.trim() || cvvDigits.length < 3) {
                window.alert("Please fill valid payment details.");
                return;
            }
        }

        await buyPolicy(paymentTarget.tier, paymentTarget.premium);
    };

    const startSimulatedTrip = async (orderId) => {
        setRunningOrderId(orderId);
        appendLine(`Order #${orderId} accepted. Fetching polyline.`);

        const res = await fetch("/api/start_delivery", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ order_id: orderId })
        });
        const data = await res.json();

        appendLine(`Risk assessment: ${data.suggested_action}`);
        if (data.parametric_triggered) {
            appendLine("Trigger fired: claim auto-filed and paid.");
        }

        const pathPoints = (data.route_data && data.route_data.path) || [];
        if (pathPoints.length > 0) {
            appendLine("Initiating live GPS telemetry.");
            const step = Math.max(1, Math.floor(pathPoints.length / 5));
            for (let i = 0; i < pathPoints.length; i += step) {
                const pt = pathPoints[i];
                appendLine(`GPS ping: ${pt.latitude.toFixed(4)}, ${pt.longitude.toFixed(4)}`);
                await fetch("/api/update_gps", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ order_id: orderId, lat: pt.latitude, lon: pt.longitude })
                });
                await new Promise((resolve) => setTimeout(resolve, 700));
            }
        } else {
            appendLine("Error: Could not retrieve polyline from API.");
        }

        appendLine(`Route #${orderId} complete.`);
        setTimeout(() => window.location.reload(), 1300);
    };

    return (
        <main className="app-layout two-col dashboard-shell">
            <header className="panel worker-topbar">
                <button className="profile-btn" type="button" title={`Signed in as ${initial.worker.username}`}>
                    <span className="profile-avatar">{String(initial.worker.username || "W").slice(0, 1).toUpperCase()}</span>
                    <span>
                        <strong>{initial.worker.username}</strong>
                        <small>Worker Profile</small>
                    </span>
                </button>
                <div className="worker-top-actions">
                    <a className="btn btn-ghost" href="/logout">Logout</a>
                </div>
            </header>

            <section className="sidebar-col">
                <div className="panel worker-balance-panel">
                    <h2>Worker Hub</h2>
                    <p className="balance">{formatMoney(initial.worker.wallet_balance)}</p>
                    <div className="weather-box">
                        <h3>Live Conditions</h3>
                        <p>Weather: <strong>{initial.live_weather.forecast}</strong></p>
                        <p>Risk Multiplier: <strong>{initial.live_weather.risk_multiplier}x</strong></p>
                    </div>
                </div>

                {!initial.policy ? (
                    <div className="panel">
                        <h3 className="warning-title">No Weekly Shield Active</h3>
                        <div className="stack-list">
                            {initial.options.map((opt) => (
                                <div
                                    className={`policy-option ${initial.recommended === opt.tier ? "recommended" : ""} ${hoveredTier === opt.tier ? "hovered" : ""}`}
                                    key={opt.tier}
                                    onMouseEnter={() => setHoveredTier(opt.tier)}
                                    onMouseLeave={() => setHoveredTier("")}
                                >
                                    <h4>{opt.tier} Plan - {formatMoney(opt.premium)}</h4>
                                    <p>{opt.xai_description}</p>
                                    <button
                                        className="btn btn-primary"
                                        disabled={buyingTier === opt.tier}
                                        onClick={() => startPayment(opt)}
                                    >
                                        {buyingTier === opt.tier ? "Processing..." : "Buy Cover"}
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                ) : (
                    <div className="panel policy-panel">
                        <div className="row space-between">
                            <div>
                                <h3>{initial.policy.tier} Shield Active</h3>
                                <p>Premium paid: {formatMoney(initial.policy.total_premium)} / week</p>
                            </div>
                            <div className="align-right">
                                <small>Coverage limit</small>
                                <strong>{formatMoney(initial.policy.coverage_limit)}</strong>
                            </div>
                        </div>
                        <div className="meter-wrap">
                            <div className="row space-between">
                                <span>Time Remaining</span>
                                <strong>{initial.days_left} days</strong>
                            </div>
                            <div className="meter"><div style={{ width: `${initial.time_left_pct}%` }}></div></div>
                        </div>
                        <div className="meter-wrap">
                            <div className="row space-between">
                                <span>Coverage Used</span>
                                <strong>{formatMoney(initial.policy.coverage_used)} / {formatMoney(initial.policy.coverage_limit)}</strong>
                            </div>
                            <div className="meter danger"><div style={{ width: `${coveragePercent}%` }}></div></div>
                        </div>
                        <button className="btn btn-ghost" onClick={() => setDocsOpen((v) => !v)}>
                            {docsOpen ? "Hide" : "View"} policy documents
                        </button>
                        {docsOpen && (
                            <div className="doc-box">
                                <strong>Terms & Conditions</strong>
                                <p>{initial.policy.terms_text}</p>
                                <strong>Algorithmic Rules</strong>
                                <p>{initial.policy.rules_text}</p>
                            </div>
                        )}
                    </div>
                )}
            </section>

            <section className="main-col">
                <div className="panel">
                    <h2>Pending Order Queue</h2>
                    {pendingOrders.length === 0 ? (
                        <div className="empty-state">Queue is empty. Waiting for dispatcher.</div>
                    ) : (
                        <div className="stack-list">
                            {pendingOrders.map((order) => (
                                <article className="order-card" key={order.id}>
                                    <div className="row space-between card-head">
                                        <h4>Order #{order.id}</h4>
                                        <span className="pill">Action required</span>
                                    </div>
                                    <div className="route-grid">
                                        <div>
                                            <label>Pickup</label>
                                            <p>{order.origin_name}</p>
                                            <small>({order.origin_lat}, {order.origin_lon})</small>
                                        </div>
                                        <div>
                                            <label>Dropoff</label>
                                            <p>{order.dest_name}</p>
                                            <small>({order.dest_lat}, {order.dest_lon})</small>
                                        </div>
                                    </div>
                                    <div className="row action-row">
                                        <button
                                            className="btn btn-primary"
                                            disabled={runningOrderId === order.id}
                                            onClick={() => startSimulatedTrip(order.id)}
                                        >
                                            {runningOrderId === order.id ? "Tracking..." : "Accept Route"}
                                        </button>
                                        <button className="btn btn-danger" onClick={() => rejectOrder(order.id)}>Decline</button>
                                    </div>
                                </article>
                            ))}
                        </div>
                    )}
                </div>

                <div className="panel terminal" ref={terminalRef}>
                    {terminalLines.map((line, idx) => <p key={idx}>{"> " + line}</p>)}
                </div>
            </section>

            {paymentTarget && (
                <div className="payment-backdrop" onClick={closePayment}>
                    <div className="payment-modal" onClick={(e) => e.stopPropagation()}>
                        <h3>Dummy Payment Gateway</h3>
                        <p className="subtitle">You are purchasing <strong>{paymentTarget.tier}</strong> for <strong>{formatMoney(paymentTarget.premium)}</strong>.</p>
                        <div className="payment-method-tabs">
                            <button
                                type="button"
                                className={`payment-tab ${paymentMethod === "card" ? "active" : ""}`}
                                onClick={() => setPaymentMethod("card")}
                            >
                                Card Payment
                            </button>
                            <button
                                type="button"
                                className={`payment-tab ${paymentMethod === "qr" ? "active" : ""}`}
                                onClick={() => setPaymentMethod("qr")}
                            >
                                QR Payment
                            </button>
                        </div>

                        {paymentMethod === "card" ? (
                            <div className="payment-grid">
                                <label>
                                    Card Holder
                                    <input
                                        type="text"
                                        value={paymentForm.cardHolder}
                                        onChange={(e) => setPaymentForm((prev) => ({ ...prev, cardHolder: e.target.value }))}
                                        placeholder="Full name"
                                    />
                                </label>
                                <label>
                                    Card Number
                                    <input
                                        type="text"
                                        value={paymentForm.cardNumber}
                                        onChange={(e) => setPaymentForm((prev) => ({ ...prev, cardNumber: e.target.value }))}
                                        placeholder="1234 5678 9012 3456"
                                    />
                                </label>
                                <div className="payment-grid-2">
                                    <label>
                                        Expiry
                                        <div className="expiry-picker-wrap">
                                            <input
                                                type="text"
                                                value={paymentForm.expiry}
                                                onChange={(e) => setPaymentForm((prev) => ({ ...prev, expiry: e.target.value }))}
                                                placeholder="MM/YY"
                                                readOnly
                                            />
                                            <button type="button" className="calendar-btn" onClick={openExpiryPicker} aria-label="Select expiry month and year">
                                                📅
                                            </button>
                                            {showExpiryPicker && (
                                                <div className="expiry-popover">
                                                    <input
                                                        ref={monthPickerRef}
                                                        type="month"
                                                        onChange={(e) => handleMonthPick(e.target.value)}
                                                    />
                                                </div>
                                            )}
                                        </div>
                                    </label>
                                    <label>
                                        CVV
                                        <input
                                            type="password"
                                            value={paymentForm.cvv}
                                            onChange={(e) => setPaymentForm((prev) => ({ ...prev, cvv: e.target.value }))}
                                            placeholder="123"
                                        />
                                    </label>
                                </div>
                            </div>
                        ) : (
                            <div className="qr-payment-box">
                                <div className="qr-code" aria-label="Dummy QR code"></div>
                                <p>Scan this dummy QR from any UPI app to simulate payment.</p>
                                <p className="qr-id">UPI: guidewire-demo@upi</p>
                            </div>
                        )}
                        <div className="payment-actions">
                            <button className="btn btn-ghost" onClick={closePayment} disabled={Boolean(buyingTier)}>Cancel</button>
                            <button className="btn btn-primary" onClick={handlePaymentConfirm} disabled={Boolean(buyingTier)}>
                                {buyingTier
                                    ? "Processing..."
                                    : paymentMethod === "card"
                                        ? `Pay ${formatMoney(paymentTarget.premium)}`
                                        : `Confirm QR Payment ${formatMoney(paymentTarget.premium)}`}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </main>
    );
}

ReactDOM.createRoot(document.getElementById("react-root")).render(<DashboardApp />);