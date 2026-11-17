package com.logisticsauto.api.repo;

import com.logisticsauto.api.domain.Document;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface DocumentRepository extends JpaRepository<Document, Integer> {
    Optional<Document> findByFilename(String filename);
}
