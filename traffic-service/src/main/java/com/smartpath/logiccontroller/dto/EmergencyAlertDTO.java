package com.smartpath.logiccontroller.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record EmergencyAlertDTO(
    String timestamp,
    @JsonProperty("tipo_alerta") String tipoAlerta,
    List<DetectionDTO> deteccoes
) {}