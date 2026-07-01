package com.smartpath.logiccontroller.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public record CommandDTO(
    String timestamp,
    @JsonProperty("cruzamento_id") String cruzamentoId,
    String acao,
    @JsonProperty("tempo_verde") int tempoVerde
) {}