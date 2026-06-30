import os
import shutil
import json
import re
from datetime import datetime

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

def get_next_version():
    os.makedirs(MODELS_DIR, exist_ok=True)
    versions = []
    for d in os.listdir(MODELS_DIR):
        if os.path.isdir(os.path.join(MODELS_DIR, d)) and re.match(r"^v\d+$", d):
            versions.append(int(d[1:]))
    if not versions:
        return "v1"
    return f"v{max(versions) + 1}"

def create_version_checkpoint(version_name, metrics, dataset="Prepared FF++ & DFDC Split"):
    v_dir = os.path.join(MODELS_DIR, version_name)
    os.makedirs(v_dir, exist_ok=True)
    
    files = ["efficientnet_dfdc.pt", "xception_ffpp.pt", "ensemble.pkl", "current.json"]
    for f in files:
        src = os.path.join(MODELS_DIR, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(v_dir, f))
            
    metadata = {
        "version": version_name,
        "accuracy": metrics.get("accuracy", 0.0),
        "precision": metrics.get("precision", 0.0),
        "recall": metrics.get("recall", 0.0),
        "f1": metrics.get("f1", 0.0),
        "dataset": dataset,
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }
    with open(os.path.join(v_dir, "metadata.json"), "w") as out:
        json.dump(metadata, out, indent=4)
        
    with open(os.path.join(MODELS_DIR, "current.json"), "w") as out:
        json.dump(metadata, out, indent=4)
        
    rotate_versions()
    return v_dir

def rotate_versions():
    versions = []
    for d in os.listdir(MODELS_DIR):
        if os.path.isdir(os.path.join(MODELS_DIR, d)) and re.match(r"^v\d+$", d):
            versions.append((int(d[1:]), d))
            
    versions.sort(reverse=True)
    if len(versions) > 3:
        archive_dir = os.path.join(MODELS_DIR, "archive")
        os.makedirs(archive_dir, exist_ok=True)
        for _, v_name in versions[3:]:
            src = os.path.join(MODELS_DIR, v_name)
            dst = os.path.join(archive_dir, v_name)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.move(src, dst)
            print(f"[INFO] Archived version {v_name} to models/archive/")

def rollback_to_version(version_name):
    src_dir = os.path.join(MODELS_DIR, version_name)
    if not os.path.exists(src_dir):
        src_dir = os.path.join(MODELS_DIR, "archive", version_name)
        
    if not os.path.exists(src_dir):
        raise FileNotFoundError(f"Version {version_name} not found.")
        
    files = ["efficientnet_dfdc.pt", "xception_ffpp.pt", "ensemble.pkl", "current.json", "metadata.json"]
    for f in files:
        src = os.path.join(src_dir, f)
        if os.path.exists(src):
            dst = os.path.join(MODELS_DIR, f)
            shutil.copy2(src, dst)
            
    meta_path = os.path.join(src_dir, "metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r") as r:
            meta = json.load(r)
        with open(os.path.join(MODELS_DIR, "current.json"), "w") as w:
            json.dump(meta, w, indent=4)
            
    print(f"[SUCCESS] Rolled back active serving models to {version_name}")
