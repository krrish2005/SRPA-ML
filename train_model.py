"""Train and compare multiple ML models for Smart Router Placement Advisor.

Dataset provenance: synthetic_wifi_rssi.csv is generated locally by this script.
Its RSSI target is produced by the project's original calculate_rssi() physics
simulator. It is NOT downloaded from an external/public dataset and is NOT a
set of real Wi-Fi measurements.
"""
import os, csv, random, json
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.neighbors import KNeighborsRegressor, KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, precision_recall_fscore_support, classification_report,
    confusion_matrix)
from simulation import calculate_rssi
from ml_engine import build_features, FEATURE_NAMES

ROOT=os.path.dirname(__file__)
DATA_DIR=os.path.join(ROOT,"data"); MODEL_DIR=os.path.join(ROOT,"models")
os.makedirs(DATA_DIR,exist_ok=True); os.makedirs(MODEL_DIR,exist_ok=True)
DATA_PATH=os.path.join(DATA_DIR,"synthetic_wifi_rssi.csv")
METRICS_PATH=os.path.join(MODEL_DIR,"model_comparison.json")
BEST_PATH=os.path.join(MODEL_DIR,"best_rssi_regressor.joblib")
CLASSIFIER_PATHS={
    "Random Forest Classifier":os.path.join(MODEL_DIR,"random_forest_classifier.joblib"),
    "Logistic Regression":os.path.join(MODEL_DIR,"logistic_regression_classifier.joblib"),
    "KNN Classifier":os.path.join(MODEL_DIR,"knn_classifier.joblib")}
MATERIALS=["drywall","wood","glass","brick","concrete","metal","furniture","appliance"]
CLASS_NAMES=["Dead Zone","Very Weak","Weak","Fair","Good","Excellent"]

def generate_dataset(n_rows=18000, seed=42):
    random.seed(seed); np.random.seed(seed)
    X=[]; y=[]
    with open(DATA_PATH,"w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f); writer.writerow(FEATURE_NAMES+["rssi_dbm"])
        for _ in range(n_rows):
            width=random.uniform(6,30); height=random.uniform(5,24)
            router={"x":random.uniform(.2,width-.2),"y":random.uniform(.2,height-.2)}
            target=(random.uniform(0,width),random.uniform(0,height))
            tx=random.uniform(14,27); n=random.uniform(2.0,4.0); pl0=random.choice([40.0,46.8])
            walls=[]
            for _ in range(random.randint(0,5)):
                if random.random()<.5:
                    x=random.uniform(0,width); walls.append({"x1":x,"y1":random.uniform(0,height),"x2":x,"y2":random.uniform(0,height),"material":random.choice(MATERIALS)})
                else:
                    yy=random.uniform(0,height); walls.append({"x1":random.uniform(0,width),"y1":yy,"x2":random.uniform(0,width),"y2":yy,"material":random.choice(MATERIALS)})
            obstacles=[]
            for _ in range(random.randint(0,3)):
                ox=random.uniform(0,max(.1,width-1)); oy=random.uniform(0,max(.1,height-1))
                obstacles.append({"x":ox,"y":oy,"width":random.uniform(.3,min(3,width-ox)),"height":random.uniform(.3,min(3,height-oy),),"material":random.choice(MATERIALS)})
            feats=build_features(width,height,router,target,tx,n,pl0,walls,obstacles)
            label=calculate_rssi((router["x"],router["y"]),target,tx,n,walls,obstacles,pl0)
            X.append(feats); y.append(label); writer.writerow(feats+[label])
    return np.asarray(X,dtype=float),np.asarray(y,dtype=float)

def to_signal_class(y):
    # Mutually exclusive bands based on the project's documented RSSI thresholds.
    return np.digitize(y,[-85,-75,-67,-60,-50]).astype(int)

def main():
    print("Generating 18,000 synthetic training examples...")
    X,y=generate_dataset(n_rows=18000,seed=42)
    indices=np.arange(len(y))
    train_idx,test_idx=train_test_split(indices,test_size=.20,random_state=42)
    X_train,X_test=X[train_idx],X[test_idx]; y_train,y_test=y[train_idx],y[test_idx]
    # Three comparable regressors predict the same continuous RSSI target.
    regressors={
        "Random Forest Regressor":RandomForestRegressor(n_estimators=180,min_samples_leaf=2,max_features=.9,n_jobs=-1,random_state=42),
        "KNN Regressor":Pipeline([("scale",StandardScaler()),("model",KNeighborsRegressor(n_neighbors=7,weights="distance",n_jobs=-1))]),
        "Linear Regression":Pipeline([("scale",StandardScaler()),("model",LinearRegression())])}
    reg_results={}; trained_reg={}
    for name,model in regressors.items():
        print("Training",name); model.fit(X_train,y_train); pred=model.predict(X_test)
        reg_results[name]={"MAE_dBm":round(float(mean_absolute_error(y_test,pred)),4),
            "RMSE_dBm":round(float(np.sqrt(mean_squared_error(y_test,pred))),4),
            "R2":round(float(r2_score(y_test,pred)),5)}
        trained_reg[name]=model
    best_name=min(reg_results,key=lambda n:reg_results[n]["RMSE_dBm"])
    joblib.dump(trained_reg[best_name],BEST_PATH,compress=3)

    # Logistic Regression is a classifier, so compare it with RF/KNN classifiers
    # on the same six signal-quality categories, not on continuous RSSI.
    yc=to_signal_class(y); yc_train,yc_test=yc[train_idx],yc[test_idx]
    classifiers={
        "Random Forest Classifier":RandomForestClassifier(n_estimators=180,min_samples_leaf=2,n_jobs=-1,random_state=42,class_weight="balanced_subsample"),
        "Logistic Regression":Pipeline([("scale",StandardScaler()),("model",LogisticRegression(max_iter=2000,class_weight="balanced"))]),
        "KNN Classifier":Pipeline([("scale",StandardScaler()),("model",KNeighborsClassifier(n_neighbors=7,weights="distance",n_jobs=-1))])}
    cls_results={}
    for name,model in classifiers.items():
        print("Training",name); model.fit(X_train,yc_train); pred=model.predict(X_test)
        p,r,f,_=precision_recall_fscore_support(yc_test,pred,average="weighted",zero_division=0)
        cls_results[name]={"accuracy_percent":round(float(accuracy_score(yc_test,pred)*100),3),
            "precision_weighted":round(float(p),4),"recall_weighted":round(float(r),4),"f1_weighted":round(float(f),4),
            "class_names":CLASS_NAMES,
            "confusion_matrix":confusion_matrix(yc_test,pred,labels=[0,1,2,3,4,5]).tolist()}
        joblib.dump(model,CLASSIFIER_PATHS[name],compress=3)
    best_cls=max(cls_results,key=lambda n:cls_results[n]["f1_weighted"])
    report={"dataset":{"file":"data/synthetic_wifi_rssi.csv","source":"Generated locally by train_model.py; RSSI labels produced by the project's original simulation.calculate_rssi physics formula.",
        "external_dataset":False,"real_wifi_measurements":False,"total_rows":int(len(y)),"features":FEATURE_NAMES,"target":"rssi_dbm",
        "random_seed":42,"split":"train_test_split(test_size=0.20, random_state=42)","train_rows":int(len(train_idx)),"test_rows":int(len(test_idx))},
        "regression_comparison":{"purpose":"Predict continuous RSSI in dBm; lower MAE/RMSE and higher R2 are better.","results":reg_results,"best_model_by_RMSE":best_name},
        "classification_comparison":{"purpose":"Classify RSSI into signal-quality bands; higher accuracy/F1 are better.","bands":{"Dead Zone":"RSSI < -85 dBm","Very Weak":"-85 to < -75 dBm","Weak":"-75 to < -67 dBm","Fair":"-67 to < -60 dBm","Good":"-60 to < -50 dBm","Excellent":"RSSI >= -50 dBm"},"results":cls_results,"best_model_by_weighted_F1":best_cls},
        "important_limitation":"These results measure agreement with synthetic labels generated by the project's physics simulator. They do not prove real-world Wi-Fi accuracy. For real-world validation, collect measured RSSI readings from actual routers/devices and evaluate on a held-out set of those measurements."}
    with open(METRICS_PATH,"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
    # Compatibility metrics file used by earlier UI/code.
    with open(os.path.join(MODEL_DIR,"training_metrics.json"),"w",encoding="utf-8") as f:
        json.dump({"selected_regressor":best_name,**reg_results[best_name],"rows":len(y),"train_rows":len(train_idx),"test_rows":len(test_idx),"dataset":report["dataset"]["file"],"warning":report["important_limitation"]},f,indent=2)
    print(json.dumps(report,indent=2)); print("Selected runtime regressor:",best_name)

if __name__=="__main__": main()
