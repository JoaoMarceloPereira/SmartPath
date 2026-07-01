package com.smartpath.logiccontroller.service;

import com.smartpath.logiccontroller.config.RabbitMQConfig;
import com.smartpath.logiccontroller.dto.CommandDTO;
import com.smartpath.logiccontroller.dto.DetectionDTO;
import com.smartpath.logiccontroller.dto.EmergencyAlertDTO;
import com.smartpath.logiccontroller.dto.TrafficBatchDTO;
import com.smartpath.logiccontroller.model.TrafficDecision;
import com.smartpath.logiccontroller.repository.TrafficDecisionRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
public class TrafficLogicService {

    private static final Logger logger = LoggerFactory.getLogger(TrafficLogicService.class);

    private final RabbitTemplate rabbitTemplate;
    private final TrafficDecisionRepository decisionRepository;
    private final TrafficSettingsService settingsService;

    public TrafficLogicService(RabbitTemplate rabbitTemplate, TrafficDecisionRepository decisionRepository, TrafficSettingsService settingsService) {
        this.rabbitTemplate = rabbitTemplate;
        this.decisionRepository = decisionRepository;
        this.settingsService = settingsService;
    }

    public void calculateGreenTime(TrafficBatchDTO batch) {
        if (batch.deteccoes() == null || batch.deteccoes().isEmpty()) {
            logger.info("Lote de detecção vazio. Nenhuma ação necessária.");
            return;
        }

        // 1. Agrupa as detecções por cruzamento
        Map<String, List<DetectionDTO>> detectionsByIntersection = batch.deteccoes().stream()
                .collect(Collectors.groupingBy(DetectionDTO::cruzamentoId));

        // 2. Calcula a "pressão" de tráfego para cada cruzamento
        Map<String, Double> pressureScores = detectionsByIntersection.entrySet().stream()
                .collect(Collectors.toMap(
                        Map.Entry::getKey,
                        entry -> calculatePressure(entry.getValue())
                ));

        // 3. Encontra o cruzamento com a maior pressão
        Optional<Map.Entry<String, Double>> winner = pressureScores.entrySet().stream()
                .max(Map.Entry.comparingByValue());

        winner.ifPresent(entry -> {
            String winningIntersection = entry.getKey();
            double pressure = entry.getValue();

            // 4. Calcula o tempo de verde baseado na pressão
            int greenTime = calculateDynamicGreenTime(pressure);

            // 5. Cria e envia o comando
            sendTrafficCommand(winningIntersection, "ABRIR_SEMAFORO", greenTime, pressure);
        });
    }

    public void handleEmergency(EmergencyAlertDTO alert) {
        if (alert.deteccoes() == null || alert.deteccoes().isEmpty()) {
            logger.warn("Alerta de emergência recebido sem dados de detecção.");
            return;
        }
        // Pega o cruzamento da primeira detecção de emergência
        String intersectionId = alert.deteccoes().get(0).cruzamentoId();
        int emergencyGreenTime = settingsService.getSetting("emergency_duration", 45);

        logger.warn("🚨 OVERRIDE DE EMERGÊNCIA: Abrindo {} por {} segundos.", intersectionId, emergencyGreenTime);
        sendTrafficCommand(intersectionId, "ABERTURA_EMERGENCIA", emergencyGreenTime, 999.0); // Pressão máxima para emergência
    }

    private double calculatePressure(List<DetectionDTO> detections) {
        return detections.stream().mapToDouble(detection -> {
            return switch (detection.classeVeiculo()) {
                case "carro" -> settingsService.getSetting("peso_carro", 2);
                case "moto" -> settingsService.getSetting("peso_moto", 1);
                case "veiculo_pesado" -> settingsService.getSetting("peso_pesado", 3);
                default -> 0.5;
            };
        }).sum();
    }

    private int calculateDynamicGreenTime(double pressure) {
        int minGreen = settingsService.getSetting("min_green", 5);
        int maxGreen = settingsService.getSetting("max_green", 30);
        // Lógica simples: 1 segundo de verde para cada 2 pontos de pressão, com limites.
        int calculatedTime = (int) (minGreen + (pressure / 2.0));
        return Math.max(minGreen, Math.min(maxGreen, calculatedTime));
    }

    private void sendTrafficCommand(String intersectionId, String action, int greenTime, double pressure) {
        var timestamp = LocalDateTime.now(ZoneOffset.UTC);
        var command = new CommandDTO(timestamp.toString(), intersectionId, action, greenTime);

        rabbitTemplate.convertAndSend(RabbitMQConfig.QUEUE_COMMAND, command);
        logger.info("🚦 [COMANDO ENVIADO] -> {}: Ação: {}, Tempo: {}s", intersectionId, action, greenTime);

        // Persiste a decisão no banco de dados
        var decision = new TrafficDecision(timestamp, intersectionId, action, greenTime, pressure);
        decisionRepository.save(decision);
    }
}