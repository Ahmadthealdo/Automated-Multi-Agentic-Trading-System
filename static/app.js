/* ==========================================================================
   LeetCode-Style React Conversion for Multi-Agent Trading System
   ========================================================================== */

const { useState, useEffect, useRef } = React;

// ==========================================================================
// 1. SUB-COMPONENT: Candlestick Chart (SVG-based)
// ==========================================================================
function CandlestickChart({ candles, decision, ticker, strategyName }) {
    if (!candles || candles.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-[240px] bg-[#2D2D2D] rounded border border-[#3F3F3F]">
                <div className="text-[#A0A4A8] text-xs font-mono animate-pulse">
                    AWAITING MARKET FEEDS FOR {ticker || "ASSET"}...
                </div>
            </div>
        );
    }

    let minPrice = Infinity;
    let maxPrice = -Infinity;
    
    candles.forEach(c => {
        if (c.low < minPrice) minPrice = c.low;
        if (c.high > maxPrice) maxPrice = c.high;
    });
    
    const padding = (maxPrice - minPrice) * 0.08 || 1;
    const chartMinPrice = minPrice - padding;
    const chartMaxPrice = maxPrice + padding;
    const priceRange = chartMaxPrice - chartMinPrice;
    
    const svgWidth = 500;
    const svgHeight = 240;
    const numCandles = candles.length;
    const candleWidth = (svgWidth / numCandles) * 0.6;
    const spacing = (svgWidth / numCandles);

    // Calculate Y coordinates for TP, SL, Entry if active
    let tpY = null;
    let slY = null;
    let entryY = null;

    const showBounds = decision && 
                       decision.ticker === ticker && 
                       decision.TAKE_PROFIT > 0 && 
                       decision.STOP_LOSS > 0;

    if (showBounds && priceRange > 0) {
        tpY = svgHeight - ((decision.TAKE_PROFIT - chartMinPrice) / priceRange) * svgHeight;
        slY = svgHeight - ((decision.STOP_LOSS - chartMinPrice) / priceRange) * svgHeight;
        
        const entryPrice = decision.ENTRY_PRICE || (decision.TAKE_PROFIT / (1 + (strategyName === "15m" ? 0.02 : strategyName === "1h" ? 0.05 : strategyName === "4h" ? 0.08 : 0.15)));
        entryY = svgHeight - ((entryPrice - chartMinPrice) / priceRange) * svgHeight;
    }

    return (
        <div className="relative w-full bg-[#2D2D2D] rounded border border-[#3F3F3F] p-4 flex flex-col justify-between">
            <div className="flex justify-between items-center mb-2 border-b border-[#3F3F3F] pb-2">
                <span className="text-xs font-mono text-[#3DD9F7] font-semibold">
                    Live Feed Canvas - {ticker}
                </span>
                <div className="flex gap-4 text-[10px] font-mono text-[#A0A4A8]">
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-[#29B86F] rounded-full inline-block"></span> Bullish
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-[#FF7A45] rounded-full inline-block"></span> Bearish
                    </span>
                </div>
            </div>
            
            <div className="flex-grow flex items-center justify-center relative overflow-hidden h-[180px]">
                <svg className="w-full h-full" viewBox={`0 0 ${svgWidth} ${svgHeight}`}>
                    {/* SVG Grid Lines */}
                    <line x1="0" y1={svgHeight * 0.25} x2={svgWidth} y2={svgHeight * 0.25} stroke="#3F3F3F" strokeWidth="0.5" strokeDasharray="3,3" />
                    <line x1="0" y1={svgHeight * 0.5} x2={svgWidth} y2={svgHeight * 0.5} stroke="#3F3F3F" strokeWidth="0.5" strokeDasharray="3,3" />
                    <line x1="0" y1={svgHeight * 0.75} x2={svgWidth} y2={svgHeight * 0.75} stroke="#3F3F3F" strokeWidth="0.5" strokeDasharray="3,3" />
                    
                    {/* Draw Candlesticks */}
                    {candles.map((c, idx) => {
                        const x = idx * spacing + spacing / 2;
                        const yHigh = svgHeight - ((c.high - chartMinPrice) / priceRange) * svgHeight;
                        const yLow = svgHeight - ((c.low - chartMinPrice) / priceRange) * svgHeight;
                        const yOpen = svgHeight - ((c.open - chartMinPrice) / priceRange) * svgHeight;
                        const yClose = svgHeight - ((c.close - chartMinPrice) / priceRange) * svgHeight;
                        
                        const isBullish = c.close >= c.open;
                        const color = isBullish ? "#29B86F" : "#FF7A45";
                        const rY = Math.min(yOpen, yClose);
                        const rHeight = Math.max(Math.abs(yOpen - yClose), 1.5);
                        const rX = x - candleWidth / 2;

                        return (
                            <g key={idx}>
                                {/* Wick */}
                                <line x1={x} y1={yHigh} x2={x} y2={yLow} stroke={color} strokeWidth="1.5" />
                                {/* Body */}
                                <rect x={rX} y={rY} width={candleWidth} height={rHeight} fill={color} stroke={color} strokeWidth="0.5" />
                            </g>
                        );
                    })}

                    {/* Overlay Targets if decision active */}
                    {showBounds && (
                        <g>
                            {/* Take Profit Target */}
                            {tpY >= 0 && tpY <= svgHeight && (
                                <g>
                                    <line x1="0" y1={tpY} x2={svgWidth} y2={tpY} stroke="#29B86F" strokeWidth="1" strokeDasharray="4,4" />
                                    <text x="5" y={tpY - 4} fill="#29B86F" className="text-[9px] font-mono">TP: ${decision.TAKE_PROFIT.toFixed(2)}</text>
                                </g>
                            )}

                            {/* Entry Price Target */}
                            {entryY >= 0 && entryY <= svgHeight && (
                                <g>
                                    <line x1="0" y1={entryY} x2={svgWidth} y2={entryY} stroke="#3DD9F7" strokeWidth="1" strokeDasharray="4,4" />
                                    <text x="5" y={entryY - 4} fill="#3DD9F7" className="text-[9px] font-mono">Entry: ${decision.ENTRY_PRICE.toFixed(2)}</text>
                                </g>
                            )}

                            {/* Stop Loss Target */}
                            {slY >= 0 && slY <= svgHeight && (
                                <g>
                                    <line x1="0" y1={slY} x2={svgWidth} y2={slY} stroke="#EF4743" strokeWidth="1" strokeDasharray="4,4" />
                                    <text x="5" y={slY - 4} fill="#EF4743" className="text-[9px] font-mono">SL: ${decision.STOP_LOSS.toFixed(2)}</text>
                                </g>
                            )}
                        </g>
                    )}
                </svg>
                {/* Status Overlay Badge */}
                {decision && decision.ticker === ticker && (
                    <div className="absolute top-2 left-2 bg-[#1A1A1A] bg-opacity-80 px-2 py-1 rounded border border-[#3F3F3F] text-[9px] font-mono flex items-center gap-1.5 select-none">
                        <span className="text-[#A0A4A8] uppercase">Signal:</span>
                        <span className={decision.action.includes("BUY") ? "text-[#29B86F] font-bold" : decision.action.includes("SELL") ? "text-[#FF7A45] font-bold" : "text-white font-bold"}>
                            {decision.action}
                        </span>
                        <span className="text-[#3F3F3F]">|</span>
                        <span className="text-[#A0A4A8] uppercase">Risk:</span>
                        <span className={decision.risk_status === "APPROVED" ? "text-[#29B86F] font-bold" : "text-[#EF4743] font-bold"}>
                            {decision.risk_status}
                        </span>
                    </div>
                )}
            </div>
        </div>
    );
}

// ==========================================================================
// 2. MAIN COMPONENT: AuthPortal (Sign In / Sign Up Card with flips)
// ==========================================================================
function AuthPortal({ onLoginSuccess }) {
    const [isSignUp, setIsSignUp] = useState(false);
    const [loginEmail, setLoginEmail] = useState("");
    const [loginPassword, setLoginPassword] = useState("");
    const [loginError, setLoginError] = useState("");

    // Signup form state
    const [signupName, setSignupName] = useState("");
    const [signupEmail, setSignupEmail] = useState("");
    const [signupMobile, setSignupMobile] = useState("");
    const [signupPassword, setSignupPassword] = useState("");
    const [signupError, setSignupError] = useState("");
    const [signupSuccess, setSignupSuccess] = useState("");

    const [shake, setShake] = useState(false);

    const triggerShake = () => {
        setShake(true);
        setTimeout(() => setShake(false), 400);
    };

    const handleLogin = async (e) => {
        e.preventDefault();
        setLoginError("");

        if (!loginEmail.trim() || !loginPassword.trim()) {
            setLoginError("Email and Password are required fields.");
            triggerShake();
            return;
        }

        try {
            const response = await fetch("/api/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: loginEmail.trim(), password: loginPassword.trim() })
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Credentials verification failed.");
            }

            sessionStorage.setItem("active_operator", JSON.stringify(data.operator));
            onLoginSuccess(data.operator);
        } catch (err) {
            setLoginError(err.message);
            triggerShake();
        }
    };

    const handleSignup = async (e) => {
        e.preventDefault();
        setSignupError("");
        setSignupSuccess("");

        // Basic validations
        if (!signupName.trim() || !signupEmail.trim() || !signupMobile.trim() || !signupPassword.trim()) {
            setSignupError("All registration fields are required.");
            triggerShake();
            return;
        }

        if (signupPassword.length < 6) {
            setSignupError("Password must be at least 6 characters.");
            triggerShake();
            return;
        }

        // Pakistani mobile regex validator
        const mobileRegex = /^(03|\+923)\d{9}$/;
        if (!mobileRegex.test(signupMobile.trim())) {
            setSignupError("Mobile must be a valid format (e.g. +923xxxxxxxxx or 03xxxxxxxxx).");
            triggerShake();
            return;
        }

        const payload = {
            full_name: signupName.trim(),
            email: signupEmail.trim(),
            mobile_number: signupMobile.trim(),
            password: signupPassword.trim()
        };

        try {
            const response = await fetch("/api/signup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Operator registration rejected.");
            }

            setSignupSuccess("Registration successful! Redirecting to login portal...");
            setTimeout(() => {
                setIsSignUp(false);
                setLoginEmail(signupEmail);
                setSignupName("");
                setSignupEmail("");
                setSignupMobile("");
                setSignupPassword("");
                setSignupSuccess("");
            }, 2000);
        } catch (err) {
            setSignupError(err.message);
            triggerShake();
        }
    };

    return (
        <div className="fixed inset-0 w-full h-full flex items-center justify-center bg-[#1A1A1A] z-50 p-4">
            <div className={`w-full max-w-[500px] bg-[#232323] border border-[#3F3F3F] p-8 rounded shadow-md transition-transform duration-300 ${shake ? "shake-feedback" : ""}`}>
                
                {/* Institutional Header */}
                <div className="text-center border-b border-[#3F3F3F] pb-4 mb-6">
                    <span className="text-[10px] font-mono text-[#3DD9F7] uppercase tracking-wider block mb-1">
                        Secure Operator Console Gate
                    </span>
                    <h2 className="text-lg font-bold text-white uppercase tracking-tight">
                        Multi-Agent Relational Trading System
                    </h2>
                </div>

                {/* Sliding Toggle Control */}
                <div className="relative w-full bg-[#1A1A1A] p-1 rounded border border-[#3F3F3F] flex mb-6 select-none">
                    <div 
                        className="auth-toggle-slider" 
                        style={{ transform: isSignUp ? 'translateX(100%)' : 'translateX(0)' }}
                    />
                    <button 
                        onClick={() => { setIsSignUp(false); setLoginError(""); setSignupError(""); }}
                        className={`relative z-10 w-1/2 text-center text-xs font-semibold py-2 transition-colors duration-200 ${!isSignUp ? "text-[#1A1A1A]" : "text-[#A0A4A8] hover:text-white"}`}
                    >
                        Access Portal
                    </button>
                    <button 
                        onClick={() => { setIsSignUp(true); setLoginError(""); setSignupError(""); }}
                        className={`relative z-10 w-1/2 text-center text-xs font-semibold py-2 transition-colors duration-200 ${isSignUp ? "text-[#1A1A1A]" : "text-[#A0A4A8] hover:text-white"}`}
                    >
                        Register Operator
                    </button>
                </div>

                {!isSignUp ? (
                    /* SIGN IN FORM */
                    <form onSubmit={handleLogin} className="space-y-4">
                        <div>
                            <label className="block text-[10px] font-mono text-[#3DD9F7] uppercase tracking-wider font-semibold mb-1">
                                Operator Email Channel
                            </label>
                            <input 
                                type="email" 
                                value={loginEmail}
                                onChange={(e) => setLoginEmail(e.target.value)}
                                className="w-full bg-[#2D2D2D] border border-[#3F3F3F] rounded px-3 py-2 text-xs text-white focus:outline-none"
                                placeholder="operator@trading.com"
                            />
                        </div>
                        <div>
                            <label className="block text-[10px] font-mono text-[#3DD9F7] uppercase tracking-wider font-semibold mb-1">
                                Password Hashing Key
                            </label>
                            <input 
                                type="password" 
                                value={loginPassword}
                                onChange={(e) => setLoginPassword(e.target.value)}
                                className="w-full bg-[#2D2D2D] border border-[#3F3F3F] rounded px-3 py-2 text-xs text-white focus:outline-none"
                                placeholder="••••••••"
                            />
                        </div>

                        {loginError && (
                            <div className="text-[11px] text-[#EF4743] font-mono bg-red-950 bg-opacity-30 border border-[#EF4743] p-2 rounded">
                                Error: {loginError}
                            </div>
                        )}

                        <button 
                            type="submit"
                            className="w-full bg-[#3DD9F7] hover:bg-opacity-90 text-[#1A1A1A] font-bold font-mono tracking-wider py-2.5 rounded text-xs uppercase"
                        >
                            Open Communication Session
                        </button>
                    </form>
                ) : (
                    /* SIGN UP FORM */
                    <form onSubmit={handleSignup} className="space-y-3">
                        <div>
                            <label className="block text-[10px] font-mono text-[#3DD9F7] uppercase tracking-wider font-semibold mb-1">
                                Operator Full Name
                            </label>
                            <input 
                                type="text" 
                                value={signupName}
                                onChange={(e) => setSignupName(e.target.value)}
                                className="w-full bg-[#2D2D2D] border border-[#3F3F3F] rounded px-3 py-1.5 text-xs text-white focus:outline-none"
                                placeholder="FAQ"
                            />
                        </div>
                        <div>
                            <label className="block text-[10px] font-mono text-[#3DD9F7] uppercase tracking-wider font-semibold mb-1">
                                Operator Email Channel
                            </label>
                            <input 
                                type="email" 
                                value={signupEmail}
                                onChange={(e) => setSignupEmail(e.target.value)}
                                className="w-full bg-[#2D2D2D] border border-[#3F3F3F] rounded px-3 py-1.5 text-xs text-white focus:outline-none"
                                placeholder="operator@trading.com"
                            />
                        </div>
                        <div>
                            <label className="block text-[10px] font-mono text-[#3DD9F7] uppercase tracking-wider font-semibold mb-1">
                                Mobile Verification Number
                            </label>
                            <input 
                                type="text" 
                                value={signupMobile}
                                onChange={(e) => setSignupMobile(e.target.value)}
                                className="w-full bg-[#2D2D2D] border border-[#3F3F3F] rounded px-3 py-1.5 text-xs text-white focus:outline-none"
                                placeholder="+923001234567"
                            />
                        </div>
                        <div>
                            <label className="block text-[10px] font-mono text-[#3DD9F7] uppercase tracking-wider font-semibold mb-1">
                                Password (Min 6 Chars)
                            </label>
                            <input 
                                type="password" 
                                value={signupPassword}
                                onChange={(e) => setSignupPassword(e.target.value)}
                                className="w-full bg-[#2D2D2D] border border-[#3F3F3F] rounded px-3 py-1.5 text-xs text-white focus:outline-none"
                                placeholder="••••••••"
                            />
                        </div>

                        {signupError && (
                            <div className="text-[11px] text-[#EF4743] font-mono bg-red-950 bg-opacity-30 border border-[#EF4743] p-2 rounded">
                                Error: {signupError}
                            </div>
                        )}

                        {signupSuccess && (
                            <div className="text-[11px] text-[#29B86F] font-mono bg-green-950 bg-opacity-30 border border-[#29B86F] p-2 rounded">
                                {signupSuccess}
                            </div>
                        )}

                        <button 
                            type="submit"
                            className="w-full bg-[#3DD9F7] hover:bg-opacity-90 text-[#1A1A1A] font-bold font-mono tracking-wider py-2.5 rounded text-xs uppercase"
                        >
                            Commit Relational Credentials
                        </button>
                    </form>
                )}

            </div>
        </div>
    );
}

// ==========================================================================
// 3. MAIN COMPONENT: Dashboard (3-column layout)
// ==========================================================================
function Dashboard({ operator, onSignOut }) {
    // Strategy configs matching model schemas
    const strategyOptions = [
        { key: 'A', interval: '15m', period: '7d', name: 'Intraday Scalp' },
        { key: 'B', interval: '1h', period: '30d', name: 'Intraday Swing' },
        { key: 'C', interval: '4h', period: '60d', name: 'Medium Swing' },
        { key: 'D', interval: '1d', period: '180d', name: 'Macro Position' }
    ];

    const [activeStrat, setActiveStrat] = useState(strategyOptions[0]);
    const [ticker, setTicker] = useState("BTC-USD");
    const [priceData, setPriceData] = useState(null);
    const [isRunning, setIsRunning] = useState(false);
    const [logs, setLogs] = useState("[Telemetry Logs ready]\nOperator validated. Lock established.\n---------------------------------------\n");
    const [decision, setDecision] = useState(null);
    const [audits, setAudits] = useState([]);
    
    // Telemetry clocks
    const [utcTime, setUtcTime] = useState("");

    useEffect(() => {
        const updateClock = () => {
            const now = new Date();
            setUtcTime(now.toUTCString().replace("GMT", "UTC"));
        };
        updateClock();
        const interval = setInterval(updateClock, 1000);
        return () => clearInterval(interval);
    }, []);

    // Fetch live yfinance chart data
    const fetchChart = async (customTicker = ticker, customStrat = activeStrat) => {
        if (!customTicker.trim()) return;
        try {
            const cleanTicker = customTicker.trim().toUpperCase();
            const response = await fetch(`/api/price-chart?ticker=${cleanTicker}&period=${customStrat.period}&interval=${customStrat.interval}`);
            if (!response.ok) throw new Error("Fetch failed");
            const data = await response.json();
            setPriceData(data);
        } catch (e) {
            console.error("Failed to fetch price chart:", e);
        }
    };

    // Load initial chart and history
    useEffect(() => {
        fetchChart();
        fetchHistory();
    }, [activeStrat]);

    // Poll price data every 10 seconds
    useEffect(() => {
        const poll = setInterval(() => {
            fetchChart();
        }, 10000);
        return () => clearInterval(poll);
    }, [ticker, activeStrat]);

    // Retrieve Audit History records
    const fetchHistory = async () => {
        try {
            const res = await fetch("/api/history");
            if (res.ok) {
                const data = await res.json();
                setAudits(data);
            }
        } catch (e) {
            console.error("Failed to fetch ledger logs:", e);
        }
    };

    const handleQuickSelect = (selTicker) => {
        setTicker(selTicker);
        fetchChart(selTicker, activeStrat);
    };

    const handleExecute = async () => {
        if (!ticker.trim()) {
            alert("Provide a target security ticker symbol before execution.");
            return;
        }

        const targetTicker = ticker.trim().toUpperCase();

        // Crypto formatting check
        const cryptoKeywords = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOT', 'DOGE', 'LTC', 'LINK', 'UNI', 'AVAX'];
        if (cryptoKeywords.includes(targetTicker)) {
            alert(`Polite Correction: Cryptocurrency assets must be explicitly mapped with their base currency pair. Please use '${targetTicker}-USD' instead of '${targetTicker}'.`);
            return;
        }

        setIsRunning(true);
        setDecision(null);
        
        let runLogs = `[Telemetry Trace initialized] Booting Master Desk Router...\n`;
        runLogs += `Asset Locked: '${targetTicker}' | Strategy Target: '${activeStrat.name}'\n`;
        runLogs += `Accessing Neon PostgreSQL connection pooler and launching AI analyst...\n`;
        runLogs += `Evaluating moving averages, crossovers, MACD, and RSI levels...\n`;
        runLogs += `Requesting compliance check from Risk Manager Guardrail...\n`;
        runLogs += `Please stand by. Model reasoning takes 25-40 seconds...\n`;
        setLogs(runLogs);

        const payload = {
            ticker: targetTicker,
            interval: activeStrat.interval,
            period: activeStrat.period,
            strategy: activeStrat.name,
            user_name: operator.full_name,
            user_email: operator.email,
            user_phone: operator.mobile_number
        };

        try {
            const response = await fetch("/api/trade", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Agent execution failed.");
            }

            setDecision(data);
            
            // Append formatted completion logs
            runLogs += `-------------------------------------------------------\n`;
            runLogs += `QUANT DESK SIGNAL RETURNED:\n`;
            runLogs += `Asset Ticker     : ${data.ticker}\n`;
            runLogs += `Strategy Action  : ${data.action}\n`;
            runLogs += `Risk Verdict     : ${data.risk_status}\n`;
            runLogs += `Budget Allocation: ${data.budget_allocation}\n`;
            runLogs += `Position Entry   : ${data.ENTRY_PRICE > 0 ? '$' + data.ENTRY_PRICE.toFixed(2) : 'N/A'}\n`;
            runLogs += `Take Profit Target: ${data.TAKE_PROFIT > 0 ? '$' + data.TAKE_PROFIT.toFixed(2) : 'N/A'}\n`;
            runLogs += `Stop Loss Target  : ${data.STOP_LOSS > 0 ? '$' + data.STOP_LOSS.toFixed(2) : 'N/A'}\n`;
            runLogs += `Justification    : ${data.justification}\n`;
            setLogs(runLogs);

            // Reload audits
            fetchHistory();
            
            // Reload price chart to update TP/SL wicks instantly
            fetchChart(targetTicker, activeStrat);

        } catch (e) {
            runLogs += `\n[Error] Pipeline crashed: ${e.message}\n`;
            setLogs(runLogs);
            alert("Error running Multi-Agent Execution. See trace logs for details.");
        } finally {
            setIsRunning(false);
        }
    };

    // Derived statistics calculations
    const totalRuns = audits.length;
    const approvedRuns = audits.filter(a => a.risk_status === 'APPROVED').length;
    const successRate = totalRuns > 0 ? Math.round((approvedRuns / totalRuns) * 100) : 100;

    return (
        <div className="min-h-screen flex flex-col justify-between p-6 bg-[#1A1A1A]">
            <div>
                {/* 1. TOP NAVIGATION BAR */}
                <header className="leetcode-panel p-4 rounded mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
                        <h1 className="text-base font-extrabold uppercase tracking-widest text-[#E4E6EB]">
                            Automated <span className="text-[#3DD9F7]">Trading Desk</span>
                        </h1>
                        <span className="hidden sm:inline text-[#3F3F3F]">|</span>
                        <div className="text-[11px] font-mono text-[#A0A4A8] tracking-wider">
                            Framework: <span className="text-[#3DD9F7] font-semibold">OpenAI Agents SDK</span> &nbsp;•&nbsp; Database: <span className="text-[#29B86F] font-semibold">Neon PostgreSQL</span>
                        </div>
                    </div>
                    
                    <div className="flex flex-col sm:flex-row items-center gap-3">
                        <div className="font-mono text-xs text-[#3DD9F7] tracking-wider font-medium bg-[#1A1A1A] px-3 py-1 rounded border border-[#3F3F3F]">
                            {utcTime || "SYSTEM TIME: UTC"}
                        </div>
                        
                        <div className="flex items-center space-x-2 border border-[#3F3F3F] px-3 py-1 rounded bg-[#1A1A1A]">
                            <span className="w-2 h-2 bg-[#29B86F] rounded-full"></span>
                            <span className="font-mono text-[10px] tracking-wide text-[#29B86F] uppercase">
                                Operator Connected
                            </span>
                        </div>
                    </div>
                </header>

                {/* 3-COLUMN LAYOUT GRID */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
                    
                    {/* LEFT COLUMN: SIDEBAR (3 Columns) */}
                    <aside className="col-span-1 lg:col-span-3 flex flex-col gap-6">
                        
                        {/* Operator Profile */}
                        <div className="leetcode-panel p-5 rounded">
                            <div className="border-b border-[#3F3F3F] pb-3 mb-4 flex justify-between items-center">
                                <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-[#3DD9F7]">
                                    Operator Profile
                                </h3>
                                <button 
                                    onClick={onSignOut}
                                    className="text-[10px] font-mono text-[#EF4743] hover:underline"
                                >
                                    Sign Out
                                </button>
                            </div>
                            <div className="space-y-3 font-mono text-[11px]">
                                <div>
                                    <span className="text-[#A0A4A8] block">FULL NAME</span>
                                    <span className="text-white font-medium">{operator.full_name}</span>
                                </div>
                                <div>
                                    <span className="text-[#A0A4A8] block">EMAIL GATEWAY</span>
                                    <span className="text-white truncate block">{operator.email}</span>
                                </div>
                                <div>
                                    <span className="text-[#A0A4A8] block">VERIFICATION PHONE</span>
                                    <span className="text-white">{operator.verified_phone || operator.mobile_number}</span>
                                </div>
                            </div>
                        </div>

                        {/* Portfolio Stats */}
                        <div className="leetcode-panel p-5 rounded">
                            <div className="border-b border-[#3F3F3F] pb-3 mb-4">
                                <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-[#3DD9F7]">
                                    Portfolio Ledger
                                </h3>
                            </div>
                            
                            <div className="space-y-4 font-mono text-[11px]">
                                <div className="bg-[#1A1A1A] p-3 rounded border border-[#3F3F3F]">
                                    <span className="text-[#A0A4A8] text-[9px] block">TOTAL ACCOUNT CAPITAL</span>
                                    <span className="text-base font-bold text-white block mt-0.5">$10,000.00 USDT</span>
                                </div>
                                <div className="grid grid-cols-2 gap-2">
                                    <div className="bg-[#1A1A1A] p-2.5 rounded border border-[#3F3F3F]">
                                        <span className="text-[#A0A4A8] text-[9px] block">TOTAL RUNS</span>
                                        <span className="text-sm font-bold text-white mt-0.5 block">{totalRuns}</span>
                                    </div>
                                    <div className="bg-[#1A1A1A] p-2.5 rounded border border-[#3F3F3F]">
                                        <span className="text-[#A0A4A8] text-[9px] block">AUDIT COMPLY</span>
                                        <span className="text-sm font-bold text-[#29B86F] mt-0.5 block">{successRate}%</span>
                                    </div>
                                </div>
                                
                                <div className="pt-2 border-t border-[#3F3F3F] text-[10px] text-[#A0A4A8] leading-relaxed">
                                    Risk rules strictly block allocation budgets if strategies fall below setup baseline thresholds.
                                </div>
                            </div>
                        </div>

                    </aside>

                    {/* CENTER COLUMN: TRADING DASHBOARD (6 Columns) */}
                    <main className="col-span-1 lg:col-span-6 flex flex-col gap-6">
                        
                        {/* Search & Quick-Select Asset Bar */}
                        <div className="leetcode-panel p-5 rounded">
                            <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center mb-4">
                                <div className="w-full sm:w-1/2">
                                    <label className="block text-[10px] font-mono text-[#3DD9F7] uppercase tracking-wider mb-1">
                                        Target Asset Ticker
                                    </label>
                                    <div className="flex gap-2">
                                        <input 
                                            type="text" 
                                            value={ticker}
                                            onChange={(e) => setTicker(e.target.value)}
                                            className="w-full bg-[#2D2D2D] border border-[#3F3F3F] rounded px-3 py-2 text-xs text-white focus:outline-none"
                                            placeholder="BTC-USD, AAPL"
                                        />
                                        <button 
                                            onClick={() => fetchChart(ticker, activeStrat)}
                                            className="bg-[#3DD9F7] hover:bg-opacity-90 text-[#1A1A1A] px-3 font-mono font-bold text-xs rounded"
                                        >
                                            LOAD
                                        </button>
                                    </div>
                                </div>
                                <div className="w-full sm:w-1/2">
                                    <span className="block text-[10px] font-mono text-[#A0A4A8] uppercase tracking-wider mb-1.5 font-semibold">
                                        Popular Quick Selects
                                    </span>
                                    <div className="flex flex-wrap gap-1.5">
                                        {['BTC-USD', 'ETH-USD', 'SOL-USD', 'AAPL', 'NVDA', 'TSLA'].map(tick => (
                                            <button 
                                                key={tick}
                                                onClick={() => handleQuickSelect(tick)}
                                                className={`asset-badge ${ticker.toUpperCase().trim() === tick ? 'border-[#3DD9F7] text-white bg-opacity-10 bg-[#3DD9F7]' : ''}`}
                                            >
                                                {tick}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                            
                            {/* Live Price Display Bar */}
                            {priceData && (
                                <div className="mt-3 pt-3 border-t border-[#3F3F3F] flex flex-wrap gap-4 justify-between items-center text-xs font-mono">
                                    <div>
                                        <span className="text-[#A0A4A8] text-[9px] block">LIVE PRICE</span>
                                        <span className="text-base font-bold text-white">${priceData.current_price.toFixed(2)}</span>
                                    </div>
                                    <div>
                                        <span className="text-[#A0A4A8] text-[9px] block">24H VARIANCE</span>
                                        <span className={`text-xs font-bold block ${priceData.price_change_pct >= 0 ? 'text-[#29B86F]' : 'text-[#EF4743]'}`}>
                                            {priceData.price_change_pct >= 0 ? '+' : ''}{priceData.price_change_pct.toFixed(2)}%
                                        </span>
                                    </div>
                                    <div>
                                        <span className="text-[#A0A4A8] text-[9px] block">24H HIGH / LOW</span>
                                        <span className="text-white block">${priceData.high.toFixed(2)} / ${priceData.low.toFixed(2)}</span>
                                    </div>
                                    <div>
                                        <span className="text-[#A0A4A8] text-[9px] block">VOLUME</span>
                                        <span className="text-white block">{priceData.volume.toLocaleString()}</span>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* SVG Candlestick Chart */}
                        <CandlestickChart 
                            candles={priceData ? priceData.candles : []} 
                            decision={decision} 
                            ticker={ticker.toUpperCase().trim()} 
                            strategyName={activeStrat.interval}
                        />

                        {/* Strategy selectors */}
                        <div className="leetcode-panel p-5 rounded">
                            <label className="block text-[10px] font-mono text-[#3DD9F7] uppercase tracking-wider mb-2 font-semibold">
                                Lookback Calculation Strategy
                            </label>
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                {strategyOptions.map(opt => (
                                    <button 
                                        key={opt.key}
                                        onClick={() => setActiveStrat(opt)}
                                        className={`strategy-card p-2 rounded text-center text-[10px] font-mono flex flex-col justify-between h-[54px] ${activeStrat.key === opt.key ? 'active' : ''}`}
                                    >
                                        <span className="font-bold text-white block">{opt.name}</span>
                                        <span className="text-[#A0A4A8] text-[9px] mt-1 block">{opt.interval} / {opt.period}</span>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Order execution panel */}
                        <div className="leetcode-panel p-5 rounded">
                            <button 
                                onClick={handleExecute}
                                disabled={isRunning}
                                className="w-full bg-[#29B86F] hover:bg-opacity-90 disabled:opacity-50 text-[#1A1A1A] font-mono font-bold tracking-widest py-3 rounded text-xs uppercase transition-all duration-200 flex items-center justify-center space-x-2"
                            >
                                <span>{isRunning ? "PROCESSING QUANT PIPELINE..." : "RUN MULTI-AGENT EXECUTION"}</span>
                                {isRunning && (
                                    <div className="w-4 h-4 border-2 border-black border-t-transparent animate-spin rounded-full"></div>
                                )}
                            </button>
                        </div>

                    </main>

                    {/* RIGHT COLUMN: SIDEBAR (3 Columns) */}
                    <aside className="col-span-1 lg:col-span-3 flex flex-col gap-6">
                        
                        {/* Gamification / Achievements / Leaderboard */}
                        <div className="leetcode-panel p-5 rounded">
                            <div className="border-b border-[#3F3F3F] pb-3 mb-4">
                                <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-[#3DD9F7]">
                                    System Achievements
                                </h3>
                            </div>
                            
                            <div className="space-y-3 font-mono text-[10px]">
                                <div className="flex items-center justify-between p-2 rounded bg-[#1A1A1A] border border-[#3F3F3F]">
                                    <div className="flex items-center gap-2">
                                        <span className="text-[#29B86F]">✔</span>
                                        <div>
                                            <p className="font-bold text-white">Tunnel Established</p>
                                            <p className="text-[9px] text-[#A0A4A8]">Operator credentials verified</p>
                                        </div>
                                    </div>
                                    <span className="text-[#29B86F]">10 XP</span>
                                </div>
                                
                                <div className={`flex items-center justify-between p-2 rounded bg-[#1A1A1A] border ${totalRuns > 0 ? 'border-[#3F3F3F]' : 'border-transparent opacity-60'}`}>
                                    <div className="flex items-center gap-2">
                                        <span className={totalRuns > 0 ? "text-[#29B86F]" : "text-[#A0A4A8]"}>
                                            {totalRuns > 0 ? "✔" : "○"}
                                        </span>
                                        <div>
                                            <p className="font-bold text-white">Quantum Explorer</p>
                                            <p className="text-[9px] text-[#A0A4A8]">Executed first agent check</p>
                                        </div>
                                    </div>
                                    <span className="text-[#3DD9F7]">30 XP</span>
                                </div>

                                <div className={`flex items-center justify-between p-2 rounded bg-[#1A1A1A] border ${approvedRuns > 0 ? 'border-[#3F3F3F]' : 'border-transparent opacity-60'}`}>
                                    <div className="flex items-center gap-2">
                                        <span className={approvedRuns > 0 ? "text-[#29B86F]" : "text-[#A0A4A8]"}>
                                            {approvedRuns > 0 ? "✔" : "○"}
                                        </span>
                                        <div>
                                            <p className="font-bold text-white">Audit Compliant</p>
                                            <p className="text-[9px] text-[#A0A4A8]">Risk Manager approved run</p>
                                        </div>
                                    </div>
                                    <span className="text-[#3DD9F7]">50 XP</span>
                                </div>
                            </div>
                        </div>

                        {/* Real-time price targets monitor */}
                        <div className="leetcode-panel p-5 rounded flex-grow flex flex-col min-h-[220px]">
                            <div className="border-b border-[#3F3F3F] pb-3 mb-4">
                                <h3 className="text-xs font-bold uppercase tracking-wider font-mono text-[#3DD9F7]">
                                    Live Strategy Targets
                                </h3>
                            </div>
                            
                            {decision ? (
                                <div className="space-y-3 font-mono text-[11px] flex-grow flex flex-col justify-between">
                                    <div className="space-y-2">
                                        <div className="flex justify-between items-center bg-[#1A1A1A] p-2 rounded border border-[#3F3F3F]">
                                            <span className="text-[#A0A4A8]">SIGNAL TIER:</span>
                                            <span className={`font-bold uppercase ${decision.action.includes('BUY') ? 'text-[#29B86F]' : (decision.action.includes('SELL') ? 'text-[#FF7A45]' : 'text-[#A0A4A8]')}`}>
                                                {decision.action}
                                            </span>
                                        </div>
                                        <div className="flex justify-between items-center bg-[#1A1A1A] p-2 rounded border border-[#3F3F3F]">
                                            <span className="text-[#A0A4A8]">RISK COMPLY:</span>
                                            <span className={`font-bold ${decision.risk_status === 'APPROVED' ? 'text-[#29B86F]' : 'text-[#EF4743]'}`}>
                                                {decision.risk_status}
                                            </span>
                                        </div>
                                        <div className="flex justify-between items-center bg-[#1A1A1A] p-2 rounded border border-[#3F3F3F]">
                                            <span className="text-[#A0A4A8]">ALLOCATION:</span>
                                            <span className="font-bold text-white">{decision.budget_allocation}</span>
                                        </div>
                                        <div className="flex justify-between items-center bg-[#1A1A1A] p-2 rounded border border-[#3F3F3F]">
                                            <span className="text-[#A0A4A8]">ENTRY PRICE:</span>
                                            <span className="font-bold text-[#3DD9F7]">${decision.ENTRY_PRICE.toFixed(2)}</span>
                                        </div>
                                    </div>
                                    
                                    <div className="pt-2 text-[9px] text-[#A0A4A8] leading-tight border-t border-[#3F3F3F]">
                                        <span className="font-bold block text-white mb-0.5">JUSTIFICATION:</span>
                                        {decision.justification}
                                    </div>
                                </div>
                            ) : (
                                <div className="text-center text-[#A0A4A8] text-[10px] font-mono my-auto">
                                    {isRunning ? "ANALYZING SIGNAL MATH..." : "AWAITING MULTI-AGENT EXECUTION RUN"}
                                </div>
                            )}
                        </div>

                        {/* Real-time traces logs */}
                        <div className="leetcode-panel p-4 rounded h-[220px] flex flex-col justify-between">
                            <div className="border-b border-[#3F3F3F] pb-2 mb-2">
                                <span className="font-mono text-[10px] text-[#3DD9F7] uppercase tracking-wider font-bold">
                                    Agent Live Traces Monitor
                                </span>
                            </div>
                            <pre className="flex-grow font-mono text-[9px] text-[#29B86F] overflow-y-auto bg-black p-3.5 rounded leading-relaxed whitespace-pre-wrap select-all border border-[#3F3F3F]">
                                {logs}
                            </pre>
                        </div>

                    </aside>
                </div>
            </div>

            {/* 4. FOOTER LEDGER TABLE */}
            <footer className="leetcode-panel p-6 rounded mt-6 font-mono">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#3F3F3F] pb-3 mb-4">
                    <h4 className="font-sans font-bold text-xs tracking-wider uppercase text-white">
                        Neon PostgreSQL Relational Ledgers - Execution Audit Registry
                    </h4>
                    <button 
                        onClick={fetchHistory}
                        className="text-[10px] text-[#3DD9F7] hover:underline transition-all"
                    >
                        REFRESH LEDGERS &rarr;
                    </button>
                </div>
                
                <div className="overflow-x-auto max-h-[220px]">
                    <table className="w-full text-left text-[10px]">
                        <thead>
                            <tr className="border-b border-[#3F3F3F] text-[#A0A4A8] uppercase tracking-wider text-[9px]">
                                <th className="py-2 pb-3 font-semibold">Timestamp (UTC)</th>
                                <th className="py-2 pb-3 font-semibold">Operator</th>
                                <th className="py-2 pb-3 font-semibold">Asset</th>
                                <th className="py-2 pb-3 font-semibold">Decision</th>
                                <th className="py-2 pb-3 font-semibold">Risk Audit</th>
                                <th className="py-2 pb-3 font-semibold">Capital</th>
                                <th className="py-2 pb-3 font-semibold">Alloc. Budget</th>
                                <th className="py-2 pb-3 font-semibold">Entry</th>
                                <th className="py-2 pb-3 font-semibold">TP Target</th>
                                <th className="py-2 pb-3 font-semibold">SL Target</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#3F3F3F] divide-opacity-30">
                            {audits.length === 0 ? (
                                <tr>
                                    <td colSpan="10" className="py-6 text-center text-[#A0A4A8] uppercase">
                                        No audits registered. Run a quantitative cycle to populate Neon tables.
                                    </td>
                                </tr>
                            ) : (
                                audits.map(r => {
                                    const formattedDate = new Date(r.timestamp).toISOString().replace("T", " ").slice(0, 19);
                                    return (
                                        <tr key={r.id} className="hover:bg-white hover:bg-opacity-5 transition-colors">
                                            <td className="py-2.5 text-[#A0A4A8]">{formattedDate}</td>
                                            <td className="py-2.5 text-[#3DD9F7] font-medium">{r.user_name}</td>
                                            <td className="py-2.5 text-[#E4E6EB]">{r.ticker}</td>
                                            <td className={`py-2.5 font-bold ${r.action.includes('BUY') ? 'text-[#29B86F]' : (r.action.includes('SELL') ? 'text-[#FF7A45]' : 'text-[#A0A4A8]')}`}>
                                                {r.action}
                                            </td>
                                            <td className={`py-2.5 font-bold ${r.risk_status === 'APPROVED' ? 'text-[#29B86F]' : 'text-[#EF4743]'}`}>
                                                {r.risk_status}
                                            </td>
                                            <td className="py-2.5 text-[#E4E6EB]">{r.stable_capital}</td>
                                            <td className="py-2.5 text-[#FF7A45]">{r.budget_allocation}</td>
                                            <td className="py-2.5 text-[#3DD9F7]">
                                                {r.entry_price && r.entry_price !== '0.0' && r.entry_price !== '0' ? '$' + parseFloat(r.entry_price).toFixed(2) : 'N/A'}
                                            </td>
                                            <td className="py-2.5 text-[#29B86F]">
                                                {r.take_profit && r.take_profit !== '0.0' && r.take_profit !== '0' ? '$' + parseFloat(r.take_profit).toFixed(2) : 'N/A'}
                                            </td>
                                            <td className="py-2.5 text-[#EF4743]">
                                                {r.stop_loss && r.stop_loss !== '0.0' && r.stop_loss !== '0' ? '$' + parseFloat(r.stop_loss).toFixed(2) : 'N/A'}
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>
            </footer>
        </div>
    );
}

// ==========================================================================
// 4. ENTRY COMPONENT: App wrapper containing Router
// ==========================================================================
function App() {
    const [operator, setOperator] = useState(null);

    // Read operator session storage on boot
    useEffect(() => {
        const stored = sessionStorage.getItem("active_operator");
        if (stored) {
            try {
                setOperator(JSON.parse(stored));
            } catch (e) {
                console.error("Session decode warning:", e);
            }
        }
    }, []);

    const handleLoginSuccess = (op) => {
        setOperator(op);
    };

    const handleSignOut = () => {
        sessionStorage.removeItem("active_operator");
        setOperator(null);
    };

    if (!operator) {
        return <AuthPortal onLoginSuccess={handleLoginSuccess} />;
    }

    return <Dashboard operator={operator} onSignOut={handleSignOut} />;
}

// Render the application node root cleanly
const container = document.getElementById("root");
const root = ReactDOM.createRoot(container);
root.render(<App />);
