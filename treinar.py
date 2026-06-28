# -*- coding: utf-8 -*-
"""Script para Treinamento da IA YOLOv8 no Dataset de Detecção de Veículos"""

import os
from ultralytics import YOLO

def treinar_modelo():
    # 1. Determinar o modelo inicial: resume do último checkpoint ou começa do zero.
    model_path = 'yolov8n.pt'  # Padrão: começar do zero
    try:
        # Procura o checkpoint mais recente para resumir o treinamento.
        runs_dir = 'runs/detect'
        if os.path.exists(runs_dir):
            latest_run_dir = max([os.path.join(runs_dir, d) for d in os.listdir(runs_dir) if d.startswith('train')], default=None, key=os.path.getmtime)
            
            if latest_run_dir and os.path.exists(os.path.join(latest_run_dir, 'weights', 'last.pt')):
                model_path = os.path.join(latest_run_dir, 'weights', 'last.pt')
                print(f"✅ Checkpoint encontrado! Resumindo treinamento de: {model_path}")
    except (FileNotFoundError, ValueError):
        # Ignora se a pasta 'runs/detect' não existir ou estiver vazia.
        pass

    print(f"🚀 Carregando modelo para treinamento: {model_path}")
    model = YOLO(model_path)
    
    # 2. Iniciar o treinamento
    print("Iniciando o treinamento...")
    results = model.train(
        data='Banco_de_Dados/Vehicle_Detection_Image_Dataset/data.yaml',
        epochs=50,              # Número sugerido de épocas para um bom treino completo
        imgsz=640,              # Tamanho de imagem de entrada
        device='cpu',           # Alterado para CPU para garantir compatibilidade
        batch=8,                # Tamanho do lote reduzido para evitar erro de memória
        optimizer='auto',       # Otimizador automático
        patience=10,            # Parada antecipada se não houver melhoria
        workers=4,              # Reduzir número de workers para economizar memória
        cache=False             # Desativar cache para economizar memória
    )
    print("\n✅ Treinamento concluído!")
    
    # Usa o caminho real onde o modelo foi salvo para a mensagem final
    best_model_path = os.path.join(results.save_dir, 'weights', 'best.pt')
    print(f"✨ O melhor modelo foi salvo em: {best_model_path}")

if __name__ == "__main__":
    treinar_modelo()
