package com.smartpath.logiccontroller.listener;

import com.rabbitmq.client.Channel;
import com.smartpath.logiccontroller.config.RabbitMQConfig;
import com.smartpath.logiccontroller.dto.EmergencyAlertDTO;
import com.smartpath.logiccontroller.dto.TrafficBatchDTO;
import com.smartpath.logiccontroller.service.TrafficLogicService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;
import java.io.IOException;

@Component
public class TrafficMessageListener {

    private static final Logger logger = LoggerFactory.getLogger(TrafficMessageListener.class);
    private final TrafficLogicService trafficLogicService;

    public TrafficMessageListener(TrafficLogicService trafficLogicService) {
        this.trafficLogicService = trafficLogicService;
    }

    @RabbitListener(queues = RabbitMQConfig.QUEUE_VEHICLE, ackMode = "MANUAL")
    public void receiveVehicleDetections(TrafficBatchDTO batch, Message message, Channel channel) throws IOException {
        long deliveryTag = message.getMessageProperties().getDeliveryTag();
        try {
            logger.info("📥 [DADO RECEBIDO] Lote de detecções da fila '{}'.", RabbitMQConfig.QUEUE_VEHICLE);
            trafficLogicService.calculateGreenTime(batch);
            channel.basicAck(deliveryTag, false); // Confirma o sucesso do processamento
            logger.debug("Mensagem {} processada com sucesso.", deliveryTag);
        } catch (Exception e) {
            logger.error("❌ Erro ao processar lote de detecção. Rejeitando mensagem {}.", deliveryTag, e);
            // Rejeita a mensagem e a devolve para a fila para nova tentativa.
            channel.basicNack(deliveryTag, false, true);
        }
    }

    @RabbitListener(queues = RabbitMQConfig.QUEUE_EMERGENCY, ackMode = "MANUAL")
    public void receiveEmergencyAlert(EmergencyAlertDTO alert, Message message, Channel channel) throws IOException {
        long deliveryTag = message.getMessageProperties().getDeliveryTag();
        try {
            logger.warn("📥 [ALERTA RECEBIDO] Alerta da fila '{}'.", RabbitMQConfig.QUEUE_EMERGENCY);
            trafficLogicService.handleEmergency(alert);
            channel.basicAck(deliveryTag, false);
        } catch (Exception e) {
            logger.error("❌ Erro ao processar alerta de emergência. Rejeitando mensagem {}.", deliveryTag, e);
            channel.basicNack(deliveryTag, false, true);
        }
    }
}