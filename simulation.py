"""
simulation.py - Wi-Fi Signal Estimation & Router Placement Optimization

Physics Model:
1. Log-Distance Path Loss (LDPL) Model:
   RSSI(d) = P_tx - [PL_0 + 10 * n * log10(d / d_0)] - Total_Wall_Loss - Total_Obstacle_Loss
   where:
   - P_tx is the router transmit power in dBm (e.g. 20 dBm)
   - PL_0 is the reference path loss at d_0 = 1 meter (~40.0 dB for 2.4 GHz, ~47.0 dB for 5 GHz)
   - n is the path-loss exponent (2.0 = free space, 2.5 - 3.5 = residential indoor, 4.0+ = dense concrete)
   - d is Euclidean distance in meters, clamped to d >= 1.0m to avoid log(0) singularity
   - Total_Wall_Loss is the cumulative attenuation of intersected walls, doors, and windows
   - Total_Obstacle_Loss is attenuation from furniture, appliances, or architectural columns

2. Coverage Categories (Standard Wi-Fi Engineering):
   - Excellent:  RSSI >= -50 dBm
   - Good:       -60 dBm <= RSSI < -50 dBm
   - Fair:       -67 dBm <= RSSI < -60 dBm
   - Weak:       -75 dBm <= RSSI < -67 dBm
   - Very Weak:  -85 dBm <= RSSI < -75 dBm
   - Dead Zone:  RSSI < -85 dBm

   Aggregated Metrics:
   - Good Coverage: RSSI >= -67 dBm (Excellent + Good + Fair; standard voice/video benchmark)
   - Weak Coverage: -85 dBm <= RSSI < -67 dBm (Weak + Very Weak)
   - Dead Zone:     RSSI < -85 dBm
   These categories partition 100% of valid floor-plan cells without overlap.
"""

import math
import numpy as np

# Reference Path Loss at 1.0 meter (d0 = 1.0m)
# For 2.4 GHz: 20*log10(2400) + 20*log10(0.001) + 32.44 ~= 40.04 dB
DEFAULT_PL_0 = 40.0

# Material Attenuation in dB (2.4 GHz standard indoor empirical values)
DEFAULT_ATTENUATION = {
    'drywall': 3.0,
    'wood': 4.0,
    'glass': 2.5,
    'brick': 8.0,
    'concrete': 14.0,
    'metal': 20.0,
    'furniture': 4.5,
    'appliance': 12.0,
    'door_wood': 3.0,
    'door_open': 0.5,
    'window_glass': 2.5
}

# Signal Quality Thresholds in dBm
THRESHOLDS = {
    'excellent': -50.0,
    'good': -60.0,
    'fair': -67.0,
    'weak': -75.0,
    'very_weak': -85.0
}


def line_intersection_point(p1, p2, p3, p4):
    """
    Computes the 2D intersection point between segments p1-p2 and p3-p4 if they intersect.
    Returns (True, (ix, iy)) if intersecting, otherwise (False, None).
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if abs(denom) < 1e-9:
        return False, None

    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom

    if (0.0 <= ua <= 1.0) and (0.0 <= ub <= 1.0):
        ix = x1 + ua * (x2 - x1)
        iy = y1 + ua * (y2 - y1)
        return True, (ix, iy)

    return False, None


def line_intersection(p1, p2, p3, p4):
    """Boolean helper checking if line segment p1-p2 intersects p3-p4."""
    intersects, _ = line_intersection_point(p1, p2, p3, p4)
    return intersects


def point_in_box(px, py, box):
    """Checks if point (px, py) is strictly inside a rectangular box."""
    bx = float(box['x'])
    by = float(box['y'])
    bw = float(box['width'])
    bh = float(box['height'])
    return (bx <= px <= bx + bw) and (by <= py <= by + bh)


def segment_intersects_box(p1, p2, box):
    """Checks if line segment p1-p2 intersects or passes through a rectangular box."""
    bx = float(box['x'])
    by = float(box['y'])
    bw = float(box['width'])
    bh = float(box['height'])

    if point_in_box(p1[0], p1[1], box) or point_in_box(p2[0], p2[1], box):
        return True

    b_corners = [
        ((bx, by), (bx + bw, by)),
        ((bx + bw, by), (bx + bw, by + bh)),
        ((bx + bw, by + bh), (bx, by + bh)),
        ((bx, by + bh), (bx, by))
    ]

    for edge_p1, edge_p2 in b_corners:
        if line_intersection(p1, p2, edge_p1, edge_p2):
            return True

    return False


def get_barrier_attenuation(barrier):
    """Returns the attenuation in dB for a wall, door, or window."""
    if 'attenuation' in barrier and barrier['attenuation'] is not None:
        try:
            return max(0.0, float(barrier['attenuation']))
        except (ValueError, TypeError):
            pass
    mat = str(barrier.get('material', 'brick')).lower()
    return DEFAULT_ATTENUATION.get(mat, 6.0)


def calculate_rssi(router_pos, target_point, tx_power=20.0, path_loss_exponent=2.8, walls=None, obstacles=None, reference_loss=DEFAULT_PL_0):
    """
    Calculates Received Signal Strength Indicator (RSSI) in dBm at target_point.
    
    Formula:
      RSSI(d) = P_tx - [PL_0 + 10 * n * log10(d)] - Sum(Wall_Losses) - Sum(Obstacle_Losses)
    """
    if walls is None:
        walls = []
    if obstacles is None:
        obstacles = []

    dx = target_point[0] - router_pos[0]
    dy = target_point[1] - router_pos[1]
    dist = math.sqrt(dx * dx + dy * dy)

    # Reference distance d0 = 1.0 meter
    d = max(dist, 1.0)

    # Physical Log-Distance Path Loss
    pl_0 = float(reference_loss)
    distance_loss = pl_0 + 10.0 * float(path_loss_exponent) * math.log10(d)

    # Wall penetration losses with de-duplication for shared endpoints/corners
    wall_loss = 0.0
    detected_intersections = []

    for wall in walls:
        p1 = (float(wall['x1']), float(wall['y1']))
        p2 = (float(wall['x2']), float(wall['y2']))
        intersects, ipt = line_intersection_point(router_pos, target_point, p1, p2)
        if intersects and ipt is not None:
            # Check if this intersection point is within 5cm of an already-counted intersection
            is_dup = False
            for prev_pt in detected_intersections:
                if math.hypot(ipt[0] - prev_pt[0], ipt[1] - prev_pt[1]) < 0.05:
                    is_dup = True
                    break
            if not is_dup:
                detected_intersections.append(ipt)
                wall_loss += get_barrier_attenuation(wall)

    # Obstacle losses (furniture, appliances, columns)
    obstacle_loss = 0.0
    for obs in obstacles:
        if 'width' in obs and 'height' in obs:
            if segment_intersects_box(router_pos, target_point, obs):
                obstacle_loss += get_barrier_attenuation(obs)
        elif 'x1' in obs and 'y1' in obs and 'x2' in obs and 'y2' in obs:
            p1 = (float(obs['x1']), float(obs['y1']))
            p2 = (float(obs['x2']), float(obs['y2']))
            if line_intersection(router_pos, target_point, p1, p2):
                obstacle_loss += get_barrier_attenuation(obs)

    rssi = float(tx_power) - distance_loss - wall_loss - obstacle_loss

    # Realistic physical limits [-100 dBm, 30 dBm]
    rssi = max(-100.0, min(30.0, rssi))
    return round(float(rssi), 2)


def compute_coverage_metrics(signal_array, thresholds=None):
    """
    Computes consistent, non-overlapping coverage analytics from an array of simulated RSSI values.
    Ensures that all coverage tiers sum to 100.0% (+- 0.1% rounding).
    """
    if thresholds is None:
        thresholds = THRESHOLDS

    arr = np.asarray(signal_array, dtype=float).flatten()
    total_cells = len(arr)
    if total_cells == 0:
        return {
            "average_rssi_dbm": -100.0,
            "good_coverage_percent": 0.0,
            "weak_coverage_percent": 0.0,
            "dead_zone_percent": 100.0,
            "breakdown": {
                "excellent": 0.0, "good": 0.0, "fair": 0.0,
                "weak": 0.0, "very_weak": 0.0, "dead_zone": 100.0
            }
        }

    th_exc = float(thresholds.get('excellent', -50.0))
    th_good = float(thresholds.get('good', -60.0))
    th_fair = float(thresholds.get('fair', -67.0))
    th_weak = float(thresholds.get('weak', -75.0))
    th_vweak = float(thresholds.get('very_weak', -85.0))

    # Detailed non-overlapping tiers
    c_exc = np.sum(arr >= th_exc)
    c_good = np.sum((arr >= th_good) & (arr < th_exc))
    c_fair = np.sum((arr >= th_fair) & (arr < th_good))
    c_weak = np.sum((arr >= th_weak) & (arr < th_fair))
    c_vweak = np.sum((arr >= th_vweak) & (arr < th_weak))
    c_dead = np.sum(arr < th_vweak)

    pct_exc = round(float(c_exc / total_cells * 100.0), 1)
    pct_good = round(float(c_good / total_cells * 100.0), 1)
    pct_fair = round(float(c_fair / total_cells * 100.0), 1)
    pct_weak = round(float(c_weak / total_cells * 100.0), 1)
    pct_vweak = round(float(c_vweak / total_cells * 100.0), 1)
    pct_dead = round(float(c_dead / total_cells * 100.0), 1)

    # Primary Dashboard Categories:
    # 1. Good Coverage (RSSI >= th_fair, standard >= -67 dBm)
    # 2. Weak Coverage (th_vweak <= RSSI < th_fair, -85 to -67 dBm)
    # 3. Dead Zone (RSSI < th_vweak, < -85 dBm)
    good_total_cells = c_exc + c_good + c_fair
    weak_total_cells = c_weak + c_vweak
    dead_total_cells = c_dead

    good_pct = round(float(good_total_cells / total_cells * 100.0), 1)
    weak_pct = round(float(weak_total_cells / total_cells * 100.0), 1)
    dead_pct = round(float(dead_total_cells / total_cells * 100.0), 1)

    return {
        "average_rssi_dbm": round(float(np.mean(arr)), 2),
        "good_coverage_percent": good_pct,
        "weak_coverage_percent": weak_pct,
        "dead_zone_percent": dead_pct,
        "min_rssi_dbm": round(float(np.min(arr)), 2),
        "max_rssi_dbm": round(float(np.max(arr)), 2),
        "total_cells_evaluated": total_cells,
        "breakdown": {
            "excellent": pct_exc,
            "good": pct_good,
            "fair": pct_fair,
            "weak": pct_weak,
            "very_weak": pct_vweak,
            "dead_zone": pct_dead
        }
    }


def generate_heatmap(width, height, resolution=0.5, router=None, walls=None, obstacles=None, path_loss_exponent=2.8, reference_loss=DEFAULT_PL_0, thresholds=None):
    """
    Computes a 2D matrix of RSSI values across the floor plan grid using NumPy.
    Returns grid coordinates, 2D heatmap matrix, and summary coverage metrics.
    """
    width = float(width)
    height = float(height)

    if router is None:
        router = {'x': width / 2.0, 'y': height / 2.0, 'tx_power': 20.0}
    if walls is None:
        walls = []
    if obstacles is None:
        obstacles = []

    router_pos = (float(router.get('x', width / 2.0)), float(router.get('y', height / 2.0)))
    tx_power = float(router.get('tx_power', 20.0))
    res = max(0.1, min(2.0, float(resolution)))

    xs = np.arange(0.0, width + res * 0.5, res)
    ys = np.arange(0.0, height + res * 0.5, res)

    # Pre-allocate 2D array
    grid = np.zeros((len(ys), len(xs)), dtype=float)

    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            grid[i, j] = calculate_rssi(
                router_pos=router_pos,
                target_point=(float(x), float(y)),
                tx_power=tx_power,
                path_loss_exponent=path_loss_exponent,
                walls=walls,
                obstacles=obstacles,
                reference_loss=reference_loss
            )

    metrics = compute_coverage_metrics(grid, thresholds=thresholds)

    return {
        "xs": [round(float(x), 2) for x in xs],
        "ys": [round(float(y), 2) for y in ys],
        "heatmap": grid.tolist(),
        "metrics": metrics,
        "thresholds": thresholds or THRESHOLDS
    }


def find_optimal_placement(width, height, walls=None, obstacles=None, router_position=None, tx_power=20.0, path_loss_exponent=2.8, reference_loss=DEFAULT_PL_0):
    """
    Searches for the optimal router placement that maximizes good coverage (>= -67 dBm)
    and minimizes dead zones (< -85 dBm) across the floor plan.

    If router_position is provided, calculates baseline metrics and net improvements.
    """
    if walls is None:
        walls = []
    if obstacles is None:
        obstacles = []

    width = float(width)
    height = float(height)
    tx_power = float(tx_power)
    path_loss_exponent = float(path_loss_exponent)

    # Candidate search grid (adaptive step)
    area = width * height
    cand_step = 1.0 if area <= 300 else (1.5 if area <= 600 else 2.0)
    cand_xs = np.arange(cand_step * 0.5, width, cand_step)
    cand_ys = np.arange(cand_step * 0.5, height, cand_step)

    # Sample evaluation grid across the room
    eval_step = 1.0 if area <= 300 else (1.5 if area <= 600 else 2.0)
    eval_xs = np.arange(eval_step * 0.5, width, eval_step)
    eval_ys = np.arange(eval_step * 0.5, height, eval_step)
    eval_points = [(float(x), float(y)) for y in eval_ys for x in eval_xs]

    # Baseline evaluation if starting router position is provided
    initial_metrics = None
    if router_position and 'x' in router_position and 'y' in router_position:
        init_pos = (float(router_position['x']), float(router_position['y']))
        init_signals = np.array([
            calculate_rssi(init_pos, pt, tx_power, path_loss_exponent, walls, obstacles, reference_loss)
            for pt in eval_points
        ])
        initial_metrics = compute_coverage_metrics(init_signals)
        initial_metrics["position"] = {"x": round(init_pos[0], 2), "y": round(init_pos[1], 2)}

    best_score = -1e9
    best_pos = (round(width / 2.0, 2), round(height / 2.0, 2))
    best_metrics = None

    for cx in cand_xs:
        for cy in cand_ys:
            cand_pos = (float(cx), float(cy))

            # Skip candidate if placed inside an obstacle
            inside_obs = False
            for obs in obstacles:
                if 'width' in obs and 'height' in obs and point_in_box(cx, cy, obs):
                    inside_obs = True
                    break
            if inside_obs:
                continue

            signals = np.array([
                calculate_rssi(cand_pos, pt, tx_power, path_loss_exponent, walls, obstacles, reference_loss)
                for pt in eval_points
            ])

            cand_metrics = compute_coverage_metrics(signals)
            good_pct = cand_metrics["good_coverage_percent"]
            dead_pct = cand_metrics["dead_zone_percent"]
            avg_rssi = cand_metrics["average_rssi_dbm"]

            # Fitness Score:
            # - Heavily rewards good coverage (+2.0x)
            # - Heavily penalizes dead zones (-3.0x)
            # - Moderately rewards higher average signal strength (+0.5x)
            score = (good_pct * 2.0) - (dead_pct * 3.0) + (avg_rssi * 0.5)

            if score > best_score:
                best_score = score
                best_pos = (round(float(cx), 2), round(float(cy), 2))
                best_metrics = cand_metrics

    if best_metrics is None:
        best_metrics = {
            "good_coverage_percent": 0.0,
            "weak_coverage_percent": 0.0,
            "dead_zone_percent": 100.0,
            "average_rssi_dbm": -100.0
        }

    # Generate human-friendly recommendation explanation
    summary_text = (
        f"Optimal position identified at ({best_pos[0]}m, {best_pos[1]}m). "
        f"Projected Good Coverage: {best_metrics['good_coverage_percent']}%, "
        f"Dead Zones: {best_metrics['dead_zone_percent']}%, "
        f"Average Signal: {best_metrics['average_rssi_dbm']} dBm."
    )

    response = {
        "status": "success",
        "recommended_position": {
            "x": best_pos[0],
            "y": best_pos[1]
        },
        "expected_good_coverage": best_metrics["good_coverage_percent"],
        "expected_weak_coverage": best_metrics.get("weak_coverage_percent", 0.0),
        "expected_dead_zone_percent": best_metrics["dead_zone_percent"],
        "expected_average_rssi_dbm": best_metrics["average_rssi_dbm"],
        "evaluated_candidates_count": len(cand_xs) * len(cand_ys),
        "summary": summary_text
    }

    if initial_metrics:
        coverage_gain = round(best_metrics["good_coverage_percent"] - initial_metrics["good_coverage_percent"], 1)
        dead_reduction = round(initial_metrics["dead_zone_percent"] - best_metrics["dead_zone_percent"], 1)
        rssi_gain = round(best_metrics["average_rssi_dbm"] - initial_metrics["average_rssi_dbm"], 2)

        response["initial_metrics"] = initial_metrics
        response["improvement"] = {
            "good_coverage_gain_percent": coverage_gain,
            "dead_zone_reduction_percent": max(0.0, dead_reduction),
            "average_rssi_gain_dbm": rssi_gain
        }

    return response


# Preset Floor Plan Templates
PRESETS = {
    "Studio": {
        "name": "Studio Compact Apartment",
        "width": 10.0,
        "height": 7.5,
        "suggested_router": {"x": 5.0, "y": 3.75},
        "rooms": [
            {"name": "Living & Bedroom", "x": 0.0, "y": 0.0, "width": 6.0, "height": 7.5},
            {"name": "Kitchenette", "x": 6.0, "y": 0.0, "width": 4.0, "height": 4.0},
            {"name": "Bathroom", "x": 6.0, "y": 4.0, "width": 4.0, "height": 3.5}
        ],
        "walls": [
            {"x1": 6.0, "y1": 0.0, "x2": 6.0, "y2": 7.5, "material": "brick"},
            {"x1": 6.0, "y1": 4.0, "x2": 10.0, "y2": 4.0, "material": "drywall"}
        ],
        "doors": [
            {"x1": 6.0, "y1": 2.0, "x2": 6.0, "y2": 3.0, "material": "door_open"},
            {"x1": 6.0, "y1": 5.25, "x2": 6.0, "y2": 6.25, "material": "door_wood"}
        ]
    },
    "1BHK": {
        "name": "1 BHK Apartment",
        "width": 12.0,
        "height": 9.0,
        "suggested_router": {"x": 5.5, "y": 4.5},
        "rooms": [
            {"name": "Living Room", "x": 0.0, "y": 0.0, "width": 6.5, "height": 5.0},
            {"name": "Bedroom", "x": 6.5, "y": 0.0, "width": 5.5, "height": 5.0},
            {"name": "Kitchen", "x": 0.0, "y": 5.0, "width": 5.0, "height": 4.0},
            {"name": "Bathroom", "x": 5.0, "y": 5.0, "width": 3.0, "height": 4.0},
            {"name": "Balcony", "x": 8.0, "y": 5.0, "width": 4.0, "height": 4.0}
        ],
        "walls": [
            # Main bedroom partition
            {"x1": 6.5, "y1": 0.0, "x2": 6.5, "y2": 5.0, "material": "brick"},
            # Kitchen & bath partition
            {"x1": 0.0, "y1": 5.0, "x2": 8.0, "y2": 5.0, "material": "brick"},
            {"x1": 5.0, "y1": 5.0, "x2": 5.0, "y2": 9.0, "material": "drywall"},
            {"x1": 8.0, "y1": 5.0, "x2": 8.0, "y2": 9.0, "material": "glass"}
        ],
        "doors": [
            {"x1": 6.5, "y1": 2.5, "x2": 6.5, "y2": 3.5, "material": "door_wood"}
        ]
    },
    "2BHK": {
        "name": "2 BHK Family Apartment",
        "width": 16.0,
        "height": 11.0,
        "suggested_router": {"x": 8.0, "y": 5.5},
        "rooms": [
            {"name": "Living & Dining", "x": 0.0, "y": 0.0, "width": 8.5, "height": 6.0},
            {"name": "Master Bedroom", "x": 8.5, "y": 0.0, "width": 7.5, "height": 6.0},
            {"name": "Bedroom 2", "x": 8.5, "y": 6.0, "width": 7.5, "height": 5.0},
            {"name": "Kitchen", "x": 0.0, "y": 6.0, "width": 5.0, "height": 5.0},
            {"name": "Bathroom 1", "x": 5.0, "y": 6.0, "width": 3.5, "height": 2.5},
            {"name": "Bathroom 2", "x": 5.0, "y": 8.5, "width": 3.5, "height": 2.5}
        ],
        "walls": [
            # Master bedroom wall
            {"x1": 8.5, "y1": 0.0, "x2": 8.5, "y2": 11.0, "material": "concrete"},
            # Horizontal split
            {"x1": 0.0, "y1": 6.0, "x2": 16.0, "y2": 6.0, "material": "brick"},
            {"x1": 5.0, "y1": 6.0, "x2": 5.0, "y2": 11.0, "material": "drywall"},
            {"x1": 5.0, "y1": 8.5, "x2": 8.5, "y2": 8.5, "material": "drywall"}
        ],
        "doors": [
            {"x1": 8.5, "y1": 2.5, "x2": 8.5, "y2": 3.5, "material": "door_wood"},
            {"x1": 8.5, "y1": 7.5, "x2": 8.5, "y2": 8.5, "material": "door_wood"}
        ]
    },
    "3BHK": {
        "name": "3 BHK Spacious Home",
        "width": 20.0,
        "height": 14.0,
        "suggested_router": {"x": 10.0, "y": 6.5},
        "rooms": [
            {"name": "Grand Living Room", "x": 0.0, "y": 0.0, "width": 9.0, "height": 7.0},
            {"name": "Dining & Foyer", "x": 0.0, "y": 7.0, "width": 9.0, "height": 7.0},
            {"name": "Master Suite", "x": 9.0, "y": 0.0, "width": 11.0, "height": 5.0},
            {"name": "Bedroom 2", "x": 9.0, "y": 5.0, "width": 6.5, "height": 5.0},
            {"name": "Bedroom 3", "x": 9.0, "y": 10.0, "width": 6.5, "height": 4.0},
            {"name": "Kitchen & Pantry", "x": 15.5, "y": 5.0, "width": 4.5, "height": 4.5},
            {"name": "Balcony Deck", "x": 15.5, "y": 9.5, "width": 4.5, "height": 4.5}
        ],
        "walls": [
            {"x1": 9.0, "y1": 0.0, "x2": 9.0, "y2": 14.0, "material": "concrete"},
            {"x1": 9.0, "y1": 5.0, "x2": 20.0, "y2": 5.0, "material": "brick"},
            {"x1": 9.0, "y1": 10.0, "x2": 15.5, "y2": 10.0, "material": "brick"},
            {"x1": 15.5, "y1": 5.0, "x2": 15.5, "y2": 14.0, "material": "drywall"},
            {"x1": 0.0, "y1": 7.0, "x2": 9.0, "y2": 7.0, "material": "wood"}
        ],
        "doors": [
            {"x1": 9.0, "y1": 2.0, "x2": 9.0, "y2": 3.0, "material": "door_wood"},
            {"x1": 9.0, "y1": 7.5, "x2": 9.0, "y2": 8.5, "material": "door_wood"}
        ]
    },
    "4BHK": {
        "name": "4 BHK Luxury Residence",
        "width": 24.0,
        "height": 16.0,
        "suggested_router": {"x": 12.0, "y": 8.0},
        "rooms": [
            {"name": "Formal Living", "x": 0.0, "y": 0.0, "width": 10.0, "height": 8.0},
            {"name": "Dining & Kitchen", "x": 0.0, "y": 8.0, "width": 10.0, "height": 8.0},
            {"name": "Master Suite", "x": 10.0, "y": 0.0, "width": 8.0, "height": 7.0},
            {"name": "Guest Suite", "x": 18.0, "y": 0.0, "width": 6.0, "height": 7.0},
            {"name": "Bedroom 3", "x": 10.0, "y": 7.0, "width": 7.0, "height": 5.0},
            {"name": "Bedroom 4", "x": 10.0, "y": 12.0, "width": 7.0, "height": 4.0},
            {"name": "Home Office / Gym", "x": 17.0, "y": 7.0, "width": 7.0, "height": 9.0}
        ],
        "walls": [
            {"x1": 10.0, "y1": 0.0, "x2": 10.0, "y2": 16.0, "material": "concrete"},
            {"x1": 17.0, "y1": 7.0, "x2": 17.0, "y2": 16.0, "material": "brick"},
            {"x1": 18.0, "y1": 0.0, "x2": 18.0, "y2": 7.0, "material": "brick"},
            {"x1": 10.0, "y1": 7.0, "x2": 24.0, "y2": 7.0, "material": "concrete"},
            {"x1": 10.0, "y1": 12.0, "x2": 17.0, "y2": 12.0, "material": "drywall"},
            {"x1": 0.0, "y1": 8.0, "x2": 10.0, "y2": 8.0, "material": "brick"}
        ],
        "doors": [
            {"x1": 10.0, "y1": 3.5, "x2": 10.0, "y2": 4.5, "material": "door_wood"},
            {"x1": 10.0, "y1": 9.0, "x2": 10.0, "y2": 10.0, "material": "door_wood"}
        ]
    },
    "open_plan": {
        "name": "Open Floor Plan Studio",
        "width": 18.0,
        "height": 12.0,
        "suggested_router": {"x": 9.0, "y": 6.0},
        "rooms": [
            {"name": "Open Work / Lounge Area", "x": 0.0, "y": 0.0, "width": 18.0, "height": 8.0},
            {"name": "Glass Conference Room", "x": 0.0, "y": 8.0, "width": 8.0, "height": 4.0},
            {"name": "Kitchenette & Restrooms", "x": 8.0, "y": 8.0, "width": 10.0, "height": 4.0}
        ],
        "walls": [
            {"x1": 0.0, "y1": 8.0, "x2": 8.0, "y2": 8.0, "material": "glass"},
            {"x1": 8.0, "y1": 8.0, "x2": 8.0, "y2": 12.0, "material": "glass"},
            {"x1": 8.0, "y1": 8.0, "x2": 18.0, "y2": 8.0, "material": "drywall"}
        ],
        "doors": [
            {"x1": 4.0, "y1": 8.0, "x2": 5.0, "y2": 8.0, "material": "door_wood"}
        ]
    }
}


def get_preset_layout(preset_key):
    """Retrieves a deep copy of a preset floor plan."""
    key = str(preset_key).strip().lower()
    mapping = {
        "studio": "Studio",
        "1bhk": "1BHK",
        "2bhk": "2BHK",
        "3bhk": "3BHK",
        "4bhk": "4BHK",
        "open": "open_plan",
        "open_plan": "open_plan",
        "open floor plan": "open_plan"
    }
    if key not in mapping:
        raise KeyError(f"Preset '{preset_key}' not found.")
    actual_key = mapping[key]
    import copy
    return copy.deepcopy(PRESETS[actual_key])
