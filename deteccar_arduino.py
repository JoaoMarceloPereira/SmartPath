# -*- coding: utf-8 -*-
"""DETECCAR_ARDUINO: Detecção de Veículos e Controle Físico de Múltiplos Semáforos com YOLOv8"""

import os
import cv2
import time
import serial
import json
import numpy as np
import pika
from collections import deque
from datetime import datetime, timezone
from ultralytics import YOLO
import base64
import asyncio
import websockets
import threading
import webbrowser
import http.server

# 📌 Definição das Faixas (Polígonos ROI) para detecção separada por via
# ATENÇÃO: Estas coordenadas são exemplos (para um vídeo padrão de ~1280x720).
# Ajuste as coordenadas [x, y] de acordo com a perspectiva da sua câmera de trânsito.
FAIXAS_CRUZAMENTO_1 = {
    "faixa_1_esquerda": np.array([[0, 720], [600, 720], [400, 100], [0, 100]], np.int32),
    "faixa_2_direita": np.array([[600, 720], [1280, 720], [1280, 100], [400, 100]], np.int32)
}
FAIXAS_CRUZAMENTO_2 = {
    "faixa_1_esquerda": np.array([[0, 720], [600, 720], [400, 100], [0, 100]], np.int32),
    "faixa_2_direita": np.array([[600, 720], [1280, 720], [1280, 100], [400, 100]], np.int32)
}

# 📌 Estado Global para o Dashboard Web (WebSocket)
dashboard_state = {
    "state": {
        "intersections": {
            "1": {"counts": {"cars": 0, "motorcycles": 0, "heavy": 0}, "frame": "", "starvation": 0, "pressure_base": 0.0, "pressure_total": 0.0},
            "2": {"counts": {"cars": 0, "motorcycles": 0, "heavy": 0}, "frame": "", "starvation": 0, "pressure_base": 0.0, "pressure_total": 0.0}
        },
        "active_intersection": 0,
        "light_state": "VERMELHO",
        "tempo_restante": 0,
        "scenarios": {"emergency_active": 0, "pedestrian_active": 0},
        "esperando_ciclo_terminar": False
    },
    "settings": {
        "peso_carro": 1.5, "peso_moto": 1.0, "peso_pesado": 3.0,
        "min_green": 5, "max_green": 30, "starvation_factor": 5,
        "yellow_duration": 3, "emergency_duration": 45, "pedestrian_duration": 15
    },
    "mode": "simulation"
}

async def telemetry_handler(websocket):
    try:
        while True:
            await websocket.send(json.dumps(dashboard_state))
            await asyncio.sleep(0.15)
    except Exception:
        pass

def start_ws_server():
    async def main():
        async with websockets.serve(telemetry_handler, "0.0.0.0", 8001, max_size=None):
            print("🌐 Servidor WebSocket rodando na porta 8001")
            await asyncio.Future()  # roda para sempre
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: porta 8001 em uso! Feche outros processos python.exe.\nDetalhes: {e}\n")

ws_thread = threading.Thread(target=start_ws_server, daemon=True)
ws_thread.start()

def start_http_server():
    frontend_dir = os.path.abspath("frontend")

    class FrontendHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=frontend_dir, **kwargs)
        def log_message(self, format, *args):
            pass

    class ThreadingHTTPServer(http.server.ThreadingHTTPServer):
        pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 3000), FrontendHandler)
    print("🌐 Servidor HTTP do frontend rodando em http://127.0.0.1:3000")
    httpd.serve_forever()

http_thread = threading.Thread(target=start_http_server, daemon=True)
http_thread.start()

# 📌 Configurações do RabbitMQ
RABBITMQ_HOST = 'localhost'
RABBITMQ_PORT = 5673
QUEUE_VEHICLE  = 'vehicle.detected'
QUEUE_EMERGENCY = 'emergency.alert'
QUEUE_SIGNAL   = 'signal.update'
QUEUE_COMMAND  = 'traffic.command'

# Buffer circular por tempo: armazena tuplas (timestamp, payload)
# Mensagens com mais de 5 minutos são descartadas automaticamente no envio
BUFFER_TTL_SECONDS = 300  # 5 minutos
payload_buffer = deque()

rabbitmq_conn = None
rabbitmq_channel = None

def conectar_rabbitmq():
    global rabbitmq_conn, rabbitmq_channel
    try:
        rabbitmq_conn = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT))
        rabbitmq_channel = rabbitmq_conn.channel()
        rabbitmq_channel.queue_declare(queue=QUEUE_VEHICLE,   durable=True)
        rabbitmq_channel.queue_declare(queue=QUEUE_EMERGENCY, durable=True)
        rabbitmq_channel.queue_declare(queue=QUEUE_SIGNAL,    durable=True)
        rabbitmq_channel.queue_declare(queue=QUEUE_COMMAND,   durable=True)
        print("✅ Conectado ao RabbitMQ com sucesso.")
    except Exception as e:
        print(f"⚠️ RabbitMQ offline ou inacessível: {e}")
        rabbitmq_conn = None

def enviar_para_mensageria(payload):
    global rabbitmq_conn, rabbitmq_channel

    if rabbitmq_conn is None or not rabbitmq_conn.is_open:
        conectar_rabbitmq()

    agora = time.time()
    try:
        if rabbitmq_channel and rabbitmq_channel.is_open:
            # Esvazia o buffer descartando mensagens expiradas (> 5 min)
            while payload_buffer:
                ts, old_payload = payload_buffer[0]
                if agora - ts > BUFFER_TTL_SECONDS:
                    payload_buffer.popleft()  # descarta expirado
                    continue
                rabbitmq_channel.basic_publish(
                    exchange='', routing_key=QUEUE_VEHICLE,
                    body=json.dumps(old_payload),
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                payload_buffer.popleft()

            rabbitmq_channel.basic_publish(
                exchange='', routing_key=QUEUE_VEHICLE,
                body=json.dumps(payload),
                properties=pika.BasicProperties(delivery_mode=2)
            )
        else:
            raise ConnectionError("Canal RabbitMQ fechado")
    except Exception as e:
        payload_buffer.append((agora, payload))
        print(f"⚠️ Erro ao enviar. Buffer: {len(payload_buffer)} mensagens | {e}")

def enviar_alerta_emergencia(payload):
    global rabbitmq_conn, rabbitmq_channel
    if rabbitmq_conn is None or not rabbitmq_conn.is_open:
        conectar_rabbitmq()
    try:
        if rabbitmq_channel and rabbitmq_channel.is_open:
            rabbitmq_channel.basic_publish(exchange='', routing_key=QUEUE_EMERGENCY, body=json.dumps(payload), properties=pika.BasicProperties(delivery_mode=2))
            print("🚨 ALERTA DE EMERGÊNCIA ENVIADO PARA MENSAGERIA!")
    except Exception as e:
        print(f"⚠️ Erro ao enviar alerta de emergência: {e}")

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

# Usando o modelo padrão do YOLOv8 para facilitar os testes (ele baixa automaticamente)
MODEL_PATH = 'yolov8n.pt'
model = YOLO(MODEL_PATH)

# 📌 Tentativa inicial de conexão ao RabbitMQ
conectar_rabbitmq()

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
    inicio_ciclo = 0.0
    duracao_verde = 0.0
    
    # Variáveis para controle de spam do alerta de ambulância
    ultimo_alerta_emergencia = 0
    COOLDOWN_EMERGENCIA = 5 # Segundos de intervalo entre alertas
    
    print("\nIniciando sistema de detecção (Modo Oculto)...\nO painel será aberto automaticamente no seu navegador padrão.\nPressione Ctrl+C neste terminal para encerrar.")

    # 🔹 Abre o Dashboard HTML automaticamente no navegador padrão
    time.sleep(1)  # Aguarda o servidor HTTP subir
    webbrowser.open("http://127.0.0.1:3000/index.html")

    # 🔹 Função para processar detecções, separar por faixas e gerar JSON
    def processar_deteccoes(boxes, cruzamento_id, faixas_roi, nomes_classes):
        carros, motos, pesados = 0, 0, 0
        payloads = []
        ambulancias_detectadas = []
        timestamp_atual = datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z"

        if boxes is not None:
            for box in boxes:
                cls_id = int(box.cls[0])
                confianca = float(box.conf[0])
                nome_yolo = nomes_classes[cls_id].lower()
                
                # Coordenadas do centro da bounding box
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                centro_x = int((x1 + x2) / 2)
                centro_y = int((y1 + y2) / 2)
                
                nome_classe = "desconhecido"
                
                # Identificação de classes dinâmica (suporta YOLO nativo e customizado)
                if 'ambulance' in nome_yolo or 'ambulancia' in nome_yolo:
                    nome_classe = "ambulancia"
                elif cls_id == 2 or nome_yolo == 'car':
                    carros += 1
                    nome_classe = "carro"
                elif cls_id == 3 or nome_yolo == 'motorcycle':
                    motos += 1
                    nome_classe = "moto"
                elif cls_id in [5, 7] or nome_yolo in ['bus', 'truck']:
                    pesados += 1
                    nome_classe = "veiculo_pesado"
                
                if nome_classe != "desconhecido":
                    faixa_detectada = "desconhecida"
                    for nome_faixa, poligono in faixas_roi.items():
                        # >= 0 significa que o ponto está dentro ou na borda do polígono
                        if cv2.pointPolygonTest(poligono, (centro_x, centro_y), False) >= 0:
                            faixa_detectada = nome_faixa
                            break
                            
                    payload = {
                        "timestamp": timestamp_atual,
                        "cruzamento_id": cruzamento_id,
                        "faixa": faixa_detectada,
                        "classe_veiculo": nome_classe,
                        "confianca": round(confianca, 2)
                    }
                    payloads.append(payload)
                    
                    if nome_classe == "ambulancia":
                        ambulancias_detectadas.append(payload)
                    
        return carros, motos, pesados, payloads, ambulancias_detectadas

    frame_count = 0
    while cap1.isOpened() and cap2.isOpened():
        frame_start = time.time()
        frame_count += 1
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
        
        # Cruzamento 1
        ret1, frame1 = cap1.read()
        if not ret1:
            cap1.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret1, frame1 = cap1.read()
        results1 = model.predict(frame1, imgsz=640, conf=0.5, verbose=False)

        # Cruzamento 2
        ret2, frame2 = cap2.read()
        if not ret2:
            cap2.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret2, frame2 = cap2.read()
        results2 = model.predict(frame2, imgsz=640, conf=0.5, verbose=False)


        carros1, motos1, pesados1, payloads1, amb1 = processar_deteccoes(results1[0].boxes, "cruzamento_1", FAIXAS_CRUZAMENTO_1, model.names)
        carros2, motos2, pesados2, payloads2, amb2 = processar_deteccoes(results2[0].boxes, "cruzamento_2", FAIXAS_CRUZAMENTO_2, model.names)

        # 🔹 Envio de Alerta de Emergência (Prioridade Máxima)
        todas_ambulancias = amb1 + amb2
        if todas_ambulancias and (time.time() - ultimo_alerta_emergencia > COOLDOWN_EMERGENCIA):
            payload_emergencia = {
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z",
                "tipo_alerta": "AMBULANCIA_DETECTADA",
                "deteccoes": todas_ambulancias
            }
            enviar_alerta_emergencia(payload_emergencia)
            ultimo_alerta_emergencia = time.time()

        # 🔹 Envio do Payload JSON para Mensageria (A cada ~30 frames)
        todos_payloads = payloads1 + payloads2
        if todos_payloads and frame_count % 30 == 0:
            payload_lote = {
                "timestamp_lote": datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z",
                "deteccoes": todos_payloads
            }
            enviar_para_mensageria(payload_lote)

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
        # Agora a decisão vem do Cérebro Java! Lemos a fila de comandos.
        if not esperando_ciclo_terminar:
            if rabbitmq_channel and rabbitmq_channel.is_open:
                ultimo_comando = None
                tags_para_confirmar = []
                # Drena a fila para pegar apenas a decisão mais recente da IA
                while True:
                    method, properties, body = rabbitmq_channel.basic_get(queue=QUEUE_COMMAND, auto_ack=False)
                    if method:
                        tags_para_confirmar.append(method.delivery_tag)
                        ultimo_comando = body
                    else:
                        break
                
                if ultimo_comando:
                    comando_java = json.loads(ultimo_comando)
                    # Suporta tanto o formato do Python (snake_case) quanto o do Java (camelCase)
                    cruzamento_alvo = comando_java.get("cruzamento_id") or comando_java.get("cruzamentoId")
                    tempo_verde = comando_java.get("tempo_verde") or comando_java.get("tempoVerde", 5)

                    vencedor = 1 if cruzamento_alvo == "cruzamento_1" else 2
                    semaforo_aberto = vencedor
                    inicio_ciclo = time.time()
                    duracao_verde = tempo_verde

                    if arduino:
                        arduino.write(f"G{vencedor}:{tempo_verde}\n".encode('utf-8'))

                    # Confirma o processamento de TODAS as mensagens drenadas (evita vazamento de memória)
                    for tag in tags_para_confirmar:
                        rabbitmq_channel.basic_ack(delivery_tag=tag)
                        
                    esperando_ciclo_terminar = True
                    print(f"🚦 [JAVA -> PYTHON] Abrindo {cruzamento_alvo} por {tempo_verde}s")

        # 🔹 Anotação dos frames para visualização (Display)
        frame1_anotado = results1[0].plot()
        frame2_anotado = results2[0].plot()
        
        # Desenhar Polígonos das Faixas (ROIs) nos frames
        for nome_faixa, poligono in FAIXAS_CRUZAMENTO_1.items():
            cv2.polylines(frame1_anotado, [poligono], isClosed=True, color=(255, 0, 0), thickness=2)
            cv2.putText(frame1_anotado, nome_faixa, tuple(poligono[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
        for nome_faixa, poligono in FAIXAS_CRUZAMENTO_2.items():
            cv2.polylines(frame2_anotado, [poligono], isClosed=True, color=(255, 0, 0), thickness=2)
            cv2.putText(frame2_anotado, nome_faixa, tuple(poligono[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Redimensionar para o Web Dashboard (ainda mais leve para não travar a tela)
        frame1_anotado = cv2.resize(frame1_anotado, (480, 360))
        frame2_anotado = cv2.resize(frame2_anotado, (480, 360))
        
        # 🔹 Converter frames para base64 e atualizar estado do Dashboard
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 40]
        _, buffer1 = cv2.imencode('.jpg', frame1_anotado, encode_param)
        _, buffer2 = cv2.imencode('.jpg', frame2_anotado, encode_param)
        frame1_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer1).decode('utf-8')
        frame2_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer2).decode('utf-8')

        dashboard_state["mode"] = "hardware" if arduino else "simulation"
        dashboard_state["state"]["esperando_ciclo_terminar"] = esperando_ciclo_terminar
        dashboard_state["state"]["active_intersection"] = semaforo_aberto
        if semaforo_aberto == 1:
            dashboard_state["state"]["light_state"] = estado_semaforo_1
        elif semaforo_aberto == 2:
            dashboard_state["state"]["light_state"] = estado_semaforo_2
        else:
            dashboard_state["state"]["light_state"] = "VERMELHO"
            
        dashboard_state["state"]["tempo_restante"] = tempo_restante
        dashboard_state["state"]["intersections"]["1"]["counts"] = {"cars": carros1, "motorcycles": motos1, "heavy": pesados1}
        dashboard_state["state"]["intersections"]["1"]["frame"] = frame1_b64
        dashboard_state["state"]["intersections"]["2"]["counts"] = {"cars": carros2, "motorcycles": motos2, "heavy": pesados2}
        dashboard_state["state"]["intersections"]["2"]["frame"] = frame2_b64
        
        # Modo Headless (Sem Janela OpenCV antiga)
        # O processamento visual ocorre 100% no Dashboard Web (index.html)
        
        # Controle de 30 FPS: aguarda o tempo necessário para manter o ritmo
        elapsed = time.time() - frame_start
        sleep_time = (1.0 / 30) - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

    # Libera os recursos ao final
    cap1.release()
    cap2.release()
    cv2.destroyAllWindows()
    if arduino:
        arduino.close()
        print("Conexão Serial fechada.")

if __name__ == "__main__":
    processar_video_e_controlar_semaforo(VIDEO_PATH_1, VIDEO_PATH_2)
