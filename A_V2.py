import pandas as pd
import numpy as np
import heapq
from collections import defaultdict
import time
import os
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# --- 1. 模型常量与参数定义 ---
TUNNEL_WIDTH = 4.0
TUNNEL_HEIGHT = 3.0
INITIAL_WATER_HEIGHT = 0.1
FLOW_RATE_PER_SOURCE = 1.5  # 单个源点的流量, 0.5 m^3/s

# --- 2. 坡度相关参数 ---
SLOPE_THRESHOLD = 0.02

# --- 3. 文件路径与场景配置 ---
INPUT_FILE = '附件2.xlsx'
OUTPUT_FILE = 'result_A.xlsx'
INFLOW_POINT_A = np.array([4143.12, 4376.28, 6.33])
INFLOW_POINT_B = np.array([5883.14, 5643.35, 40.37])
DELAY_SECONDS = 120

# --- 4. 逃生与再规划参数 ---
INITIAL_ESCAPE_START_TIME_SECONDS = 60.0
REPLANNING_TIME_SECONDS = DELAY_SECONDS + 60.0
ALPHA_WEIGHT = 0.7
BETA_WEIGHT = 0.3

# --- 5. 矿工配置 ---
MINERS_PROFILES = {
    '矿工1': {
        'start_node_id': 'placeholder',
        # 将速度改慢，增加逃生难度，更容易被水追上触发重规划
        'speeds': {'dry': 1.5, 'with_flow': 1.0, 'against_flow': 0.5},
        'max_water_height': 0.3,
        'risk_aversion': 2.0
    },
    '矿工2': {
        'start_node_id': 'placeholder',
        'speeds': {'dry': 1.5, 'with_flow': 1.0, 'against_flow': 0.5},
        'max_water_height': 0.3,
        'risk_aversion': 2.0
    },
    '矿工3': {
        'start_node_id': 'placeholder',
        'speeds': {'dry': 1.5, 'with_flow': 1.0, 'against_flow': 0.5},
        'max_water_height': 0.3,
        'risk_aversion': 2.0
    }
}
EXIT_NODES = []

# --- Matplotlib 中文设置 ---
font_path = 'C:/Windows/Fonts/SimHei.ttf'
my_font = fm.FontProperties(fname=font_path) if os.path.exists(font_path) else fm.FontProperties()

# --- 6. 数据加载与预处理 ---
def load_data_and_build_graph(file_path):
    print("Loading data and building graph...")
    points_df = pd.read_excel(file_path, sheet_name='端点', header=1)
    if 'Unnamed: 0' in points_df.columns:
        points_df = points_df.rename(columns={'Unnamed: 0': '端点编号', 'x (m)': 'x', 'y (m)': 'y', 'z (m)': 'z'})
    else:
        points_df.columns = ['端点编号', 'x', 'y', 'z']
    tunnels_df = pd.read_excel(file_path, sheet_name='巷道', header=0)
    nodes = {row['端点编号']: row[['x', 'y', 'z']].values for _, row in points_df.iterrows()}
    graph = defaultdict(list)
    slope_info = {}
    for _, row in tunnels_df.iterrows():
        u, v = row['巷道端点1'], row['巷道端点2']
        if u not in nodes or v not in nodes: continue
        p1, p2 = nodes[u], nodes[v]
        length = np.linalg.norm(p1 - p2)
        height_diff = p2[2] - p1[2]
        slope = height_diff / length if length > 0 else 0
        key = tuple(sorted((u, v)))
        slope_info[key] = {'length': length, 'height_diff': height_diff, 'slope': slope,
                           'tunnel_id': str(row['巷道编号'])}
        graph[u].append({'to': v, 'length': length, 'key': key, 'slope': slope})
        graph[v].append({'to': u, 'length': length, 'key': key, 'slope': -slope})
    return points_df, tunnels_df, nodes, graph, slope_info


def find_closest_tunnel_and_project_point(nodes, tunnels_df, point):
    min_dist, best_match = float('inf'), None
    for _, row in tunnels_df.iterrows():
        u_id, v_id = row['巷道端点1'], row['巷道端点2']
        if u_id not in nodes or v_id not in nodes: continue
        p_u, p_v = nodes[u_id], nodes[v_id]
        line_vec, point_vec = p_v - p_u, point - p_u
        line_len = np.linalg.norm(line_vec)
        if line_len < 1e-9: continue
        t = np.dot(point_vec, line_vec) / (line_len ** 2)
        t_clamped = max(0, min(1, t))
        dist = np.linalg.norm(point - (p_u + t_clamped * line_vec))
        if dist < min_dist:
            min_dist = dist
            best_match = {'nodes': (u_id, v_id), 'dist_to_u': t_clamped * line_len,
                          'dist_to_v': (1 - t_clamped) * line_len, 'tunnel_id': str(row['巷道编号'])}
    return best_match


# --- 7. 精确水流模拟引擎 ---
def calculate_arrival_times_for_source(nodes, graph, start_info, start_time=0):
    node_arrivals = {node_id: float('inf') for node_id in nodes}
    pq, processed_nodes = [], set()
    start_u, start_v = start_info['nodes']
    base_velocity = (FLOW_RATE_PER_SOURCE / 2.0) / (TUNNEL_WIDTH * INITIAL_WATER_HEIGHT)
    time_to_u = start_info['dist_to_u'] / base_velocity if base_velocity > 0 else float('inf')
    time_to_v = start_info['dist_to_v'] / base_velocity if base_velocity > 0 else float('inf')
    node_arrivals[start_u], node_arrivals[start_v] = start_time + time_to_u, start_time + time_to_v
    heapq.heappush(pq, (start_time + time_to_u, start_u))
    heapq.heappush(pq, (start_time + time_to_v, start_v))
    while pq:
        current_time, current_node = heapq.heappop(pq)
        if current_node in processed_nodes: continue
        processed_nodes.add(current_node)
        for edge in graph[current_node]:
            neighbor = edge['to']
            if neighbor in processed_nodes: continue
            new_arrival_time = current_time + edge['length'] / base_velocity
            if new_arrival_time < node_arrivals[neighbor]:
                node_arrivals[neighbor] = new_arrival_time
                heapq.heappush(pq, (new_arrival_time, neighbor))
    return node_arrivals


def build_gravity_directed_graph(graph):
    directed_graph = defaultdict(list)
    for u, neighbors in graph.items():
        for edge in neighbors:
            if edge['slope'] <= SLOPE_THRESHOLD:
                directed_graph[u].append(edge)
    return directed_graph


def calculate_fill_times(nodes, graph, slope_info, node_arrivals, start_times):
    node_states = {node_id: 'DRY' for node_id in nodes}
    tunnels = {}
    for key, info in slope_info.items():
        base_volume = info['length'] * TUNNEL_WIDTH * (TUNNEL_HEIGHT - INITIAL_WATER_HEIGHT)
        tunnels[key] = {'volume_to_fill': base_volume, 'filled_volume': 0.0, 'inflow': 0.0, 'state': 'DRY',
                        'last_update': 0.0, 'slope': info['slope']}
    pq, event_counter, tunnel_fills, tunnel_flow_source = [], 0, {}, {}
    active_filling_tunnels = set()
    num_active_sources = 0
    for node_id, arrival_time in node_arrivals.items():
        if arrival_time < float('inf'):
            heapq.heappush(pq, (arrival_time, event_counter, 'NODE_WET', {'node_id': node_id}));
            event_counter += 1
    for t in start_times:
        heapq.heappush(pq, (t, event_counter, 'ACTIVATE_SOURCE', {}));
        event_counter += 1

    def get_current_inflow_rate():
        return FLOW_RATE_PER_SOURCE * num_active_sources

    directed_graph = build_gravity_directed_graph(graph)

    def redistribute_flow(time_of_change):
        nonlocal event_counter
        for key in list(active_filling_tunnels):
            tunnel = tunnels[key]
            delta_t = time_of_change - tunnel['last_update']
            if delta_t > 0 and tunnel['inflow'] > 0: tunnel['filled_volume'] += tunnel['inflow'] * delta_t
            tunnel['last_update'] = time_of_change
        priority_tunnels, new_active_set = [], set()
        for u, state in node_states.items():
            if state == 'WET':
                for edge in directed_graph.get(u, []):
                    v, key = edge['to'], edge['key']
                    if node_states.get(v) == 'WET' and tunnels[key]['state'] != 'FILLED':
                        slope = tunnels[key]['slope']
                        priority = 2 if abs(slope) <= SLOPE_THRESHOLD else (1 if slope < -SLOPE_THRESHOLD else 3)
                        priority_tunnels.append((priority, u, key))
        priority_tunnels.sort()
        total_weight, tunnel_weights = 0, {}
        for _, u, key in priority_tunnels:
            if key not in new_active_set:
                if key not in tunnel_flow_source: tunnel_flow_source[key] = u
                weight = 1.0
                tunnel_weights[key] = weight
                total_weight += weight
                new_active_set.add(key)
        active_filling_tunnels.clear()
        active_filling_tunnels.update(new_active_set)
        current_q = get_current_inflow_rate()
        for key in active_filling_tunnels:
            tunnel = tunnels[key]
            tunnel['inflow'] = current_q * (tunnel_weights[key] / total_weight) if total_weight > 0 else 0
            if tunnel['state'] == 'DRY': tunnel['state'] = 'FILLING'
            if tunnel['inflow'] > 1e-9:
                remaining_vol = tunnel['volume_to_fill'] - tunnel['filled_volume']
                if remaining_vol > 0:
                    fill_time = time_of_change + remaining_vol / tunnel['inflow']
                    heapq.heappush(pq, (fill_time, event_counter, 'TUNNEL_FULL', {'key': key}));
                    event_counter += 1

    while pq:
        current_time, _, event_type, data = heapq.heappop(pq)
        if event_type == 'ACTIVATE_SOURCE':
            num_active_sources += 1
            redistribute_flow(current_time)
            continue
        if event_type == 'NODE_WET':
            node_id = data['node_id']
            if node_states[node_id] == 'WET': continue
            node_states[node_id] = 'WET'
            redistribute_flow(current_time)
        elif event_type == 'TUNNEL_FULL':
            key = data['key']
            if tunnels[key]['state'] == 'FILLED': continue
            tunnel = tunnels[key]
            final_vol = tunnel['filled_volume'] + tunnel['inflow'] * (current_time - tunnel['last_update'])
            if final_vol < tunnel['volume_to_fill'] - 1e-6: continue
            tunnels[key]['state'] = 'FILLED'
            tunnel_fills[key] = current_time
            redistribute_flow(current_time)
    return tunnel_fills, tunnel_flow_source


# --- 8. 逃生与再规划模块 ---
def get_water_height_at_time(tunnel_key, current_time, node_arrivals, tunnel_fills):
    p1, p2 = tunnel_key
    t_arrival = min(node_arrivals.get(p1, float('inf')), node_arrivals.get(p2, float('inf')))
    if current_time < t_arrival: return 0.0
    t_fill = tunnel_fills.get(tunnel_key, float('inf'))
    if current_time >= t_fill: return TUNNEL_HEIGHT
    fill_duration = t_fill - t_arrival
    if fill_duration <= 1e-6: return TUNNEL_HEIGHT
    return min(TUNNEL_HEIGHT, ((current_time - t_arrival) / fill_duration) * (
            TUNNEL_HEIGHT - INITIAL_WATER_HEIGHT) + INITIAL_WATER_HEIGHT)


def find_escape_route(miner_profile, graph, points_df, node_arrivals, tunnel_fills, tunnel_flow_source,
                      escape_start_time, record_iteration=False):
    start_node, speeds, max_h, risk_aversion = miner_profile['start_node_id'], miner_profile['speeds'], miner_profile[
        'max_water_height'], miner_profile['risk_aversion']
    point_coords_map = {row['端点编号']: row[['x', 'y', 'z']].values for _, row in points_df.iterrows()}
    exit_coords = [point_coords_map[node] for node in EXIT_NODES]
    pq, visited, iteration_costs = [(0, 0, escape_start_time, start_node, [(start_node, escape_start_time)])], {}, []
    while pq:
        _, g_cost, current_time, current_node, path = heapq.heappop(pq)
        if current_node in EXIT_NODES:
            return (path, g_cost, current_time, iteration_costs) if record_iteration else (path, g_cost, current_time)
        if visited.get(current_node, float('inf')) <= g_cost: continue
        visited[current_node] = g_cost
        if record_iteration: iteration_costs.append(g_cost)
        for edge in graph[current_node]:
            neighbor, key, length = edge['to'], edge['key'], edge['length']
            water_h = get_water_height_at_time(key, current_time + (length / speeds['dry']) / 2, node_arrivals,
                                               tunnel_fills)
            if water_h > max_h: continue
            speed = speeds['dry']
            if water_h > 0: speed = speeds['with_flow'] if tunnel_flow_source.get(key) == current_node else speeds[
                'against_flow']
            travel_time = length / speed
            gen_cost = ALPHA_WEIGHT * travel_time + BETA_WEIGHT * ((water_h / max_h) ** risk_aversion)
            new_g_cost = g_cost + gen_cost
            h_dist = min([np.linalg.norm(point_coords_map[neighbor] - ec) for ec in exit_coords])
            h_cost = ALPHA_WEIGHT * (h_dist / speeds['dry'])
            new_path = path + [(neighbor, current_time + travel_time)]
            heapq.heappush(pq, (new_g_cost + h_cost, new_g_cost, current_time + travel_time, neighbor, new_path))
    return (None, -1, -1, iteration_costs) if record_iteration else (None, -1, -1)


def find_miner_position_at_time(initial_path, target_time):
    path_traveled = [initial_path[0]]
    for i in range(len(initial_path) - 1):
        start_node, start_time = initial_path[i]
        end_node, end_time = initial_path[i + 1]
        if end_time >= target_time:
            return start_node, start_time, path_traveled
        path_traveled.append(initial_path[i + 1])
    return initial_path[-1][0], initial_path[-1][1], path_traveled


def execute_escape_with_rolling_replanning(miner_profile, initial_planned_path, graph, points_df,
                                           node_arrivals, tunnel_fills, tunnel_flow_source):
    """
    执行滚动时域逃生模拟，并记录路径和重规划点。
    返回: (完整路径列表, 总耗时, 重规划次数, 重规划发生的位置列表)
    """
    # 1. 初始化状态
    current_node, current_time = initial_planned_path[0]
    planned_path = initial_planned_path
    full_path_traveled = [(current_node, current_time)]
    replanning_count = 0

    # [新增] 用于记录触发重规划的坐标点（用于后续绘图）
    replanning_points = []

    path_idx = 0

    # 2. 模拟行进循环
    while current_node not in EXIT_NODES:
        # 异常处理：如果路径走完了但还没到出口（例如路径中断或需要最后一步引导）
        if path_idx >= len(planned_path) - 1:
            profile_for_replan = {**miner_profile, 'start_node_id': current_node}
            # 尝试原地重规划
            planned_path, _, _, _ = find_escape_route(profile_for_replan, graph, points_df, node_arrivals, tunnel_fills,
                                                      tunnel_flow_source, current_time, record_iteration=True)

            if not planned_path or len(planned_path) <= 1:
                return None, -1, replanning_count, replanning_points  # 失败返回

            # 记录重规划
            replanning_count += 1
            replanning_points.append(current_node)  # [记录点]

            path_idx = 0
            continue

        # 获取当前计划路段信息
        start_node, _ = planned_path[path_idx]
        next_node, _ = planned_path[path_idx + 1]

        # 在图中查找边信息
        edge_details = next((edge for edge in graph[start_node] if edge['to'] == next_node), None)
        if not edge_details:
            return None, -1, replanning_count, replanning_points

        tunnel_key, length = edge_details['key'], edge_details['length']

        # 3. 安全性预测：预测到达路段中点时的水位
        # 假设以旱地速度行进一半路程所需的时间
        estimated_arrival_mid = current_time + (length / miner_profile['speeds']['dry']) / 2
        water_height = get_water_height_at_time(tunnel_key, estimated_arrival_mid, node_arrivals, tunnel_fills)

        # --- 核心判断：是否触发重规划 ---
        if water_height > miner_profile['max_water_height']:
            print(
                f" - [警报] 路径失效! t={current_time:.1f}s, 从 {start_node}->{next_node} 预期水位超标。触发滚动再规划...")

            # [关键步骤] 记录重规划发生的位置
            replanning_points.append(current_node)
            replanning_count += 1

            # 执行重规划 A* 搜索
            profile_for_replan = {**miner_profile, 'start_node_id': current_node}
            new_path, _, _, _ = find_escape_route(profile_for_replan, graph, points_df, node_arrivals, tunnel_fills,
                                                  tunnel_flow_source, current_time, record_iteration=True)

            # 处理重规划结果
            if not new_path or len(new_path) <= 1:
                print(f" - [失败] 再规划失败! 在{current_node}处已无安全路径。")
                return None, -1, replanning_count, replanning_points

            # 更新路径并重置索引，立即按新路径执行
            planned_path = new_path
            path_idx = 0
            continue  # 跳过本次移动逻辑，重新评估新路径的第一步

        # --- 4. 正常行进逻辑 (如果路径安全) ---
        speed = miner_profile['speeds']['dry']
        # 如果有水但未超限，根据流向调整速度
        if water_height > 0:
            if tunnel_flow_source.get(tunnel_key) == start_node:
                speed = miner_profile['speeds']['with_flow']
            else:
                speed = miner_profile['speeds']['against_flow']

        travel_time = length / speed
        current_time += travel_time
        current_node = next_node

        full_path_traveled.append((current_node, current_time))
        path_idx += 1

    return full_path_traveled, current_time, replanning_count, replanning_points

# --- 9. 全新绘图函数 (2x3 Grid, 18pt font, 2:1 Ratio) ---
def plot_final_dashboard(points_df, tunnels_df, escape_results, all_costs_log):
    print("\n--- Generating Final 2x3 Dashboard (2:1 Ratio, Large Font) ---")

    # 2:1 Ratio -> Width 30, Height 15 (30 / 15 = 2.0)
    fig, axes = plt.subplots(2, 3, figsize=(30, 12))

    # Configuration - Increased Font Size
    FONT_SIZE = 26
    TITLE_SIZE = 28

    miners = ['矿工1', '矿工2', '矿工3']
    miners_display = {'矿工1': 'Miner 1', '矿工2': 'Miner 2', '矿工3': 'Miner 3'}
    colors = {'矿工1': 'red', '矿工2': 'blue', '矿工3': 'green'}

    coords_map = points_df.set_index('端点编号').to_dict('index')

    tunnel_segments = []
    for _, tunnel in tunnels_df.iterrows():
        node1_id, node2_id = tunnel['巷道端点1'], tunnel['巷道端点2']
        if node1_id in coords_map and node2_id in coords_map:
            p1, p2 = coords_map[node1_id], coords_map[node2_id]
            tunnel_segments.append(([p1['x'], p2['x']], [p1['y'], p2['y']]))

    # --- TOP ROW: Escape Routes ---
    for i, miner_key in enumerate(miners):
        ax = axes[0, i]
        color = colors[miner_key]
        miner_name_eng = miners_display.get(miner_key, miner_key)

        # 1. Background Tunnels
        for seg_x, seg_y in tunnel_segments:
            ax.plot(seg_x, seg_y, color='#D3D3D3', linewidth=0.8, zorder=1)

        # 2. Path & Markers
        miner_result = escape_results[escape_results['矿工'] == miner_key]

        if not miner_result.empty and miner_result.iloc[0]['是否成功逃生'] == '是':
            row = miner_result.iloc[0]
            path_str = row['最终逃生路径']
            path_nodes = [node for node in path_str.split(' -> ')]
            path_x = [coords_map[node]['x'] for node in path_nodes]
            path_y = [coords_map[node]['y'] for node in path_nodes]

            # Line
            ax.plot(path_x, path_y, color=color, linewidth=2.5, label='Escape Path', zorder=2)
            # Start (Circle)
            ax.scatter(path_x[0], path_y[0], color=color, s=120, marker='o', edgecolors='black', label='Start',
                       zorder=3)
            # Exit (X)
            ax.scatter(path_x[-1], path_y[-1], color=color, s=180, marker='X', edgecolors='black', label='Exit',
                       zorder=3)

        # 3. Styling (Top Row)
        ax.set_title(f"{miner_name_eng} Escape Route", fontsize=TITLE_SIZE)
        ax.set_xlabel("X Coordinate (m)", fontsize=FONT_SIZE)
        ax.set_ylabel("Y Coordinate (m)", fontsize=FONT_SIZE)
        ax.set_xlim(2000, 8000)
        ax.set_ylim(3500, 7000)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.tick_params(axis='both', which='major', labelsize=FONT_SIZE)
        ax.legend(fontsize=FONT_SIZE, loc='lower right')

    # --- BOTTOM ROW: Optimization Process ---
    for i, miner_key in enumerate(miners):
        ax = axes[1, i]
        color = colors[miner_key]
        miner_name_eng = miners_display.get(miner_key, miner_key)
        costs_log = all_costs_log.get(miner_key, [])

        # 1. Plot Curve
        if costs_log:
            ax.plot(range(len(costs_log)), costs_log, marker='.', color=color, linewidth=2.0)

        # 2. Styling (Bottom Row)
        ax.set_title(f"{miner_name_eng} Optimization Process", fontsize=TITLE_SIZE)
        ax.set_xlabel("Iteration Step", fontsize=FONT_SIZE)
        ax.set_ylabel("Path Cost (Generalized)", fontsize=FONT_SIZE)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.tick_params(axis='both', which='major', labelsize=FONT_SIZE)

    plt.tight_layout()
    plot_filename = 'Q4_Final_Dashboard_2to1.png'
    plot_filename_eps = 'Q4_Final_Dashboard_2to1.eps'
    plt.savefig(plot_filename_eps, format='eps', bbox_inches='tight')
    print(f"Final Dashboard saved as '{plot_filename_eps}'")
    plt.close()


def plot_trajectory_comparison(points_df, tunnels_df, rolling_result, dk_path_nodes, miner_name="Miner 1"):
    """
    绘制 Rolling A* 与 D-K 算法的路径对比图，包含重规划点标注。
    (增强版：修复了 'P' 前缀导致的匹配失败问题，并增加了调试信息)
    """
    print(f"\n--- Generating Trajectory Comparison for {miner_name} ---")

    # 1. 准备画布
    fig, ax = plt.subplots(figsize=(12, 10))

    # --- [关键修复] 构建一个兼容的坐标映射表 ---
    # 同时支持 "P0351" (str) 和 351 (int)
    coords_map = {}
    for _, row in points_df.iterrows():
        nid = row['端点编号']
        coords_map[nid] = {'x': row['x'], 'y': row['y']}  # 原始 ID
        coords_map[str(nid)] = {'x': row['x'], 'y': row['y']}  # 字符串版 "351"
        if isinstance(nid, int):
            coords_map[f"P{nid:04d}"] = {'x': row['x'], 'y': row['y']}  # 补全版 "P0351"
        if isinstance(nid, str) and nid.startswith('P'):
            # 尝试去掉 P 存一份整数版
            try:
                coords_map[int(nid[1:])] = {'x': row['x'], 'y': row['y']}
            except:
                pass
    # --------------------------------------------------------

    # 2. 绘制背景巷道 (灰色)
    print("Plotting background tunnels...")
    for _, tunnel in tunnels_df.iterrows():
        u, v = tunnel['巷道端点1'], tunnel['巷道端点2']
        # 尝试匹配端点
        p1 = coords_map.get(u) or coords_map.get(str(u))
        p2 = coords_map.get(v) or coords_map.get(str(v))

        if p1 and p2:
            ax.plot([p1['x'], p2['x']], [p1['y'], p2['y']],
                    color='#E0E0E0', linewidth=0.8, zorder=1)  # 浅灰色背景

    # 3. 绘制 D-K 路径 (蓝色虚线)
    if dk_path_nodes:
        dk_x, dk_y = [], []
        found_count = 0
        for n in dk_path_nodes:
            # 尝试多种键值查找
            pt = coords_map.get(n) or coords_map.get(str(n))
            if not pt and isinstance(n, str) and n.startswith('P'):
                # 尝试去掉 'P' 查找
                try:
                    pt = coords_map.get(int(n[1:]))
                except:
                    pass

            if pt:
                dk_x.append(pt['x'])
                dk_y.append(pt['y'])
                found_count += 1
            else:
                pass  # print(f"Warning: Node {n} not found in map")

        print(f"D-K Path: Plotting {found_count}/{len(dk_path_nodes)} nodes.")

        if found_count > 0:
            # [视觉优化] 加宽线宽，并稍微错开一点点，防止完全重合
            ax.plot(dk_x, dk_y, color='blue', linestyle='--', linewidth=3.5, alpha=0.8,
                    label='D-K Algorithm (Benchmark)', zorder=2)
        else:
            print("[Error] D-K path nodes were provided but could not be mapped to coordinates!")

    # 4. 绘制 Rolling A* 路径 (红色实线)
    if rolling_result:
        rolling_path_nodes = [p[0] for p in rolling_result['详细路径']]
        ra_x, ra_y = [], []
        for n in rolling_path_nodes:
            pt = coords_map.get(n) or coords_map.get(str(n))
            if not pt and isinstance(n, str) and n.startswith('P'):
                try:
                    pt = coords_map.get(int(n[1:]))
                except:
                    pass
            if pt:
                ra_x.append(pt['x'])
                ra_y.append(pt['y'])

        if ra_x:
            print(f"Rolling A* Path: Plotting {len(ra_x)} nodes.")
            # [视觉优化] 红色实线比蓝色细一点点，zorder更高，确保叠在上面
            ax.plot(ra_x, ra_y, color='red', linestyle='-', linewidth=2.5, alpha=0.9,
                    label='Rolling A* (Proposed)', zorder=3)

            # 绘制起点和终点
            ax.scatter(ra_x[0], ra_y[0], s=150, c='green', marker='o', edgecolors='black', label='Start', zorder=4)
            ax.scatter(ra_x[-1], ra_y[-1], s=200, c='gold', marker='*', edgecolors='black', label='Exit', zorder=4)

        # 5. 标注重规划点 (关键步骤)
        replan_nodes = rolling_result.get('重规划点列表', [])
        if replan_nodes:
            r_node = replan_nodes[0]
            pt = coords_map.get(r_node) or coords_map.get(str(r_node))
            if not pt and isinstance(r_node, str) and r_node.startswith('P'):
                try:
                    pt = coords_map.get(int(r_node[1:]))
                except:
                    pass

            if pt:
                rx, ry = pt['x'], pt['y']
                ax.scatter(rx, ry, s=300, c='yellow', marker='^', edgecolors='black', zorder=5)
                ax.annotate('Replanning Point\n(Decision Divergence)',
                            xy=(rx, ry),
                            xytext=(rx + 400, ry + 400),
                            fontsize=12, fontweight='bold', color='black',
                            arrowprops=dict(facecolor='black', shrink=0.05, width=1))

    # 6. 图表美化
    ax.set_title(f"Trajectory Comparison: Rolling A* vs D-K ({miner_name})", fontsize=18, pad=15)
    ax.set_xlabel("X Coordinate (m)")
    ax.set_ylabel("Y Coordinate (m)")
    ax.legend(loc='best', fontsize=12, frameon=True, shadow=True)
    ax.grid(True, linestyle=':', alpha=0.6)

    # 保存图片
    filename = f'Comparison_{miner_name}.png'
    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    print(f"Comparison plot saved as '{filename}'")
    # plt.show() # 如果不需要弹出窗口可注释掉


# ==============================================================================
#                                  主 函 数
# ==============================================================================
if __name__ == '__main__':
    start_time_total = time.time()

    # 1. 加载数据与构建图
    print(">>> [Step 1] Loading Data & Building Graph...")
    points_df, tunnels_df, nodes, graph, slope_info = load_data_and_build_graph(INPUT_FILE)

    # 2. 定义坐标与寻找最近节点
    exit_coords = [(6336.99, 6073.22, 36.15), (6416.05, 6579.88, 8.69)]
    miner_coords = [(4395.15, 4614.53, 6.59), (3398.34, 5965.56, 1.31), (3879.44, 4125.47, 6.22)]


    def find_closest_node(coord, df):
        coords = np.array(df[['x', 'y', 'z']].values)
        return df.iloc[np.argmin(np.linalg.norm(coords - np.array(coord), axis=1))]['端点编号']


    EXIT_NODES.extend([find_closest_node(c, points_df) for c in exit_coords])
    for i, c in enumerate(miner_coords):
        MINERS_PROFILES[f'矿工{i + 1}']['start_node_id'] = find_closest_node(c, points_df)

    # --- [修改点] 3. 读取 D-K 算法的基准路径 (从 result_DK.xlsx 文件) ---
    print(">>> Loading D-K Benchmark Paths from 'result_DK.xlsx'...")
    DK_PATHS_DATA = {}
    dk_file_path = 'result_DK.xlsx'

    if os.path.exists(dk_file_path):
        try:
            # 读取 Excel 文件
            df_dk = pd.read_excel(dk_file_path)

            # 检查列名是否存在
            if '矿工' in df_dk.columns and '最终逃生路径' in df_dk.columns:
                # 遍历每一行，提取矿工名和路径字符串
                for _, row in df_dk.iterrows():
                    m_name = row['矿工']
                    path_str = row['最终逃生路径']

                    if isinstance(path_str, str):
                        # 将 "P0351 -> P0349..." 分割并去空格转为列表
                        path_list = [p.strip() for p in path_str.split('->')]
                        DK_PATHS_DATA[m_name] = path_list
                print(f"成功加载 D-K 路径: {list(DK_PATHS_DATA.keys())}")
            else:
                print(f"[Error] {dk_file_path} 文件中缺少 '矿工' 或 '最终逃生路径' 列。")
        except Exception as e:
            print(f"[Error] 读取 {dk_file_path} 失败: {e}")
            print("将不显示蓝色对比线。")
    else:
        print(f"[Warning] 未找到 {dk_file_path} 文件。将不显示蓝色对比线。")

    # --- Step 1 & 2: 双源水流演化模拟 ---
    print("\n>>> [Step 2] Running Water Simulation (Dual Source)...")
    # 源点 A (T=0)
    start_info_A = find_closest_tunnel_and_project_point(nodes, tunnels_df, INFLOW_POINT_A)
    node_arrivals_A = calculate_arrival_times_for_source(nodes, graph, start_info_A)
    fills_A, flow_A = calculate_fill_times(nodes, graph, slope_info, node_arrivals_A, start_times=[0])

    # 源点 B (T=DELAY)
    start_info_B = find_closest_tunnel_and_project_point(nodes, tunnels_df, INFLOW_POINT_B)
    node_arrivals_B = calculate_arrival_times_for_source(nodes, graph, start_info_B, start_time=DELAY_SECONDS)

    # 合并双源数据
    merged_arrivals = {node: min(node_arrivals_A.get(node, float('inf')), node_arrivals_B.get(node, float('inf'))) for
                       node in nodes}
    fills_dual, flow_dual = calculate_fill_times(nodes, graph, slope_info, merged_arrivals,
                                                 start_times=[0, DELAY_SECONDS])

    # 初始路径规划 (基于 T=0 状态)
    initial_paths = {}
    for miner, profile in MINERS_PROFILES.items():
        path, _, _, _ = find_escape_route(profile, graph, points_df, node_arrivals_A, fills_A, flow_A,
                                          INITIAL_ESCAPE_START_TIME_SECONDS, record_iteration=True)
        initial_paths[miner] = path

    # --- Step 3: 真实的动态滚动规划 (True Rolling Horizon) ---
    # [修正] 注意：这段代码必须在上面的循环结束后执行，不能缩进在上面的循环里
    print("\n>>> [Step 3] Executing True Rolling Horizon Strategy...")
    final_results, all_costs_log = [], {}

    for miner, profile in MINERS_PROFILES.items():
        # 1. 获取初始路径 (仅基于水源 A 生成的路径，它不知道水源 B 的存在)
        initial_path = initial_paths.get(miner)

        if not initial_path:
            final_results.append({'矿工': miner, '是否成功逃生': '否', '详细路径': None})
            continue

        print(f"  > {miner} 开始动态逃生模拟...")

        # 2. 直接传入初始路径 (initial_path)
        # 让矿工沿着“旧认知”走，撞到“新环境”
        final_path_segments, final_arrival_time, replan_count, replan_points = execute_escape_with_rolling_replanning(
            profile,
            initial_path,  # <--- 传入旧路径（包含潜在危险）
            graph, points_df,
            merged_arrivals,  # <--- 传入真实环境（双源，包含陷阱）
            fills_dual,
            flow_dual
        )

        # 3. 保存结果
        if final_path_segments:
            # 这里的 final_path_segments 已经是包含 T=0 到 T=end 的完整路径了
            total_time_min = round((final_arrival_time - INITIAL_ESCAPE_START_TIME_SECONDS) / 60.0, 2)

            result_entry = {
                '矿工': miner,
                '是否成功逃生': '是',
                '最终出口': final_path_segments[-1][0],
                '总耗时(分钟)': total_time_min,
                '最终逃生路径': ' -> '.join([p[0] for p in final_path_segments]),
                '详细路径': final_path_segments,
                '滚动再规划次数': replan_count,
                '重规划点列表': replan_points
            }
            final_results.append(result_entry)
            print(f"    [成功] 触发重规划 {replan_count} 次，生成黄色三角形: {'是' if replan_points else '否'}")

            # 4. 绘图 (从上面读取的 DK_PATHS_DATA 中获取对应矿工的路径)
            dk_path_list = DK_PATHS_DATA.get(miner, [])
            try:
                plot_trajectory_comparison(points_df, tunnels_df, result_entry, dk_path_list, miner_name=miner)
            except Exception as e:
                print(f"    [绘图失败] {e}")

        else:
            final_results.append({'矿工': miner, '是否成功逃生': '否', '详细路径': None})
            print(f"    [失败] 矿工在途中被困。")

    print(f"\nDone! Total time: {time.time() - start_time_total:.2f}s.")