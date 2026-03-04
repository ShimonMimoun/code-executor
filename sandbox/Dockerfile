# ================================================
# Code Executor Sandbox
# Multi-language execution environment
# ================================================

FROM python:3.12-slim AS base

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install common utilities, Java, Maven, and prerequisites
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    bash \
    ca-certificates \
    git \
    gnupg \
    coreutils \
    default-jdk \
    maven \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Go 1.22
RUN curl -fsSL https://go.dev/dl/go1.22.10.linux-amd64.tar.gz | tar -C /usr/local -xzf - \
    && ln -s /usr/local/go/bin/go /usr/local/bin/go

# Install .NET 8 SDK
RUN wget https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -O packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt-get update \
    && apt-get install -y dotnet-sdk-8.0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root sandbox user
RUN groupadd -g 1000 sandbox && \
    useradd -u 1000 -g sandbox -m -s /bin/bash sandbox

# Set environment variables for runtimes
ENV GOPATH=/tmp/gopath
ENV GOCACHE=/tmp/gocache
ENV DOTNET_CLI_HOME=/tmp
ENV DOTNET_NOLOGO=1
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1

# Set working directory
WORKDIR /home/sandbox

# Switch to non-root user
USER sandbox

# Default entrypoint
CMD ["bash"]
