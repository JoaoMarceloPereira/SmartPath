package com.smartpath.logiccontroller.repository;

import com.smartpath.logiccontroller.model.TrafficDecision;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface TrafficDecisionRepository extends JpaRepository<TrafficDecision, Long> {
}