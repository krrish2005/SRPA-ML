
"""Train from real measured Wi-Fi RSSI samples.

CSV must contain ml_engine.FEATURE_NAMES plus a final rssi_dbm column.
Use collect_real_data_template.csv as the schema reference.
"""
import os, json
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from ml_engine import FEATURE_NAMES, MODEL_PATH

ROOT=os.path.dirname(__file__)
DATA=os.path.join(ROOT,"data","real_wifi_rssi.csv")
OUT=os.path.join(ROOT,"models")
os.makedirs(OUT,exist_ok=True)

def main():
    if not os.path.exists(DATA):
        raise FileNotFoundError("Place your collected measurements at data/real_wifi_rssi.csv")
    df=pd.read_csv(DATA)
    required=FEATURE_NAMES+["rssi_dbm"]
    missing=[c for c in required if c not in df.columns]
    if missing: raise ValueError("Missing CSV columns: "+", ".join(missing))
    df=df[required].dropna()
    if len(df)<200:
        raise ValueError(f"Need at least 200 measured rows; found {len(df)}. Aim for 1000+.")
    X=df[FEATURE_NAMES].astype(float); y=df["rssi_dbm"].astype(float)
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.2,random_state=42)
    model=RandomForestRegressor(n_estimators=220,min_samples_leaf=2,max_features=.9,
        n_jobs=-1,random_state=42)
    model.fit(Xtr,ytr); pred=model.predict(Xte)
    metrics={"model":"RandomForestRegressor (real measurements)","rows":int(len(df)),
        "mae_db":round(float(mean_absolute_error(yte,pred)),3),
        "rmse_db":round(float(mean_squared_error(yte,pred)**.5),3),
        "r2":round(float(r2_score(yte,pred)),4),
        "warning":"Hold out a separate building/floor for a stronger generalization test."}
    joblib.dump(model,MODEL_PATH,compress=3)
    with open(os.path.join(OUT,"real_training_metrics.json"),"w") as f: json.dump(metrics,f,indent=2)
    print(json.dumps(metrics,indent=2))
    print("Updated model:",MODEL_PATH)

if __name__=="__main__": main()
