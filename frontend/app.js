// 📌 Dynamic connection endpoint resolution

// Forçamos o uso do 127.0.0.1 para evitar problemas de IPv6/IPv4 no Windows
const CONTROL_WS_URL = `ws://127.0.0.1:8001`;
const CONTROL_API_URL = `http://127.0.0.1:8081`;

let socket = null;
let settingsLoaded = false;
let maxDurationForProgress = 10; 

// UI elements mapping
const serverStatusEl = document.getElementById("server-status");
const controlModeEl = document.getElementById("control-mode");
const activeViaTextEl = document.getElementById("active-via-text");
const timerCountdownEl = document.getElementById("timer-countdown");
const timerProgressEl = document.getElementById("timer-progress");
const settingsForm = document.getElementById("settings-form");

// 📌 Initialize WS Telemetry link
function connectWS() {
    console.log(`[Dashboard] Connecting to Telemetry Stream: ${CONTROL_WS_URL}`);
    socket = new WebSocket(CONTROL_WS_URL);

    socket.onopen = () => {
        console.log("[Dashboard] Telemetry Connection Established.");
        serverStatusEl.innerText = "Online";
        serverStatusEl.className = "val status-connected";
    };

    socket.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        updateUI(payload.state, payload.mode);
        
        if (!settingsLoaded && payload.settings) {
            loadSettingsForm(payload.settings);
            settingsLoaded = true;
        }
    };

    socket.onclose = () => {
        console.log("[Dashboard] Connection lost. Reconnecting in 3 seconds...");
        serverStatusEl.innerText = "Desconectado";
        serverStatusEl.className = "val status-disconnected";
        setTimeout(connectWS, 3000);
    };

    socket.onerror = (error) => {
        console.error("[Dashboard] WebSocket error:", error);
    };
}

// 📌 Populate Configuration settings in form
function loadSettingsForm(settings) {
    Object.keys(settings).forEach(key => {
        const input = settingsForm.elements[key];
        if (input) {
            input.value = settings[key];
        }
    });
}

// 📌 POST trigger events (emergency / pedestrian)
async function triggerScenario(type, viaId) {
    try {
        const response = await fetch(`${CONTROL_API_URL}/${type}?via_id=${viaId}`, {
            method: "POST"
        });
        if (response.ok) {
            console.log(`[Dashboard] Scenario '${type}' triggered for Road ${viaId}`);
        } else {
            console.error(`[Dashboard] Scenario override failure: ${type}`);
        }
    } catch (error) {
        console.error("[Dashboard] Request failure triggering scenario:", error);
    }
}

// 📌 Save Algorithm parameters
async function saveSettings(event) {
    event.preventDefault();
    const formData = new FormData(settingsForm);
    const payload = {};
    formData.forEach((value, key) => {
        payload[key] = Number(value);
    });

    try {
        const response = await fetch(`${CONTROL_API_URL}/settings`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });
        if (response.ok) {
            alert("✅ Configurações salvas com sucesso!");
        } else {
            alert("❌ Falha ao salvar as configurações.");
        }
    } catch (error) {
        console.error("[Dashboard] Request failure saving settings:", error);
        alert("❌ Erro de conexão com o servidor de controle.");
    }
}

// 📌 Dynamically update UI indicators
function updateUI(state, mode) {
    // Mode status indicator
    controlModeEl.innerText = mode === "hardware" ? "Físico (Arduino)" : "Simulação Local";
    controlModeEl.style.color = mode === "hardware" ? "#818cf8" : "#9ca3af";

    // Update both lane grids
    for (let id = 1; id <= 2; id++) {
        const data = state.intersections[String(id)];
        if (!data) continue;
        
        // Render video frame
        const videoEl = document.getElementById(`video-stream-${id}`);
        if (data.frame) {
            videoEl.src = data.frame;
        }

        // Totals and pressures
        const totalVehicles = data.counts.cars + data.counts.motorcycles + data.counts.heavy;
        document.getElementById(`vehicles-total-${id}`).innerText = totalVehicles;
        document.getElementById(`pressure-total-${id}`).innerText = data.pressure_total.toFixed(1);
        
        // Breakdowns
        document.getElementById(`cars-${id}`).innerText = data.counts.cars;
        document.getElementById(`motos-${id}`).innerText = data.counts.motorcycles;
        document.getElementById(`heavy-${id}`).innerText = data.counts.heavy;
        document.getElementById(`starvation-${id}`).innerText = data.starvation;

        // Active State Badge
        const badgeEl = document.getElementById(`badge-${id}`);
        if (state.active_intersection === id) {
            badgeEl.innerText = "ATIVO";
            badgeEl.className = "active-badge active";
            document.getElementById(`card-intersection-${id}`).style.borderColor = "#818cf855";
        } else {
            badgeEl.innerText = "OCIOSO";
            badgeEl.className = "active-badge";
            document.getElementById(`card-intersection-${id}`).style.borderColor = "rgba(255, 255, 255, 0.05)";
        }
    }

    // Update physical lamp active states
    for (let id = 1; id <= 2; id++) {
        const overlay = document.getElementById(`semaphore-${id}`);
        const lamps = overlay.getElementsByClassName("lamp");
        
        for (let l of lamps) {
            l.classList.remove("active");
        }

        if (state.active_intersection === id) {
            if (state.light_state === "VERDE") {
                overlay.querySelector(".green").classList.add("active");
            } else if (state.light_state === "AMARELO") {
                overlay.querySelector(".yellow").classList.add("active");
            } else {
                overlay.querySelector(".red").classList.add("active");
            }
        } else {
            overlay.querySelector(".red").classList.add("active");
        }
    }

    // Active Timer and Progress Bar
    if (state.esperando_ciclo_terminar && state.active_intersection > 0) {
        const activeVia = state.active_intersection === 1 ? "VIA PRINCIPAL (C1)" : "VIA SECUNDÁRIA (C2)";
        activeViaTextEl.innerText = `${activeVia} - ${state.light_state}`;
        activeViaTextEl.style.color = state.light_state === "VERDE" ? "#39ff14" : "#ffea00";
        
        timerCountdownEl.innerText = `${state.tempo_restante}s`;
        
        if (state.tempo_restante > maxDurationForProgress) {
            maxDurationForProgress = state.tempo_restante;
        }
        
        const pct = Math.max(0, Math.min(100, (state.tempo_restante / maxDurationForProgress) * 100));
        timerProgressEl.style.width = `${pct}%`;
        
        if (state.light_state === "VERDE") {
            timerProgressEl.style.background = "linear-gradient(90deg, #818cf8, #34d399)";
        } else {
            timerProgressEl.style.background = "linear-gradient(90deg, #ffea00, #ffaa00)";
        }
    } else {
        activeViaTextEl.innerText = "TODOS VERMELHOS";
        activeViaTextEl.style.color = "#ff073a";
        timerCountdownEl.innerText = "00s";
        timerProgressEl.style.width = "0%";
        maxDurationForProgress = 10; 
    }
}

window.onload = () => {
    connectWS();
};
