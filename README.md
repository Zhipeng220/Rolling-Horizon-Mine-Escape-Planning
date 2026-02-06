# Dynamic Escape Path Planning for Mine Water Inrush

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## 📖 Overview

This repository contains the implementation code and dataset for the research paper:

**"Dynamic Escape Path Planning for Mine Water Inrush Based on Rolling Horizon Strategy under Multi-Source Conditions"**

Mine water inrush is a catastrophic hazard characterized by rapid evolution and high uncertainty. This project proposes a dynamic escape path planning method based on a **Rolling Horizon Strategy** that addresses the complex dynamics of multi-source water inrush disasters.

### Key Features

- **Dual-Source Hydraulic Evolution Model**: Quantifies non-linear acceleration of roadway submergence caused by flow superposition
- **Risk-Weighted A* Algorithm**: Balances escape efficiency and safety risks through a generalized cost function
- **Rolling Replanning Mechanism**: Triggers real-time route optimization upon detection of secondary water sources
- **High Survival Rate**: Maintains >90% survival rate even under high-inflow conditions

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Required libraries:
  ```bash
  pandas
  numpy
  matplotlib
  openpyxl
  ```

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/mine-water-inrush-escape.git
   cd mine-water-inrush-escape
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

### Quick Start

Run the main simulation:

```bash
python A_V2.py
```

The program will:
1. Load the mine topology from `Mine-Water-Inrush-Escape-Planning-Dataset.xlsx`
2. Simulate dual-source water inrush evolution
3. Execute rolling horizon path planning for three miners
4. Generate comparison visualizations and save results to `result_A.xlsx`

---

## 📁 Repository Structure

```
mine-water-inrush-escape/
│
├── A_V2.py                                          # Main implementation code
├── Mine-Water-Inrush-Escape-Planning-Dataset.xlsx  # Mine topology dataset
├── requirements.txt                                 # Python dependencies
├── README.md                                        # This file
│
├── results/                                         # Output directory (generated)
│   ├── result_A.xlsx                               # Escape planning results
│   └── Comparison_*.png                            # Trajectory visualizations
│
└── docs/                                           # Additional documentation
    └── paper.pdf                                   # Research paper (if available)
```

---

## 📊 Dataset Description

The dataset (`Mine-Water-Inrush-Escape-Planning-Dataset.xlsx`) contains:

### Sheet 1: 端点 (Endpoints)
- **端点编号**: Node ID
- **x, y, z**: 3D coordinates (meters)
- Contains 663 nodes representing roadway junctions and endpoints

### Sheet 2: 巷道 (Roadways)
- **巷道编号**: Roadway ID
- **巷道端点1, 巷道端点2**: Connected node IDs
- Contains 977 edges representing mine roadways with elevation variations

### Key Parameters

| Parameter | Value | Unit |
|-----------|-------|------|
| Tunnel Cross-section | 4.0 × 3.0 | m |
| Water Inflow Rate (per source) | 2.5 | m³/s |
| Initial Water Depth | 0.1 | m |
| Source B Inflow Delay | 90 | seconds |
| Critical Safety Water Height | 0.3 | m |
| Movement Speed (dry/with flow/against flow) | 1.5/1.0/0.5 | m/s |

---

## 🔬 Methodology

### 1. Dual-Source Water Inrush Simulation

The hydraulic evolution model simulates water propagation from two distinct outburst points:
- **Source A**: Primary water source at coordinates `(4143.12, 4376.28, 6.33)`
- **Source B**: Secondary source at `(5883.14, 5643.35, 40.37)` with 90s delay

The model calculates:
- Global earliest arrival time `T(v)` for each node
- Dynamic roadway accessibility based on water depth
- Non-linear acceleration due to flow superposition

### 2. Risk-Weighted Path Planning

The generalized cost function integrates:

```
C_G(i,j,t) = α·C_T(i,j,t) + β·C_R(i,j,t)
```

Where:
- `C_T`: Time cost (travel duration)
- `C_R`: Risk cost (water level penalty)
- `α = 0.7`, `β = 0.3` (configurable weights)

### 3. Rolling Horizon Strategy

The algorithm continuously monitors the environment and triggers replanning when:
- **Event-Driven**: Secondary water source is activated
- **Prediction-Driven**: Predicted path failure due to rising water levels

---

## 📈 Experimental Results

### Performance Comparison: Rolling A* vs D-K Algorithm

| Metric | Rolling A* | D-K Algorithm | Improvement |
|--------|------------|---------------|-------------|
| Mean Escape Time (Miner 2) | 80.67 min | 124.65 min | **35.3%** |
| Cumulative Risk (Miner 2) | 2037.05 | 3704.50 | **45.0%** |
| Success Rate (baseline) | >96% | ~85% | **+11%** |
| Robustness (1.2× inflow) | >90% | <70% | **+20%** |

### Key Findings

1. **Superposition Effect**: Dual-source conditions reduce mean tunnel fill time by ~48.75%
2. **Proactive Replanning**: Rolling A* successfully avoids "closing door" scenarios through predictive re-routing
3. **Robustness**: Algorithm maintains high success rate even under 1.5× baseline inflow rates

---

## 🖼️ Visualization Examples

The code generates trajectory comparison plots showing:
- **Blue Line**: D-K Algorithm path (baseline)
- **Red Line**: Rolling A* path (proposed method)
- **Yellow Triangle**: Replanning trigger point
- **Green Circle**: Starting position
- **Gold Star**: Exit location

Example output: `Comparison_矿工1.png`, `Comparison_矿工2.png`, `Comparison_矿工3.png`

---

## ⚙️ Configuration

Key parameters can be adjusted in `A_V2.py`:

```python
# Model Constants
TUNNEL_WIDTH = 4.0              # meters
TUNNEL_HEIGHT = 3.0             # meters
FLOW_RATE_PER_SOURCE = 2.5      # m³/s

# Escape Parameters
ALPHA_WEIGHT = 0.7              # Time cost weight
BETA_WEIGHT = 0.3               # Risk cost weight

# Miner Profiles
MINERS_PROFILES = {
    '矿工1': {
        'speeds': {'dry': 1.5, 'with_flow': 1.0, 'against_flow': 0.5},
        'max_water_height': 0.3,
        'risk_aversion': 2.0
    },
    # Additional miners...
}
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---


## 📧 Contact

For questions or collaboration inquiries:
- Email: guo.zp@outlook.com
- Issues: [GitHub Issues](https://github.com/yourusername/mine-water-inrush-escape/issues)

---

## 🙏 Acknowledgments

- Dataset based on real mine topology from safety management research
- Rolling horizon strategy inspired by operations research literature
- Special thanks to the mine safety research community

---

## 📚 References

Key references from the paper:

1. Zhao, X., et al. (2019). "A dynamic rescue route planning method based on 3D network in mine water inrush hazard." *Geomatics, Natural Hazards and Risk*, 10(1), 2387-2407.

2. Wu, Q., et al. (2020). "Finding the earliest arrival path through a time-varying network for evacuation planning of mine water inrush." *Safety Science*, 130, 104836.

3. An, L., et al. (2025). "Dynamic Escape Path Optimization Model Study Based on Spatio-Temporal Evolution of Coal Mine Water Inrush." *Processes*, 13(11), 3666.

For a complete list of references, please see the [paper](docs/paper.pdf).

---

## 🔄 Version History

- **v1.0** (2025-01) - Initial release
  - Dual-source hydraulic model
  - Rolling horizon A* algorithm
  - Visualization tools
  - Complete dataset

---

## ⚠️ Disclaimer

This software is provided for research and educational purposes only. Real-world mine emergency planning requires professional safety assessment and should not rely solely on computational models. Always consult with certified mine safety engineers and emergency response professionals.

---

**Status**: ✅ Research Complete | 🚀 Code Released | 📊 Dataset Available

Last Updated: February 2025

