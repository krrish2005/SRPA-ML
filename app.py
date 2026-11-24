
from flask import Flask, jsonify, render_template, request
import json, os
from simulation import get_preset_layout, PRESETS, DEFAULT_ATTENUATION, THRESHOLDS, DEFAULT_PL_0
from ml_engine import load_model, predict_heatmap, optimize_placement

try:
    ML_MODEL = load_model()
    ML_MODEL_ERROR = None
except FileNotFoundError as exc:
    ML_MODEL = None
    ML_MODEL_ERROR = str(exc)

app = Flask(__name__)


def validate_number(value, field_name, min_val=None, max_val=None, default=None):
 
    if value is None:
        if default is not None:
            return default
        raise ValueError(f"Missing required numeric field: '{field_name}'")

    try:
        num = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Field '{field_name}' must be a valid number, got {repr(value)}")

    if min_val is not None and num < min_val:
        raise ValueError(f"Field '{field_name}' cannot be less than {min_val}, got {num}")

    if max_val is not None and num > max_val:
        raise ValueError(f"Field '{field_name}' cannot exceed {max_val}, got {num}")

    return num


def validate_walls_list(walls):
    """Validates that walls is a list of coordinate dictionaries."""
    if walls is None:
        return []
    if not isinstance(walls, list):
        raise ValueError("'walls' must be a list of wall segment objects.")

    validated = []
    for idx, w in enumerate(walls):
        if not isinstance(w, dict):
            raise ValueError(f"Wall at index {idx} must be an object/dictionary.")

        for coord in ['x1', 'y1', 'x2', 'y2']:
            if coord not in w:
                raise ValueError(f"Wall at index {idx} is missing coordinate '{coord}'.")
            try:
                float(w[coord])
            except (ValueError, TypeError):
                raise ValueError(f"Wall at index {idx} coordinate '{coord}' must be numeric.")

        wall_entry = {
            'x1': float(w['x1']),
            'y1': float(w['y1']),
            'x2': float(w['x2']),
            'y2': float(w['y2']),
            'material': str(w.get('material', 'brick'))
        }
        if 'attenuation' in w and w['attenuation'] is not None:
            try:
                wall_entry['attenuation'] = float(w['attenuation'])
            except (ValueError, TypeError):
                pass
        validated.append(wall_entry)

    return validated


def validate_obstacles_list(obstacles):
    """Validates that obstacles is a list of bounding boxes or segments."""
    if obstacles is None:
        return []
    if not isinstance(obstacles, list):
        raise ValueError("'obstacles' must be a list of obstacle objects.")

    validated = []
    for idx, obs in enumerate(obstacles):
        if not isinstance(obs, dict):
            raise ValueError(f"Obstacle at index {idx} must be an object/dictionary.")

        if 'width' in obs and 'height' in obs:
            for field in ['x', 'y', 'width', 'height']:
                if field not in obs:
                    raise ValueError(f"Obstacle at index {idx} is missing '{field}'.")
                try:
                    float(obs[field])
                except (ValueError, TypeError):
                    raise ValueError(f"Obstacle at index {idx} field '{field}' must be numeric.")

            validated.append({
                'x': float(obs['x']),
                'y': float(obs['y']),
                'width': max(0.1, float(obs['width'])),
                'height': max(0.1, float(obs['height'])),
                'material': str(obs.get('material', 'furniture')),
                'attenuation': float(obs['attenuation']) if 'attenuation' in obs and obs['attenuation'] is not None else None
            })
        elif 'x1' in obs and 'y1' in obs and 'x2' in obs and 'y2' in obs:
            validated.append({
                'x1': float(obs['x1']),
                'y1': float(obs['y1']),
                'x2': float(obs['x2']),
                'y2': float(obs['y2']),
                'material': str(obs.get('material', 'furniture')),
                'attenuation': float(obs['attenuation']) if 'attenuation' in obs and obs['attenuation'] is not None else None
            })
        else:
            raise ValueError(f"Obstacle at index {idx} must provide either (x, y, width, height) or (x1, y1, x2, y2).")

    return validated


@app.route('/')
def index():
    """Renders the main interactive dashboard."""
    return render_template('index.html')


@app.route('/api/health', methods=['GET'])
def health():
    """
    Health check endpoint confirming that the backend API is active.
    Returns:
        JSON confirmation with status, API version, and supported materials.
    """
    return jsonify({
        "status": "online",
        "message": "Smart Router Placement Advisor Backend is active.",
        "ml_model_loaded": ML_MODEL is not None,
        "ml_model_type": "Best regressor selected by model comparison" if ML_MODEL is not None else None,
        "version": "1.0.0",
        "materials": list(DEFAULT_ATTENUATION.keys()),
        "thresholds": THRESHOLDS,
        "presets": list(PRESETS.keys())
    }), 200


@app.route('/api/model-comparison', methods=['GET'])
def model_comparison():
    """Return the saved hold-out comparison report for teacher/demo review."""
    report_path = os.path.join(os.path.dirname(__file__), 'models', 'model_comparison.json')
    if not os.path.exists(report_path):
        return jsonify({"status": "error", "error": "Comparison report missing. Run python train_model.py"}), 404
    with open(report_path, 'r', encoding='utf-8') as handle:
        return jsonify({"status": "success", "comparison": json.load(handle)}), 200


@app.route('/api/presets', methods=['GET'])
def get_presets():
    """Returns a list of all available floor plan presets and their high-level metadata."""
    summary = {}
    for key, data in PRESETS.items():
        summary[key] = {
            "name": data["name"],
            "width": data["width"],
            "height": data["height"],
            "room_count": len(data.get("rooms", [])),
            "wall_count": len(data.get("walls", []))
        }
    return jsonify({"status": "success", "presets": summary}), 200


@app.route('/api/presets/<preset_name>', methods=['GET'])
def get_preset(preset_name):
    """Returns the full layout structure for a specific preset (rooms, walls, suggested router)."""
    try:
        preset_data = get_preset_layout(preset_name)
        return jsonify({"status": "success", "preset": preset_data}), 200
    except KeyError:
        return jsonify({"status": "error", "error": f"Preset '{preset_name}' not found."}), 404


@app.route('/api/optimize', methods=['POST'])
def optimize():
    """
    Finds the optimal router coordinates given room dimensions, walls, and obstacles.
    """
    if not request.is_json and request.data:
        return jsonify({
            "status": "error",
            "error": "Invalid request: Content-Type must be 'application/json'"
        }), 400

    data = request.get_json(silent=True) or {}

    try:
        width = validate_number(data.get('width'), 'width', min_val=1.0, max_val=200.0, default=20.0)
        height = validate_number(data.get('height'), 'height', min_val=1.0, max_val=200.0, default=14.0)
        tx_power = validate_number(data.get('tx_power'), 'tx_power', min_val=5.0, max_val=35.0, default=20.0)
        path_loss_exponent = validate_number(
            data.get('path_loss_exponent'), 'path_loss_exponent', min_val=1.5, max_val=5.0, default=2.8
        )
        reference_loss = validate_number(
            data.get('reference_loss'), 'reference_loss', min_val=20.0, max_val=60.0, default=DEFAULT_PL_0
        )

        walls = validate_walls_list(data.get('walls'))
        obstacles = validate_obstacles_list(data.get('obstacles'))

        router_position = data.get('router_position') or data.get('router')
        if router_position:
            if not isinstance(router_position, dict) or 'x' not in router_position or 'y' not in router_position:
                raise ValueError("'router_position' must be an object with 'x' and 'y' coordinates.")
            router_position = {
                'x': float(router_position['x']),
                'y': float(router_position['y'])
            }

        if ML_MODEL is None:
            return jsonify({"status": "error", "error": "ML model is not trained. Run: python train_model.py"}), 503
        result = optimize_placement(
            model=ML_MODEL,
            width=width,
            height=height,
            walls=walls,
            obstacles=obstacles,
            router_position=router_position,
            tx_power=tx_power,
            path_loss_exponent=path_loss_exponent,
            reference_loss=reference_loss
        )
        return jsonify(result), 200

    except ValueError as ve:
        return jsonify({
            "status": "error",
            "error": str(ve)
        }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": f"Internal computation error: {str(e)}"
        }), 500


@app.route('/api/simulate', methods=['POST'])
def simulate():
    """
    Computes a 2D RSSI Wi-Fi signal heatmap matrix across the floor plan.
    """
    if not request.is_json and request.data:
        return jsonify({
            "status": "error",
            "error": "Invalid request: Content-Type must be 'application/json'"
        }), 400

    data = request.get_json(silent=True) or {}

    try:
        width = validate_number(data.get('width'), 'width', min_val=1.0, max_val=200.0, default=20.0)
        height = validate_number(data.get('height'), 'height', min_val=1.0, max_val=200.0, default=14.0)
        resolution = validate_number(data.get('resolution'), 'resolution', min_val=0.1, max_val=2.0, default=0.5)
        path_loss_exponent = validate_number(
            data.get('path_loss_exponent'), 'path_loss_exponent', min_val=1.5, max_val=5.0, default=2.8
        )
        reference_loss = validate_number(
            data.get('reference_loss'), 'reference_loss', min_val=20.0, max_val=60.0, default=DEFAULT_PL_0
        )

        router_raw = data.get('router') or {'x': width / 2.0, 'y': height / 2.0, 'tx_power': 20.0}
        if not isinstance(router_raw, dict):
            raise ValueError("'router' must be an object with 'x' and 'y'.")

        router = {
            'x': float(router_raw.get('x', width / 2.0)),
            'y': float(router_raw.get('y', height / 2.0)),
            'tx_power': validate_number(router_raw.get('tx_power'), 'router.tx_power', min_val=5.0, max_val=35.0, default=20.0)
        }

        walls = validate_walls_list(data.get('walls'))
        obstacles = validate_obstacles_list(data.get('obstacles'))
        thresholds = data.get('thresholds')

        if ML_MODEL is None:
            return jsonify({"status": "error", "error": "ML model is not trained. Run: python train_model.py"}), 503
        result = predict_heatmap(
            model=ML_MODEL,
            width=width,
            height=height,
            resolution=resolution,
            router=router,
            walls=walls,
            obstacles=obstacles,
            path_loss_exponent=path_loss_exponent,
            reference_loss=reference_loss,
            thresholds=thresholds
        )
        return jsonify(result), 200

    except ValueError as ve:
        return jsonify({
            "status": "error",
            "error": str(ve)
        }), 400
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": f"Internal simulation error: {str(e)}"
        }), 500


@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/'):
        return jsonify({"status": "error", "error": "Endpoint not found"}), 404
    return "Page Not Found", 404


@app.errorhandler(405)
def method_not_allowed_error(error):
    if request.path.startswith('/api/'):
        return jsonify({"status": "error", "error": f"HTTP method '{request.method}' not allowed on this endpoint"}), 405
    return "Method Not Allowed", 405


if __name__ == '__main__':
    print("==================================================")
    print("📡 Smart Router Placement Advisor Backend Starting")
    print("Local URL: http://127.0.0.1:5000")
    print("==================================================")
    app.run(debug=True, host='127.0.0.1', port=5000)
