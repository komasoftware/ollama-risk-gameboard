# Simple Dockerfile for Rust Risk Board Game Server
FROM rust:1.82-slim

WORKDIR /app

# Copy only manifest first for caching
COPY Cargo.toml ./

# Create a dummy src/main.rs to build dependencies
RUN mkdir src && echo "fn main() {}" > src/main.rs && cargo build --release && rm src/main.rs

# Copy the actual source code
COPY src/ ./src/

# Build the application (this will generate Cargo.lock)
RUN cargo build --release

# Copy config files
COPY Rocket.toml ./
COPY game_config.json ./
COPY custom_players.json ./
COPY conquer_probabilities.bin ./

# Expose the port (Cloud Run will set PORT env var)
EXPOSE 8080

# Run the server with dynamic port binding
CMD ["sh", "-c", "ROCKET_PORT=${PORT:-8080} /app/target/release/risk_board_game_server"] 