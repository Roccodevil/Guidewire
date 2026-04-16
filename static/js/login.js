const { useEffect, useMemo, useState } = React;

const ROLE_META = {
    worker: {
        title: "Worker Login",
        subtitle: "Track deliveries, accept routes, and manage your weekly shield.",
        badge: "Worker",
        theme: "worker",
        focusTitle: "Worker dashboard"
    },
    company: {
        title: "Company Login",
        subtitle: "Dispatch deliveries, choose routes, and manage active workers.",
        badge: "Company",
        theme: "company",
        focusTitle: "Fleet control"
    },
    admin: {
        title: "Admin Login",
        subtitle: "Manage workers, policy tiers, and live telemetry in one place.",
        badge: "Admin",
        theme: "admin",
        focusTitle: "System oversight"
    }
};

const THEME_META = {
    worker: {
        title: "Worker Portal",
        accent: "#1f7a5e",
        accentSoft: "rgba(31, 122, 94, 0.12)",
        glow: "rgba(31, 122, 94, 0.20)",
        image: "/static/images/worker.png",
        background: "linear-gradient(135deg, #f2f8f4 0%, #edf6f0 48%, #f8fbf6 100%)"
    },
    company: {
        title: "Company Portal",
        accent: "#2c8f7c",
        accentSoft: "rgba(44, 143, 124, 0.12)",
        glow: "rgba(44, 143, 124, 0.20)",
        image: "/static/images/company.png",
        background: "linear-gradient(135deg, #f1fbf8 0%, #edf8f5 48%, #f8fcfb 100%)"
    },
    admin: {
        title: "Admin Portal",
        accent: "#396b4b",
        accentSoft: "rgba(57, 107, 75, 0.12)",
        glow: "rgba(57, 107, 75, 0.22)",
        image: "/static/images/admin.png",
        background: "linear-gradient(135deg, #f4f8f1 0%, #eff6ec 48%, #fbfcf8 100%)"
    }
};

function BrandTitle({ text }) {
    return (
        <h1 className="brand-title brand-title-hover" aria-label={text}>
            {text.split("").map((letter, index) => (
                <span
                    key={`${letter}-${index}`}
                    className={`brand-letter ${letter === " " ? "brand-space" : ""}`}
                    style={{ "--delay": `${index * 35}ms` }}
                    aria-hidden="true"
                >
                    {letter === " " ? "\u00A0" : letter}
                </span>
            ))}
        </h1>
    );
}

function LoginApp() {
    const data = window.__LOGIN_DATA__ || { flashes: [], login_role: "worker" };
    const initialRole = data.login_role && ROLE_META[data.login_role] ? data.login_role : "worker";
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [role, setRole] = useState(initialRole);

    useEffect(() => {
        gsap.from(".auth-panel", { y: 30, opacity: 0, duration: 0.8, ease: "power3.out" });
        gsap.from(".role-switch", { y: 18, opacity: 0, duration: 0.65, delay: 0.1, ease: "power2.out" });
        gsap.from(".bg-orb", { scale: 0.6, opacity: 0, duration: 1.2, stagger: 0.08, ease: "sine.out" });
    }, []);

    const roleOptions = useMemo(() => Object.entries(ROLE_META), []);
    const currentMeta = ROLE_META[role];
    const theme = THEME_META[role];

    const pageStyle = {
        "--theme-accent": theme.accent,
        "--theme-accent-soft": theme.accentSoft,
        "--theme-glow": theme.glow,
        "--corner-image": `url(${theme.image})`,
        background: theme.background
    };

    return (
        <main className="auth-layout role-login-layout" style={pageStyle}>
            <div className="bg-orb orb-a" aria-hidden="true"></div>
            <div className="bg-orb orb-b" aria-hidden="true"></div>
            <section className="auth-panel role-login-panel">
                <div className="role-panel-head">
                    <div>
                        <BrandTitle text="Gig Shield" />
                        <span className="role-badge">Unified Login</span>
                        <h2>Sign in as {currentMeta.badge}</h2>
                        <p className="auth-subtitle">{currentMeta.subtitle}</p>
                    </div>
                </div>

                {data.flashes.length > 0 && (
                    <div className="flash-box">
                        {data.flashes.map((msg, idx) => (
                            <p key={idx}>{msg}</p>
                        ))}
                    </div>
                )}

                <form method="POST" action="/login" className="auth-form">
                    <div className="auth-field role-switch">
                        <label>Sign in as</label>
                        <input type="hidden" name="role" value={role} />
                        <div className="role-options" role="radiogroup" aria-label="Sign in as">
                            {roleOptions.map(([optionRole, meta]) => {
                                const isActive = role === optionRole;
                                return (
                                    <button
                                        key={optionRole}
                                        type="button"
                                        className={`role-option ${isActive ? "active" : ""}`}
                                        aria-pressed={isActive}
                                        aria-label={`Sign in as ${meta.badge}`}
                                        onClick={() => setRole(optionRole)}
                                    >
                                        <span className="role-option-badge">{meta.badge}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                    <input
                        type="text"
                        name="username"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="Username"
                        required
                    />
                    <input
                        type="password"
                        name="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Password"
                        required
                    />
                    <button type="submit" className="btn btn-primary">Sign In</button>
                </form>

                <p className="auth-hint">Only {role} accounts can sign in with this selected role.</p>
            </section>
        </main>
    );
}

ReactDOM.createRoot(document.getElementById("react-root")).render(<LoginApp />);
