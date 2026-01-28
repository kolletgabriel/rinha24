FROM eclipse-temurin:21.0.1_12-jdk-jammy

WORKDIR /opt

# Installing Gatling and removing example/tutorial files:
ARG GATLING_VERSION="3.10.3"
ARG URL="https://repo1.maven.org/maven2/io/gatling/highcharts/gatling-charts-highcharts-bundle/${GATLING_VERSION}/gatling-charts-highcharts-bundle-${GATLING_VERSION}-bundle.zip"
RUN apt-get update && apt-get install unzip \
    && curl -fsSL "$URL" > ./gatling.zip \
    && unzip -d . ./gatling.zip \
    && mv gatling-charts-highcharts-bundle-${GATLING_VERSION} gatling \
    && rm ./gatling.zip \
    && rm -rf gatling/user-files/resources/* \
    && rm -rf gatling/user-files/simulations/*

# Using files from the challenge:
COPY ./user-files/simulations ./gatling/user-files/simulations

ENTRYPOINT ["gatling/bin/gatling.sh"]
CMD ["-rm", "local", "-s", "RinhaBackendCrebitosSimulation", "-rd", "Rinha de Backend - 2024/Q1: Crébito"]
