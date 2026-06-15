package com.smartpath.logiccontroller.service;

import org.springframework.stereotype.Service;

@Service
public class FuzzyTrafficService {

    /**
     * Motor Fuzzy Simplificado: Calcula o tempo verde (0 a 120s)
     * baseado na pressão do trânsito e no tempo de inanição (starvation).
     */
    public int calcularTempoVerde(int carros, int motos, int pesados, int starvationTime) {
        // Pesos configuráveis (alinhados com a configuração Python)
        double pesoCarro = 1.5;
        double pesoMoto = 1.0;
        double pesoPesado = 3.0;

        double pressaoTrafego = (carros * pesoCarro) + (motos * pesoMoto) + (pesados * pesoPesado);

        // Regras baseadas em limites (Simulação Fuzzy: Baixo, Médio, Alto)
        int tempoCalculado = 5; // Tempo mínimo de 5 segundos

        if (pressaoTrafego >= 50) {
            tempoCalculado = 60; // Tráfego Intenso
        } else if (pressaoTrafego >= 20) {
            tempoCalculado = 30; // Tráfego Moderado
        } else if (pressaoTrafego > 0) {
            tempoCalculado = 15; // Tráfego Leve
        }

        // Fator de Starvation: Se a via está esperando muito, ganha tempo extra
        tempoCalculado += (starvationTime / 5); 

        return Math.max(5, Math.min(tempoCalculado, 120)); // Limita entre 5 e 120s
    }
}