package com.smartpath.logiccontroller.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "traffic_decision")
public class TrafficDecision {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "traffic_decision_seq")
    @SequenceGenerator(name = "traffic_decision_seq", sequenceName = "traffic_decision_id_seq", allocationSize = 1)
    private Long id;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "intersection_id", nullable = false)
    private String intersectionId;

    @Column(name = "action", nullable = false)
    private String action;

    @Column(name = "green_time", nullable = false)
    private int greenTime;

    @Column(name = "pressure", nullable = false)
    private double pressure;

    public TrafficDecision() {}

    public TrafficDecision(LocalDateTime createdAt, String intersectionId, String action, int greenTime, double pressure) {
        this.createdAt = createdAt;
        this.intersectionId = intersectionId;
        this.action = action;
        this.greenTime = greenTime;
        this.pressure = pressure;
    }

    public Long getId() { return id; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public String getIntersectionId() { return intersectionId; }
    public String getAction() { return action; }
    public int getGreenTime() { return greenTime; }
    public double getPressure() { return pressure; }
}
