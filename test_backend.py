"""
test_backend.py - Comprehensive Unit & API Integration Tests
Tests Flask API routes (/api/health, /api/optimize, /api/simulate, /api/presets),
input validation, error handling, Wi-Fi propagation models, and coverage analytics.
"""

import json
import unittest
import numpy as np
from app import app
import simulation


class TestSmartRouterBackend(unittest.TestCase):

    def setUp(self):
        """Configure test client."""
        app.config['TESTING'] = True
        self.client = app.test_client()

    # --- 1. Health Check Endpoint Tests ---

    def test_health_endpoint(self):
        """GET /api/health should return 200 OK and online status."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get('status'), 'online')
        self.assertIn('message', data)
        self.assertEqual(data.get('version'), '1.0.0')
        self.assertIn('materials', data)
        self.assertIn('thresholds', data)

    # --- 2. Presets Endpoint Tests ---

    def test_presets_list_endpoint(self):
        """GET /api/presets should return all available layout templates."""
        response = self.client.get('/api/presets')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('Studio', data['presets'])
        self.assertIn('1BHK', data['presets'])
        self.assertIn('2BHK', data['presets'])
        self.assertIn('3BHK', data['presets'])
        self.assertIn('open_plan', data['presets'])

    def test_preset_detail_endpoint(self):
        """GET /api/presets/1BHK and /api/presets/Studio should return valid rooms, walls, and dimensions."""
        response = self.client.get('/api/presets/1BHK')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        preset = data.get('preset')
        self.assertIsNotNone(preset)
        self.assertEqual(preset['width'], 12.0)
        self.assertEqual(preset['height'], 9.0)
        self.assertGreater(len(preset['rooms']), 0)
        self.assertGreater(len(preset['walls']), 0)

        # Also verify Studio preset
        res_studio = self.client.get('/api/presets/studio')
        self.assertEqual(res_studio.status_code, 200)
        p_studio = res_studio.get_json().get('preset')
        self.assertEqual(p_studio['width'], 10.0)
        self.assertEqual(p_studio['height'], 7.5)

    def test_preset_not_found(self):
        """GET /api/presets/unknown should return 404."""
        response = self.client.get('/api/presets/nonexistent_layout_xyz')
        self.assertEqual(response.status_code, 404)

    # --- 3. Optimization Endpoint Tests ---

    def test_optimize_valid_payload(self):
        """POST /api/optimize with standard room dimensions should return recommended coordinates."""
        payload = {
            "width": 15.0,
            "height": 10.0,
            "tx_power": 20.0,
            "path_loss_exponent": 2.8,
            "walls": [
                {"x1": 7.5, "y1": 0.0, "x2": 7.5, "y2": 7.0, "material": "brick"}
            ]
        }
        response = self.client.post(
            '/api/optimize',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('recommended_position', data)
        rec = data['recommended_position']
        self.assertIn('x', rec)
        self.assertIn('y', rec)
        # Recommended position must be inside the room
        self.assertTrue(0 <= rec['x'] <= 15.0)
        self.assertTrue(0 <= rec['y'] <= 10.0)
        self.assertIn('expected_good_coverage', data)
        self.assertIn('expected_average_rssi_dbm', data)

    def test_optimize_with_obstacles_and_baseline(self):
        """POST /api/optimize with obstacles and starting router position should calculate improvement."""
        payload = {
            "width": 12.0,
            "height": 8.0,
            "router_position": {"x": 1.0, "y": 1.0},
            "walls": [
                {"x1": 6.0, "y1": 0.0, "x2": 6.0, "y2": 6.0, "material": "concrete"}
            ],
            "obstacles": [
                {"x": 8.0, "y": 3.0, "width": 2.0, "height": 2.0, "material": "metal", "attenuation": 18.0}
            ],
            "tx_power": 22.0
        }
        response = self.client.post(
            '/api/optimize',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('improvement', data)
        self.assertIn('initial_metrics', data)
        self.assertIn('recommended_position', data)

    def test_optimize_invalid_dimensions(self):
        """POST /api/optimize with negative dimensions should return 400 Bad Request."""
        payload = {"width": -5.0, "height": 10.0}
        response = self.client.post(
            '/api/optimize',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data.get('status'), 'error')
        self.assertIn('width', data.get('error', '').lower())

    def test_optimize_invalid_wall_coordinates(self):
        """POST /api/optimize with malformed wall coordinates should return 400 Bad Request."""
        payload = {
            "width": 10.0,
            "height": 10.0,
            "walls": [{"x1": "invalid", "y1": 0, "x2": 5, "y2": 5}]
        }
        response = self.client.post(
            '/api/optimize',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data.get('status'), 'error')

    # --- 4. Simulation Endpoint Tests ---

    def test_simulate_valid_payload(self):
        """POST /api/simulate should return 2D heatmap matrix and coverage stats."""
        payload = {
            "width": 10.0,
            "height": 8.0,
            "resolution": 1.0,
            "router": {"x": 5.0, "y": 4.0, "tx_power": 20.0},
            "walls": [],
            "path_loss_exponent": 2.5
        }
        response = self.client.post(
            '/api/simulate',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('heatmap', data)
        self.assertIn('metrics', data)
        self.assertIn('average_rssi_dbm', data['metrics'])
        self.assertIn('good_coverage_percent', data['metrics'])
        self.assertIn('weak_coverage_percent', data['metrics'])
        self.assertIn('dead_zone_percent', data['metrics'])

    def test_simulate_invalid_resolution(self):
        """POST /api/simulate with negative resolution should return 400 Bad Request."""
        payload = {
            "width": 10.0,
            "height": 8.0,
            "resolution": -1.0
        }
        response = self.client.post(
            '/api/simulate',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    # --- 5. Signal Estimation Physics & Math Tests ---

    def test_signal_decreases_with_distance(self):
        """Signal strength should decrease as distance from the router increases."""
        router = (0.0, 0.0)
        pt_near = (2.0, 0.0)
        pt_far = (10.0, 0.0)

        rssi_near = simulation.calculate_rssi(router, pt_near, tx_power=20.0, path_loss_exponent=2.8)
        rssi_far = simulation.calculate_rssi(router, pt_far, tx_power=20.0, path_loss_exponent=2.8)

        self.assertGreater(rssi_near, rssi_far)

    def test_wall_causes_attenuation(self):
        """A wall in line of sight should reduce the signal compared to free line of sight."""
        router = (0.0, 0.0)
        target = (6.0, 0.0)

        # Free space (no wall)
        rssi_free = simulation.calculate_rssi(router, target, tx_power=20.0, walls=[])

        # With a brick wall intersecting the ray at x=3
        brick_wall = [{"x1": 3.0, "y1": -2.0, "x2": 3.0, "y2": 2.0, "material": "brick"}]
        rssi_walled = simulation.calculate_rssi(router, target, tx_power=20.0, walls=brick_wall)

        # Attenuation of brick is ~8 dB
        self.assertAlmostEqual(rssi_free - rssi_walled, 8.0, delta=0.5)

    def test_obstacle_bounding_box_attenuation(self):
        """A rectangular obstacle in line of sight should attenuate signal."""
        router = (0.0, 0.0)
        target = (8.0, 0.0)

        rssi_free = simulation.calculate_rssi(router, target, tx_power=20.0, obstacles=[])
        obstacle = [{"x": 3.0, "y": -1.0, "width": 2.0, "height": 2.0, "material": "metal", "attenuation": 20.0}]
        rssi_blocked = simulation.calculate_rssi(router, target, tx_power=20.0, obstacles=obstacle)

        self.assertAlmostEqual(rssi_free - rssi_blocked, 20.0, delta=0.5)

    def test_line_intersection_logic(self):
        """Verify 2D ray intersection logic."""
        # Crossing segments
        self.assertTrue(simulation.line_intersection((0, 0), (4, 4), (0, 4), (4, 0)))
        # Parallel non-intersecting segments
        self.assertFalse(simulation.line_intersection((0, 0), (4, 0), (0, 2), (4, 2)))
        # Segments that do not cross
        self.assertFalse(simulation.line_intersection((0, 0), (2, 2), (5, 5), (8, 8)))

    # --- 6. Coverage Analytics Rigorous Tests (Bug Fix Verification) ---

    def test_coverage_percentages_sum_to_100(self):
        """Good, weak, and dead zone coverage categories must strictly sum to ~100%."""
        res = simulation.generate_heatmap(
            width=20.0,
            height=14.0,
            resolution=0.5,
            router={"x": 5.0, "y": 5.0, "tx_power": 20.0},
            walls=[{"x1": 10.0, "y1": 0.0, "x2": 10.0, "y2": 14.0, "material": "concrete"}]
        )
        metrics = res["metrics"]
        total = (
            metrics["good_coverage_percent"] +
            metrics["weak_coverage_percent"] +
            metrics["dead_zone_percent"]
        )
        self.assertAlmostEqual(total, 100.0, delta=0.2)

    def test_dead_zone_is_not_stuck_at_zero(self):
        """A large room with concrete walls and low router power must exhibit non-zero dead zones."""
        res = simulation.generate_heatmap(
            width=25.0,
            height=20.0,
            resolution=0.5,
            router={"x": 1.0, "y": 1.0, "tx_power": 12.0},  # Low power in far corner
            walls=[
                {"x1": 10.0, "y1": 0.0, "x2": 10.0, "y2": 20.0, "material": "concrete"},
                {"x1": 18.0, "y1": 0.0, "x2": 18.0, "y2": 20.0, "material": "concrete"}
            ]
        )
        metrics = res["metrics"]
        self.assertGreater(metrics["dead_zone_percent"], 0.0)
        self.assertLess(metrics["good_coverage_percent"], 100.0)

    def test_moving_router_changes_coverage_percentages(self):
        """Moving router from corner to center must measurably alter good coverage and average signal."""
        # Corner position behind concrete wall
        res_corner = simulation.generate_heatmap(
            width=20.0,
            height=14.0,
            resolution=0.5,
            router={"x": 1.0, "y": 1.0, "tx_power": 20.0},
            walls=[{"x1": 10.0, "y1": 0.0, "x2": 10.0, "y2": 14.0, "material": "concrete"}]
        )
        # Center position
        res_center = simulation.generate_heatmap(
            width=20.0,
            height=14.0,
            resolution=0.5,
            router={"x": 10.0, "y": 7.0, "tx_power": 20.0},
            walls=[{"x1": 10.0, "y1": 0.0, "x2": 10.0, "y2": 14.0, "material": "concrete"}]
        )
        # Average RSSI and coverage must differ
        self.assertNotEqual(
            res_corner["metrics"]["average_rssi_dbm"],
            res_center["metrics"]["average_rssi_dbm"]
        )
        self.assertNotEqual(
            res_corner["metrics"]["good_coverage_percent"],
            res_center["metrics"]["good_coverage_percent"]
        )

    def test_average_signal_matches_grid_mean(self):
        """Reported average RSSI must match the exact mathematical mean of all simulated grid cells."""
        res = simulation.generate_heatmap(
            width=10.0,
            height=10.0,
            resolution=1.0,
            router={"x": 5.0, "y": 5.0, "tx_power": 20.0}
        )
        grid = np.array(res["heatmap"])
        computed_mean = round(float(np.mean(grid)), 2)
        self.assertEqual(res["metrics"]["average_rssi_dbm"], computed_mean)


if __name__ == '__main__':
    unittest.main()
