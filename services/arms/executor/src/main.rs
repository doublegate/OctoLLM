//! OctoLLM Executor Arm
//!
//! Sandboxed execution environment for external tools and commands.

use axum::{routing::get, Router};

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let app = Router::new()
        .route("/health", get(|| async { "OK" }));

    let listener = tokio::net::TcpListener::bind("0.0.0.0:8006")
        .await
        .unwrap();

    tracing::info!("Executor arm listening on {}", listener.local_addr().unwrap());

    axum::serve(listener, app)
        .await
        .unwrap();
}
