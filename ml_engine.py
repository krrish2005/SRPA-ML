
"""ML inference engine for Smart Router Placement Advisor.

At runtime, RSSI is predicted by a trained RandomForestRegressor. Geometry helpers
only calculate distances/intersections and barrier features; they do not calculate RSSI.
"""
import os
import math
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "best_rssi_regressor.joblib")
FEATURE_NAMES = [
    "distance_m", "dx_m", "dy_m", "tx_power", "path_loss_exponent",
    "reference_loss", "wall_loss_feature", "obstacle_loss_feature",
    "wall_crossings", "obstacle_crossings", "room_width", "room_height",
    "target_x_norm", "target_y_norm", "router_x_norm", "router_y_norm"
]
ATTENUATION = {
    "drywall": 3.0, "wood": 4.0, "glass": 2.5, "brick": 8.0,
    "concrete": 14.0, "metal": 20.0, "furniture": 4.5,
    "appliance": 12.0, "door_wood": 3.0, "door_open": 0.5,
    "window_glass": 2.5
}

def _loss(item):
    try:
        if item.get("attenuation") is not None:
            return max(0.0, float(item["attenuation"]))
    except (TypeError, ValueError):
        pass
    return ATTENUATION.get(str(item.get("material", "brick")).lower(), 6.0)

def _intersection(a, b, c, d):
    x1,y1=a; x2,y2=b; x3,y3=c; x4,y4=d
    den=(y4-y3)*(x2-x1)-(x4-x3)*(y2-y1)
    if abs(den)<1e-9: return False, None
    ua=((x4-x3)*(y1-y3)-(y4-y3)*(x1-x3))/den
    ub=((x2-x1)*(y1-y3)-(y2-y1)*(x1-x3))/den
    if 0 <= ua <= 1 and 0 <= ub <= 1:
        return True, (x1+ua*(x2-x1), y1+ua*(y2-y1))
    return False, None

def _segment_box(a,b,o):
    x,y,w,h=map(float,(o["x"],o["y"],o["width"],o["height"]))
    if x <= a[0] <= x+w and y <= a[1] <= y+h: return True
    if x <= b[0] <= x+w and y <= b[1] <= y+h: return True
    corners=[((x,y),(x+w,y)),((x+w,y),(x+w,y+h)),
             ((x+w,y+h),(x,y+h)),((x,y+h),(x,y))]
    return any(_intersection(a,b,c,d)[0] for c,d in corners)

def build_features(width, height, router, target, tx_power=20.0,
                   path_loss_exponent=2.8, reference_loss=40.0,
                   walls=None, obstacles=None):
    walls=walls or []; obstacles=obstacles or []
    rx,ry=float(router["x"]),float(router["y"])
    tx,ty=float(target[0]),float(target[1])
    dx,dy=tx-rx,ty-ry
    distance=math.hypot(dx,dy)
    wall_loss=0.0; wall_hits=[]
    for wall in walls:
        hit,pt=_intersection((rx,ry),(tx,ty),
            (float(wall["x1"]),float(wall["y1"])),
            (float(wall["x2"]),float(wall["y2"])))
        if hit and pt is not None and all(math.hypot(pt[0]-q[0],pt[1]-q[1]) >= .05 for q in wall_hits):
            wall_hits.append(pt); wall_loss += _loss(wall)
    obs_loss=0.0; obs_hits=0
    for obs in obstacles:
        hit=False
        if "width" in obs and "height" in obs:
            hit=_segment_box((rx,ry),(tx,ty),obs)
        elif all(k in obs for k in ("x1","y1","x2","y2")):
            hit=_intersection((rx,ry),(tx,ty),(float(obs["x1"]),float(obs["y1"])),
                              (float(obs["x2"]),float(obs["y2"])))[0]
        if hit:
            obs_hits += 1; obs_loss += _loss(obs)
    return [
        distance, dx, dy, float(tx_power), float(path_loss_exponent),
        float(reference_loss), wall_loss, obs_loss, len(wall_hits), obs_hits,
        float(width), float(height), tx/max(float(width),.01), ty/max(float(height),.01),
        rx/max(float(width),.01), ry/max(float(height),.01)
    ]

def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError("Best ML regression model not found. Run: python train_model.py")
    return joblib.load(MODEL_PATH)

def predict_rssi(model, width, height, router, target, tx_power=20.0,
                 path_loss_exponent=2.8, reference_loss=40.0,
                 walls=None, obstacles=None):
    features=build_features(width,height,router,target,tx_power,path_loss_exponent,
                            reference_loss,walls,obstacles)
    pred=float(model.predict(np.asarray([features],dtype=float))[0])
    return round(max(-100.0,min(30.0,pred)),2)

def predict_heatmap(model, width, height, resolution=.5, router=None, walls=None,
                    obstacles=None, path_loss_exponent=2.8, reference_loss=40.0,
                    thresholds=None):
    width=float(width); height=float(height)
    router=router or {"x":width/2,"y":height/2,"tx_power":20}
    resolution=max(.1,min(2.,float(resolution)))
    xs=np.arange(0,width+resolution*.5,resolution)
    ys=np.arange(0,height+resolution*.5,resolution)
    pts=[(float(x),float(y)) for y in ys for x in xs]
    features=[build_features(width,height,router,p,router.get("tx_power",20),
        path_loss_exponent,reference_loss,walls,obstacles) for p in pts]
    values=model.predict(np.asarray(features,dtype=float)).reshape(len(ys),len(xs))
    values=np.clip(values,-100,30)
    th=thresholds or {"excellent":-50,"good":-60,"fair":-67,"weak":-75,"very_weak":-85}
    flat=values.ravel()
    total=max(1,len(flat))
    good=float(np.mean(flat >= float(th.get("fair",-67)))*100)
    weak=float(np.mean((flat >= float(th.get("very_weak",-85))) & (flat < float(th.get("fair",-67))))*100)
    dead=max(0.,100.-good-weak)
    metrics={
        "average_rssi_dbm":round(float(np.mean(flat)),2),
        "good_coverage_percent":round(good,1),
        "weak_coverage_percent":round(weak,1),
        "dead_zone_percent":round(dead,1),
        "min_rssi_dbm":round(float(np.min(flat)),2),
        "max_rssi_dbm":round(float(np.max(flat)),2),
        "total_cells_evaluated":int(total),
        "breakdown":{
            "excellent":round(float(np.mean(flat>=float(th.get("excellent",-50)))*100),1),
            "good":round(float(np.mean((flat>=float(th.get("good",-60)))&(flat<float(th.get("excellent",-50))))*100),1),
            "fair":round(float(np.mean((flat>=float(th.get("fair",-67)))&(flat<float(th.get("good",-60))))*100),1),
            "weak":round(float(np.mean((flat>=float(th.get("weak",-75)))&(flat<float(th.get("fair",-67))))*100),1),
            "very_weak":round(float(np.mean((flat>=float(th.get("very_weak",-85)))&(flat<float(th.get("weak",-75))))*100),1),
            "dead_zone":round(float(np.mean(flat<float(th.get("very_weak",-85)))*100),1)
        }
    }
    return {"xs":[round(float(v),2) for v in xs],"ys":[round(float(v),2) for v in ys],
            "heatmap":values.round(2).tolist(),"metrics":metrics,"thresholds":th}

def optimize_placement(model,width,height,walls=None,obstacles=None,router_position=None,
                       tx_power=20.,path_loss_exponent=2.8,reference_loss=40.):
    width=float(width); height=float(height); walls=walls or []; obstacles=obstacles or []
    area=width*height
    step=1.0 if area<=300 else (1.5 if area<=600 else 2.0)
    xs=np.arange(step*.5,width,step); ys=np.arange(step*.5,height,step)
    eval_step=step
    ex=np.arange(eval_step*.5,width,eval_step); ey=np.arange(eval_step*.5,height,eval_step)
    points=[(float(x),float(y)) for y in ey for x in ex]
    if not points: points=[(width/2,height/2)]
    def evaluate(pos):
        features=[build_features(width,height,{"x":pos[0],"y":pos[1]},p,tx_power,
            path_loss_exponent,reference_loss,walls,obstacles) for p in points]
        vals=np.clip(model.predict(np.asarray(features,dtype=float)),-100,30)
        good=float(np.mean(vals>=-67)*100); dead=float(np.mean(vals< -85)*100)
        avg=float(np.mean(vals))
        return {"good_coverage_percent":round(good,1),
                "weak_coverage_percent":round(max(0,100-good-dead),1),
                "dead_zone_percent":round(dead,1),"average_rssi_dbm":round(avg,2)}
    initial=None
    if router_position and "x" in router_position and "y" in router_position:
        initial=evaluate((float(router_position["x"]),float(router_position["y"])))
        initial["position"]={"x":float(router_position["x"]),"y":float(router_position["y"])}
    candidates=[(float(x),float(y)) for x in xs for y in ys]
    if not candidates: candidates=[(width/2,height/2)]
    best=None; best_score=-1e9; best_metrics=None
    for pos in candidates:
        if any("width" in o and "height" in o and
               float(o["x"])<=pos[0]<=float(o["x"])+float(o["width"]) and
               float(o["y"])<=pos[1]<=float(o["y"])+float(o["height"]) for o in obstacles):
            continue
        metrics=evaluate(pos)
        score=2*metrics["good_coverage_percent"]-3*metrics["dead_zone_percent"]+.5*metrics["average_rssi_dbm"]
        if score>best_score: best_score=score; best=pos; best_metrics=metrics
    if best is None: best=(width/2,height/2); best_metrics=evaluate(best)
    result={"status":"success","recommended_position":{"x":round(best[0],2),"y":round(best[1],2)},
        "expected_good_coverage":best_metrics["good_coverage_percent"],
        "expected_weak_coverage":best_metrics["weak_coverage_percent"],
        "expected_dead_zone_percent":best_metrics["dead_zone_percent"],
        "expected_average_rssi_dbm":best_metrics["average_rssi_dbm"],
        "evaluated_candidates_count":len(candidates),
        "summary":f"ML model recommends ({best[0]:.2f}m, {best[1]:.2f}m). Predicted good coverage: {best_metrics['good_coverage_percent']}%, dead zones: {best_metrics['dead_zone_percent']}%, average RSSI: {best_metrics['average_rssi_dbm']} dBm.",
        "model_type":"RandomForestRegressor"}
    if initial:
        result["initial_metrics"]=initial
        result["improvement"]={
            "good_coverage_gain_percent":round(best_metrics["good_coverage_percent"]-initial["good_coverage_percent"],1),
            "dead_zone_reduction_percent":round(max(0,initial["dead_zone_percent"]-best_metrics["dead_zone_percent"]),1),
            "average_rssi_gain_dbm":round(best_metrics["average_rssi_dbm"]-initial["average_rssi_dbm"],2)}
    return result
