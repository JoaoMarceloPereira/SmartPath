import pika
import json
import time
import serial
import paho.mqtt.client as mqtt
import os

# RabbitMQ Config
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5673))
QUEUE_COMMAND = 'traffic.command'

# MQTT Config for ESP32/IoT Devices
MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_TOPIC = "smartpath/traffic-light/command"

# Serial Config for Arduino
PORTA_SERIAL = os.getenv('PORTA_SERIAL', 'COM3')
BAUD_RATE = 9600

arduino = None
try:
    arduino = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=1)
    print(f"✅ Conectado ao Arduino na porta {PORTA_SERIAL}")
    time.sleep(2)
except Exception as e:
    print(f"⚠️ Arduino não encontrado na porta {PORTA_SERIAL}. Erro: {e}")

# MQTT Client Setup
mqtt_client = mqtt.Client(client_id="TrafficLightService")
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
    print(f"✅ Conectado ao broker MQTT em {MQTT_BROKER}:{MQTT_PORT}")
except Exception as e:
    print(f"⚠️ Erro ao conectar no MQTT: {e}")

def on_command_received(ch, method, properties, body):
    try:
        comando_str = body.decode('utf-8')
        comando = json.loads(comando_str)
        
        cruzamento_alvo = comando.get("cruzamento_id") or comando.get("cruzamentoId")
        tempo_verde = comando.get("tempo_verde") or comando.get("tempoVerde", 5)
        acao = comando.get("acao", "ABRIR_SEMAFORO")
        
        vencedor = 1 if cruzamento_alvo == "cruzamento_1" else 2
        
        print(f"🚦 [COMANDO RECEBIDO] Cruzamento: {vencedor}, Tempo Verde: {tempo_verde}s, Ação: {acao}")
        
        # Enviar via Serial (Arduino)
        if arduino and arduino.is_open:
            arduino.write(f"G{vencedor}:{tempo_verde}\n".encode('utf-8'))
            print(f"📡 Enviado para Arduino: G{vencedor}:{tempo_verde}")
            
        # Enviar via MQTT (ESP32)
        payload = json.dumps({
            "cruzamento": vencedor,
            "tempo_verde": tempo_verde,
            "acao": acao
        })
        mqtt_client.publish(MQTT_TOPIC, payload)
        print(f"📡 Publicado no MQTT ({MQTT_TOPIC}): {payload}")
        
        # Confirma processamento da mensagem
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f"❌ Erro ao processar comando: {e}")

def main():
    while True:
        try:
            print(f"🔄 Conectando ao RabbitMQ em {RABBITMQ_HOST}:{RABBITMQ_PORT}...")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT)
            )
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_COMMAND, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_COMMAND, on_message_callback=on_command_received)
            
            print('✅ Aguardando comandos na fila traffic.command. Para sair pressione CTRL+C')
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            print("⚠️ RabbitMQ indisponível. Tentando novamente em 5 segundos...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("Encerrando Traffic Light Service...")
            break
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
