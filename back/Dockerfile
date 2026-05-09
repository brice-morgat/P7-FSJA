FROM gradle:8.7-jdk17-alpine@sha256:86b77d6cc9e7b1d6928e1ad95d8fb4bd1f71a796a77bfb86216f8d836e87f16e AS build

WORKDIR /workspace/back
COPY back/ ./
RUN gradle --no-daemon clean build

FROM eclipse-temurin:17-jre-alpine@sha256:b0ae54a36f82e04dc6c45e40ca5c55762e20b9a0858ee457faf557d440a9b571

WORKDIR /app
RUN addgroup -S app && adduser -S app -G app
COPY --from=build /workspace/back/build/libs/*.jar /app/microcrm.jar
RUN chown app:app /app/microcrm.jar
USER app

EXPOSE 8080

CMD ["java", "-jar", "/app/microcrm.jar"]
