package com.smartpath.logiccontroller.service;

import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class TrafficSettingsService {

    private final Map<String, Integer> settings = new ConcurrentHashMap<>();

    public TrafficSettingsService() {
        // Valores padrão, alinhados com o script Python
        settings.put("peso_carro", 2); // Ajustado para inteiro
        settings.put("peso_moto", 1);
        settings.put("peso_pesado", 3);
        settings.put("min_green", 5);
        settings.put("max_green", 30);
        settings.put("yellow_duration", 3);
        settings.put("emergency_duration", 45);
    }

    public int getSetting(String key, int defaultValue) {
        return settings.getOrDefault(key, defaultValue);
    }

    public Map<String, Integer> getAllSettings() {
        return Map.copyOf(settings);
    }

    public void updateSettings(Map<String, Integer> newSettings) {
        settings.putAll(newSettings);
    }
}