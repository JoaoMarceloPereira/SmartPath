import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File
from ultralytics import YOLO
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
import uvicorn
import io
from PIL import Image

app = FastAPI(title="SmartPath AI Service")

# Prometheus Metrics
Instrumentator().instrument(app).expose(app)

# Load YOLO model
MODEL_PATH = "models/yolov8n.pt"
try:
    model = YOLO(MODEL_PATH)
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

class DetectionResult(BaseModel):
    classe: str
    confianca: float
    bbox: list[float]

@app.get("/health")
def health_check():
    return {"status": "ok", "model_loaded": model is not None}

def process_image(file_bytes: bytes):
    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    image_np = np.array(image)
    image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
    return image_bgr

@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    if not model:
        return {"error": "Model not loaded"}
        
    contents = await file.read()
    image = process_image(contents)
    
    results = model.predict(image, conf=0.5, verbose=False)
    
    detections = []
    if results:
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            confianca = float(box.conf[0])
            nome_yolo = model.names[cls_id].lower()
            
            nome_classe = "desconhecido"
            if 'ambulance' in nome_yolo or 'ambulancia' in nome_yolo:
                nome_classe = "ambulancia"
            elif cls_id == 2 or nome_yolo == 'car':
                nome_classe = "carro"
            elif cls_id == 3 or nome_yolo == 'motorcycle':
                nome_classe = "moto"
            elif cls_id in [5, 7] or nome_yolo in ['bus', 'truck']:
                nome_classe = "veiculo_pesado"
            else:
                nome_classe = nome_yolo
                
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append(DetectionResult(
                classe=nome_classe,
                confianca=confianca,
                bbox=[x1, y1, x2, y2]
            ))
            
    return {"detections": detections}

@app.post("/count")
async def count_vehicles(file: UploadFile = File(...)):
    if not model:
        return {"error": "Model not loaded"}
        
    contents = await file.read()
    image = process_image(contents)
    
    results = model.predict(image, conf=0.5, verbose=False)
    
    counts = {"carro": 0, "moto": 0, "veiculo_pesado": 0, "ambulancia": 0, "outros": 0}
    if results:
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            nome_yolo = model.names[cls_id].lower()
            
            if 'ambulance' in nome_yolo or 'ambulancia' in nome_yolo:
                counts["ambulancia"] += 1
            elif cls_id == 2 or nome_yolo == 'car':
                counts["carro"] += 1
            elif cls_id == 3 or nome_yolo == 'motorcycle':
                counts["moto"] += 1
            elif cls_id in [5, 7] or nome_yolo in ['bus', 'truck']:
                counts["veiculo_pesado"] += 1
            else:
                counts["outros"] += 1
                
    return {"counts": counts}

@app.post("/congestion")
async def congestion_level(file: UploadFile = File(...)):
    """Calculates congestion level based on vehicle counts in the image."""
    counts_response = await count_vehicles(file)
    if "error" in counts_response:
        return counts_response
        
    counts = counts_response["counts"]
    total_vehicles = counts["carro"] + counts["moto"] + counts["veiculo_pesado"]
    
    # Simple heuristic for congestion
    level = "BAIXO"
    if total_vehicles > 15:
        level = "ALTO"
    elif total_vehicles > 5:
        level = "MEDIO"
        
    return {
        "level": level,
        "total_vehicles": total_vehicles,
        "emergency_vehicle_present": counts["ambulancia"] > 0
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
