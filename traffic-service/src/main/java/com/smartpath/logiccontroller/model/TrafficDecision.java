package com.smartpath.logiccontroller.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "traffic_decisions", indexes = { @Index(name = "idx_decision_timestamp", columnList = "createdAt"), @Index(name = "idx_decision_intersection", columnList = "intersectionId") })
public class TrafficDecision {
 
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
 
    @Column(nullable = false)
    private LocalDateTime createdAt;
 
    @Column(nullable = false)
    private String intersectionId;
 
    @Column(nullable = false)
    private String action;
 
    @Column(nullable = false)
    private int greenTimeSeconds;
 
    @Column(nullable = false)
    private double trafficPressure;
 
    public TrafficDecision() {}
 
    public TrafficDecision(LocalDateTime createdAt, String intersectionId, String action, int greenTimeSeconds, double trafficPressure) {
        this.createdAt = createdAt;
        this.intersectionId = intersectionId;
        this.action = action;
        this.greenTimeSeconds = greenTimeSeconds;
        this.trafficPressure = trafficPressure;
    }
 
    public Long getId() { return id; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public String getIntersectionId() { return intersectionId; }
    public String getAction() { return action; }
    public int getGreenTimeSeconds() { return greenTimeSeconds; }
    public double getTrafficPressure() { return trafficPressure; }
}
