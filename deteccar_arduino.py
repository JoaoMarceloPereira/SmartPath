# -*- coding: utf-8 -*-
"""DETECCAR_ARDUINO: Detecção de Veículos e Controle Físico de Múltiplos Semáforos com YOLOv8"""

import os
import cv2
import time
import serial
import numpy as np
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
# Utilizando transito.mp4 como fonte para o cruzamento 1
VIDEO_PATH_1 = 'transito.mp4'

# Como não temos um segundo vídeo diferente no momento, vamos usar o mesmo 
# para simular o segundo cruzamento. Você pode alterar este caminho futuramente.
VIDEO_PATH_2 = 'transito1.mp4' 

MODEL_PATH = 'yolov8n.pt'  # 📌 Modelo YOLOv8 pré-treinado
model = YOLO(MODEL_PATH)

def processar_video_e_controlar_semaforo(video_path1, video_path2):
    # Inicia a captura de vídeo
    cap1 = cv2.VideoCapture(video_path1)
    cap2 = cv2.VideoCapture(video_path2)
    
    if not cap1.isOpened():
        print(f"❌ Não foi possível abrir o vídeo (ou câmera): {video_path1}")
        return
    if not cap2.isOpened():
        print(f"❌ Não foi possível abrir o vídeo (ou câmera): {video_path2}")
        return

    esperando_ciclo_terminar = False
    semaforo_aberto = 0 # 0 = nenhum, 1 = cruzamento 1, 2 = cruzamento 2
    ciclos_espera_1 = 0
    ciclos_espera_2 = 0
    
    print("\nIniciando sistema de detecção para Múltiplos Cruzamentos...\nPressione 'q' na janela de vídeo para sair.")

    while cap1.isOpened() and cap2.isOpened():
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()
        
        if not ret1:
            cap1.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret1, frame1 = cap1.read()
        if not ret2:
            cap2.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret2, frame2 = cap2.read()

        # 🔹 Inferência da Detecção (conf=0.5 reduz falsos positivos)
        # Filtrando apenas classes relacionadas a trânsito: 2 (carro), 3 (moto), 5 (ônibus), 7 (caminhão)
        classes_transito = [2, 3, 5, 7]
        results1 = model.predict(frame1, imgsz=640, conf=0.5, classes=classes_transito, verbose=False)
        results2 = model.predict(frame2, imgsz=640, conf=0.5, classes=classes_transito, verbose=False)
        
        # 🔹 Função para contar os veículos nos resultados
        def contar_veiculos(boxes):
            carros = 0
            motos = 0
            pesados = 0
            if boxes is not None:
                for box in boxes:
                    cls_id = int(box.cls[0])
                    if cls_id == 2:
                        carros += 1
                    elif cls_id == 3:
                        motos += 1
                    elif cls_id in [5, 7]:
                        pesados += 1
            return carros, motos, pesados

        carros1, motos1, pesados1 = contar_veiculos(results1[0].boxes)
        carros2, motos2, pesados2 = contar_veiculos(results2[0].boxes)

        # 🔹 Lógica de Cálculo de Pressão e Starvation
        # Pesos: Carro (1.5), Moto (1.0), Pesados (3.0)
        pressao_base_1 = (carros1 * 1.5) + (motos1 * 1.0) + (pesados1 * 3.0)
        pressao_base_2 = (carros2 * 1.5) + (motos2 * 1.0) + (pesados2 * 3.0)
        
        # Adiciona bônus de starvation (tempo de espera) para forçar o cruzamento a abrir eventualmente
        pressao_total_1 = pressao_base_1 + (ciclos_espera_1 * 5)
        pressao_total_2 = pressao_base_2 + (ciclos_espera_2 * 5)

        # 🔹 Comunicação com o Arduino (Verifica se o ciclo anterior acabou)
        if arduino and arduino.in_waiting > 0:
            resposta = arduino.readline().decode('utf-8').strip()
            if resposta == "CICLO_COMPLETO":
                esperando_ciclo_terminar = False
                print("Ciclo completo. Pronto para nova avaliação.")

        # 🔹 Tomada de decisão: Qual semáforo abrir?
        if not esperando_ciclo_terminar:
            if pressao_total_1 >= pressao_total_2:
                # Vencedor é o Cruzamento 1
                vencedor = 1
                # O tempo de verde é baseado na pressão REAL do cruzamento, e não no bônus de espera
                tempo_verde = max(5, min(int(pressao_base_1), 30))
                comando = f"G1:{tempo_verde}\n"
                
                # Reseta o ciclo de espera de quem abriu e incrementa quem ficou esperando
                ciclos_espera_1 = 0
                ciclos_espera_2 += 1
            else:
                # Vencedor é o Cruzamento 2
                vencedor = 2
                tempo_verde = max(5, min(int(pressao_base_2), 30))
                comando = f"G2:{tempo_verde}\n"
                
                ciclos_espera_2 = 0
                ciclos_espera_1 += 1
                
            semaforo_aberto = vencedor
            
            if arduino:
                arduino.write(comando.encode('utf-8'))
            esperando_ciclo_terminar = True
            print(f"🚦 Enviando Verde p/ Cruzamento {vencedor} por {tempo_verde}s (C1={pressao_total_1:.1f}, C2={pressao_total_2:.1f})")

        # 🔹 Anotação dos frames para visualização (Display)
        frame1_anotado = results1[0].plot()
        frame2_anotado = results2[0].plot()
        
        # Redimensionar para ficar amigável na tela lado a lado
        frame1_anotado = cv2.resize(frame1_anotado, (640, 480))
        frame2_anotado = cv2.resize(frame2_anotado, (640, 480))
        
        # Combinar as imagens lado a lado (Topo)
        frames_topo = np.hstack((frame1_anotado, frame2_anotado))

        # Criar painel de informações (Fundo preto, 1280x150)
        painel_info = np.zeros((150, 1280, 3), dtype=np.uint8)

        cor_verde = (0, 255, 0)
        cor_vermelha = (0, 0, 255)
        
        # Textos do Cruzamento 1 (Painel esquerdo)
        status1 = "VERDE" if semaforo_aberto == 1 else "VERMELHO"
        cv2.putText(painel_info, "CRUZAMENTO 1", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(painel_info, f"Status: {status1}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor_verde if semaforo_aberto == 1 else cor_vermelha, 2)
        cv2.putText(painel_info, f"Pressao: {pressao_base_1:.1f} | Espera: {ciclos_espera_1} ciclos", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(painel_info, f"Veiculos: {carros1} carros, {motos1} motos, {pesados1} pesados", (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        # Textos do Cruzamento 2 (Painel direito)
        status2 = "VERDE" if semaforo_aberto == 2 else "VERMELHO"
        cv2.putText(painel_info, "CRUZAMENTO 2", (650, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(painel_info, f"Status: {status2}", (650, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor_verde if semaforo_aberto == 2 else cor_vermelha, 2)
        cv2.putText(painel_info, f"Pressao: {pressao_base_2:.1f} | Espera: {ciclos_espera_2} ciclos", (650, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(painel_info, f"Veiculos: {carros2} carros, {motos2} motos, {pesados2} pesados", (650, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        # Combinar topo e painel de informações
        frame_combinado = np.vstack((frames_topo, painel_info))
        
        # Exibe o frame na tela
        cv2.imshow('Controle Inteligente de Multiplos Cruzamentos', frame_combinado)
        
        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    # Libera os recursos ao final
    cap1.release()
    cap2.release()
    cv2.destroyAllWindows()
    if arduino:
        arduino.close()
        print("Conexão Serial fechada.")

if __name__ == "__main__":
    processar_video_e_controlar_semaforo(VIDEO_PATH_1, VIDEO_PATH_2)
