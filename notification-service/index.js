const amqp = require('amqplib');
const express = require('express');

const app = express();
const PORT = process.env.PORT || 8084;
const RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://guest:guest@rabbitmq:5672';
const QUEUE_EMERGENCY = 'emergency.alert';

async function connectRabbitMQ() {
  try {
    const connection = await amqp.connect(RABBITMQ_URL);
    const channel = await connection.createChannel();
    await channel.assertQueue(QUEUE_EMERGENCY, { durable: true });
    
    console.log(`✅ Conectado ao RabbitMQ. Aguardando mensagens na fila: ${QUEUE_EMERGENCY}`);
    
    channel.consume(QUEUE_EMERGENCY, (msg) => {
      if (msg !== null) {
        const content = msg.content.toString();
        console.log(`🚨 [ALERTA RECEBIDO] ${content}`);
        
        // Simulação de envio de notificação (Email, SMS, Push)
        const payload = JSON.parse(content);
        sendEmailAlert(payload);
        sendSmsAlert(payload);
        
        channel.ack(msg);
      }
    });
  } catch (error) {
    console.error('⚠️ Erro ao conectar no RabbitMQ. Tentando novamente...', error.message);
    setTimeout(connectRabbitMQ, 5000);
  }
}

function sendEmailAlert(payload) {
  console.log(`📧 [EMAIL] Enviando email para autoridades de trânsito. Assunto: Emergência detectada!`);
}

function sendSmsAlert(payload) {
  console.log(`📱 [SMS] Disparando SMS para agentes próximos.`);
}

app.get('/health', (req, res) => res.json({ status: 'UP' }));

app.listen(PORT, () => {
  console.log(`Notification Service rodando na porta ${PORT}`);
  connectRabbitMQ();
});
