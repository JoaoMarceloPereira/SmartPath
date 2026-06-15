package com.smartpath.logiccontroller.config;

import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;

@Configuration
public class RabbitMQConfig {

    @Bean
    public Queue vehicleDetectedQueue() {
        return QueueBuilder.durable("vehicle.detected").build();
    }

    @Bean
    public Queue emergencyAlertQueue() {
        return QueueBuilder.durable("emergency.alert").build();
    }

    @Bean
    public Queue signalUpdateQueue() {
        return QueueBuilder.durable("signal.update").build();
    }

    @Bean
    public Queue trafficCommandQueue() {
        return QueueBuilder.durable("traffic.command").build();
    }

    // Adiciona o Conversor Automático de JSON
    @Bean
    public MessageConverter jsonMessageConverter() {
        return new Jackson2JsonMessageConverter();
    }
}