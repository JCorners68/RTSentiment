# Start from the official PostgreSQL 14 image
FROM postgres:14

# Set environment variables to avoid interactive prompts during installs
ENV DEBIAN_FRONTEND=noninteractive

# Switch to root user to install packages
USER root

# Install necessary build dependencies
# Combined essential tools and specific libraries needed
# Install necessary build dependencies including lsb-release
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    git \
    cmake \
    ca-certificates \
    wget \
    # --- ADD THIS PACKAGE ---
    lsb-release \
    # -----------------------
    postgresql-server-dev-14 \
    libssl-dev \
    zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*

# Install Apache Arrow and Parquet development libraries using the official Apache repo
# (This block should now work because lsb-release is installed)
RUN wget https://apache.jfrog.io/artifactory/arrow/$(lsb_release --id --short | tr 'A-Z' 'a-z')/apache-arrow-apt-source-latest-$(lsb_release --codename --short).deb \
    && apt-get install -y ./apache-arrow-apt-source-latest-$(lsb_release --codename --short).deb \
    && rm -f ./apache-arrow-apt-source-latest-$(lsb_release --codename --short).deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       libarrow-dev \
       libparquet-dev \
    # Clean up apt lists after install
    && rm -rf /var/lib/apt/lists/*

# Clone, build, and install parquet_fdw from the specified repository
WORKDIR /tmp
RUN git clone https://github.com/adjust/parquet_fdw.git \
    && cd parquet_fdw \
    # --- Build and Install Step ---
    && make \
    && make install \
    # -----------------------------
    && cd / \
    && rm -rf /tmp/parquet_fdw

# Switch back to the postgres user before copying SQL or finishing
USER postgres

# Copy the SQL initialization script to run on database startup
# Ensure init-fdw.sql is in the same directory as the Dockerfile (or adjust path)
# COPY init-fdw.sql /docker-entrypoint-initdb.d/

# Reset workdir (optional, good practice)
WORKDIR /var/lib/postgresql/data

# The base image's entrypoint will handle starting PostgreSQL
# CMD ["postgres"] # Inherited from base image, no need to redefine usually