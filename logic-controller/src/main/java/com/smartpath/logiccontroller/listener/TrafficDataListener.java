package com.smartpath.logiccontroller.listener;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;
import com.smartpath.logiccontroller.dto.TrafficBatchDTO;
import com.smartpath.logiccontroller.dto.EmergencyAlertDTO;
import com.smartpath.logiccontroller.service.TrafficLogicService;

@Component
public class TrafficDataListener {

    private static final Logger logger = LoggerFactory.getLogger(TrafficDataListener.class);

    private final TrafficLogicService trafficLogicService;

    public TrafficDataListener(TrafficLogicService trafficLogicService) {
        this.trafficLogicService = trafficLogicService;
    }

    // Ouve os dados regulares de tráfego
    @RabbitListener(queues = "vehicle.detected")
    public void receiveTrafficData(TrafficBatchDTO batch) {
        logger.info("🚗 [LOTE RECEBIDO] Processando {} detecções...", batch.deteccoes().size());
        
        // Envia os dados para a inteligência processar
        trafficLogicService.calculateGreenTime(batch);
    }

    // Ouve os alertas de prioridade máxima (Ambulância)
    @RabbitListener(queues = "emergency.alert")
    public void receiveEmergencyAlert(EmergencyAlertDTO alert) {
        logger.warn("🚨 [ALERTA DE EMERGÊNCIA RECEBIDO] Ambulância detectada!");
        trafficLogicService.handleEmergency(alert);
    }

    // Ouve as atualizações de status dos semáforos
    @RabbitListener(queues = "signal.update")
    public void receiveSignalUpdate(String signalData) {
        logger.info("🚦 [ATUALIZAÇÃO DE SINAL] Status recebido: {}", signalData);
        // Lógica para registrar histórico ou repassar via WebSocket/Gateway futuramente
    }
}