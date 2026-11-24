# Smart Router Placement Advisor — Multi-Model ML Edition

## Model comparison (important for project viva)

This version trains and evaluates multiple algorithms instead of claiming a single model is universally best:

- **RSSI regression:** Random Forest Regressor, KNN Regressor, and Linear Regression all predict the same continuous target (`rssi_dbm`). Compare MAE, RMSE (lower is better), and R² (higher is better). The lowest-RMSE regressor is saved as `models/best_rssi_regressor.joblib` and powers the heatmap and placement optimizer.
- **Signal-category classification:** Random Forest Classifier, Logistic Regression, and KNN Classifier predict six RSSI bands (Dead Zone through Excellent). Compare accuracy and weighted F1 (higher is better). Logistic Regression is a classifier, not a continuous RSSI regressor, so it is evaluated on the classification task.

### Dataset provenance and exact split

`data/synthetic_wifi_rssi.csv` is generated locally by `train_model.py`; it is **not downloaded from Kaggle, UCI, or another public dataset**. It contains **18,000 synthetic rows**. The target RSSI values are generated using this project's original `simulation.calculate_rssi()` physics formula. The 16 input features are listed in the CSV header and in `models/model_comparison.json`. A reproducible 80:20 split with `random_state=42` gives **14,400 training rows** and **3,600 held-out testing rows**. All models use the same split.

**Honest limitation:** These test results measure how well the models learn the simulator-generated labels. They are not proof of accuracy against real Wi-Fi signals. For real-world claims, collect actual RSSI measurements with a phone/laptop Wi-Fi analyzer and train/evaluate on those measured values.

### Re-train and see the results

```powershell
python train_model.py
```

The script writes `models/model_comparison.json`, model files under `models/`, and prints all metrics in the terminal. The report is also available from the running Flask app at `http://127.0.0.1:5000/api/model-comparison`. The application uses the best regression model selected by hold-out RMSE.

### Results generated in this training run

**Regression (continuous RSSI):**

| Model | MAE (dBm) | RMSE (dBm) | R² |
|---|---:|---:|---:|
| Random Forest Regressor | 1.1697 | 1.8870 | 0.98394 |
| KNN Regressor | 3.0729 | 4.1062 | 0.92395 |
| Linear Regression | 2.7697 | 3.8739 | 0.93231 |

**Classification (signal bands):**

| Model | Accuracy | Weighted F1 |
|---|---:|---:|
| Random Forest Classifier | 84.333% | 0.8422 |
| Logistic Regression | 87.861% | 0.8798 |
| KNN Classifier | 71.972% | 0.7129 |

These figures are from the synthetic hold-out split described above and should be reported with that qualification.

---

# 📡 Smart Router Placement Advisor

A professional, modern, interactive Wi-Fi planning, indoor radio-frequency (RF) propagation simulator, and router placement optimization web application.

---

## 🌟 Overview & Key Features

* **Physical Log-Distance Path Loss (LDPL) Model**: Simulates indoor Wi-Fi signal attenuation based on real-world free-space reference loss ($PL_0 \approx 40.0\text{ dB}$ at $1\text{m}$ for $2.4\text{ GHz}$; $47.0\text{ dB}$ for $5.0\text{ GHz}$), distance power decay, and barrier absorption.
* **Accurate, Non-Overlapping Coverage Analytics**:
  - **Good Coverage ($\ge -67\text{ dBm}$)**: Standard benchmark for high-speed browsing, 4K streaming, and low-latency video conferencing.
  - **Weak Coverage ($-85\text{ dBm} \le RSSI < -67\text{ dBm}$)**: Marginal connection with potential buffering and lower throughput.
  - **Dead Zone ($< -85\text{ dBm}$)**: Area experiencing dropped connections and high packet loss.
  - Categories strictly partition 100% of all valid floor plan grid cells without overlap or omissions.
* **Dynamic Floor Plans & Architectural Presets**:
  - One-click presets: **1 BHK**, **2 BHK**, **3 BHK**, **4 BHK**, **Open Floor Plan**, and **Custom Layout**.
  - Dynamic room resizing: Configure room width and height in meters ($4\text{m}$ to $60\text{m}$).
  - **Custom Room Manager**: Add rectangular rooms with customizable dimensions and position coordinates; delete rooms on the fly.
  - Labeled room inspector displaying room boundaries and dimensions.
* **Interactive HTML5 Canvas Workspace**:
  - **Draggable Access Point (AP)** with animated pulsing radio waves and precise coordinate readouts.
  - **Interactive Wall & Opening Tools**: Click and drag to construct custom partitions, doors, or windows with immediate signal impact.
  - **Multi-Material Barrier Modeling**: Supports Drywall ($-3\text{ dB}$), Wood ($-4\text{ dB}$), Glass ($-2.5\text{ dB}$), Brick ($-8\text{ dB}$), Reinforced Concrete ($-14\text{ dB}$), Doors ($-0.5\text{ dB}$ to $-3\text{ dB}$), and Windows.
  - **Live Cursor Hover Tooltip**: Real-time inspection displaying exact $(X, Y)$ coordinates and instantaneous simulated signal in dBm.
  - **High-Resolution PNG Export**: One-click download of the active floor plan and heatmap canvas.
* **Intelligent Router Placement Optimizer**:
  - Multi-objective optimization algorithm balancing good coverage maximization and dead zone elimination:
    $$F(x, y) = 2.0 \cdot \text{Good Coverage \%} - 3.0 \cdot \text{Dead Zone \%} + 0.5 \cdot \text{Average RSSI}$$
  - Baseline comparison showing net coverage gains and dead zone reductions in a structured side-by-side table.
  - One-click "Move Router to Optimal Position" button with target reticle visualization.
* **Modern Dark Dashboard Theme**:
  - Engineered with a high-contrast commercial SaaS dark theme (`Plus Jakarta Sans` & `JetBrains Mono` typography).
  - Responsive layout for desktop, laptop, and tablet displays.
  - Signal distribution histogram chart, real-time backend latency monitor, debounced simulation requests, and smooth animated progress bars.

---

## 🏗️ Project Architecture & File Structure

```text
Smart Router Placement advisor/
│
├── app.py                 # Flask server, REST API routing & strict input validation
├── simulation.py          # Core RF propagation math, presets & NumPy optimization
├── test_backend.py        # Automated test suite (18 unit, API & physics tests)
├── requirements.txt       # Python dependencies (Flask & NumPy)
├── README.md              # Project documentation & usage guide
│
├── templates/
│   └── index.html         # Modern dark dashboard template
│
└── static/
    ├── style.css          # Professional dashboard styling, progress bars & legends
    └── script.js          # Interactive canvas pipeline, drag handlers & API client
```

---

## 📐 Mathematical Model & Physics Principles

### 1. The Log-Distance Path Loss (LDPL) Equation
$$RSSI(d) = P_{tx} - \left[ PL_0 + 10 \cdot n \cdot \log_{10}\left(\frac{d}{d_0}\right) \right] - \sum \text{Wall Losses} - \sum \text{Obstacle Losses}$$

Where:
* $RSSI(d)$: Received Signal Strength Indicator in $\text{dBm}$ at distance $d$.
* $P_{tx}$: Router transmission power in $\text{dBm}$ (configurable from $10$ to $30\text{ dBm}$, default $20\text{ dBm}$).
* $d_0$: Reference distance ($1.0\text{ meter}$).
* $PL_0$: Reference path loss at $1.0\text{m}$ calculated from Friis transmission equation:
  - **2.4 GHz Band**: $PL_0 \approx 40.04\text{ dB}$
  - **5.0 GHz Band**: $PL_0 \approx 46.80\text{ dB}$
* $n$: Path loss exponent ($2.0$ for free space, $2.5 - 3.5$ for residential interiors, $4.0+$ for dense concrete).
* $d$: Euclidean distance in meters, clamped to $d \ge 1.0\text{ m}$ to avoid singularity.
* $\sum \text{Wall Losses}$: Sum of attenuation from all walls crossed by the direct line-of-sight ray. De-duplicated to prevent double-counting shared wall vertices.

### 2. Signal Quality Tiers

| Category | Range (dBm) | Visual Color | Expected User Experience |
| :--- | :--- | :--- | :--- |
| **Excellent** | $\ge -50\text{ dBm}$ | Cyan (`#00f0ff`) | Maximum theoretical speed, lowest latency. |
| **Good** | $-60 \le RSSI < -50$ | Green (`#10b981`) | 4K video conferencing, low-latency online gaming. |
| **Fair** | $-67 \le RSSI < -60$ | Lime (`#84cc16`) | Recommended minimum threshold for smooth browsing. |
| **Weak** | $-75 \le RSSI < -67$ | Amber (`#f59e0b`) | Slower speeds, intermittent buffering. |
| **Very Weak** | $-85 \le RSSI < -75$ | Orange (`#f97316`) | Marginal connection, frequent packet retries. |
| **Dead Zone** | $< -85\text{ dBm}$ | Red (`#ef4444`) | Disconnections, high packet loss, unusable. |

### 3. Aggregated Coverage Metrics
$$\text{Good Coverage \%} + \text{Weak Coverage \%} + \text{Dead Zone \%} = 100.0\%$$
* **Good Coverage**: Total percentage of grid cells with $RSSI \ge -67\text{ dBm}$.
* **Weak Coverage**: Total percentage of grid cells with $-85\text{ dBm} \le RSSI < -67\text{ dBm}$.
* **Dead Zone**: Total percentage of grid cells with $RSSI < -85\text{ dBm}$.
* **Average Signal**: The exact mathematical mean of all valid simulated floor plan cells.

---

## 🔌 API Endpoints

### 1. `GET /api/health`
Confirms server availability, API version, supported materials, and signal thresholds.

### 2. `GET /api/presets`
Returns available architectural templates (`1BHK`, `2BHK`, `3BHK`, `4BHK`, `open_plan`) with room count and dimensions.

### 3. `GET /api/presets/<preset_name>`
Returns full layout structure (room polygons, wall segments, door positions, suggested router coordinates).

### 4. `POST /api/simulate`
* **Request JSON:**
  ```json
  {
    "width": 16.0,
    "height": 11.0,
    "resolution": 0.5,
    "router": {"x": 8.0, "y": 5.5, "tx_power": 20.0},
    "walls": [{"x1": 8.5, "y1": 0.0, "x2": 8.5, "y2": 11.0, "material": "concrete"}],
    "path_loss_exponent": 2.8,
    "reference_loss": 40.0
  }
  ```
* **Response JSON:** Returns $xs$, $ys$ coordinate axes, 2D heatmap matrix, and detailed non-overlapping coverage metrics.

### 5. `POST /api/optimize`
* **Request JSON:** Floor plan dimensions, walls, obstacles, router baseline position, and radio settings.
* **Response JSON:** Returns recommended $(X, Y)$ coordinate, projected coverage metrics, and baseline improvement comparison.

---

## 🚀 Installation & How to Run on Windows

### Prerequisites
* Python 3.8 or higher installed on your computer.

### Step 1: Open Terminal in the Project Directory
```powershell
cd "c:\Users\Krrish malhotra\Desktop\Smart Router Placement advisor"
```

### Step 2: Activate the Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell displays an execution policy restriction, run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` first)*

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Run the Backend Test Suite
```powershell
python -m unittest test_backend.py -v
```
*(All 18 unit, API, and coverage tests will run and pass)*

### Step 5: Start the Web Application
```powershell
python app.py
```

### Step 6: Access the Dashboard
Open your web browser and navigate to:
**`http://127.0.0.1:5000`**

---

## 📸 Application Screenshots

*(Screenshots can be captured directly from your browser once the application is running)*

* **Heatmap Simulation Dashboard**: Shows 2D color-coded RSSI distribution with interactive router dragging.
* **Layout Presets & Wall Drawing**: Shows room boundaries and custom walls drawn across the apartment.
* **Placement Optimizer Panel**: Shows calculated optimal coordinates and coverage gains.

---

## 🔬 Limitations & Simulation Scope

* **2D Planar Modeling**: Calculations assume a single horizontal elevation. Signals traveling across multiple floors in high-rise buildings are subject to additional slab penetration losses.
* **Ray Tracing vs. Multipath**: The model calculates direct line-of-sight propagation with wall absorption. It does not compute multi-bounce wave reflections (multipath interference).
* **Antenna Pattern**: The simulation models an omnidirectional antenna with uniform horizontal gain. Directional patch antennas or beamforming arrays will modify radiation patterns.
* **Disclaimer**: This is a spatial estimation and planning tool designed for engineering demonstration, not a substitute for physical spectrum analyzer measurements.
