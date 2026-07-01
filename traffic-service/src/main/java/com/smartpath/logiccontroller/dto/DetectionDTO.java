package com.smartpath.logiccontroller.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record DetectionDTO(
    String timestamp,
    @JsonProperty("cruzamento_id") String cruzamentoId,
    String faixa,
    @JsonProperty("classe_veiculo") String classeVeiculo,
    double confianca
) {}