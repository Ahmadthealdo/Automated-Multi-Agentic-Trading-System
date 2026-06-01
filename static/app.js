/* ==========================================================================
   Integrated Multi-Agent Trading Desk Front-End Controller
   ========================================================================== */

// Core dashboard parameters state
let currentInterval = "15m";
let currentPeriod = "7d";
let currentStrategy = "Intraday Scalp";
let activeOperator = null;

// Telemetry Time Tracking
setInterval(() => {
    const clock = document.getElementById("telemetry-clock");
    if (clock) {
        const now = new Date();
        clock.innerText = `SYSTEM TIME: ${now.toUTCString().replace("GMT", "UTC")}`;
    }
}, 1000);

// Perspective flips signup/login overlay containers
function toggleAuthCard(showSignUp) {
    const container = document.getElementById("flip-container");
    const loginErr = document.getElementById("login-error");
    const signupErr = document.getElementById("signup-error");
    
    if (loginErr) loginErr.classList.add("hidden");
    if (signupErr) signupErr.classList.add("hidden");
    
    if (container) {
        if (showSignUp) {
            container.classList.add("flip-card-flipped");
        } else {
            container.classList.remove("flip-card-flipped");
        }
    }
}

// Validation focus triggers for input parameters with strict criteria and shake effects
function validateField(fieldId, type) {
    const el = document.getElementById(fieldId);
    if (!el) return false;
    
    const val = el.value.trim();
    let isValid = true;
    
    if (type === 'name') {
        isValid = val.length > 0;
    } else if (type === 'email') {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        isValid = re.test(val);
    } else if (type === 'mobile') {
        const re = /^(03|\+923)\d{9}$/;
        isValid = re.test(val);
    } else if (type === 'password') {
        // Enforce basic complexity: minimum 6 characters
        isValid = val.length >= 6;
    }
    
    if (!isValid) {
        el.style.borderColor = "#F97316"; // Flash alert-orange on errors
        el.style.boxShadow = "0 0 10px rgba(249, 115, 22, 0.4)";
    } else {
        el.style.borderColor = "rgba(56, 189, 248, 0.15)";
        el.style.boxShadow = "none";
    }
    return isValid;
}

// Shake card feedback helper on validation errors
function triggerCardShake() {
    const container = document.getElementById("auth-card-container");
    if (container) {
        container.classList.add("shake-feedback");
        setTimeout(() => {
            container.classList.remove("shake-feedback");
        }, 400);
    }
}

// User signup execution handler
async function handleSignup() {
    const nameEl = document.getElementById("signup-name");
    const emailEl = document.getElementById("signup-email");
    const mobileEl = document.getElementById("signup-mobile");
    const pwdEl = document.getElementById("signup-password");
    const signupErr = document.getElementById("signup-error");
    
    if (signupErr) signupErr.classList.add("hidden");
    
    const isNameValid = validateField("signup-name", "name");
    const isEmailValid = validateField("signup-email", "email");
    const isMobileValid = validateField("signup-mobile", "mobile");
    const isPwdValid = validateField("signup-password", "password");
    
    if (!isNameValid || !isEmailValid || !isMobileValid || !isPwdValid) {
        triggerCardShake();
        if (signupErr) {
            signupErr.innerText = "Error: Input format validations failed. Ensure password is at least 6 characters.";
            signupErr.classList.remove("hidden");
        }
        return;
    }
    
    const payload = {
        full_name: nameEl.value.trim(),
        email: emailEl.value.trim(),
        mobile_number: mobileEl.value.trim(),
        password: pwdEl.value.trim()
    };
    
    try {
        const response = await fetch("/api/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Operator registration protocol rejected.");
        }
        
        // Show success in message block, flip back to sign in
        if (signupErr) {
            signupErr.classList.remove("text-cyber-crimson");
            signupErr.classList.add("text-cyber-success");
            signupErr.style.borderColor = "#10B981";
            signupErr.innerText = "Registration Committed successfully! Redirecting to Sign In...";
            signupErr.classList.remove("hidden");
        }
        
        setTimeout(() => {
            toggleAuthCard(false);
            if (signupErr) {
                signupErr.classList.add("text-cyber-crimson");
                signupErr.style.borderColor = "";
            }
        }, 2000);
        
    } catch (err) {
        triggerCardShake();
        if (signupErr) {
            signupErr.innerText = err.message;
            signupErr.classList.remove("hidden");
        }
    }
}

// User login execution handler
async function handleLogin() {
    const emailEl = document.getElementById("login-email");
    const pwdEl = document.getElementById("login-password");
    const loginErr = document.getElementById("login-error");
    
    if (loginErr) loginErr.classList.add("hidden");
    
    const payload = {
        email: emailEl.value.trim(),
        password: pwdEl.value.trim()
    };
    
    try {
        const response = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Authentication rejected. Operator mismatch.");
        }
        
        // Save operator session locally
        sessionStorage.setItem("active_operator", JSON.stringify(data.operator));
        activeOperator = data.operator;
        
        // Trigger modal fade-out animation
        const modal = document.getElementById("auth-modal");
        const workspace = document.getElementById("main-workspace");
        
        if (modal) {
            modal.classList.add("opacity-0", "scale-95");
            setTimeout(() => {
                modal.classList.add("hidden");
            }, 700);
        }
        
        // Unlock interactive dashboard workspace
        if (workspace) {
            workspace.classList.remove("opacity-10", "opacity-20", "blur-md", "blur-sm", "pointer-events-none");
            workspace.classList.add("opacity-100");
        }
        
        // Update operator status indicator badge
        const badge = document.getElementById("operator-badge");
        if (badge) {
            badge.innerText = `OPERATOR: ${data.operator.full_name}`;
            badge.classList.remove("text-slate-300");
            badge.classList.add("text-cyber-success", "glow-success");
        }
        
        // Ingest Neon DB registry audit logs
        fetchAuditHistory();
        
    } catch (err) {
        triggerCardShake();
        if (loginErr) {
            loginErr.innerText = err.message;
            loginErr.classList.remove("hidden");
        }
    }
}

/// Timeframe selector parameter state switcher
function selectStrategy(option, interval, period, strategy) {
    currentInterval = interval;
    currentPeriod = period;
    currentStrategy = strategy;
    
    // Remove active styles from buttons
    document.querySelectorAll(".strategy-btn").forEach(btn => {
        btn.classList.remove("active");
    });
    
    // Highlight selected strategy button
    const activeBtn = document.getElementById(`strat-${option}`);
    if (activeBtn) {
        activeBtn.classList.add("active");
    }
    
    // Update strategy label in indicator monitors
    const stratLabel = document.getElementById("indicator-strategy");
    if (stratLabel) {
        stratLabel.innerText = strategy;
    }
    
    // Immediately fetch chart for new timeframe strategy settings
    fetchRealtimeChart();
}

// Ingest quantitative committed database audits
async function fetchAuditHistory() {
    const body = document.getElementById("audit-table-body");
    if (!body) return;
    
    try {
        const response = await fetch("/api/history");
        if (!response.ok) throw new Error();
        const records = await response.json();
        
        if (records.length === 0) {
            body.innerHTML = `<tr><td colspan="10" class="py-4 text-center text-slate-500">No audits found in registry database. Run a quantitative cycle to populate audits.</td></tr>`;
            return;
        }
        
        body.innerHTML = records.map(r => {
            const formattedDate = new Date(r.timestamp).toISOString().replace("T", " ").slice(0, 19);
            const riskColor = r.risk_status === 'APPROVED' ? 'text-cyber-success glow-success' : 'text-cyber-crimson glow-crimson';
            const actionColor = r.action.includes('BUY') ? 'text-cyber-success font-bold' : (r.action.includes('SELL') ? 'text-cyber-crimson font-bold' : 'text-slate-400');
            return `
                <tr class="border-b border-slate-900 border-opacity-50 hover:bg-slate-900 hover:bg-opacity-30 transition-colors">
                    <td class="py-3 text-slate-400">${formattedDate}</td>
                    <td class="py-3 text-cyber-cyan font-medium">${r.user_name}</td>
                    <td class="py-3 text-slate-200">${r.ticker}</td>
                    <td class="py-3 ${actionColor}">${r.action}</td>
                    <td class="py-3 ${riskColor}">${r.risk_status}</td>
                    <td class="py-3 text-slate-300">${r.stable_capital}</td>
                    <td class="py-3 text-cyber-amber">${r.budget_allocation}</td>
                    <td class="py-3 text-cyber-cyan font-medium">${r.entry_price && r.entry_price !== '0.0' ? '$' + parseFloat(r.entry_price).toFixed(2) : 'N/A'}</td>
                    <td class="py-3 text-cyber-success font-medium">${r.take_profit !== '0.0' ? '$' + parseFloat(r.take_profit).toFixed(2) : 'N/A'}</td>
                    <td class="py-3 text-cyber-crimson font-medium">${r.stop_loss !== '0.0' ? '$' + parseFloat(r.stop_loss).toFixed(2) : 'N/A'}</td>
                </tr>
            `;
        }).join('');
        
    } catch (err) {
        body.innerHTML = `<tr><td colspan="10" class="py-4 text-center text-cyber-crimson">Failed to load system run audits from Neon PostgreSQL.</td></tr>`;
    }
}

// Global parameters for actual live candlestick mapping
let currentCandles = [];
let chartMinPrice = 0;
let chartMaxPrice = 0;

// Fetch and scaling actual yfinance candlesticks programmatically
async function fetchRealtimeChart() {
    const tickerEl = document.getElementById("target-ticker");
    if (!tickerEl) return;
    const ticker = tickerEl.value.trim().toUpperCase();
    if (!ticker) return;
    
    try {
        const response = await fetch(`/api/price-chart?ticker=${ticker}&period=${currentPeriod}&interval=${currentInterval}`);
        if (!response.ok) throw new Error();
        const data = await response.json();
        
        currentCandles = data.candles;
        
        const overlay = document.getElementById("chart-overlay-text");
        if (overlay) {
            overlay.classList.add("hidden");
        }
        
        renderCandlesticks(data.candles);
    } catch (e) {
        console.error("Realtime chart fetch failed:", e);
    }
}

// Render wicks/bodies inside expanded SVG coordinates
function renderCandlesticks(candles) {
    const candlesGroup = document.getElementById("chart-candles");
    if (!candlesGroup) return;
    
    candlesGroup.innerHTML = "";
    if (!candles || candles.length === 0) return;
    
    let minPrice = Infinity;
    let maxPrice = -Infinity;
    
    candles.forEach(c => {
        if (c.low < minPrice) minPrice = c.low;
        if (c.high > maxPrice) maxPrice = c.high;
    });
    
    const padding = (maxPrice - minPrice) * 0.08 || 1;
    chartMinPrice = minPrice - padding;
    chartMaxPrice = maxPrice + padding;
    
    const priceRange = chartMaxPrice - chartMinPrice;
    
    const svgWidth = 400;
    const svgHeight = 200;
    
    const numCandles = candles.length;
    const candleWidth = (svgWidth / numCandles) * 0.6;
    const spacing = (svgWidth / numCandles);
    
    candles.forEach((c, idx) => {
        const x = idx * spacing + spacing / 2;
        
        const yHigh = svgHeight - ((c.high - chartMinPrice) / priceRange) * svgHeight;
        const yLow = svgHeight - ((c.low - chartMinPrice) / priceRange) * svgHeight;
        const yOpen = svgHeight - ((c.open - chartMinPrice) / priceRange) * svgHeight;
        const yClose = svgHeight - ((c.close - chartMinPrice) / priceRange) * svgHeight;
        
        const isBullish = c.close >= c.open;
        const color = isBullish ? "#10B981" : "#F97316";
        
        // Wick wicks line
        const wick = document.createElementNS("http://www.w3.org/2000/svg", "line");
        wick.setAttribute("x1", x);
        wick.setAttribute("y1", yHigh);
        wick.setAttribute("x2", x);
        wick.setAttribute("y2", yLow);
        wick.setAttribute("stroke", color);
        wick.setAttribute("stroke-width", "1.5");
        candlesGroup.appendChild(wick);
        
        // Body candle rect
        const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        const rY = Math.min(yOpen, yClose);
        const rHeight = Math.max(Math.abs(yOpen - yClose), 1.5);
        const rX = x - candleWidth / 2;
        
        rect.setAttribute("x", rX);
        rect.setAttribute("y", rY);
        rect.setAttribute("width", candleWidth);
        rect.setAttribute("height", rHeight);
        rect.setAttribute("fill", color);
        rect.setAttribute("stroke", color);
        rect.setAttribute("stroke-width", "0.5");
        candlesGroup.appendChild(rect);
    });
}

// Select Asset Quick Badges handler
function selectQuickAsset(ticker) {
    const tickerEl = document.getElementById("target-ticker");
    if (tickerEl) {
        tickerEl.value = ticker;
        fetchRealtimeChart();
    }
}

// Multi-agent autonomous desk triggers
async function executeTradingDesk() {
    const tickerEl = document.getElementById("target-ticker");
    if (!tickerEl) return;
    
    const ticker = tickerEl.value.trim().toUpperCase();
    if (!ticker) {
        alert("Please specify a target asset ticker symbol before execution.");
        return;
    }
    
    // Crypto validation checks
    const cryptoKeywords = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOT', 'DOGE', 'LTC', 'LINK', 'UNI', 'AVAX'];
    if (cryptoKeywords.includes(ticker)) {
        alert(`Polite Correction: Cryptocurrency assets must be explicitly mapped with their base currency pair. Please use '${ticker}-USD' instead of '${ticker}'.`);
        return;
    }
    
    // UI loading components
    const executeBtn = document.getElementById("execute-btn");
    const btnText = document.getElementById("btn-text");
    const spinner = document.getElementById("loader-spinner");
    const consoleBox = document.getElementById("live-console-feed");
    
    if (executeBtn) {
        executeBtn.disabled = true;
        executeBtn.style.opacity = "0.7";
    }
    if (btnText) btnText.innerText = "Executing Multi-Agent desk pipeline...";
    if (spinner) spinner.classList.remove("hidden");
    
    // Reset decision signal indicator during runs
    const signalBadge = document.getElementById("indicator-signal");
    if (signalBadge) {
        signalBadge.innerText = "ANALYZING...";
        signalBadge.className = "font-mono text-sm text-cyber-amber font-black tracking-widest uppercase mt-1 animate-pulse";
    }
    
    // Dynamic loading indicators
    document.getElementById("indicator-allocation").innerText = "AUDITING...";
    document.getElementById("indicator-entry").innerText = "CALCULATING...";
    document.getElementById("indicator-tp").innerText = "CALCULATING...";
    document.getElementById("indicator-sl").innerText = "CALCULATING...";
    
    if (consoleBox) {
        consoleBox.innerHTML = `[Telemetry Trace initialized] Booting Master Desk Router...\n`;
        consoleBox.innerHTML += `Asset Locked: '${ticker}' | Timeframe locked: '${currentStrategy}'\n`;
        consoleBox.innerHTML += `Accessing Neon PostgreSQL connection pooler and launching AI analyst...\n`;
        consoleBox.innerHTML += `Please stand by. Model reasoning takes 25-40 seconds...\n`;
    }
    
    const payload = {
        ticker: ticker,
        interval: currentInterval,
        period: currentPeriod,
        strategy: currentStrategy,
        user_name: activeOperator.full_name,
        user_email: activeOperator.email,
        user_phone: activeOperator.mobile_number
    };
    
    try {
        const response = await fetch("/api/trade", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Autonomous agent execution crashed.");
        }
        
        // Print logs to console
        if (consoleBox) {
            consoleBox.innerHTML += `-----------------------------------------------------------------------------------------------------\n`;
            consoleBox.innerHTML += `QUANT DESK SIGNAL RETURNED:\n`;
            consoleBox.innerHTML += `Asset Ticker     : ${data.ticker}\n`;
            consoleBox.innerHTML += `Strategy Action  : ${data.action}\n`;
            consoleBox.innerHTML += `Risk Verdict : ${data.risk_status}\n`;
            consoleBox.innerHTML += `Budget Allocation: ${data.budget_allocation}\n`;
            consoleBox.innerHTML += `Position Entry   : ${data.ENTRY_PRICE !== 0 ? '$' + data.ENTRY_PRICE.toFixed(2) : 'N/A'}\n`;
            consoleBox.innerHTML += `Take Profit Target: ${data.TAKE_PROFIT !== 0 ? '$' + data.TAKE_PROFIT : 'N/A'}\n`;
            consoleBox.innerHTML += `Stop Loss Target  : ${data.STOP_LOSS !== 0 ? '$' + data.STOP_LOSS : 'N/A'}\n`;
            consoleBox.innerHTML += `Justification    : ${data.justification}\n`;
        }
        
        // Update main dashboard metrics
        document.getElementById("indicator-allocation").innerText = data.budget_allocation;
        document.getElementById("indicator-entry").innerText = data.ENTRY_PRICE !== 0 ? `$${data.ENTRY_PRICE.toFixed(2)}` : 'N/A';
        document.getElementById("indicator-tp").innerText = data.TAKE_PROFIT !== 0 ? `$${data.TAKE_PROFIT.toFixed(2)}` : 'N/A';
        document.getElementById("indicator-sl").innerText = data.STOP_LOSS !== 0 ? `$${data.STOP_LOSS.toFixed(2)}` : 'N/A';
        
        // Highlight active decision signal card clearly
        if (signalBadge) {
            signalBadge.innerText = data.action;
            signalBadge.classList.remove("text-[#94A3B8]", "text-[#10B981]", "text-[#F97316]", "glow-success", "glow-crimson", "animate-pulse");
            
            if (data.action.includes("BUY")) {
                signalBadge.classList.add("text-[#10B981]", "glow-success", "font-black");
            } else if (data.action.includes("SELL")) {
                signalBadge.classList.add("text-[#F97316]", "glow-crimson", "font-black");
            } else {
                signalBadge.classList.add("text-[#94A3B8]");
            }
        }
        
        // Plot bounds dynamically in SVG Candlestick Chart scaled to actual live prices
        const chartOverlay = document.getElementById("chart-overlay-text");
        const tpLine = document.getElementById("tp-line");
        const entryLine = document.getElementById("entry-line");
        const slLine = document.getElementById("sl-line");
        
        if (data.TAKE_PROFIT !== 0 && data.STOP_LOSS !== 0 && chartMinPrice !== chartMaxPrice) {
            const priceRange = chartMaxPrice - chartMinPrice;
            const svgHeight = 200;
            
            // Scaled coordinates mapping
            const tpY = svgHeight - ((data.TAKE_PROFIT - chartMinPrice) / priceRange) * svgHeight;
            const slY = svgHeight - ((data.STOP_LOSS - chartMinPrice) / priceRange) * svgHeight;
            
            // Extract entry price from returned float payload
            const entryPrice = data.TAKE_PROFIT / (1 + (currentInterval === "15m" ? 0.02 : currentInterval === "1h" ? 0.05 : currentInterval === "4h" ? 0.08 : 0.15));
            const entryY = svgHeight - ((entryPrice - chartMinPrice) / priceRange) * svgHeight;
            
            if (chartOverlay) chartOverlay.classList.add("hidden");
            if (tpLine && tpY >= 0 && tpY <= svgHeight) { tpLine.setAttribute("y1", tpY); tpLine.setAttribute("y2", tpY); tpLine.classList.remove("hidden"); }
            if (entryLine && entryY >= 0 && entryY <= svgHeight) { entryLine.setAttribute("y1", entryY); entryLine.setAttribute("y2", entryY); entryLine.classList.remove("hidden"); }
            if (slLine && slY >= 0 && slY <= svgHeight) { slLine.setAttribute("y1", slY); slLine.setAttribute("y2", slY); slLine.classList.remove("hidden"); }
        } else {
            if (tpLine) tpLine.classList.add("hidden");
            if (entryLine) entryLine.classList.add("hidden");
            if (slLine) slLine.classList.add("hidden");
            if (chartOverlay) {
                chartOverlay.innerText = "HOLD/SELL - NO TARGETS PLOTTED";
                chartOverlay.classList.remove("hidden");
            }
        }

        // Ingest previous audit logs
        fetchAuditHistory();
        
    } catch (err) {
        if (consoleBox) {
            consoleBox.innerHTML += `\n[Error] Pipeline crashed: ${err.message}\n`;
        }
        document.getElementById("indicator-allocation").innerText = "ERROR";
        document.getElementById("indicator-entry").innerText = "ERROR";
        document.getElementById("indicator-tp").innerText = "ERROR";
        document.getElementById("indicator-sl").innerText = "ERROR";
        if (signalBadge) {
            signalBadge.innerText = "ERROR";
            signalBadge.className = "font-mono text-sm text-[#F97316] font-black tracking-widest mt-1";
        }
    } finally {
        // Re-enable trigger button
        if (executeBtn) {
            executeBtn.disabled = false;
            executeBtn.style.opacity = "";
        }
        if (btnText) btnText.innerText = "Execute Multi-Agent Desk";
        if (spinner) spinner.classList.add("hidden");
    }
}

// Keyboard typing dynamic real-time price updates
document.getElementById("target-ticker").addEventListener("input", () => {
    fetchRealtimeChart();
});

// Setup 10-second polling updates
setInterval(() => {
    const workspace = document.getElementById("main-workspace");
    if (workspace && !workspace.classList.contains("pointer-events-none")) {
        fetchRealtimeChart();
    }
}, 10000);

// Clear operator session locally on browser exit
window.addEventListener("beforeunload", () => {
    sessionStorage.removeItem("active_operator");
});
