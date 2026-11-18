package com.logisticsauto.api.repo;

import com.logisticsauto.api.domain.Transaction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface TransactionRepository extends JpaRepository<Transaction, Integer> {
    Optional<Transaction> findFirstByDocumentId(Integer documentId);
}
