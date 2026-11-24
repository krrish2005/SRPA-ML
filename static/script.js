/**
 * script.js - Smart Router Placement Advisor
 * Commercial-Grade Wi-Fi Heatmap & Router Placement Engine
 */

document.addEventListener("DOMContentLoaded", () => {
    // --- Canvas & Core Elements ---
    const canvas = document.getElementById("mainFloorCanvas");
    const ctx = canvas.getContext("2d");
    const canvasViewport = document.getElementById("canvasViewportContainer");
    const saasTooltip = document.getElementById("saasTooltip");
    const saasLoader = document.getElementById("saasLoader");
    const loaderMsg = document.getElementById("loaderMsg");
    const canvasScaleBar = document.getElementById("canvasScaleBar");
    const scaleBarText = document.getElementById("scaleBarText");

    // --- State Definition ---
    let floor = {
        width: 16.0,
        height: 11.0,
        resolution: 0.5
    };

    let router = {
        x: 8.0,
        y: 5.5,
        tx_power: 20.0
    };

    let recommendedRouter = null;
    let frequency = 2.4; // 2.4 GHz (PL0 = 40.0) or 5.0 GHz (PL0 = 47.0)
    let pathLossExponent = 2.8;

    let activeTool = "drag"; // "drag", "wall", "door", "window", "pan"
    let activeBarrierMaterial = "brick";
    let snapToGrid = true;
    let heatmapMode = "gradient"; // "gradient", "tiers", "deadzones"

    let rooms = [];
    let walls = [];
    let doors = [];
    let wallHistory = [];

    let currentHeatmapData = null;
    let isDraggingRouter = false;
    let isDrawingBarrier = false;
    let barrierStart = null;
    let simulationTimer = null;

    // Canvas Pan & Zoom
    let zoomLevel = 1.0;
    let panOffset = { x: 0, y: 0 };
    let isPanning = false;
    let panStart = { x: 0, y: 0 };

    // View Toggles
    let showRooms = true;
    let showWalls = true;
    let showHeatmap = true;

    // --- DOM Elements ---
    // Global Header & Navigation
    const globalNavTabs = document.querySelectorAll("#globalNav .view-tab");
    const appViews = document.querySelectorAll(".app-view");
    const currentPresetName = document.getElementById("currentPresetName");
    const currentPresetDim = document.getElementById("currentPresetDim");
    const backendPingDot = document.getElementById("backendPingDot");
    const backendStatusLabel = document.getElementById("backendStatusLabel");
    const backendLatency = document.getElementById("backendLatency");
    const simDot = document.getElementById("simDot");
    const simStateText = document.getElementById("simStateText");

    const btnHeaderReset = document.getElementById("btnHeaderReset");
    const btnHeaderOptimize = document.getElementById("btnHeaderOptimize");
    const btnHeaderSimulate = document.getElementById("btnHeaderSimulate");

    // Studio Dock Tabs & Panels
    const dockTabs = document.querySelectorAll(".dock-tab");
    const dockPanels = document.querySelectorAll(".dock-panel");

    // Dock 1: Layout & Presets
    const selectPreset = document.getElementById("selectPreset");
    const btnLoadPreset = document.getElementById("btnLoadPreset");
    const floorWidth = document.getElementById("floorWidth");
    const floorHeight = document.getElementById("floorHeight");
    const gridResolution = document.getElementById("gridResolution");
    const btnUpdateDimensions = document.getElementById("btnUpdateDimensions");

    // Dock 2: Room Manager
    const btnToggleAddRoom = document.getElementById("btnToggleAddRoom");
    const addRoomForm = document.getElementById("addRoomForm");
    const newRoomName = document.getElementById("newRoomName");
    const newRoomW = document.getElementById("newRoomW");
    const newRoomH = document.getElementById("newRoomH");
    const newRoomX = document.getElementById("newRoomX");
    const newRoomY = document.getElementById("newRoomY");
    const btnCreateRoom = document.getElementById("btnCreateRoom");
    const roomManagerList = document.getElementById("roomManagerList");

    // Dock 3: Radio & AP
    const sliderTxPower = document.getElementById("sliderTxPower");
    const valTxPower = document.getElementById("valTxPower");
    const btnBand24 = document.getElementById("btnBand24");
    const btnBand50 = document.getElementById("btnBand50");
    const sliderPathLoss = document.getElementById("sliderPathLoss");
    const valPathLoss = document.getElementById("valPathLoss");
    const numRouterX = document.getElementById("numRouterX");
    const numRouterY = document.getElementById("numRouterY");
    const btnRecenterRouter = document.getElementById("btnRecenterRouter");

    // Dock 4: Walls & Barriers
    const toolSelectDrag = document.getElementById("toolSelectDrag");
    const toolSelectWall = document.getElementById("toolSelectWall");
    const toolSelectDoor = document.getElementById("toolSelectDoor");
    const toolSelectWindow = document.getElementById("toolSelectWindow");
    const selectMaterial = document.getElementById("selectMaterial");
    const barrierMaterialWrapper = document.getElementById("barrierMaterialWrapper");
    const btnUndoLastWall = document.getElementById("btnUndoLastWall");
    const btnClearWallsBtn = document.getElementById("btnClearWallsBtn");

    // Workspace Header Toolbar
    const activeModeText = document.getElementById("activeModeText");
    const activeDimPill = document.getElementById("activeDimPill");
    const toggleGridSnap = document.getElementById("toggleGridSnap");
    const toggleRooms = document.getElementById("toggleRooms");
    const toggleWalls = document.getElementById("toggleWalls");
    const toggleHeatmap = document.getElementById("toggleHeatmap");
    const selectHeatmapMode = document.getElementById("selectHeatmapMode");

    const btnZoomOut = document.getElementById("btnZoomOut");
    const btnZoomReset = document.getElementById("btnZoomReset");
    const btnZoomIn = document.getElementById("btnZoomIn");
    const btnFitCanvas = document.getElementById("btnFitCanvas");
    const btnExportImage = document.getElementById("btnExportImage");

    // Studio Bottom KPI Bar
    const barGoodPct = document.getElementById("barGoodPct");
    const barWeakPct = document.getElementById("barWeakPct");
    const barDeadPct = document.getElementById("barDeadPct");
    const barAvgRssi = document.getElementById("barAvgRssi");
    const barGridCells = document.getElementById("barGridCells");
    const btnStudioOptimize = document.getElementById("btnStudioOptimize");

    // Tooltip HUD
    const ttCoords = document.getElementById("ttCoords");
    const ttRssi = document.getElementById("ttRssi");
    const ttQualityBadge = document.getElementById("ttQualityBadge");
    const ttPhySpeed = document.getElementById("ttPhySpeed");
    const ttDistance = document.getElementById("ttDistance");
    const ttBarriers = document.getElementById("ttBarriers");

    // Executive Overview View
    const ovHealthScore = document.getElementById("ovHealthScore");
    const ovHealthTag = document.getElementById("ovHealthTag");
    const ovHealthFill = document.getElementById("ovHealthFill");
    const ovHealthSub = document.getElementById("ovHealthSub");
    const ovGoodPct = document.getElementById("ovGoodPct");
    const ovGoodFill = document.getElementById("ovGoodFill");
    const ovDeadPct = document.getElementById("ovDeadPct");
    const ovDeadFill = document.getElementById("ovDeadFill");
    const ovAvgRssi = document.getElementById("ovAvgRssi");
    const ovMaxRssi = document.getElementById("ovMaxRssi");
    const ovMinRssi = document.getElementById("ovMinRssi");
    const ovQualityLabel = document.getElementById("ovQualityLabel");
    const overviewRoomsTbody = document.getElementById("overviewRoomsTbody");
    const ovRoomCountTag = document.getElementById("ovRoomCountTag");
    const btnAuditBackToStudio = document.getElementById("btnAuditBackToStudio");
    const btnAuditRunOptimizer = document.getElementById("btnAuditRunOptimizer");

    // Signal Analytics View
    const analyticsHistogram = document.getElementById("analyticsHistogram");
    const ttsGood = document.getElementById("ttsGood");
    const ttsWeak = document.getElementById("ttsWeak");
    const ttsDead = document.getElementById("ttsDead");
    const statGrossArea = document.getElementById("statGrossArea");
    const statResolution = document.getElementById("statResolution");
    const statTotalCells = document.getElementById("statTotalCells");
    const statMaxSignal = document.getElementById("statMaxSignal");
    const statMinSignal = document.getElementById("statMinSignal");
    const statDynRange = document.getElementById("statDynRange");
    const statTxEirp = document.getElementById("statTxEirp");
    const statPl0 = document.getElementById("statPl0");
    const statExponent = document.getElementById("statExponent");
    const btnAnalyticsBackToStudio = document.getElementById("btnAnalyticsBackToStudio");

    // Placement Advisor View
    const btnRunOptimizerMain = document.getElementById("btnRunOptimizerMain");
    const optBannerTitle = document.getElementById("optBannerTitle");
    const optBannerDesc = document.getElementById("optBannerDesc");
    const btnApplyOptimizedPos = document.getElementById("btnApplyOptimizedPos");
    const optComparisonGrid = document.getElementById("optComparisonGrid");
    const compCurrentPos = document.getElementById("compCurrentPos");
    const compCurGood = document.getElementById("compCurGood");
    const compCurDead = document.getElementById("compCurDead");
    const compCurAvg = document.getElementById("compCurAvg");
    const compRecPos = document.getElementById("compRecPos");
    const compRecGood = document.getElementById("compRecGood");
    const compRecDead = document.getElementById("compRecDead");
    const compRecAvg = document.getElementById("compRecAvg");
    const gainGoodVal = document.getElementById("gainGoodVal");
    const gainDeadVal = document.getElementById("gainDeadVal");
    const gainRssiVal = document.getElementById("gainRssiVal");

    // Projects & Persistence View
    const saveProjectName = document.getElementById("saveProjectName");
    const btnSaveCurrentProject = document.getElementById("btnSaveCurrentProject");
    const savedProjectsList = document.getElementById("savedProjectsList");
    const btnExportPngAlt = document.getElementById("btnExportPngAlt");
    const btnExportJson = document.getElementById("btnExportJson");
    const fileDropZone = document.getElementById("fileDropZone");
    const importJsonInput = document.getElementById("importJsonInput");


    // =========================================================================
    // 1. CANVAS COORDINATES & SCALING
    // =========================================================================

    function resizeCanvasToContainer() {
        const rect = canvasViewport.getBoundingClientRect();
        if (rect.width > 50 && rect.height > 50) {
            const dpr = window.devicePixelRatio || 1;
            canvas.width = Math.floor(rect.width * dpr);
            canvas.height = Math.floor(rect.height * dpr);
            canvas.style.width = `${rect.width}px`;
            canvas.style.height = `${rect.height}px`;
        }
        renderCanvas();
    }

    function getBaseScale() {
        // Fits floor dimension into canvas while keeping aspect ratio and 40px margin
        const margin = 40 * (window.devicePixelRatio || 1);
        const availW = Math.max(100, canvas.width - margin * 2);
        const availH = Math.max(100, canvas.height - margin * 2);
        const scaleX = availW / floor.width;
        const scaleY = availH / floor.height;
        return Math.min(scaleX, scaleY) * zoomLevel;
    }

    function getOrigin() {
        const s = getBaseScale();
        const dpr = window.devicePixelRatio || 1;
        const floorCanvasW = floor.width * s;
        const floorCanvasH = floor.height * s;
        const ox = (canvas.width - floorCanvasW) / 2 + panOffset.x * dpr;
        const oy = (canvas.height - floorCanvasH) / 2 + panOffset.y * dpr;
        return { ox, oy, scale: s };
    }

    function toCanvasX(xm) {
        const { ox, scale } = getOrigin();
        return ox + xm * scale;
    }

    function toCanvasY(ym) {
        const { oy, scale } = getOrigin();
        return oy + ym * scale;
    }

    function toMeterX(pixelX) {
        const { ox, scale } = getOrigin();
        const xm = (pixelX - ox) / scale;
        return Math.max(0, Math.min(floor.width, xm));
    }

    function toMeterY(pixelY) {
        const { oy, scale } = getOrigin();
        const ym = (pixelY - oy) / scale;
        return Math.max(0, Math.min(floor.height, ym));
    }

    function applyGridSnap(val, step = 0.5) {
        if (!snapToGrid) return val;
        return Math.round(val / step) * step;
    }


    // =========================================================================
    // 2. SIGNAL COLOR MAPPING & WIRELESS METRICS
    // =========================================================================

    function getRssiColor(rssi) {
        if (heatmapMode === "tiers") {
            if (rssi >= -67.0) return [16, 185, 129, 180];  // Good Coverage
            if (rssi >= -85.0) return [245, 158, 11, 180];  // Weak Coverage
            return [239, 68, 68, 180];                      // Dead Zone
        }

        if (heatmapMode === "deadzones") {
            if (rssi < -85.0) return [239, 68, 68, 210];   // Spotlight Dead Zones
            return [15, 23, 42, 40];                         // Dim background
        }

        // Default Continuous Gradient
        if (rssi >= -50.0) return [0, 240, 255, 195];   // Excellent (Cyan)
        if (rssi >= -60.0) return [16, 185, 129, 185];  // Good (Emerald)
        if (rssi >= -67.0) return [132, 204, 22, 180];  // Fair (Lime)
        if (rssi >= -75.0) return [245, 158, 11, 175];  // Weak (Amber)
        if (rssi >= -85.0) return [249, 115, 22, 170];  // Very Weak (Orange)
        return [239, 68, 68, 165];                      // Dead Zone (Crimson)
    }

    function getQualityDescription(rssi) {
        if (rssi >= -50.0) return { label: "Excellent", color: "var(--sig-exc)", speed: "866+ Mbps" };
        if (rssi >= -60.0) return { label: "Good", color: "var(--sig-good)", speed: "433 - 866 Mbps" };
        if (rssi >= -67.0) return { label: "Fair", color: "var(--sig-fair)", speed: "150 - 433 Mbps" };
        if (rssi >= -75.0) return { label: "Weak", color: "var(--sig-weak)", speed: "54 - 150 Mbps" };
        if (rssi >= -85.0) return { label: "Very Weak", color: "var(--sig-vweak)", speed: "6 - 54 Mbps" };
        return { label: "Dead Zone", color: "var(--sig-dead)", speed: "0 Mbps (Dropped)" };
    }

    // Line intersection helper to count walls in line of sight
    function linesIntersect(x1, y1, x2, y2, x3, y3, x4, y4) {
        const denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1);
        if (Math.abs(denom) < 1e-9) return false;
        const ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom;
        const ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom;
        return (ua >= 0 && ua <= 1 && ub >= 0 && ub <= 1);
    }

    function countObstructionsInRay(targetX, targetY) {
        let count = 0;
        const allSegments = walls.concat(doors);
        for (const w of allSegments) {
            if (linesIntersect(router.x, router.y, targetX, targetY, w.x1, w.y1, w.x2, w.y2)) {
                count++;
            }
        }
        return count;
    }


    // =========================================================================
    // 3. TOAST NOTIFICATIONS & HEALTH CHECK
    // =========================================================================

    function showToast(message, type = "info") {
        const stack = document.getElementById("toastStack");
        const toast = document.createElement("div");
        toast.className = `toast-msg ${type}`;
        
        const icons = { success: "✓", error: "✕", info: "ℹ" };
        toast.innerHTML = `<span style="font-weight:700;">${icons[type] || "•"}</span> <span>${message}</span>`;
        
        stack.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(8px)";
            toast.style.transition = "all 0.25s ease";
            setTimeout(() => toast.remove(), 250);
        }, 3200);
    }

    async function checkBackendHealth() {
        const start = performance.now();
        try {
            const res = await fetch("/api/health");
            const duration = Math.round(performance.now() - start);
            if (res.ok) {
                const data = await res.json();
                backendPingDot.className = "status-ping online";
                backendStatusLabel.textContent = `Online (${data.version || "v1.0"})`;
                backendLatency.textContent = `${duration} ms`;
            } else {
                throw new Error();
            }
        } catch {
            backendPingDot.className = "status-ping error";
            backendStatusLabel.textContent = "Offline";
            backendLatency.textContent = "Err";
        }
    }


    // =========================================================================
    // 4. SIMULATION PIPELINE (DEBOUNCED)
    // =========================================================================

    function debouncedSimulation(delay = 100) {
        setSimStatus("calculating");
        if (simulationTimer) clearTimeout(simulationTimer);
        simulationTimer = setTimeout(() => {
            triggerSimulation();
        }, delay);
    }

    function setSimStatus(state) {
        if (state === "calculating") {
            simDot.className = "sim-dot";
            simStateText.textContent = "Calculating...";
        } else {
            simDot.className = "sim-dot active";
            simStateText.textContent = "Up to date";
        }
    }

    async function triggerSimulation() {
        setSimStatus("calculating");
        try {
            const referenceLoss = (frequency === 5.0) ? 47.0 : 40.0;
            const payload = {
                width: floor.width,
                height: floor.height,
                resolution: parseFloat(gridResolution.value) || 0.5,
                router: router,
                walls: walls.concat(doors),
                path_loss_exponent: pathLossExponent,
                reference_loss: referenceLoss
            };

            const res = await fetch("/api/simulate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const errData = await res.json();
                showToast("Simulation error: " + (errData.error || "Unknown"), "error");
                return;
            }

            const data = await res.json();
            currentHeatmapData = data;

            updateAllAnalyticsDisplays(data.metrics);
            updateRoomByRoomAudit();
            renderCanvas();
        } catch (err) {
            console.error("Simulation failure:", err);
            showToast("Network error during simulation", "error");
        } finally {
            setSimStatus("ready");
        }
    }


    // =========================================================================
    // 5. UPDATE ANALYTICS & ROOM-BY-ROOM AUDIT
    // =========================================================================

    function updateAllAnalyticsDisplays(metrics) {
        if (!metrics) return;

        // 1. Studio Bottom KPI Bar
        barGoodPct.textContent = `${metrics.good_coverage_percent}%`;
        barWeakPct.textContent = `${metrics.weak_coverage_percent}%`;
        barDeadPct.textContent = `${metrics.dead_zone_percent}%`;
        barAvgRssi.textContent = `${metrics.average_rssi_dbm} dBm`;
        barGridCells.textContent = `${metrics.total_cells_evaluated || "--"} cells`;

        // 2. Executive Overview Hero Cards
        ovGoodPct.textContent = `${metrics.good_coverage_percent}%`;
        ovGoodFill.style.width = `${metrics.good_coverage_percent}%`;

        ovDeadPct.textContent = `${metrics.dead_zone_percent}%`;
        ovDeadFill.style.width = `${metrics.dead_zone_percent}%`;

        ovAvgRssi.textContent = `${metrics.average_rssi_dbm} dBm`;
        ovMaxRssi.textContent = `${metrics.max_rssi_dbm} dBm`;
        ovMinRssi.textContent = `${metrics.min_rssi_dbm} dBm`;

        const q = getQualityDescription(metrics.average_rssi_dbm);
        ovQualityLabel.textContent = `${q.label} average floor connectivity`;
        ovQualityLabel.style.color = q.color;

        // Health Score (0 - 100)
        let health = Math.round(metrics.good_coverage_percent * 0.85 - metrics.dead_zone_percent * 1.5 + 15);
        health = Math.max(10, Math.min(100, health));
        ovHealthScore.textContent = `${health}/100`;
        ovHealthFill.style.width = `${health}%`;

        if (health >= 80) {
            ovHealthTag.textContent = "Optimal";
            ovHealthTag.className = "status-tag tag-success";
            ovHealthSub.textContent = "High-speed wireless propagation with minimal dead zones.";
        } else if (health >= 60) {
            ovHealthTag.textContent = "Moderate";
            ovHealthTag.className = "status-tag";
            ovHealthSub.textContent = "Acceptable coverage, but peripheral rooms may suffer packet loss.";
        } else {
            ovHealthTag.textContent = "Sub-optimal";
            ovHealthTag.className = "status-tag tag-danger";
            ovHealthSub.textContent = "Critical dead zones detected. Optimization or access point move advised.";
        }

        // 3. Signal Analytics Tab
        ttsGood.textContent = `${metrics.good_coverage_percent}%`;
        ttsWeak.textContent = `${metrics.weak_coverage_percent}%`;
        ttsDead.textContent = `${metrics.dead_zone_percent}%`;

        statGrossArea.textContent = `${(floor.width * floor.height).toFixed(1)} m²`;
        statResolution.textContent = `${gridResolution.value} m`;
        statTotalCells.textContent = `${metrics.total_cells_evaluated} points`;
        statMaxSignal.textContent = `${metrics.max_rssi_dbm} dBm`;
        statMinSignal.textContent = `${metrics.min_rssi_dbm} dBm`;
        statDynRange.textContent = `${(metrics.max_rssi_dbm - metrics.min_rssi_dbm).toFixed(1)} dB`;
        statTxEirp.textContent = `${router.tx_power} dBm EIRP (${Math.round(Math.pow(10, router.tx_power / 10))} mW)`;
        statPl0.textContent = `${frequency.toFixed(1)} GHz (${frequency === 5.0 ? "47.0" : "40.0"} dB)`;
        statExponent.textContent = pathLossExponent.toFixed(1);

        renderHistogram(metrics.breakdown);
    }

    function renderHistogram(breakdown) {
        if (!breakdown || !analyticsHistogram) return;
        analyticsHistogram.innerHTML = "";

        const tiers = [
            { key: "excellent", label: "Excellent (≥ -50)", color: "var(--sig-exc)", val: breakdown.excellent },
            { key: "good", label: "Good (-60 to -50)", color: "var(--sig-good)", val: breakdown.good },
            { key: "fair", label: "Fair (-67 to -60)", color: "var(--sig-fair)", val: breakdown.fair },
            { key: "weak", label: "Weak (-75 to -67)", color: "var(--sig-weak)", val: breakdown.weak },
            { key: "very_weak", label: "Very Weak (-85 to -75)", color: "var(--sig-vweak)", val: breakdown.very_weak },
            { key: "dead_zone", label: "Dead Zone (< -85)", color: "var(--sig-dead)", val: breakdown.dead_zone }
        ];

        tiers.forEach(t => {
            const row = document.createElement("div");
            row.className = "hist-bar-row";
            row.innerHTML = `
                <span class="hist-lbl">${t.label}</span>
                <div class="hist-track">
                    <div class="hist-fill" style="width: ${t.val}%; background-color: ${t.color};"></div>
                </div>
                <span class="hist-pct">${t.val}%</span>
            `;
            analyticsHistogram.appendChild(row);
        });
    }

    function updateRoomByRoomAudit() {
        if (!overviewRoomsTbody) return;
        overviewRoomsTbody.innerHTML = "";

        if (rooms.length === 0) {
            overviewRoomsTbody.innerHTML = `<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:1.5rem;">No rooms configured. Load a preset or create custom rooms in the Studio.</td></tr>`;
            if (ovRoomCountTag) ovRoomCountTag.textContent = "0 Rooms";
            return;
        }

        if (ovRoomCountTag) ovRoomCountTag.textContent = `${rooms.length} Defined Rooms`;

        if (!currentHeatmapData || !currentHeatmapData.heatmap) return;

        const { xs, ys, heatmap } = currentHeatmapData;

        rooms.forEach((r, idx) => {
            // Find all cells inside room bounding box
            let cellValues = [];
            for (let i = 0; i < ys.length; i++) {
                const cy = ys[i];
                if (cy >= r.y && cy <= r.y + r.height) {
                    for (let j = 0; j < xs.length; j++) {
                        const cx = xs[j];
                        if (cx >= r.x && cx <= r.x + r.width) {
                            cellValues.push(heatmap[i][j]);
                        }
                    }
                }
            }

            let avgRssi = -100;
            let goodPct = 0;
            let deadPct = 100;

            if (cellValues.length > 0) {
                const sum = cellValues.reduce((a, b) => a + b, 0);
                avgRssi = Math.round((sum / cellValues.length) * 10) / 10;
                const goodCount = cellValues.filter(v => v >= -67.0).length;
                const deadCount = cellValues.filter(v => v < -85.0).length;
                goodPct = Math.round((goodCount / cellValues.length) * 1000) / 10;
                deadPct = Math.round((deadCount / cellValues.length) * 1000) / 10;
            }

            // Grade assignment
            let grade = "C";
            let advice = "Acceptable signal; fine for general browsing.";
            if (avgRssi >= -55.0) {
                grade = "A+";
                advice = "Ultra-fast line of sight. Gigabit ready.";
            } else if (avgRssi >= -62.0) {
                grade = "A";
                advice = "Strong wireless link. Excellent for 4K streaming.";
            } else if (avgRssi >= -68.0) {
                grade = "B";
                advice = "Good connection; standard VoIP & HD calls.";
            } else if (avgRssi >= -76.0) {
                grade = "C";
                advice = "Moderate wall attenuation; casual browsing.";
            } else if (avgRssi >= -84.0) {
                grade = "D";
                advice = "High latency; packet dropouts likely.";
            } else {
                grade = "F";
                advice = "Dead Zone! Reposition router or add mesh repeater.";
            }

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${r.name}</strong></td>
                <td class="mono">${r.width}m × ${r.height}m</td>
                <td class="mono">${(r.width * r.height).toFixed(1)} m²</td>
                <td class="mono"><strong>${avgRssi} dBm</strong></td>
                <td class="text-good mono">${goodPct}%</td>
                <td class="text-dead mono">${deadPct}%</td>
                <td><span class="grade-badge grade-${grade[0]}">${grade}</span></td>
                <td style="font-size:0.73rem;color:var(--text-secondary);">${advice}</td>
            `;
            overviewRoomsTbody.appendChild(tr);
        });
    }


    // =========================================================================
    // 6. CANVAS RENDERING ENGINE
    // =========================================================================

    function renderCanvas() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const dpr = window.devicePixelRatio || 1;
        const { ox, oy, scale } = getOrigin();
        const floorCanvasW = floor.width * scale;
        const floorCanvasH = floor.height * scale;

        // 1. Dark Technical Blueprint Background
        ctx.fillStyle = "#030611";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Floor Boundary Canvas Area
        ctx.fillStyle = "#060a17";
        ctx.fillRect(ox, oy, floorCanvasW, floorCanvasH);

        // Subtle Blueprint Grid Lines (1.0m intervals)
        ctx.lineWidth = 0.5 * dpr;
        ctx.strokeStyle = "rgba(43, 61, 99, 0.28)";

        for (let x = 0; x <= floor.width; x += 1.0) {
            const cx = toCanvasX(x);
            ctx.beginPath();
            ctx.moveTo(cx, oy);
            ctx.lineTo(cx, oy + floorCanvasH);
            ctx.stroke();
        }
        for (let y = 0; y <= floor.height; y += 1.0) {
            const cy = toCanvasY(y);
            ctx.beginPath();
            ctx.moveTo(ox, cy);
            ctx.lineTo(ox + floorCanvasW, cy);
            ctx.stroke();
        }

        // 2. Heatmap Layer
        if (showHeatmap && currentHeatmapData && currentHeatmapData.heatmap) {
            const { xs, ys, heatmap } = currentHeatmapData;
            const cellW = floorCanvasW / xs.length;
            const cellH = floorCanvasH / ys.length;

            for (let i = 0; i < ys.length; i++) {
                for (let j = 0; j < xs.length; j++) {
                    const rssi = heatmap[i][j];
                    const [r, g, b, a] = getRssiColor(rssi);
                    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${a / 255})`;
                    ctx.fillRect(ox + j * cellW, oy + i * cellH, cellW + 1, cellH + 1);
                }
            }
        }

        // 3. Outer Floor Perimeter Border
        ctx.lineWidth = 2 * dpr;
        ctx.strokeStyle = "#38bdf8";
        ctx.strokeRect(ox, oy, floorCanvasW, floorCanvasH);

        // 4. Rooms Layer
        if (showRooms && rooms.length > 0) {
            rooms.forEach(r => {
                const rx = toCanvasX(r.x);
                const ry = toCanvasY(r.y);
                const rw = r.width * scale;
                const rh = r.height * scale;

                // Subtle room frosted background
                ctx.fillStyle = "rgba(11, 18, 33, 0.4)";
                ctx.fillRect(rx, ry, rw, rh);

                // Dashed room partition border
                ctx.lineWidth = 1 * dpr;
                ctx.setLineDash([4 * dpr, 4 * dpr]);
                ctx.strokeStyle = "rgba(148, 163, 184, 0.45)";
                ctx.strokeRect(rx, ry, rw, rh);
                ctx.setLineDash([]);

                // Room Label Backdrop Pill
                const labelText = r.name;
                const dimText = `${r.width}m × ${r.height}m`;
                const cx = rx + rw / 2;
                const cy = ry + rh / 2;

                ctx.font = `600 ${11 * dpr}px 'Plus Jakarta Sans', sans-serif`;
                const textW = Math.max(ctx.measureText(labelText).width, 70 * dpr);

                ctx.fillStyle = "rgba(5, 9, 20, 0.85)";
                ctx.fillRect(cx - textW / 2 - 8 * dpr, cy - 16 * dpr, textW + 16 * dpr, 32 * dpr);
                ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
                ctx.lineWidth = 0.5 * dpr;
                ctx.strokeRect(cx - textW / 2 - 8 * dpr, cy - 16 * dpr, textW + 16 * dpr, 32 * dpr);

                // Label & Dimension Text
                ctx.fillStyle = "#ffffff";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText(labelText, cx, cy - 5 * dpr);

                ctx.fillStyle = "rgba(148, 163, 184, 0.85)";
                ctx.font = `500 ${9 * dpr}px 'JetBrains Mono', monospace`;
                ctx.fillText(dimText, cx, cy + 8 * dpr);
            });
        }

        // 5. Walls & Doors Layer
        if (showWalls) {
            walls.forEach(w => {
                const x1 = toCanvasX(w.x1);
                const y1 = toCanvasY(w.y1);
                const x2 = toCanvasX(w.x2);
                const y2 = toCanvasY(w.y2);

                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.lineCap = "round";

                if (w.material === "concrete") {
                    ctx.lineWidth = 7 * dpr;
                    ctx.strokeStyle = "#94a3b8"; // Slate Gray Concrete
                } else if (w.material === "brick") {
                    ctx.lineWidth = 5.5 * dpr;
                    ctx.strokeStyle = "#fb923c"; // Orange Brick
                } else if (w.material === "metal") {
                    ctx.lineWidth = 7 * dpr;
                    ctx.strokeStyle = "#ef4444"; // Metal Red
                } else if (w.material === "wood") {
                    ctx.lineWidth = 4.5 * dpr;
                    ctx.strokeStyle = "#d97706"; // Amber Wood
                } else if (w.material === "glass") {
                    ctx.lineWidth = 3.5 * dpr;
                    ctx.strokeStyle = "rgba(0, 240, 255, 0.9)"; // Cyan Glass
                } else {
                    ctx.lineWidth = 4 * dpr;
                    ctx.strokeStyle = "#e2e8f0"; // Drywall
                }
                ctx.stroke();
            });

            // Doors
            doors.forEach(d => {
                const x1 = toCanvasX(d.x1);
                const y1 = toCanvasY(d.y1);
                const x2 = toCanvasX(d.x2);
                const y2 = toCanvasY(d.y2);

                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.lineWidth = 3.5 * dpr;
                ctx.setLineDash([4 * dpr, 3 * dpr]);
                ctx.strokeStyle = (d.material === "door_open") ? "rgba(16, 185, 129, 0.95)" : "#a16207";
                ctx.stroke();
                ctx.setLineDash([]);
            });
        }

        // 6. In-Progress Drawing Line
        if (isDrawingBarrier && barrierStart) {
            const bx = toCanvasX(barrierStart.x);
            const by = toCanvasY(barrierStart.y);
            const cx = toCanvasX(barrierStart.currentX);
            const cy = toCanvasY(barrierStart.currentY);

            ctx.beginPath();
            ctx.moveTo(bx, by);
            ctx.lineTo(cx, cy);
            ctx.lineWidth = 4 * dpr;
            ctx.setLineDash([6 * dpr, 6 * dpr]);
            ctx.strokeStyle = "#00f0ff";
            ctx.stroke();
            ctx.setLineDash([]);

            // Distance badge on drawing line
            const len = Math.hypot(barrierStart.currentX - barrierStart.x, barrierStart.currentY - barrierStart.y);
            const midX = (bx + cx) / 2;
            const midY = (by + cy) / 2 - 14 * dpr;

            ctx.fillStyle = "rgba(10, 15, 29, 0.95)";
            ctx.fillRect(midX - 28 * dpr, midY - 10 * dpr, 56 * dpr, 20 * dpr);
            ctx.strokeStyle = "#00f0ff";
            ctx.lineWidth = 1 * dpr;
            ctx.strokeRect(midX - 28 * dpr, midY - 10 * dpr, 56 * dpr, 20 * dpr);

            ctx.fillStyle = "#00f0ff";
            ctx.font = `700 ${10 * dpr}px 'JetBrains Mono', monospace`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(`${len.toFixed(1)}m`, midX, midY);
        }

        // 7. Recommended Router Ghost Target
        if (recommendedRouter) {
            const ox = toCanvasX(recommendedRouter.x);
            const oy = toCanvasY(recommendedRouter.y);

            // Pulsing Target Reticle
            ctx.beginPath();
            ctx.arc(ox, oy, 26 * dpr, 0, Math.PI * 2);
            ctx.strokeStyle = "rgba(16, 185, 129, 0.7)";
            ctx.lineWidth = 2 * dpr;
            ctx.setLineDash([4 * dpr, 4 * dpr]);
            ctx.stroke();
            ctx.setLineDash([]);

            // Crosshairs
            ctx.beginPath();
            ctx.moveTo(ox - 32 * dpr, oy); ctx.lineTo(ox + 32 * dpr, oy);
            ctx.moveTo(ox, oy - 32 * dpr); ctx.lineTo(ox, oy + 32 * dpr);
            ctx.strokeStyle = "rgba(16, 185, 129, 0.5)";
            ctx.lineWidth = 1 * dpr;
            ctx.stroke();

            // Bullseye
            ctx.beginPath();
            ctx.arc(ox, oy, 6 * dpr, 0, Math.PI * 2);
            ctx.fillStyle = "#10b981";
            ctx.fill();

            // Target Tag
            ctx.fillStyle = "#34d399";
            ctx.font = `700 ${10.5 * dpr}px 'Plus Jakarta Sans', sans-serif`;
            ctx.textAlign = "center";
            ctx.fillText("Recommended AP", ox, oy - 15 * dpr);
        }

        // 8. Active Router (Access Point) Icon
        const rx = toCanvasX(router.x);
        const ry = toCanvasY(router.y);

        // Concentric Pulsing Radio Wave Rings
        ctx.beginPath();
        ctx.arc(rx, ry, 28 * dpr, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(0, 240, 255, 0.22)";
        ctx.lineWidth = 2 * dpr;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(rx, ry, 20 * dpr, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(0, 240, 255, 0.55)";
        ctx.lineWidth = 2 * dpr;
        ctx.stroke();

        // AP Base Circle
        ctx.beginPath();
        ctx.arc(rx, ry, 13 * dpr, 0, Math.PI * 2);
        ctx.fillStyle = "#0284c7";
        ctx.fill();
        ctx.lineWidth = 2.5 * dpr;
        ctx.strokeStyle = "#ffffff";
        ctx.stroke();

        // AP Center Text
        ctx.fillStyle = "#ffffff";
        ctx.font = `800 ${10 * dpr}px 'Plus Jakarta Sans', sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("AP", rx, ry);

        // Live Coordinate Tag below icon
        ctx.fillStyle = "rgba(248, 250, 252, 0.95)";
        ctx.font = `600 ${9.5 * dpr}px 'JetBrains Mono', monospace`;
        ctx.fillText(`(${router.x.toFixed(1)}m, ${router.y.toFixed(1)}m)`, rx, ry + 20 * dpr);

        // Update Scale Bar Display
        if (scaleBarText) {
            const scaleBarPixelW = 2.0 * scale / dpr;
            const barLine = document.querySelector(".scale-bar-line");
            if (barLine) barLine.style.width = `${Math.round(scaleBarPixelW)}px`;
            scaleBarText.textContent = "2.0 meters";
        }
    }


    // =========================================================================
    // 7. MOUSE & CANVAS INTERACTION PIPELINE
    // =========================================================================

    function getCanvasEventCoords(e) {
        const rect = canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        const pixelX = (e.clientX - rect.left) * dpr;
        const pixelY = (e.clientY - rect.top) * dpr;
        const meterX = toMeterX(pixelX);
        const meterY = toMeterY(pixelY);
        return { pixelX, pixelY, meterX, meterY, clientX: e.clientX, clientY: e.clientY };
    }

    canvas.addEventListener("mousedown", (e) => {
        const coords = getCanvasEventCoords(e);
        const distToRouter = Math.hypot(coords.meterX - router.x, coords.meterY - router.y);

        // Spacebar or Middle Click or Pan Tool = Pan
        if (e.button === 1 || e.spaceKey || activeTool === "pan") {
            isPanning = true;
            panStart = { x: e.clientX - panOffset.x, y: e.clientY - panOffset.y };
            return;
        }

        if (activeTool === "drag" || distToRouter <= 1.2) {
            isDraggingRouter = true;
            const sx = applyGridSnap(coords.meterX);
            const sy = applyGridSnap(coords.meterY);
            router.x = Math.max(0.5, Math.min(floor.width - 0.5, sx));
            router.y = Math.max(0.5, Math.min(floor.height - 0.5, sy));
            numRouterX.value = router.x.toFixed(2);
            numRouterY.value = router.y.toFixed(2);
            renderCanvas();
        } else {
            isDrawingBarrier = true;
            const sx = applyGridSnap(coords.meterX);
            const sy = applyGridSnap(coords.meterY);
            barrierStart = { x: sx, y: sy, currentX: sx, currentY: sy };
        }
    });

    canvas.addEventListener("mousemove", (e) => {
        const coords = getCanvasEventCoords(e);

        if (isPanning) {
            panOffset.x = e.clientX - panStart.x;
            panOffset.y = e.clientY - panStart.y;
            renderCanvas();
            return;
        }

        // Tooltip HUD update
        updateCanvasTooltip(coords.clientX, coords.clientY, coords.meterX, coords.meterY);

        if (isDraggingRouter) {
            const sx = applyGridSnap(coords.meterX);
            const sy = applyGridSnap(coords.meterY);
            router.x = Math.max(0.5, Math.min(floor.width - 0.5, sx));
            router.y = Math.max(0.5, Math.min(floor.height - 0.5, sy));
            numRouterX.value = router.x.toFixed(2);
            numRouterY.value = router.y.toFixed(2);
            renderCanvas();
            debouncedSimulation(70);
        } else if (isDrawingBarrier && barrierStart) {
            barrierStart.currentX = applyGridSnap(coords.meterX);
            barrierStart.currentY = applyGridSnap(coords.meterY);
            renderCanvas();
        }
    });

    window.addEventListener("mouseup", (e) => {
        if (isPanning) {
            isPanning = false;
        }
        if (isDraggingRouter) {
            isDraggingRouter = false;
            triggerSimulation();
        } else if (isDrawingBarrier && barrierStart) {
            const rect = canvas.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            const pixelX = (e.clientX - rect.left) * dpr;
            const pixelY = (e.clientY - rect.top) * dpr;
            const meterX = applyGridSnap(toMeterX(pixelX));
            const meterY = applyGridSnap(toMeterY(pixelY));

            const len = Math.hypot(meterX - barrierStart.x, meterY - barrierStart.y);
            if (len >= 0.5) {
                const newElem = {
                    x1: parseFloat(barrierStart.x.toFixed(2)),
                    y1: parseFloat(barrierStart.y.toFixed(2)),
                    x2: parseFloat(meterX.toFixed(2)),
                    y2: parseFloat(meterY.toFixed(2)),
                    material: (activeTool === "door") ? "door_wood" : ((activeTool === "window") ? "glass" : activeBarrierMaterial)
                };

                if (activeTool === "door") {
                    doors.push(newElem);
                    wallHistory.push({ type: "door", data: newElem });
                    showToast(`Added door (${len.toFixed(1)}m)`, "info");
                } else {
                    walls.push(newElem);
                    wallHistory.push({ type: "wall", data: newElem });
                    showToast(`Added ${newElem.material} wall (${len.toFixed(1)}m)`, "info");
                }
                triggerSimulation();
            }
            isDrawingBarrier = false;
            barrierStart = null;
            renderCanvas();
        }
    });

    canvas.addEventListener("mouseleave", () => {
        saasTooltip.style.display = "none";
    });

    // Mouse Wheel Zooming
    canvas.addEventListener("wheel", (e) => {
        e.preventDefault();
        const delta = e.deltaY < 0 ? 1.1 : 0.9;
        const newZoom = Math.max(0.5, Math.min(3.0, zoomLevel * delta));
        if (newZoom !== zoomLevel) {
            zoomLevel = newZoom;
            btnZoomReset.textContent = `${Math.round(zoomLevel * 100)}%`;
            renderCanvas();
        }
    }, { passive: false });

    function updateCanvasTooltip(clientX, clientY, mx, my) {
        if (!currentHeatmapData || !currentHeatmapData.heatmap) {
            saasTooltip.style.display = "none";
            return;
        }

        const { xs, ys, heatmap } = currentHeatmapData;
        const col = Math.min(xs.length - 1, Math.max(0, Math.floor((mx / floor.width) * xs.length)));
        const row = Math.min(ys.length - 1, Math.max(0, Math.floor((my / floor.height) * ys.length)));
        const val = heatmap[row][col];

        ttCoords.textContent = `📍 X: ${mx.toFixed(1)}m, Y: ${my.toFixed(1)}m`;
        ttRssi.textContent = `${val.toFixed(1)} dBm`;

        const q = getQualityDescription(val);
        ttQualityBadge.textContent = q.label;
        ttQualityBadge.style.color = q.color;
        ttPhySpeed.textContent = `Est. PHY: ${q.speed}`;

        const dist = Math.hypot(mx - router.x, my - router.y);
        ttDistance.textContent = `Dist: ${dist.toFixed(1)}m`;

        const barrierCount = countObstructionsInRay(mx, my);
        ttBarriers.textContent = `Barriers: ${barrierCount}`;

        saasTooltip.style.display = "flex";
        
        // Tooltip position clamped to viewport
        const tooltipW = 200;
        const tooltipH = 100;
        let left = clientX + 16;
        let top = clientY + 16;

        if (left + tooltipW > window.innerWidth) left = clientX - tooltipW - 16;
        if (top + tooltipH > window.innerHeight) top = clientY - tooltipH - 16;

        saasTooltip.style.left = `${left}px`;
        saasTooltip.style.top = `${top}px`;
    }


    // =========================================================================
    // 8. GLOBAL VIEW & DOCK TAB SWITCHING
    // =========================================================================

    function switchView(viewId) {
        globalNavTabs.forEach(tab => {
            if (tab.getAttribute("data-view") === viewId) tab.classList.add("active");
            else tab.classList.remove("active");
        });

        appViews.forEach(v => {
            if (v.id === viewId) v.classList.add("active");
            else v.classList.remove("active");
        });

        if (viewId === "view-studio") {
            setTimeout(resizeCanvasToContainer, 50);
        } else if (viewId === "view-overview") {
            updateRoomByRoomAudit();
        } else if (viewId === "view-projects") {
            renderSavedProjectsList();
        }
    }

    globalNavTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            const viewId = tab.getAttribute("data-view");
            switchView(viewId);
        });
    });

    dockTabs.forEach(dt => {
        dt.addEventListener("click", () => {
            dockTabs.forEach(t => t.classList.remove("active"));
            dockPanels.forEach(p => p.classList.remove("active"));

            dt.classList.add("active");
            const panelId = dt.getAttribute("data-dock");
            const panel = document.getElementById(panelId);
            if (panel) panel.classList.add("active");
        });
    });


    // =========================================================================
    // 9. PRESETS LOADING & ARCHITECTURAL TEMPLATES
    // =========================================================================

    async function loadPresetArchitecture(presetKey) {
        saasLoader.style.display = "flex";
        loaderMsg.textContent = `Loading preset '${presetKey}'...`;

        try {
            const res = await fetch(`/api/presets/${presetKey}`);
            if (!res.ok) throw new Error("Preset fetch failed");

            const data = await res.json();
            const preset = data.preset;

            floor.width = preset.width;
            floor.height = preset.height;
            floorWidth.value = floor.width;
            floorHeight.value = floor.height;

            currentPresetName.textContent = preset.name || presetKey;
            currentPresetDim.textContent = `${floor.width.toFixed(1)}m × ${floor.height.toFixed(1)}m`;
            activeDimPill.textContent = `Floor Scale: ${floor.width.toFixed(1)}m × ${floor.height.toFixed(1)}m (${(floor.width * floor.height).toFixed(1)} m²)`;

            rooms = preset.rooms || [];
            walls = preset.walls || [];
            doors = preset.doors || [];
            wallHistory = [];
            recommendedRouter = null;

            if (preset.suggested_router) {
                router.x = preset.suggested_router.x;
                router.y = preset.suggested_router.y;
            } else {
                router.x = floor.width / 2.0;
                router.y = floor.height / 2.0;
            }

            numRouterX.value = router.x.toFixed(2);
            numRouterY.value = router.y.toFixed(2);

            // Reset Zoom and Pan
            zoomLevel = 1.0;
            panOffset = { x: 0, y: 0 };
            btnZoomReset.textContent = "100%";

            updateRoomManagerUI();
            showToast(`Loaded ${preset.name || presetKey}`, "success");
            await triggerSimulation();
        } catch (err) {
            console.error("Failed to load preset:", err);
            showToast(`Could not load preset ${presetKey}`, "error");
        } finally {
            saasLoader.style.display = "none";
        }
    }

    btnLoadPreset.addEventListener("click", () => {
        loadPresetArchitecture(selectPreset.value);
    });

    document.querySelectorAll(".pg-card").forEach(card => {
        card.addEventListener("click", () => {
            const presetKey = card.getAttribute("data-preset");
            loadPresetArchitecture(presetKey);
            switchView("view-studio");
        });
    });


    // =========================================================================
    // 10. ROOM CREATOR & MANAGER
    // =========================================================================

    function updateRoomManagerUI() {
        roomManagerList.innerHTML = "";
        if (rooms.length === 0) {
            roomManagerList.innerHTML = `<li style="color:var(--text-muted);font-style:italic;padding:0.4rem;">No rooms defined (Open layout)</li>`;
            return;
        }

        rooms.forEach((r, idx) => {
            const li = document.createElement("li");
            li.innerHTML = `
                <div>
                    <strong>${idx + 1}.</strong> ${r.name}
                    <div style="font-size:0.68rem; color:var(--text-muted);">${r.width}m × ${r.height}m • Pos (${r.x}m, ${r.y}m)</div>
                </div>
                <button class="room-del-btn" data-index="${idx}" title="Delete Room">✕</button>
            `;
            roomManagerList.appendChild(li);
        });

        roomManagerList.querySelectorAll(".room-del-btn").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const idx = parseInt(e.target.getAttribute("data-index"), 10);
                const removed = rooms.splice(idx, 1)[0];
                showToast(`Removed room '${removed.name}'`, "info");
                updateRoomManagerUI();
                updateRoomByRoomAudit();
                renderCanvas();
            });
        });
    }

    btnToggleAddRoom.addEventListener("click", () => {
        addRoomForm.style.display = (addRoomForm.style.display === "none") ? "block" : "none";
    });

    btnCreateRoom.addEventListener("click", () => {
        const name = newRoomName.value.trim() || "New Room";
        const rw = parseFloat(newRoomW.value);
        const rh = parseFloat(newRoomH.value);
        const rx = parseFloat(newRoomX.value);
        const ry = parseFloat(newRoomY.value);

        if (rw > 0 && rh > 0 && rx + rw <= floor.width && ry + rh <= floor.height) {
            rooms.push({ name: name, x: rx, y: ry, width: rw, height: rh });
            
            // Build drywall boundaries around room
            walls.push({ x1: rx, y1: ry, x2: rx + rw, y2: ry, material: "drywall" });
            walls.push({ x1: rx + rw, y1: ry, x2: rx + rw, y2: ry + rh, material: "drywall" });
            walls.push({ x1: rx + rw, y1: ry + rh, x2: rx, y2: ry + rh, material: "drywall" });
            walls.push({ x1: rx, y1: ry + rh, x2: rx, y2: ry, material: "drywall" });

            updateRoomManagerUI();
            addRoomForm.style.display = "none";
            newRoomName.value = "";
            showToast(`Created room '${name}'`, "success");
            triggerSimulation();
        } else {
            showToast("Room dimensions exceed floor boundaries", "error");
        }
    });


    // =========================================================================
    // 11. TOOLBAR, ZOOM & WALL ACTIONS
    // =========================================================================

    const toolCards = [toolSelectDrag, toolSelectWall, toolSelectDoor, toolSelectWindow];
    toolCards.forEach(tc => {
        tc.addEventListener("click", () => {
            toolCards.forEach(c => c.classList.remove("active"));
            tc.classList.add("active");
            activeTool = tc.getAttribute("data-tool");

            const toolLabels = {
                drag: "Tool: Move Router Mode",
                wall: `Tool: Draw ${activeBarrierMaterial} Wall`,
                door: "Tool: Add Door (3.0 dB Wood)",
                window: "Tool: Add Window (2.5 dB Glass)"
            };
            activeModeText.textContent = toolLabels[activeTool] || "Tool Active";
            barrierMaterialWrapper.style.display = (activeTool === "wall") ? "block" : "none";
        });
    });

    selectMaterial.addEventListener("change", (e) => {
        activeBarrierMaterial = e.target.value;
        if (activeTool === "wall") {
            activeModeText.textContent = `Tool: Draw ${activeBarrierMaterial} Wall`;
        }
    });

    toggleGridSnap.addEventListener("change", (e) => {
        snapToGrid = e.target.checked;
        showToast(snapToGrid ? "0.5m Grid Snap Enabled" : "Grid Snap Disabled", "info");
    });

    toggleRooms.addEventListener("change", (e) => {
        showRooms = e.target.checked;
        renderCanvas();
    });

    toggleWalls.addEventListener("change", (e) => {
        showWalls = e.target.checked;
        renderCanvas();
    });

    toggleHeatmap.addEventListener("change", (e) => {
        showHeatmap = e.target.checked;
        renderCanvas();
    });

    selectHeatmapMode.addEventListener("change", (e) => {
        heatmapMode = e.target.value;
        renderCanvas();
    });

    // Zoom Buttons
    btnZoomIn.addEventListener("click", () => {
        zoomLevel = Math.min(3.0, zoomLevel + 0.25);
        btnZoomReset.textContent = `${Math.round(zoomLevel * 100)}%`;
        renderCanvas();
    });

    btnZoomOut.addEventListener("click", () => {
        zoomLevel = Math.max(0.5, zoomLevel - 0.25);
        btnZoomReset.textContent = `${Math.round(zoomLevel * 100)}%`;
        renderCanvas();
    });

    btnZoomReset.addEventListener("click", () => {
        zoomLevel = 1.0;
        panOffset = { x: 0, y: 0 };
        btnZoomReset.textContent = "100%";
        renderCanvas();
    });

    btnFitCanvas.addEventListener("click", () => {
        zoomLevel = 1.0;
        panOffset = { x: 0, y: 0 };
        btnZoomReset.textContent = "100%";
        renderCanvas();
        showToast("View reset & scaled to screen", "info");
    });

    // Wall Undo & Clear
    btnUndoLastWall.addEventListener("click", () => {
        if (wallHistory.length > 0) {
            const popped = wallHistory.pop();
            if (popped.type === "door") {
                doors.pop();
                showToast("Undid last door", "info");
            } else {
                walls.pop();
                showToast("Undid last wall", "info");
            }
            triggerSimulation();
        } else if (walls.length > 0) {
            walls.pop();
            showToast("Undid last wall", "info");
            triggerSimulation();
        } else {
            showToast("No custom walls to undo", "info");
        }
    });

    btnClearWallsBtn.addEventListener("click", () => {
        if (confirm("Clear all wall segments and doors?")) {
            walls = [];
            doors = [];
            wallHistory = [];
            showToast("Cleared all walls and partitions", "info");
            triggerSimulation();
        }
    });

    btnUpdateDimensions.addEventListener("click", () => {
        const nw = parseFloat(floorWidth.value);
        const nh = parseFloat(floorHeight.value);
        if (nw >= 4 && nw <= 60 && nh >= 4 && nh <= 40) {
            floor.width = nw;
            floor.height = nh;
            currentPresetName.textContent = "Custom Dimensions";
            currentPresetDim.textContent = `${floor.width.toFixed(1)}m × ${floor.height.toFixed(1)}m`;
            activeDimPill.textContent = `Floor Scale: ${floor.width.toFixed(1)}m × ${floor.height.toFixed(1)}m (${(floor.width * floor.height).toFixed(1)} m²)`;

            router.x = Math.min(router.x, floor.width - 0.5);
            router.y = Math.min(router.y, floor.height - 0.5);
            numRouterX.value = router.x.toFixed(2);
            numRouterY.value = router.y.toFixed(2);

            showToast(`Resized floor to ${floor.width}m × ${floor.height}m`, "info");
            triggerSimulation();
        } else {
            showToast("Width must be 4m-60m, Height 4m-40m", "error");
        }
    });


    // =========================================================================
    // 12. RADIO TRANSMITTER CONTROLS
    // =========================================================================

    sliderTxPower.addEventListener("input", (e) => {
        router.tx_power = parseFloat(e.target.value);
        valTxPower.textContent = `${router.tx_power} dBm`;
        debouncedSimulation();
    });

    sliderPathLoss.addEventListener("input", (e) => {
        pathLossExponent = parseFloat(e.target.value);
        valPathLoss.textContent = pathLossExponent.toFixed(1);
        debouncedSimulation();
    });

    btnBand24.addEventListener("click", () => {
        frequency = 2.4;
        btnBand24.classList.add("active");
        btnBand50.classList.remove("active");
        showToast("Switched to 2.4 GHz Band (PL₀: 40.0 dB)", "info");
        triggerSimulation();
    });

    btnBand50.addEventListener("click", () => {
        frequency = 5.0;
        btnBand50.classList.add("active");
        btnBand24.classList.remove("active");
        showToast("Switched to 5.0 GHz Band (PL₀: 47.0 dB)", "info");
        triggerSimulation();
    });

    numRouterX.addEventListener("change", (e) => {
        router.x = Math.max(0.5, Math.min(floor.width - 0.5, parseFloat(e.target.value) || floor.width / 2));
        numRouterX.value = router.x.toFixed(2);
        renderCanvas();
        triggerSimulation();
    });

    numRouterY.addEventListener("change", (e) => {
        router.y = Math.max(0.5, Math.min(floor.height - 0.5, parseFloat(e.target.value) || floor.height / 2));
        numRouterY.value = router.y.toFixed(2);
        renderCanvas();
        triggerSimulation();
    });

    btnRecenterRouter.addEventListener("click", () => {
        router.x = parseFloat((floor.width / 2).toFixed(2));
        router.y = parseFloat((floor.height / 2).toFixed(2));
        numRouterX.value = router.x.toFixed(2);
        numRouterY.value = router.y.toFixed(2);
        showToast("Router centered on floor plan", "info");
        renderCanvas();
        triggerSimulation();
    });


    // =========================================================================
    // 13. PLACEMENT OPTIMIZATION ENGINE
    // =========================================================================

    async function executeOptimization() {
        saasLoader.style.display = "flex";
        loaderMsg.textContent = "Searching spatial coordinates for optimal AP placement...";

        try {
            const referenceLoss = (frequency === 5.0) ? 47.0 : 40.0;
            const payload = {
                width: floor.width,
                height: floor.height,
                walls: walls.concat(doors),
                router_position: { x: router.x, y: router.y },
                tx_power: router.tx_power,
                path_loss_exponent: pathLossExponent,
                reference_loss: referenceLoss
            };

            const res = await fetch("/api/optimize", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error("Optimization failed");

            const data = await res.json();
            recommendedRouter = data.recommended_position;

            // Populate Optimizer View UI
            optBannerTitle.textContent = `Optimal AP Position: (${recommendedRouter.x.toFixed(1)}m, ${recommendedRouter.y.toFixed(1)}m)`;
            optBannerDesc.textContent = data.summary || "Recommended location maximizes line-of-sight and eliminates dead zones.";
            btnApplyOptimizedPos.style.display = "inline-flex";
            optComparisonGrid.style.display = "grid";

            // Current AP Stats
            const init = data.initial_metrics || {
                position: { x: router.x, y: router.y },
                good_coverage_percent: currentHeatmapData?.metrics?.good_coverage_percent || 0,
                dead_zone_percent: currentHeatmapData?.metrics?.dead_zone_percent || 0,
                average_rssi_dbm: currentHeatmapData?.metrics?.average_rssi_dbm || 0
            };

            compCurrentPos.textContent = `AP at (${init.position.x}m, ${init.position.y}m)`;
            compCurGood.textContent = `${init.good_coverage_percent}%`;
            compCurDead.textContent = `${init.dead_zone_percent}%`;
            compCurAvg.textContent = `${init.average_rssi_dbm} dBm`;

            // Recommended AP Stats
            compRecPos.textContent = `AP at (${data.recommended_position.x}m, ${data.recommended_position.y}m)`;
            compRecGood.textContent = `${data.expected_good_coverage}%`;
            compRecDead.textContent = `${data.expected_dead_zone_percent}%`;
            compRecAvg.textContent = `${data.expected_average_rssi_dbm} dBm`;

            // Gain Badges
            const goodGain = data.expected_good_coverage - init.good_coverage_percent;
            const deadReduction = init.dead_zone_percent - data.expected_dead_zone_percent;
            const rssiGain = data.expected_average_rssi_dbm - init.average_rssi_dbm;

            gainGoodVal.textContent = `${goodGain >= 0 ? "+" : ""}${goodGain.toFixed(1)}%`;
            gainDeadVal.textContent = `-${Math.max(0, deadReduction).toFixed(1)}%`;
            gainRssiVal.textContent = `${rssiGain >= 0 ? "+" : ""}${rssiGain.toFixed(1)} dB`;

            showToast("Optimal placement identified!", "success");
            renderCanvas();
        } catch (err) {
            console.error(err);
            showToast("Optimization failed. Verify parameters.", "error");
        } finally {
            saasLoader.style.display = "none";
        }
    }

    function applyRecommendedCoordinates() {
        if (recommendedRouter) {
            router.x = recommendedRouter.x;
            router.y = recommendedRouter.y;
            numRouterX.value = router.x.toFixed(2);
            numRouterY.value = router.y.toFixed(2);
            showToast(`Moved AP to optimal position (${router.x}m, ${router.y}m)`, "success");
            switchView("view-studio");
            triggerSimulation();
        }
    }

    btnRunOptimizerMain.addEventListener("click", executeOptimization);
    btnHeaderOptimize.addEventListener("click", () => {
        switchView("view-optimizer");
        executeOptimization();
    });
    btnStudioOptimize.addEventListener("click", () => {
        switchView("view-optimizer");
        executeOptimization();
    });
    btnAuditRunOptimizer.addEventListener("click", () => {
        switchView("view-optimizer");
        executeOptimization();
    });
    btnApplyOptimizedPos.addEventListener("click", applyRecommendedCoordinates);


    // =========================================================================
    // 14. PROJECT PERSISTENCE & FILE EXPORT/IMPORT
    // =========================================================================

    const STORAGE_KEY = "smart_router_saved_projects";

    function getSavedProjects() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
        } catch {
            return [];
        }
    }

    function saveProjectLocally(name) {
        const projects = getSavedProjects();
        const newProj = {
            id: Date.now(),
            name: name || `Project ${projects.length + 1}`,
            date: new Date().toLocaleDateString(),
            floor: { ...floor },
            router: { ...router },
            frequency: frequency,
            pathLossExponent: pathLossExponent,
            rooms: [...rooms],
            walls: [...walls],
            doors: [...doors]
        };
        projects.unshift(newProj);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(projects));
        renderSavedProjectsList();
        showToast(`Saved project '${newProj.name}'`, "success");
    }

    function loadProjectLocally(id) {
        const projects = getSavedProjects();
        const proj = projects.find(p => p.id === id);
        if (!proj) return;

        floor = { ...proj.floor };
        router = { ...proj.router };
        frequency = proj.frequency || 2.4;
        pathLossExponent = proj.pathLossExponent || 2.8;
        rooms = proj.rooms || [];
        walls = proj.walls || [];
        doors = proj.doors || [];

        floorWidth.value = floor.width;
        floorHeight.value = floor.height;
        numRouterX.value = router.x.toFixed(2);
        numRouterY.value = router.y.toFixed(2);
        sliderTxPower.value = router.tx_power;
        valTxPower.textContent = `${router.tx_power} dBm`;
        sliderPathLoss.value = pathLossExponent;
        valPathLoss.textContent = pathLossExponent.toFixed(1);

        if (frequency === 5.0) {
            btnBand50.classList.add("active");
            btnBand24.classList.remove("active");
        } else {
            btnBand24.classList.add("active");
            btnBand50.classList.remove("active");
        }

        currentPresetName.textContent = proj.name;
        currentPresetDim.textContent = `${floor.width.toFixed(1)}m × ${floor.height.toFixed(1)}m`;
        activeDimPill.textContent = `Floor Scale: ${floor.width.toFixed(1)}m × ${floor.height.toFixed(1)}m (${(floor.width * floor.height).toFixed(1)} m²)`;

        updateRoomManagerUI();
        showToast(`Loaded project '${proj.name}'`, "success");
        switchView("view-studio");
        triggerSimulation();
    }

    function deleteProjectLocally(id) {
        let projects = getSavedProjects();
        projects = projects.filter(p => p.id !== id);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(projects));
        renderSavedProjectsList();
        showToast("Deleted saved project", "info");
    }

    function renderSavedProjectsList() {
        if (!savedProjectsList) return;
        savedProjectsList.innerHTML = "";
        const projects = getSavedProjects();

        if (projects.length === 0) {
            savedProjectsList.innerHTML = `<li style="color:var(--text-muted);font-style:italic;padding:0.6rem;">No saved projects yet. Save your current layout above.</li>`;
            return;
        }

        projects.forEach(p => {
            const li = document.createElement("li");
            li.innerHTML = `
                <div>
                    <strong>${p.name}</strong>
                    <div style="font-size:0.68rem; color:var(--text-muted);">${p.date} • ${p.floor.width}m × ${p.floor.height}m • ${p.rooms?.length || 0} rooms</div>
                </div>
                <div style="display:flex;gap:0.4rem;">
                    <button class="btn btn-sm btn-secondary btn-load-proj" data-id="${p.id}">Load</button>
                    <button class="btn btn-sm btn-danger btn-del-proj" data-id="${p.id}">✕</button>
                </div>
            `;
            savedProjectsList.appendChild(li);
        });

        savedProjectsList.querySelectorAll(".btn-load-proj").forEach(b => {
            b.addEventListener("click", () => loadProjectLocally(parseInt(b.getAttribute("data-id"), 10)));
        });
        savedProjectsList.querySelectorAll(".btn-del-proj").forEach(b => {
            b.addEventListener("click", () => deleteProjectLocally(parseInt(b.getAttribute("data-id"), 10)));
        });
    }

    btnSaveCurrentProject.addEventListener("click", () => {
        const name = saveProjectName.value.trim() || `Wi-Fi Floor Plan (${floor.width}m×${floor.height}m)`;
        saveProjectLocally(name);
        saveProjectName.value = "";
    });

    // High-Resolution Blueprint PNG Export
    function exportHighResPng() {
        // Build dedicated export canvas with title banner & metrics overlay
        const expCanvas = document.createElement("canvas");
        const expW = 1600;
        const expH = 1100;
        expCanvas.width = expW;
        expCanvas.height = expH;
        const ectx = expCanvas.getContext("2d");

        // 1. Blueprint Background
        ectx.fillStyle = "#040711";
        ectx.fillRect(0, 0, expW, expH);

        // 2. Title Header Banner
        ectx.fillStyle = "#080d1a";
        ectx.fillRect(0, 0, expW, 80);
        ectx.strokeStyle = "#162035";
        ectx.lineWidth = 1;
        ectx.strokeRect(0, 0, expW, 80);

        ectx.fillStyle = "#ffffff";
        ectx.font = "800 22px 'Plus Jakarta Sans', sans-serif";
        ectx.fillText("Smart Router Placement Advisor — Blueprint & Signal Heatmap", 30, 48);

        ectx.fillStyle = "#00f0ff";
        ectx.font = "600 14px 'JetBrains Mono', monospace";
        ectx.textAlign = "right";
        ectx.fillText(`Floor: ${floor.width.toFixed(1)}m × ${floor.height.toFixed(1)}m | Band: ${frequency.toFixed(1)} GHz | AP EIRP: ${router.tx_power} dBm`, expW - 30, 48);
        ectx.textAlign = "left";

        // 3. Draw Main Canvas Viewport
        const drawW = expW - 60;
        const drawH = expH - 180;
        ectx.drawImage(canvas, 30, 100, drawW, drawH);

        // 4. Bottom Metrics Banner
        ectx.fillStyle = "#080d1a";
        ectx.fillRect(0, expH - 60, expW, 60);

        const good = currentHeatmapData?.metrics?.good_coverage_percent || "--";
        const dead = currentHeatmapData?.metrics?.dead_zone_percent || "--";
        const avg = currentHeatmapData?.metrics?.average_rssi_dbm || "--";

        ectx.fillStyle = "#94a3b8";
        ectx.font = "600 13px 'Plus Jakarta Sans', sans-serif";
        ectx.fillText(`Good Coverage (≥ -67 dBm): `, 30, expH - 26);
        ectx.fillStyle = "#10b981";
        ectx.fillText(`${good}%`, 220, expH - 26);

        ectx.fillStyle = "#94a3b8";
        ectx.fillText(`Dead Zones (< -85 dBm): `, 320, expH - 26);
        ectx.fillStyle = "#ef4444";
        ectx.fillText(`${dead}%`, 490, expH - 26);

        ectx.fillStyle = "#94a3b8";
        ectx.fillText(`Mean Signal: `, 580, expH - 26);
        ectx.fillStyle = "#00f0ff";
        ectx.fillText(`${avg} dBm`, 670, expH - 26);

        ectx.fillStyle = "#546682";
        ectx.textAlign = "right";
        ectx.fillText(`Generated: ${new Date().toLocaleString()}`, expW - 30, expH - 26);

        // Download
        const link = document.createElement("a");
        link.download = `wifi-planner-${floor.width}x${floor.height}m.png`;
        link.href = expCanvas.toDataURL("image/png");
        link.click();
        showToast("Exported high-res blueprint PNG", "success");
    }

    btnExportImage.addEventListener("click", exportHighResPng);
    btnExportPngAlt.addEventListener("click", exportHighResPng);

    // Export Project JSON
    btnExportJson.addEventListener("click", () => {
        const payload = {
            generator: "Smart Router Placement Advisor",
            version: "1.0.0",
            timestamp: new Date().toISOString(),
            floor: floor,
            router: router,
            frequency: frequency,
            pathLossExponent: pathLossExponent,
            rooms: rooms,
            walls: walls,
            doors: doors
        };
        const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `wifi-project-${floor.width}x${floor.height}m.json`;
        a.click();
        URL.revokeObjectURL(url);
        showToast("Exported project JSON", "success");
    });

    // Import Project JSON
    fileDropZone.addEventListener("click", () => importJsonInput.click());
    fileDropZone.addEventListener("dragover", (e) => { e.preventDefault(); fileDropZone.style.borderColor = "var(--cyan)"; });
    fileDropZone.addEventListener("dragleave", () => { fileDropZone.style.borderColor = "var(--border-hover)"; });
    fileDropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        fileDropZone.style.borderColor = "var(--border-hover)";
        if (e.dataTransfer.files.length > 0) {
            handleImportFile(e.dataTransfer.files[0]);
        }
    });
    importJsonInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) handleImportFile(e.target.files[0]);
    });

    function handleImportFile(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);
                if (data.floor) floor = { ...data.floor };
                if (data.router) router = { ...data.router };
                if (data.frequency) frequency = data.frequency;
                if (data.pathLossExponent) pathLossExponent = data.pathLossExponent;
                if (data.rooms) rooms = data.rooms;
                if (data.walls) walls = data.walls;
                if (data.doors) doors = data.doors;

                floorWidth.value = floor.width;
                floorHeight.value = floor.height;
                numRouterX.value = router.x.toFixed(2);
                numRouterY.value = router.y.toFixed(2);

                currentPresetName.textContent = "Imported JSON Project";
                updateRoomManagerUI();
                showToast("Imported project successfully!", "success");
                switchView("view-studio");
                triggerSimulation();
            } catch (err) {
                showToast("Failed to parse JSON project file", "error");
            }
        };
        reader.readAsText(file);
    }


    // =========================================================================
    // 15. NAVIGATION BACK BUTTONS & STARTUP
    // =========================================================================

    btnAuditBackToStudio.addEventListener("click", () => switchView("view-studio"));
    btnAnalyticsBackToStudio.addEventListener("click", () => switchView("view-studio"));

    btnHeaderReset.addEventListener("click", () => {
        if (confirm("Reset layout to an open space without walls?")) {
            rooms = [];
            walls = [];
            doors = [];
            wallHistory = [];
            recommendedRouter = null;
            currentPresetName.textContent = "Open Custom Plan";
            updateRoomManagerUI();
            showToast("Reset canvas to open space", "info");
            triggerSimulation();
        }
    });

    btnHeaderSimulate.addEventListener("click", () => {
        triggerSimulation();
        showToast("Recalculating Wi-Fi propagation...", "info");
    });

    // Window Resize Handling
    window.addEventListener("resize", () => {
        resizeCanvasToContainer();
    });

    // Initialize
    checkBackendHealth();
    setInterval(checkBackendHealth, 12000); // Live backend ping

    setTimeout(() => {
        resizeCanvasToContainer();
        loadPresetArchitecture("2BHK");
    }, 50);
});
