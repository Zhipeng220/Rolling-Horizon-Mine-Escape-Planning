

# Rolling Horizon Mine Escape Planning (RH-MEP)

This repository contains the implementation of a **Dynamic Escape Path Planning Algorithm** based on a **Rolling Horizon Strategy** (RH) for underground mine emergencies. The system simulates a **dual-source water inrush** scenario and guides miners to safety by dynamically re-planning routes when environmental changes (e.g., secondary outbursts or rising water levels) are detected.


## 🚀 Key Features 

* **Dual-Source Hydraulic Simulation**: Simulates water flow propagation from two distinct sources with time delays and gravity-driven flow logic.
* **Rolling Horizon Strategy**: Implements a "Lookahead Check" mechanism. If a future path segment is predicted to become unsafe, the agent triggers an immediate re-planning sequence locally.
* **Risk-Weighted A* Search**: Uses a generalized cost function combining **Travel Time** () and **Safety Risk** () to balance efficiency and survival probability.
* **3D Topology Support**: Handles complex 3D mine tunnel networks (coordinates x, y, z) and calculates slope-dependent water filling rates.
* **SOTA Metrics Evaluation**: Automatically calculates advanced metrics including **Safety Margin**, **Cumulative Risk**, and **Normalized Time** for performance benchmarking.
* **Visualization**: Generates high-resolution dashboards (`.eps`/`.jpg`) visualizing escape trajectories and optimization cost convergence.

## 🛠️ Prerequisites

The code requires **Python 3.8+** and the following dependencies:

```bash
pip install pandas numpy matplotlib openpyxl
```

* **pandas**: Data manipulation and Excel I/O.
* **numpy**: Vectorized calculations and linear algebra.
* **matplotlib**: Plotting the 2x3 dashboard and trajectories.
* **openpyxl**: Engine for reading `.xlsx` files.

## 📂 File Structure (文件结构)

Ensure your directory is organized as follows:

```text
.
├── main.py              # The core simulation and planning script
├── 附件2.xlsx           # [Input] Mine topology data (Nodes and Tunnels)
├── result_DK.xlsx       # [Optional Input] Baseline results for comparison
├── result_A.xlsx        # [Output] Final simulation results
├── Fig5.jpg             # [Output] Visualization dashboard
└── README.md            # Project documentation

```

### Input Data Format (`附件2.xlsx`)

The input Excel file must contain two sheets:

1. **端点 (Nodes)**: Columns `[端点编号, x (m), y (m), z (m)]`.
2. **巷道 (Tunnels)**: Columns `[巷道编号, 巷道端点1, 巷道端点2]`.

## ⚙️ Configuration (参数配置)

Key parameters can be adjusted in the `--- 1. 模型常量与参数定义 ---` section of `main.py`:

| Parameter | Default | Description |
| --- | --- | --- |
| `FLOW_RATE_PER_SOURCE` | `2.5` | Water inflow rate per source () |
| `INITIAL_ESCAPE_START_TIME` | `60.0` | Reaction delay time for miners (seconds) |
| `DELAY_SECONDS` | `-90` | Time offset for the second water source |
| `ALPHA_WEIGHT` | `0.7` | Weight for **Time Cost** in A* heuristic |
| `BETA_WEIGHT` | `0.3` | Weight for **Risk Cost** in A* heuristic |
| `SLOPE_THRESHOLD` | `0.02` | Threshold to determine gravity-driven flow |

## 🚀 Usage (使用方法)

Run the main script directly:

```bash
python main.py
```

### Console Output

The script will output the simulation progress, re-planning triggers, and a final comparison table:

```text
>>> SOTA 多维性能评估 (Advanced Metrics)
==========================================================================================
| 矿工   | 重规划次数 | 安全裕度(m)  | 累积风险   | 实际耗时(min)  | 归一化耗时*(min)  |
------------------------------------------------------------------------------------------
| 矿工1  | 0          | 0.127        | 1221.25    | 52.50          | 48.10             |
| 矿工2  | 1          | 0.036        | 2037.05    | 80.67          | 75.33             |
...

```

## 📊 Methodology (算法原理)

### 1. Water Inrush Evolution

The simulation calculates the **Earliest Arrival Time** for every node using a Dijkstra-based propagation on the gravity-directed graph. Tunnel states transition from `DRY`  `FILLING`  `FILLED` based on the slope and inflow volume.

### 2. Generalized Cost Function

The edge weight  is dynamic:

$$C_G(t) = \alpha \cdot C_T(t) + \beta \cdot C_R(t)$$

* **Time Cost ()**: Dependent on movement speed, which decreases significantly when moving against water flow.
* **Risk Cost ()**: Non-linear penalty based on water depth : .

### 3. Rolling Horizon Replanning

Instead of a static path, the agent performs a **Lookahead Check** at each step. If  for any downstream segment in the current plan, a **Re-planning Event** is triggered using the agent's current position as the new start node.

## 📈 Visualization (结果可视化)

The script generates `Fig5.jpg` containing:

* **Top Row**: 2D projection of the mine network and the escape trajectories for each miner.
* **Bottom Row**: Optimization process showing the "Path Cost" evolution over iterations, highlighting the smoothness of the Rolling A* convergence.

---

## ⚠️ Note

This code assumes specific column names in the input Excel files (e.g., `端点编号`, `x (m)`). If your data uses different headers, please update the `load_data_and_build_graph` function in `main.py`.

