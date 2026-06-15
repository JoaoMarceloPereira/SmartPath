package com.smartpath.logiccontroller.service;

import com.smartpath.logiccontroller.dto.CommandDTO;
import com.smartpath.logiccontroller.dto.DetectionDTO;
import com.smartpath.logiccontroller.dto.TrafficBatchDTO;
import com.smartpath.logiccontroller.dto.EmergencyAlertDTO;
import com.smartpath.logiccontroller.model.TrafficDecision;
import com.smartpath.logiccontroller.repository.TrafficDecisionRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.cache.annotation.CachePut;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class TrafficLogicService {

    private static final Logger logger = LoggerFactory.getLogger(TrafficLogicService.class);
    
    private final RabbitTemplate rabbitTemplate;
    private final TrafficDecisionRepository decisionRepository;

    public TrafficLogicService(RabbitTemplate rabbitTemplate, TrafficDecisionRepository decisionRepository) {
        this.rabbitTemplate = rabbitTemplate;
        this.decisionRepository = decisionRepository;
    }

    @CircuitBreaker(name = "trafficLogic", fallbackMethod = "fallbackCalculateGreenTime")
    public void calculateGreenTime(TrafficBatchDTO batch) {
        if (batch.deteccoes() == null || batch.deteccoes().isEmpty()) {
            return;
        }

        // 1. Agrupar os veículos detectados por Cruzamento (cruzamento_1, cruzamento_2, etc.)
        Map<String, List<DetectionDTO>> detectionsByIntersection = batch.deteccoes().stream()
                .collect(Collectors.groupingBy(DetectionDTO::cruzamentoId));

        String winningIntersection = null;
        double maxPressure = -1.0;
        int finalGreenTime = 0;

        // 2. Calcular a "Pressão de Tráfego" para descobrir quem precisa mais do verde
        for (Map.Entry<String, List<DetectionDTO>> entry : detectionsByIntersection.entrySet()) {
            String cruzamentoId = entry.getKey();
            List<DetectionDTO> detections = entry.getValue();

            long carros = detections.stream().filter(d -> d.classeVeiculo().equals("carro")).count();
            long motos = detections.stream().filter(d -> d.classeVeiculo().equals("moto")).count();
            long pesados = detections.stream().filter(d -> d.classeVeiculo().equals("veiculo_pesado")).count();

            double pressure = calculateFuzzyPressure(carros, motos, pesados);

            if (pressure > maxPressure) {
                maxPressure = pressure;
                winningIntersection = cruzamentoId;
                // Mínimo 5s, Máximo 120s
                finalGreenTime = (int) Math.min(120, Math.max(5, pressure)); 
            }
        }

        if (winningIntersection != null) {
            logger.info("🧠 CÉREBRO AVALIOU -> Vencedor: {} | Pressão: {} | Tempo Verde: {}s", winningIntersection, maxPressure, finalGreenTime);

            CommandDTO command = new CommandDTO(Instant.now().toString(), winningIntersection, "ABRIR_SEMAFORO", finalGreenTime);
            rabbitTemplate.convertAndSend("traffic.command", command);
            logger.info("📤 [COMANDO ENVIADO] Ordem despachada para a mensageria!");

            // Salvar no PostgreSQL
            TrafficDecision record = new TrafficDecision(LocalDateTime.now(), winningIntersection, "ABRIR_SEMAFORO", finalGreenTime, maxPressure);
            decisionRepository.save(record);
            logger.info("💾 [DADO SALVO] Decisão de tráfego guardada no banco de dados.");

            // Atualizar cache Redis (TTL 5 min configurado no RedisConfig)
            salvarUltimaDecisao(winningIntersection, command);
        }
    }

    public void fallbackCalculateGreenTime(TrafficBatchDTO batch, Throwable t) {
        logger.error("⚠️ Circuit Breaker ativado! Falha ao calcular tempo verde para o lote. Motivo: {}", t.getMessage());
    }

    public void handleEmergency(EmergencyAlertDTO alert) {
        if (alert.deteccoes() != null && !alert.deteccoes().isEmpty()) {
            // Descobre em qual cruzamento a ambulância está
            String cruzamentoAmbulancia = alert.deteccoes().get(0).cruzamentoId();
            
            logger.warn("🚑 ACIONANDO PROTOCOLO DE EMERGÊNCIA PARA O CRUZAMENTO: {}", cruzamentoAmbulancia);
            
            // Envia um comando prioritário com 45 segundos de verde e ação EMERGENCIA
            CommandDTO command = new CommandDTO(Instant.now().toString(), cruzamentoAmbulancia, "EMERGENCIA", 45);
            rabbitTemplate.convertAndSend("traffic.command", command);
            
            // Salvar no PostgreSQL
            TrafficDecision record = new TrafficDecision(LocalDateTime.now(), cruzamentoAmbulancia, "EMERGENCIA_AMBULANCIA", 45, 999.0);
            decisionRepository.save(record);
            salvarUltimaDecisao(cruzamentoAmbulancia, command);
        }
    }

    @CachePut(value = "ultimaDecisao", key = "#intersectionId")
    public CommandDTO salvarUltimaDecisao(String intersectionId, CommandDTO command) {
        return command;
    }

    @Cacheable(value = "ultimaDecisao", key = "#intersectionId")
    public CommandDTO obterUltimaDecisao(String intersectionId) {
        return null; // retorna null se nao houver cache (miss)
    }

    /**
     * Motor de Inferência Fuzzy Manual
     */
    private double calculateFuzzyPressure(long carros, long motos, long pesados) {
        long totalVehiculos = carros + motos + pesados;
        if (totalVehiculos == 0) return 0.0;

        // 1. FUZZIFICAÇÃO (Mapeando os dados para graus de pertinência de 0.0 a 1.0)
        // Volume de Tráfego
        double volumeBaixo = Math.max(0, Math.min(1, (10.0 - totalVehiculos) / 10.0)); // 1.0 se 0 carros, 0.0 se > 10
        double volumeAlto = Math.max(0, Math.min(1, (totalVehiculos - 5.0) / 10.0));   // 0.0 se < 5 carros, 1.0 se > 15

        // Proporção de Veículos Pesados (Eles afetam muito a velocidade de arranque)
        double proporcaoPesados = (double) pesados / totalVehiculos;
        double pesadosBaixo = Math.max(0, Math.min(1, (0.3 - proporcaoPesados) / 0.3)); // 1.0 se 0%, 0.0 se > 30%
        double pesadosAlto = Math.max(0, Math.min(1, (proporcaoPesados - 0.1) / 0.3));  // 0.0 se < 10%, 1.0 se > 40%

        // 2. REGRAS DE INFERÊNCIA (Lógica AND = Math.min)
        double regra1 = Math.min(volumeBaixo, pesadosBaixo); // Pressão Baixa (peso 10)
        double regra2 = Math.min(volumeBaixo, pesadosAlto);  // Pressão Média (peso 20)
        double regra3 = Math.min(volumeAlto, pesadosBaixo);  // Pressão Alta (peso 30)
        double regra4 = Math.min(volumeAlto, pesadosAlto);   // Pressão Muito Alta (peso 40)

        // 3. DEFUZZIFICAÇÃO (Média Ponderada para converter regras em tempo)
        double numerador = (regra1 * 10) + (regra2 * 20) + (regra3 * 30) + (regra4 * 40);
        double denominador = regra1 + regra2 + regra3 + regra4;

        if (denominador == 0) return 10.0; // Valor base se não houver peso

        return numerador / denominador;
    }
} // Fim da classe TrafficLogicService