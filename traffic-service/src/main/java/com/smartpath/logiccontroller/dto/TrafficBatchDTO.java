package com.smartpath.logiccontroller.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record TrafficBatchDTO(
    @JsonProperty("timestamp_lote") String timestampLote,
    List<DetectionDTO> deteccoes
) {}