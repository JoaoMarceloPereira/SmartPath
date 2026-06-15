package com.smartpath.logiccontroller;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;

@SpringBootApplication
@EntityScan(basePackages = "com.smartpath.logiccontroller.model")
@EnableJpaRepositories(basePackages = "com.smartpath.logiccontroller.repository")
public class LogicControllerApplication {

    public static void main(String[] args) {
        SpringApplication.run(LogicControllerApplication.class, args);
        System.out.println("✅ Logic Controller Service iniciado e escutando RabbitMQ!");
     }
}