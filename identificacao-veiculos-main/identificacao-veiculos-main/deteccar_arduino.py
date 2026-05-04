# -*- coding: utf-8 -*-
"""DETECCAR_ARDUINO: Detecção de Veículos e Controle Físico de Semáforo com YOLOv8"""

import os
import cv2
import time
import serial
from ultralytics import YOLO

# 📌 Configurações de Porta Serial (Ajuste para a porta onde o Arduino está conectado)
# No Windows, geralmente é 'COM3', 'COM4', etc. No Linux é '/dev/ttyUSB0' ou similar.
PORTA_SERIAL = 'COM3'
BAUD_RATE = 9600

# 📌 Tenta iniciar a conexão serial com o Arduino
try:
    arduino = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=1)
    print(f"✅ Conectado ao Arduino na porta {PORTA_SERIAL}")
    time.sleep(2) # Aguarda 2 segundos para o Arduino reiniciar após conectar a porta Serial
except serial.SerialException:
    arduino = None
    print(f"⚠️ Aviso: Não foi possível conectar ao Arduino na porta {PORTA_SERIAL}.")
    print("Modo de Simulação ativado (apenas imprimindo no console).")

# 📌 Caminhos dos arquivos (usando caminho relativo para portabilidade)
# Se você tiver uma webcam ao vivo, pode substituir VIDEO_PATH por 0 (ex: VIDEO_PATH = 0)
VIDEO_PATH = 'transito.mp4'

# Caminho do Colab do arquivo original, verifique se está no diretorio atual
if not os.path.exists(VIDEO_PATH):
    VIDEO_PATH = '/content/drive/MyDrive/Colab Notebooks/transito.mp4'

MODEL_PATH = 'yolov8n.pt'  # 📌 Modelo YOLOv8 pré-treinado
model = YOLO(MODEL_PATH)

def processar_video_e_controlar_semaforo(video_path):
    # Inicia a captura de vídeo
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Não foi possível abrir o vídeo (ou câmera): {video_path}")
        return

    esperando_ciclo_terminar = False
    
    print("\nIniciando sistema de detecção...\nPressione 'q' na janela de vídeo para sair.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            # Reinicia o vídeo se chegar ao fim (para testes contínuos)
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        # 🔹 Inferência da Detecção (conf=0.5 reduz falsos positivos)
        results = model.predict(frame, imgsz=640, conf=0.5, verbose=False)
        boxes = results[0].boxes
        
        # 🔹 Lógica de Tipagem de Veículos (IDs do COCO Dataset)
        carros = 0
        motos = 0
        pesados = 0 # Ônibus (5) e Caminhões (7)
        
        if boxes is not None:
            for box in boxes:
                cls_id = int(box.cls[0])
                if cls_id == 2:
                    carros += 1
                elif cls_id == 3:
                    motos += 1
                elif cls_id in [5, 7]:
                    pesados += 1

        # 🔹 Lógica de Cálculo do Tempo Verde
        # Pesos (ajustáveis): Carro precisa de 1.5s, Moto de 1s, Caminhão/Ônibus de 3s
        tempo_calculado = int((carros * 1.5) + (motos * 1) + (pesados * 3))
        
        # Definimos limites de segurança: o verde fica no mínimo 5s e no máximo 30s
        tempo_verde = max(5, min(tempo_calculado, 30))

        # 🔹 Comunicação com o Arduino
        # 1. Verifica se o Arduino mandou alguma mensagem (ex: terminou o ciclo e fechou o sinal)
        if arduino and arduino.in_waiting > 0:
            resposta = arduino.readline().decode('utf-8').strip()
            if resposta == "CICLO_COMPLETO":
                esperando_ciclo_terminar = False
                print("Sinal vermelho. Pronto para nova leitura.")

        # 2. Se não estamos esperando o Arduino terminar um ciclo verde/amarelo, podemos mandar abrir!
        if not esperando_ciclo_terminar:
            comando = f"G:{tempo_verde}\n"
            if arduino:
                arduino.write(comando.encode('utf-8'))
            esperando_ciclo_terminar = True
            print(f"🚦 Enviando sinal Verde por {tempo_verde}s (Carros:{carros}, Motos:{motos}, Pesados:{pesados})")

        # 🔹 Anotação do frame para visualização (Display)
        frame_anotado = results[0].plot()
        
        # Adiciona os textos na tela
        status_txt = "Aguardando..." if esperando_ciclo_terminar else "Calculando novo ciclo"
        cv2.putText(frame_anotado, f"Tempo Calculado para Verde: {tempo_verde}s", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame_anotado, f"Deteccoes -> Car:{carros} | Moto:{motos} | Pesados:{pesados}", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame_anotado, f"Status Arduino: {status_txt}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Exibe o frame na tela (Funciona no Windows/Linux, não funciona dentro do Google Colab puro sem adaptações)
        cv2.imshow('Deteccao de Veiculos e Controle Arduino', frame_anotado)
        
        # Reduz velocidade do vídeo (opcional, para visualização melhor) e checa se usuário apertou 'q'
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    # Libera os recursos ao final
    cap.release()
    cv2.destroyAllWindows()
    if arduino:
        arduino.close()
        print("Conexão Serial fechada.")

if __name__ == "__main__":
    processar_video_e_controlar_semaforo(VIDEO_PATH)
