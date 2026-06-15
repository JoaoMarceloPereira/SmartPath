package com.smartpath.logiccontroller;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

@SpringBootApplication
@EnableDiscoveryClient
public class LogicControllerApplication {
    public static void main(String[] args) {
        SpringApplication.run(LogicControllerApplication.class, args);
    }
}