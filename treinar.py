# -*- coding: utf-8 -*-
"""Script para Treinamento da IA YOLOv8 no Dataset de Detecção de Veículos"""

from ultralytics import YOLO

def treinar_modelo():
    # 1. Carregar o modelo YOLOv8n pré-treinado existente no projeto
    print("Carregando o modelo yolov8n.pt...")
    model = YOLO('yolov8n.pt')

    # 2. Iniciar o treinamento
    print("Iniciando o treinamento...")
    results = model.train(
        data='Banco_de_Dados/Vehicle_Detection_Image_Dataset/data.yaml',
        epochs=50,              # Número sugerido de épocas para um bom treino completo
        imgsz=640,              # Tamanho de imagem de entrada
        device=0,           # GPU Nvidia RTX 3060 via CUDA
        batch=8,                # Tamanho do lote reduzido para evitar erro de memória
        optimizer='auto',       # Otimizador automático
        patience=10,            # Parada antecipada se não houver melhoria
        workers=4,              # Reduzir número de workers para economizar memória
        cache=False             # Desativar cache para economizar memória
    )
    print("Treinamento concluído!")
    print("O melhor modelo foi salvo em: runs/detect/train/weights/best.pt")

if __name__ == "__main__":
    treinar_modelo()
