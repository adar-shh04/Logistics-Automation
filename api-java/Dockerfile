# Build stage
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN mvn -q -DskipTests package

# Run stage
FROM eclipse-temurin:21-jre
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN useradd -m appuser
USER appuser
WORKDIR /app
COPY --from=build --chown=appuser:appuser /app/target/*.jar app.jar

EXPOSE 8000
ENTRYPOINT ["java", "-Duser.timezone=UTC", "-jar", "app.jar"]
