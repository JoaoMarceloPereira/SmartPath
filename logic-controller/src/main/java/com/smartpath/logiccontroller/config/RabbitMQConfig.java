package com.smartpath.logiccontroller.config;

import org.springframework.amqp.core.Queue;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitMQConfig {

    public static final String QUEUE_VEHICLE = "vehicle.detected";
    public static final String QUEUE_EMERGENCY = "emergency.alert";
    public static final String QUEUE_COMMAND = "traffic.command";

    @Bean
    public Queue vehicleQueue() {
        return new Queue(QUEUE_VEHICLE, true); // durable = true
    }

    @Bean
    public Queue emergencyQueue() {
        return new Queue(QUEUE_EMERGENCY, true);
    }

    @Bean
    public MessageConverter jsonMessageConverter() {
        return new Jackson2JsonMessageConverter();
    }
}