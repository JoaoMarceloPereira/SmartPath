package com.smartpath.logiccontroller.listener;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.rabbitmq.client.Channel;
import com.smartpath.logiccontroller.dto.EmergencyAlertDTO;
import com.smartpath.logiccontroller.dto.TrafficBatchDTO;
import com.smartpath.logiccontroller.config.RabbitMQConfig;
import com.smartpath.logiccontroller.service.TrafficLogicService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.AmqpHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.stereotype.Component;

@Component
public class TrafficEventListener {

    private static final Logger log = LoggerFactory.getLogger(TrafficEventListener.class);
    
    private final TrafficLogicService trafficLogicService;
    private final ObjectMapper objectMapper;

    public TrafficEventListener(TrafficLogicService trafficLogicService, ObjectMapper objectMapper) {
        this.trafficLogicService = trafficLogicService;
        this.objectMapper = objectMapper;
    }

    @RabbitListener(queues = RabbitMQConfig.QUEUE_VEHICLE, ackMode = "MANUAL")
    public void onVehicleDetected(String payload, Channel channel, @Header(AmqpHeaders.DELIVERY_TAG) long tag) {
        try {
            log.info("Recebido lote de detecções de tráfego.");
            TrafficBatchDTO batch = objectMapper.readValue(payload, TrafficBatchDTO.class);
            trafficLogicService.calculateGreenTime(batch);

            // Confirmação manual garantindo que não perdemos a mensagem
            channel.basicAck(tag, false);
        } catch (Exception e) {
            log.error("Erro ao processar lote de detecções. Reenviando para a fila.", e);
            try { channel.basicNack(tag, false, true); } catch (Exception ignored) {}
        }
    }

    @RabbitListener(queues = RabbitMQConfig.QUEUE_EMERGENCY, ackMode = "MANUAL")
    public void onEmergencyAlert(String payload, Channel channel, @Header(AmqpHeaders.DELIVERY_TAG) long tag) {
        try {
            log.warn("🚨 ALERTA DE EMERGÊNCIA RECEBIDO! Acionando protocolo prioritário.");
            EmergencyAlertDTO alert = objectMapper.readValue(payload, EmergencyAlertDTO.class);
            trafficLogicService.handleEmergency(alert);

            channel.basicAck(tag, false);
        } catch (Exception e) {
            log.error("Erro ao processar emergência", e);
            try { channel.basicNack(tag, false, true); } catch (Exception ignored) {}
        }
    }
}