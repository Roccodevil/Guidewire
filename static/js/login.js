const { useEffect, useMemo, useState } = React;

const ROLE_META = {
    worker: {
        title: "Worker Portal",
        subtitle: "Track deliveries, accept routes, and manage your weekly shield.",
        href: "/login/worker",
        badge: "Worker",
        theme: "worker",
        focusTitle: "Worker dashboard"
    },
    company: {
        title: "Company Portal",
        subtitle: "Dispatch deliveries, choose routes, and manage active workers.",
        href: "/login/company",
        badge: "Company",
        theme: "company",
        focusTitle: "Fleet control"
    },
    admin: {
        title: "Admin Portal",
        subtitle: "Manage workers, policy tiers, and live telemetry in one place.",
        href: "/login/admin",
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
    const data = window.__LOGIN_DATA__ || { flashes: [], login_role: null };
    const currentRole = data.login_role;
    const currentMeta = currentRole ? ROLE_META[currentRole] : null;
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [activeRole, setActiveRole] = useState(null);

    useEffect(() => {
        gsap.from(".auth-panel", { y: 30, opacity: 0, duration: 0.8, ease: "power3.out" });
        gsap.from(".role-card", { y: 18, opacity: 0, duration: 0.65, stagger: 0.08, delay: 0.1, ease: "power2.out" });
        gsap.from(".bg-orb", { scale: 0.6, opacity: 0, duration: 1.2, stagger: 0.08, ease: "sine.out" });
    }, []);

    const roleCards = useMemo(() => Object.entries(ROLE_META), []);
    const themeRole = activeRole || "worker";
    const theme = THEME_META[themeRole];
    const roleTheme = currentRole ? THEME_META[currentRole] : theme;

    const pageStyle = {
        "--theme-accent": theme.accent,
        "--theme-accent-soft": theme.accentSoft,
        "--theme-glow": theme.glow,
        "--corner-image": `url(${theme.image})`,
        background: theme.background
    };

    if (!currentRole) {
        return (
            <main className="auth-layout role-chooser-layout" style={pageStyle}>
                <section className="chooser-shell chooser-hero">
                    <div className="chooser-head">
                        <div>
                            <BrandTitle text="Gig Shield" />
                            <span className="role-badge">Secure Access</span>
                            <h2>Choose Your Portal</h2>
                            <p className="subtitle">Gig Shield secures worker, company, and admin access in one platform.</p>
                        </div>
                    </div>

                    {data.flashes.length > 0 && (
                        <div className="flash-box">
                            {data.flashes.map((msg, idx) => (
                                <p key={idx}>{msg}</p>
                            ))}
                        </div>
                    )}

                    <div className={`role-stage ${activeRole ? `active-${activeRole}` : ""}`}>
                        {roleCards.map(([role, meta]) => (
                            <div
                                className="role-card-wrap"
                                key={role}
                                onMouseEnter={() => setActiveRole(role)}
                                onMouseLeave={() => setActiveRole(null)}
                            >
                                <a className={`role-card ${activeRole === role ? "active" : activeRole ? "inactive" : ""} role-${role}`} href={meta.href}>
                                    <span className="role-badge">{meta.badge}</span>
                                    <h2>{meta.title}</h2>
                                    <p>{meta.subtitle}</p>
                                    <div className="role-card-foot">
                                        <span className="role-link">Open login</span>
                                        <span className="role-focus">{meta.focusTitle}</span>
                                    </div>
                                </a>
                            </div>
                        ))}
                    </div>
                </section>
            </main>
        );
    }

    return (
        <main
            className="auth-layout role-login-layout"
            style={{
                "--theme-accent": roleTheme.accent,
                "--theme-accent-soft": roleTheme.accentSoft,
                "--theme-glow": roleTheme.glow,
                "--corner-image": `url(${roleTheme.image})`,
                background: roleTheme.background
            }}
        >
            <section className="auth-panel role-login-panel">
                <div className="role-panel-head">
                    <div>
                        <BrandTitle text="Gig Shield" />
                        <span className="role-badge">{currentMeta.badge}</span>
                        <h2>{currentMeta.title}</h2>
                        <p className="auth-subtitle">{currentMeta.subtitle}</p>
                    </div>
                    <a className="back-link" href="/login">Change portal</a>
                </div>

                {data.flashes.length > 0 && (
                    <div className="flash-box">
                        {data.flashes.map((msg, idx) => (
                            <p key={idx}>{msg}</p>
                        ))}
                    </div>
                )}

                <form method="POST" action={`/login/${currentRole}`} className="auth-form">
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

                <p className="auth-hint">Only {currentRole} accounts can sign in here.</p>
            </section>
        </main>
    );
}

ReactDOM.createRoot(document.getElementById("react-root")).render(<LoginApp />);
