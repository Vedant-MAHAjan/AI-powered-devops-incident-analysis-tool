"""Predefined anomaly scenarios that mimic real Kubernetes production incidents."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class AnomalyScenario:
    """Defines a production incident scenario with realistic log patterns."""

    name: str
    description: str
    anomaly_type: str
    severity: str  # critical, high, medium, low
    services: list[str]
    error_logs: list[str]
    warning_logs: list[str]
    normal_logs_before: list[str]
    weight: float = 1.0  # probability weight for selection


# ─────────────────────────────────────────────
# Scenario Definitions
# ─────────────────────────────────────────────

SCENARIOS: list[AnomalyScenario] = [
    # ── 1. OOMKilled ──
    AnomalyScenario(
        name="OOMKilled - Memory Exhaustion",
        description="Pod killed due to exceeding memory limits, typically caused by memory leaks or traffic spikes",
        anomaly_type="OOMKilled",
        severity="critical",
        services=["payment-service", "order-service"],
        normal_logs_before=[
            "Handling request POST /api/v1/payments - 200 OK (45ms)",
            "Payment processed successfully for order_id={order_id}",
            "Database query executed in 12ms",
            "Cache hit for user session {session_id}",
        ],
        warning_logs=[
            "Memory usage at 78% of limit (624Mi/800Mi)",
            "GC overhead increasing: pause time 120ms (threshold 100ms)",
            "Memory usage at 89% of limit (712Mi/800Mi)",
            "WARNING: Memory pressure detected, heap size 756Mi",
            "GC full collection triggered, reclaimed only 12Mi",
            "Memory usage at 96% of limit (768Mi/800Mi)",
        ],
        error_logs=[
            "FATAL: Container killed due to OOMKilled - exceeded memory limit of 800Mi",
            "ERROR: java.lang.OutOfMemoryError: Java heap space",
            "ERROR: Process exited with code 137 (OOMKilled)",
            "FATAL: Pod payment-service-{pod_hash} OOMKilled, restarting (attempt {restart_count}/5)",
            "ERROR: Unable to allocate 64Mi for request buffer - out of memory",
            "CRITICAL: Service degraded - memory limit exceeded, pod restarting",
        ],
        weight=2.0,
    ),

    # ── 2. CrashLoopBackOff ──
    AnomalyScenario(
        name="CrashLoopBackOff - Repeated Crash",
        description="Container repeatedly crashes and K8s backs off on restart attempts",
        anomaly_type="CrashLoopBackOff",
        severity="critical",
        services=["auth-service", "user-service"],
        normal_logs_before=[
            "Starting auth-service v2.4.1...",
            "Loading configuration from /etc/config/app.yaml",
            "Initializing database connection pool (max=20)",
        ],
        warning_logs=[
            "WARNING: Failed to connect to config server at config-service:8888",
            "WARNING: Retrying connection (attempt 2/3)...",
            "WARNING: Using cached configuration (stale: 2h)",
        ],
        error_logs=[
            "ERROR: Failed to initialize database connection: connection refused to postgres-primary:5432",
            "FATAL: Cannot start service - required dependency 'postgres-primary' is unreachable",
            "ERROR: Startup probe failed: HTTP probe failed with statuscode 503",
            "ERROR: Container auth-service-{pod_hash} restarted {restart_count} times, entering CrashLoopBackOff",
            "FATAL: Back-off restarting failed container auth-service in pod auth-service-{pod_hash}",
            "ERROR: Readiness probe failed: dial tcp 10.244.1.15:8080: connect: connection refused",
        ],
        weight=2.0,
    ),

    # ── 3. High Error Rate (5xx) ──
    AnomalyScenario(
        name="HTTP 5xx Error Spike",
        description="Sudden spike in 500 Internal Server Errors indicating backend failure",
        anomaly_type="HighErrorRate",
        severity="high",
        services=["api-gateway", "product-service", "order-service"],
        normal_logs_before=[
            "GET /api/v1/products - 200 OK (23ms)",
            "GET /api/v1/products/search?q=laptop - 200 OK (89ms)",
            "POST /api/v1/orders - 201 Created (156ms)",
            "GET /healthz - 200 OK (2ms)",
        ],
        warning_logs=[
            "WARNING: Response time exceeded threshold: GET /api/v1/products took 2340ms (threshold: 1000ms)",
            "WARNING: Database connection pool exhausted, queuing requests (12 waiting)",
            "WARNING: Upstream service product-service responding slowly (p99: 3200ms)",
        ],
        error_logs=[
            "ERROR: GET /api/v1/products - 500 Internal Server Error (timeout after 5000ms)",
            "ERROR: POST /api/v1/orders - 502 Bad Gateway - upstream connection refused",
            "ERROR: GET /api/v1/products/{product_id} - 503 Service Unavailable",
            "ERROR: Circuit breaker OPEN for product-service after 15 consecutive failures",
            "ERROR: GET /api/v1/checkout - 500 Internal Server Error: NullPointerException at OrderService.java:245",
            "ERROR: Request failed with status 500: database query timeout after 30s",
        ],
        weight=1.5,
    ),

    # ── 4. Database Connection Exhaustion ──
    AnomalyScenario(
        name="Database Connection Pool Exhaustion",
        description="All database connections consumed, new queries failing",
        anomaly_type="DatabaseConnectionExhaustion",
        severity="high",
        services=["payment-service", "inventory-service", "order-service"],
        normal_logs_before=[
            "Database connection pool status: 8/20 active connections",
            "Query executed: SELECT * FROM orders WHERE id = $1 (5ms)",
            "Transaction committed successfully for order {order_id}",
        ],
        warning_logs=[
            "WARNING: Connection pool utilization at 80% (16/20 connections)",
            "WARNING: Slow query detected: SELECT * FROM products JOIN inventory ON ... took 4500ms",
            "WARNING: Connection pool utilization at 95% (19/20 connections)",
            "WARNING: Query queue growing: 8 queries waiting for connection",
            "WARNING: Long-running transaction detected (txn_id={txn_id}, duration: 45s)",
        ],
        error_logs=[
            "ERROR: Cannot acquire connection from pool - all 20 connections in use (waited 30s)",
            "ERROR: SQLAlchemyError: QueuePool limit of size 20 overflow 10 reached, connection timed out",
            "ERROR: Database query failed: could not obtain connection within 30.0 seconds",
            "FATAL: Payment processing failed for order {order_id}: no database connection available",
            "ERROR: Health check failed: database connection timeout after 10s",
            "ERROR: Deadlock detected between transactions {txn_id} and {txn_id2}",
        ],
        weight=1.5,
    ),

    # ── 5. Disk Pressure / Volume Full ──
    AnomalyScenario(
        name="Disk Pressure - PVC Nearly Full",
        description="Persistent volume running out of space causing write failures",
        anomaly_type="DiskPressure",
        severity="high",
        services=["logging-service", "database-primary", "elasticsearch"],
        normal_logs_before=[
            "Log rotation completed: archived 3 files (total: 450Mi)",
            "Disk usage: /data: 65% (13Gi/20Gi)",
            "Elasticsearch index 'logs-2026.03.12' created successfully",
        ],
        warning_logs=[
            "WARNING: Disk usage at 82% on /data (16.4Gi/20Gi)",
            "WARNING: Node condition DiskPressure detected",
            "WARNING: Disk usage at 91% on /data (18.2Gi/20Gi) - approaching critical threshold",
            "WARNING: PVC data-elasticsearch-0 at 93% capacity",
            "WARNING: Log rotation failed to free sufficient space (needed 2Gi, freed 200Mi)",
        ],
        error_logs=[
            "ERROR: Write failed: no space left on device (/data/logs/app.log)",
            "ERROR: Elasticsearch rejected bulk index: flood stage disk watermark [95%] exceeded on node",
            "FATAL: Cannot write WAL segment: ENOSPC - disk full on /data/pg_wal/",
            "ERROR: Pod evicted due to DiskPressure condition on node worker-3",
            "ERROR: PVC data-volume-0 is FULL (20Gi/20Gi) - writes blocked",
        ],
        weight=1.0,
    ),

    # ── 6. Network / DNS Issues ──
    AnomalyScenario(
        name="DNS Resolution Failures",
        description="CoreDNS or service mesh DNS resolution intermittently failing",
        anomaly_type="NetworkDNSFailure",
        severity="medium",
        services=["api-gateway", "payment-service", "notification-service"],
        normal_logs_before=[
            "Resolved payment-service.default.svc.cluster.local to 10.96.45.12",
            "HTTP connection established to notification-service:8080",
            "gRPC channel ready for order-service:9090",
        ],
        warning_logs=[
            "WARNING: DNS lookup for redis-master.default.svc.cluster.local took 2400ms (threshold: 500ms)",
            "WARNING: Retrying DNS resolution for payment-service (attempt 2/3)",
            "WARNING: CoreDNS response latency spike: p99=3200ms",
        ],
        error_logs=[
            "ERROR: DNS resolution failed: NXDOMAIN for payment-service.default.svc.cluster.local",
            "ERROR: Failed to connect to kafka-broker-0.kafka.svc.cluster.local:9092 - Name or service not known",
            "ERROR: gRPC call to order-service failed: DNS resolution failed for order-service:9090",
            "ERROR: HTTPConnectionPool: Max retries exceeded with url /api/notify (Caused by NewConnectionError: Failed to establish a new connection: [Errno -2] Name or service not known)",
            "ERROR: Service mesh sidecar (envoy) reported: upstream_reset_before_response_started{connection_failure,delayed_connect_error:111}",
        ],
        weight=1.0,
    ),

    # ── 7. CPU Throttling ──
    AnomalyScenario(
        name="CPU Throttling - Resource Limits",
        description="Container being CPU throttled causing increased latency",
        anomaly_type="CPUThrottling",
        severity="medium",
        services=["ml-inference-service", "data-pipeline", "api-gateway"],
        normal_logs_before=[
            "Request processed in 45ms (CPU: 120m used of 500m limit)",
            "Batch inference completed: 100 items in 2.3s",
            "Health check passed, CPU utilization: 35%",
        ],
        warning_logs=[
            "WARNING: CPU throttling detected: 45% of periods throttled in last 60s",
            "WARNING: Request latency p99 increased from 200ms to 1800ms",
            "WARNING: CPU usage at 98% of limit (490m/500m)",
            "WARNING: 67% of CPU periods throttled - consider increasing CPU limits",
        ],
        error_logs=[
            "ERROR: Request timeout after 5000ms - likely due to CPU throttling (89% periods throttled)",
            "ERROR: Liveness probe failed: timeout (CPU throttled, probe took 12s vs 3s threshold)",
            "ERROR: Batch processing deadline exceeded: expected 10s, took 45s due to CPU constraints",
            "ERROR: gRPC deadline exceeded for inference request (throttled 92% of periods)",
        ],
        weight=1.0,
    ),

    # ── 8. Certificate / TLS Expiry ──
    AnomalyScenario(
        name="TLS Certificate Expiration",
        description="TLS certificates expiring or already expired causing connection failures",
        anomaly_type="CertificateExpiry",
        severity="critical",
        services=["ingress-controller", "api-gateway", "payment-service"],
        normal_logs_before=[
            "TLS handshake completed with payment-provider.example.com",
            "Certificate valid: CN=*.example.com, expires 2026-03-20",
            "mTLS connection established with upstream service",
        ],
        warning_logs=[
            "WARNING: TLS certificate for *.example.com expires in 7 days (2026-03-20)",
            "WARNING: Certificate renewal job failed: ACME challenge timed out",
            "WARNING: TLS certificate for *.example.com expires in 2 days",
        ],
        error_logs=[
            "ERROR: TLS handshake failed: x509: certificate has expired (expired on 2026-03-13)",
            "FATAL: Ingress controller cannot serve HTTPS: certificate expired for host api.example.com",
            "ERROR: mTLS connection rejected by payment-provider: client certificate expired",
            "ERROR: All HTTPS requests failing with ERR_CERT_DATE_INVALID",
            "CRITICAL: Production traffic dropping - TLS termination failing at ingress",
        ],
        weight=0.8,
    ),
]


def get_random_scenario() -> AnomalyScenario:
    """Select a random anomaly scenario weighted by probability."""
    weights = [s.weight for s in SCENARIOS]
    return random.choices(SCENARIOS, weights=weights, k=1)[0]


def get_scenario_by_type(anomaly_type: str) -> AnomalyScenario | None:
    """Find a scenario by its anomaly type."""
    for scenario in SCENARIOS:
        if scenario.anomaly_type == anomaly_type:
            return scenario
    return None


# ─────────────────────────────────────────────
# Normal operation log templates
# ─────────────────────────────────────────────

NORMAL_LOG_TEMPLATES = [
    # HTTP Access Logs
    "GET /api/v1/products - 200 OK ({latency}ms)",
    "POST /api/v1/orders - 201 Created ({latency}ms)",
    "GET /api/v1/users/{user_id} - 200 OK ({latency}ms)",
    "PUT /api/v1/cart/{cart_id} - 200 OK ({latency}ms)",
    "GET /healthz - 200 OK ({latency}ms)",
    "GET /readyz - 200 OK ({latency}ms)",
    "DELETE /api/v1/sessions/{session_id} - 204 No Content ({latency}ms)",

    # Business Logic
    "Payment processed successfully for order_id={order_id} amount=${amount}",
    "Order {order_id} status changed from 'pending' to 'confirmed'",
    "User {user_id} authenticated via OAuth2 (provider: google)",
    "Inventory updated: product {product_id} qty={quantity}",
    "Email notification queued for order {order_id} confirmation",
    "Cache hit for session {session_id} (TTL remaining: {ttl}s)",

    # System
    "Database connection pool status: {active}/{max} active connections",
    "Garbage collection completed in {gc_time}ms (heap: {heap}Mi)",
    "Config reload completed successfully (source: configmap/app-config)",
    "Background job 'cleanup-old-sessions' completed: removed {count} sessions",
    "Metrics exported: {metric_count} data points pushed to /metrics endpoint",
    "Health check passed - all dependencies healthy (db: ok, cache: ok, queue: ok)",
]

# Services that generate normal logs
SERVICES = [
    {"name": "api-gateway", "namespace": "default", "container": "api-gateway"},
    {"name": "payment-service", "namespace": "default", "container": "payment-svc"},
    {"name": "order-service", "namespace": "default", "container": "order-svc"},
    {"name": "auth-service", "namespace": "default", "container": "auth-svc"},
    {"name": "product-service", "namespace": "default", "container": "product-svc"},
    {"name": "inventory-service", "namespace": "default", "container": "inventory-svc"},
    {"name": "notification-service", "namespace": "default", "container": "notification-svc"},
    {"name": "user-service", "namespace": "default", "container": "user-svc"},
]
