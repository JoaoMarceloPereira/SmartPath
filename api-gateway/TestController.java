package com.smartpath.apigateway.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/logic")
public class TestController {

    @GetMapping("/status")
    public String getStatus() {
        return "✅ Logic Controller está online e acessível através do API Gateway!";
    }
}