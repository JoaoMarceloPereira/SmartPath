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

MODEL_PATH = 'runs/detect/train/weights/best.pt'
model = YOLO(MODEL_PATH)

def desenhar_semaforo(img, centro_x, centro_y, estado):
    # Dimensões do corpo do semáforo
    largura = 60
    altura = 130
    
    # Coordenadas do retângulo (corpo)
    x1 = centro_x - largura // 2
    y1 = centro_y - altura // 2
    x2 = centro_x + largura // 2
    y2 = centro_y + altura // 2
    
    # Desenha o fundo (corpo do semáforo)
    cv2.rectangle(img, (x1, y1), (x2, y2), (25, 25, 25), -1)      # Fundo muito escuro
    cv2.rectangle(img, (x1, y1), (x2, y2), (100, 100, 100), 2)    # Borda cinza
    
    # Raio das lâmpadas
    raio = 14
    espacamento = 35
    
    # Posições Y
    y_vermelho = centro_y - espacamento
    y_amarelo = centro_y
    y_verde = centro_y + espacamento
    
    # Definição de cores (BGR)
    cor_vermelho = (0, 0, 255) if estado == "VERMELHO" else (0, 0, 50)
    cor_amarelo = (0, 200, 255) if estado == "AMARELO" else (0, 50, 50)
    cor_verde = (0, 255, 0) if estado == "VERDE" else (0, 50, 0)
    
    # Desenhar as lâmpadas (círculos preenchidos)
    cv2.circle(img, (centro_x, y_vermelho), raio, cor_vermelho, -1)
    cv2.circle(img, (centro_x, y_amarelo), raio, cor_amarelo, -1)
    cv2.circle(img, (centro_x, y_verde), raio, cor_verde, -1)
    
    # Desenhar bordas finas para as lâmpadas
    cv2.circle(img, (centro_x, y_vermelho), raio, (70, 70, 70), 1)
    cv2.circle(img, (centro_x, y_amarelo), raio, (70, 70, 70), 1)
    cv2.circle(img, (centro_x, y_verde), raio, (70, 70, 70), 1)

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
    inicio_ciclo = 0.0
    duracao_verde = 0.0
    
    print("\nIniciando sistema de detecção para Múltiplos Cruzamentos...\nPressione 'q' na janela de vídeo para sair.")

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

    while cap1.isOpened() and cap2.isOpened():
        # 🔹 Determinar estado visual atual dos semáforos e tempo restante
        estado_semaforo_1 = "VERMELHO"
        estado_semaforo_2 = "VERMELHO"
        tempo_restante = 0
        
        if semaforo_aberto > 0:
            tempo_decorrido = time.time() - inicio_ciclo
            if tempo_decorrido < duracao_verde:
                estado_ativo = "VERDE"
                tempo_restante = max(0, int(duracao_verde - tempo_decorrido))
            elif tempo_decorrido < (duracao_verde + 3):
                estado_ativo = "AMARELO"
                tempo_restante = max(0, int(duracao_verde + 3 - tempo_decorrido))
            else:
                estado_ativo = "VERMELHO"
                
            if semaforo_aberto == 1:
                estado_semaforo_1 = estado_ativo
            elif semaforo_aberto == 2:
                estado_semaforo_2 = estado_ativo

        # 🔹 Captura de frames e inferência (Contínua, sem pausar no vermelho)
        classes_transito = [2, 3, 5, 7]
        
        # Cruzamento 1
        ret1, frame1 = cap1.read()
        if not ret1:
            cap1.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret1, frame1 = cap1.read()
        results1 = model.predict(frame1, imgsz=640, conf=0.5, classes=classes_transito, verbose=False)

        # Cruzamento 2
        ret2, frame2 = cap2.read()
        if not ret2:
            cap2.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret2, frame2 = cap2.read()
        results2 = model.predict(frame2, imgsz=640, conf=0.5, classes=classes_transito, verbose=False)


        carros1, motos1, pesados1 = contar_veiculos(results1[0].boxes)
        carros2, motos2, pesados2 = contar_veiculos(results2[0].boxes)

        # 🔹 Lógica de Cálculo de Pressão e Starvation
        # Pesos: Carro (1.5), Moto (1.0), Pesados (3.0)
        pressao_base_1 = (carros1 * 1.5) + (motos1 * 1.0) + (pesados1 * 3.0)
        pressao_base_2 = (carros2 * 1.5) + (motos2 * 1.0) + (pesados2 * 3.0)
        
        # Adiciona bônus de starvation (tempo de espera) para forçar o cruzamento a abrir eventualmente
        pressao_total_1 = pressao_base_1 + (ciclos_espera_1 * 5)
        pressao_total_2 = pressao_base_2 + (ciclos_espera_2 * 5)

        # 🔹 Comunicação com o Arduino ou Simulação (Verifica se o ciclo anterior acabou)
        if esperando_ciclo_terminar:
            if arduino:
                if arduino.in_waiting > 0:
                    resposta = arduino.readline().decode('utf-8').strip()
                    if resposta == "CICLO_COMPLETO":
                        esperando_ciclo_terminar = False
                        print("Ciclo completo (Arduino). Pronto para nova avaliação.")
            else:
                # Simulação local: o ciclo termina quando o tempo verde + 3s de amarelo expira
                tempo_decorrido = time.time() - inicio_ciclo
                if tempo_decorrido >= (duracao_verde + 3):
                    esperando_ciclo_terminar = False
                    print("Ciclo completo (Simulado). Pronto para nova avaliação.")

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
            inicio_ciclo = time.time()
            duracao_verde = tempo_verde
            
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

        # Criar painel de informações (Fundo cinza escuro para melhor contraste)
        painel_info = np.zeros((150, 1280, 3), dtype=np.uint8)
        painel_info[:] = (18, 18, 18)  # Fundo grafite muito escuro
        
        # Divisor vertical entre os dois cruzamentos
        cv2.line(painel_info, (640, 10), (640, 140), (60, 60, 60), 2)

        # Função auxiliar para obter cor do status
        def obter_cor_status(estado):
            if estado == "VERDE":
                return (0, 255, 0)
            elif estado == "AMARELO":
                return (0, 200, 255)
            else:
                return (0, 0, 255)

        cor_status1 = obter_cor_status(estado_semaforo_1)
        cor_status2 = obter_cor_status(estado_semaforo_2)
        
        # Formatar status com tempo se ativo
        status1_str = f"Status: {estado_semaforo_1}"
        if semaforo_aberto == 1 and tempo_restante > 0:
            status1_str += f" ({tempo_restante}s)"
            
        status2_str = f"Status: {estado_semaforo_2}"
        if semaforo_aberto == 2 and tempo_restante > 0:
            status2_str += f" ({tempo_restante}s)"
        
        # Textos do Cruzamento 1 (Painel esquerdo)
        cv2.putText(painel_info, "CRUZAMENTO 1", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(painel_info, status1_str, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor_status1, 2)
        cv2.putText(painel_info, f"Pressao: {pressao_base_1:.1f} | Espera: {ciclos_espera_1} ciclos", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(painel_info, f"Veiculos: {carros1} carros, {motos1} motos, {pesados1} pesados", (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        # Textos do Cruzamento 2 (Painel direito)
        cv2.putText(painel_info, "CRUZAMENTO 2", (650, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(painel_info, status2_str, (650, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor_status2, 2)
        cv2.putText(painel_info, f"Pressao: {pressao_base_2:.1f} | Espera: {ciclos_espera_2} ciclos", (650, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(painel_info, f"Veiculos: {carros2} carros, {motos2} motos, {pesados2} pesados", (650, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        # Desenhar os semáforos no painel
        desenhar_semaforo(painel_info, 520, 75, estado_semaforo_1)
        desenhar_semaforo(painel_info, 1170, 75, estado_semaforo_2)
        
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
