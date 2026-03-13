"""Prompt templates for LLM-based root cause analysis."""

# ─────────────────────────────────────────────
# System prompt for the LLM
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer (SRE) and DevOps incident responder.
You specialize in Kubernetes, cloud-native applications, and distributed systems.
Your job is to analyze production incidents, identify root causes, and suggest actionable fixes.

When analyzing an incident, you MUST provide your response in the following exact format:

## Incident Title
[A concise, descriptive title for this incident]

## Summary
[2-3 sentence summary of what happened]

## Root Cause
[Detailed explanation of the root cause]

## Impact
[Description of the impact on users/business]

## Suggested Fixes
1. [Immediate fix]
2. [Short-term fix]
3. [Additional fix if applicable]

## Prevention Steps
1. [How to prevent this in the future]
2. [Monitoring/alerting improvements]
3. [Additional prevention if applicable]

Be specific, technical, and actionable. Reference Kubernetes concepts, pod states, 
and infrastructure components where relevant."""


# ─────────────────────────────────────────────
# Analysis prompt template
# ─────────────────────────────────────────────

ANALYSIS_PROMPT = """Analyze the following Kubernetes production incident and provide a root cause analysis.

**Anomaly Type:** {anomaly_type}
**Affected Service:** {service_name}
**Severity:** {severity}
**Detected At:** {detected_at}
**Affected Pods:** {affected_pods}
**Confidence Score:** {confidence}

**Detection Metrics:**
{metrics}

**Related Log Entries:**
```
{log_entries}
```

Please provide a detailed root cause analysis following the format specified in your instructions."""


# ─────────────────────────────────────────────
# Mock RCA templates (when Ollama is unavailable)
# ─────────────────────────────────────────────

MOCK_RCA_TEMPLATES: dict[str, dict] = {
    "OOMKilled": {
        "title": "Container OOMKilled - Memory Exhaustion in {service}",
        "summary": (
            "The {service} pod was terminated by the Linux OOM killer after exceeding its memory "
            "limit of the configured resource allocation. This indicates either a memory leak in the "
            "application or insufficient memory limits for the current workload."
        ),
        "root_cause": (
            "The container's memory usage grew beyond its configured limit, triggering the Kubernetes "
            "OOM killer (exit code 137). Common causes include: (1) Memory leak in the application, "
            "possibly from unclosed connections, growing caches, or reference cycles. (2) Sudden "
            "traffic spike causing more objects to be held in memory. (3) Memory limits set too low "
            "for the application's normal operating requirements. The Java heap space error suggests "
            "the JVM's maximum heap size (-Xmx) may be misconfigured relative to the container's "
            "memory limit."
        ),
        "impact": (
            "Service degradation for {service}. Pod restarts cause brief outages (10-30s) during "
            "which requests to this service will fail or timeout. If the pod enters CrashLoopBackOff, "
            "extended downtime follows. Dependent services may also be affected through cascading failures."
        ),
        "fixes": [
            "IMMEDIATE: Increase memory limits in the pod spec (resources.limits.memory) to 1.5x current value",
            "IMMEDIATE: For JVM apps, set -Xmx to 75% of container memory limit and enable -XX:+UseContainerSupport",
            "SHORT-TERM: Profile the application's memory usage to identify potential memory leaks",
            "SHORT-TERM: Implement graceful degradation and circuit breakers for dependent services",
            "LONG-TERM: Set up Vertical Pod Autoscaler (VPA) to auto-tune resource limits",
        ],
        "prevention": [
            "Configure memory-based HPA to scale out before hitting limits",
            "Set up Prometheus alerts for memory usage at 70% and 85% thresholds",
            "Implement memory profiling in CI/CD pipeline to catch leaks before deployment",
            "Use resource quotas and limit ranges to enforce reasonable limits",
        ],
    },
    "CrashLoopBackOff": {
        "title": "CrashLoopBackOff - {service} Failing to Start",
        "summary": (
            "The {service} container is repeatedly crashing during startup, causing Kubernetes to "
            "enter CrashLoopBackOff state with exponential backoff on restart attempts. The service "
            "is effectively down."
        ),
        "root_cause": (
            "The container fails to start successfully, most likely due to: (1) A required dependency "
            "(database, config server, or external service) being unreachable. (2) Missing or invalid "
            "configuration (ConfigMap/Secret not mounted or containing wrong values). (3) Application "
            "bug introduced in the latest deployment causing immediate crash on startup. The startup "
            "and readiness probe failures confirm the application never reaches a healthy state."
        ),
        "impact": (
            "Complete outage of {service}. All requests to this service will fail. Dependent services "
            "will experience errors when calling {service}. The exponential backoff means recovery time "
            "increases with each failed attempt (10s, 20s, 40s, up to 5 minutes)."
        ),
        "fixes": [
            "IMMEDIATE: Check pod logs with 'kubectl logs <pod> --previous' to see the crash reason",
            "IMMEDIATE: Verify all dependencies are running: database, config server, message queue",
            "IMMEDIATE: If caused by bad deploy, rollback with 'kubectl rollout undo deployment/{service}'",
            "SHORT-TERM: Verify ConfigMaps and Secrets are correctly mounted and contain valid values",
            "SHORT-TERM: Check if resource limits are too restrictive for startup (startup probes may need more time)",
        ],
        "prevention": [
            "Implement init containers to wait for dependencies before starting the main container",
            "Use startup probes with generous thresholds separate from liveness probes",
            "Implement canary deployments to catch startup issues before full rollout",
            "Add pre-deployment health checks in CI/CD pipeline",
        ],
    },
    "HighErrorRate": {
        "title": "HTTP 5xx Error Spike - {service} Backend Failures",
        "summary": (
            "A significant increase in HTTP 5xx errors has been detected in {service}, indicating "
            "backend failures. The error rate has exceeded normal thresholds, and circuit breakers "
            "have been triggered."
        ),
        "root_cause": (
            "The spike in 500-series errors indicates backend service failures. Likely causes include: "
            "(1) Database connection pool exhaustion under high load. (2) Upstream service degradation "
            "causing timeout cascades. (3) Application exception (NullPointerException/unhandled error) "
            "in a code path triggered by recent deployment. (4) Resource contention (CPU/memory) causing "
            "request processing timeouts."
        ),
        "impact": (
            "User-facing impact: requests to {service} are failing with 500/502/503 errors. "
            "Circuit breakers have opened, rejecting all traffic to the failing service. "
            "This may cascade to other services in the request chain, causing widespread user-facing errors."
        ),
        "fixes": [
            "IMMEDIATE: Check if recent deployment caused the issue; rollback if needed",
            "IMMEDIATE: Scale up the service horizontally (increase replicas)",
            "IMMEDIATE: Check database and upstream service health",
            "SHORT-TERM: Tune circuit breaker thresholds and add fallback responses",
            "SHORT-TERM: Increase connection pool sizes and add request queuing",
        ],
        "prevention": [
            "Implement progressive rollouts (canary/blue-green) with automatic rollback on error rate increase",
            "Set up error rate alerts at 1%, 5%, and 10% thresholds",
            "Add request rate limiting to prevent overload",
            "Implement bulkhead pattern to isolate failures",
        ],
    },
    "DatabaseConnectionExhaustion": {
        "title": "Database Connection Pool Exhaustion - {service}",
        "summary": (
            "All database connections in the connection pool for {service} have been consumed. "
            "New queries are failing with timeout errors, causing cascading failures in the service."
        ),
        "root_cause": (
            "The database connection pool has been fully exhausted. Root causes include: "
            "(1) Slow queries holding connections for too long (likely due to missing indexes or "
            "lock contention). (2) Connection leak where connections are not properly returned to the pool. "
            "(3) Sudden traffic spike exceeding the pool's maximum capacity. (4) Database server under "
            "heavy load, causing all queries to slow down and connections to pile up."
        ),
        "impact": (
            "All database operations for {service} are failing. Any feature requiring database access "
            "returns errors. Risk of data inconsistency if transactions are partially completed. "
            "Dependent services also affected."
        ),
        "fixes": [
            "IMMEDIATE: Identify and kill long-running queries: SELECT * FROM pg_stat_activity WHERE state != 'idle'",
            "IMMEDIATE: Increase pool size temporarily (but don't exceed database max_connections)",
            "SHORT-TERM: Add query timeouts (statement_timeout) to prevent queries from holding connections indefinitely",
            "SHORT-TERM: Fix slow queries by adding missing indexes",
            "SHORT-TERM: Implement connection pool monitoring with metrics export",
        ],
        "prevention": [
            "Set up alerts on connection pool utilization at 70% and 90%",
            "Implement connection pool metrics in Prometheus/Grafana",
            "Use PgBouncer or similar connection pooler for PostgreSQL",
            "Regular slow query log analysis and index optimization",
        ],
    },
    "DiskPressure": {
        "title": "Disk Pressure - Volume Capacity Critical on {service}",
        "summary": (
            "The persistent volume for {service} is at or near full capacity. Write operations are "
            "failing, and Kubernetes has flagged the node with DiskPressure condition, which may "
            "trigger pod eviction."
        ),
        "root_cause": (
            "Disk space exhaustion caused by: (1) Log files growing unbounded without proper rotation. "
            "(2) Database WAL (Write-Ahead Log) segments accumulating faster than they are cleaned up. "
            "(3) Elasticsearch indices growing without lifecycle management. (4) Temporary files not "
            "being cleaned up. The PVC was provisioned with insufficient capacity for the workload's "
            "growth rate."
        ),
        "impact": (
            "All write operations to the volume are failing (ENOSPC). For databases, this means no new "
            "transactions can be written, effectively causing a complete write outage. Pods may be evicted "
            "from the node. Data integrity is at risk if write failures occur mid-transaction."
        ),
        "fixes": [
            "IMMEDIATE: Identify and delete unnecessary files (old logs, temp files, core dumps)",
            "IMMEDIATE: If Elasticsearch, delete old indices or increase disk watermark thresholds temporarily",
            "SHORT-TERM: Resize the PVC (if storage class supports volume expansion)",
            "SHORT-TERM: Implement log rotation with size-based limits",
            "SHORT-TERM: For databases, run VACUUM (PostgreSQL) or optimize tables",
        ],
        "prevention": [
            "Implement PVC usage monitoring with alerts at 70%, 85%, and 95%",
            "Set up automated log rotation and retention policies",
            "Use Elasticsearch ILM (Index Lifecycle Management) for automatic rollover",
            "Provision PVCs with growth headroom (2-3x current usage for 6 months)",
        ],
    },
    "NetworkDNSFailure": {
        "title": "DNS Resolution Failures Impacting {service}",
        "summary": (
            "Intermittent DNS resolution failures are occurring for {service}, preventing it from "
            "connecting to dependent services. CoreDNS may be experiencing issues."
        ),
        "root_cause": (
            "DNS resolution failures in Kubernetes typically caused by: (1) CoreDNS pods being "
            "overloaded or unhealthy. (2) ndots configuration causing excessive DNS lookups. "
            "(3) Network policy blocking DNS traffic (UDP/TCP port 53). (4) Upstream DNS server "
            "issues. The NXDOMAIN responses suggest the service names are not resolving within "
            "the cluster DNS."
        ),
        "impact": (
            "Services cannot discover and connect to their dependencies. Intermittent failures "
            "cause request timeouts and errors. Service mesh sidecars may also be affected, "
            "amplifying the problem across the cluster."
        ),
        "fixes": [
            "IMMEDIATE: Check CoreDNS pod health: kubectl get pods -n kube-system -l k8s-app=kube-dns",
            "IMMEDIATE: Verify DNS resolution from affected pod: kubectl exec -it <pod> -- nslookup <service>",
            "SHORT-TERM: Scale up CoreDNS replicas if under high load",
            "SHORT-TERM: Optimize ndots in pod DNS config (set to 2 instead of default 5)",
            "SHORT-TERM: Add NodeLocal DNSCache for caching",
        ],
        "prevention": [
            "Deploy NodeLocal DNSCache daemonset for resilient DNS caching",
            "Monitor CoreDNS metrics (request rate, latency, NXDOMAIN rate)",
            "Set appropriate ndots value in pod spec to reduce unnecessary DNS lookups",
            "Implement DNS-based health checks in service mesh configuration",
        ],
    },
    "CPUThrottling": {
        "title": "CPU Throttling Causing Latency Degradation - {service}",
        "summary": (
            "The {service} container is being CPU throttled, with a high percentage of CPU periods "
            "being throttled. This is causing significant latency increases and probe failures."
        ),
        "root_cause": (
            "CPU throttling occurs when a container's CPU usage exceeds its configured CPU limit. "
            "The CFS (Completely Fair Scheduler) enforces these limits by throttling the container. "
            "Causes: (1) CPU limits set too low for the workload (especially for bursty workloads). "
            "(2) Garbage collection or JIT compilation spikes in JVM/interpreted languages. "
            "(3) Increased traffic requiring more CPU cycles per request."
        ),
        "impact": (
            "Request latency has increased significantly (p99 from normal to >1800ms). Liveness and "
            "readiness probes may fail, causing unnecessary restarts. Overall throughput of the service "
            "is reduced."
        ),
        "fixes": [
            "IMMEDIATE: Increase CPU limits in the pod spec (resources.limits.cpu)",
            "IMMEDIATE: Consider removing CPU limits entirely (use only requests) - Google's recommendation",
            "SHORT-TERM: Profile the application to understand CPU usage patterns",
            "SHORT-TERM: Scale horizontally to distribute load across more pods",
        ],
        "prevention": [
            "Monitor container_cpu_cfs_throttled_periods_total in Prometheus",
            "Use VPA recommendations to right-size CPU requests and limits",
            "Consider using Guaranteed QoS class (requests = limits) for critical services",
            "Set up alerts when throttling exceeds 25% of periods",
        ],
    },
    "CertificateExpiry": {
        "title": "TLS Certificate Expired - {service} HTTPS Failing",
        "summary": (
            "TLS certificates used by {service} have expired, causing all HTTPS connections to fail. "
            "This is a critical issue affecting all encrypted traffic."
        ),
        "root_cause": (
            "TLS certificate expiration due to: (1) cert-manager renewal job failure (ACME challenge "
            "timeout or DNS propagation issue). (2) Manual certificates not renewed before expiry. "
            "(3) Certificate secret not updated in Kubernetes after renewal. The expired certificate "
            "causes TLS handshake failures for all HTTPS connections."
        ),
        "impact": (
            "CRITICAL: All HTTPS traffic is failing. Users see ERR_CERT_DATE_INVALID in browsers. "
            "Service-to-service mTLS connections are rejected. API integrations with external partners "
            "are broken. This is a P0 incident with direct revenue impact."
        ),
        "fixes": [
            "IMMEDIATE: Issue an emergency certificate renewal or apply a valid certificate manually",
            "IMMEDIATE: If using cert-manager, check and fix the ACME issuer: kubectl describe certificate <name>",
            "IMMEDIATE: As a temporary workaround, consider HTTP redirect while fixing TLS",
            "SHORT-TERM: Verify cert-manager is running and ACME account is valid",
        ],
        "prevention": [
            "Set up certificate expiry monitoring (cert-manager exports Prometheus metrics)",
            "Alert at 30, 14, and 7 days before expiry",
            "Use cert-manager with auto-renewal configured (renewBefore: 720h)",
            "Implement certificate rotation testing in staging environment",
        ],
    },
}

# Default template for unknown anomaly types
DEFAULT_MOCK_RCA = {
    "title": "Anomaly Detected in {service} - {anomaly_type}",
    "summary": (
        "An anomaly of type '{anomaly_type}' has been detected in {service}. "
        "The system identified unusual patterns in the application logs that require investigation."
    ),
    "root_cause": (
        "Based on the log patterns, the anomaly appears to be related to {anomaly_type}. "
        "Further investigation is needed to determine the exact root cause. "
        "The detected patterns suggest a deviation from normal operating behavior."
    ),
    "impact": (
        "The {service} service may be experiencing degraded performance or intermittent failures. "
        "Dependent services should be monitored for cascading effects."
    ),
    "fixes": [
        "Investigate the affected pods: kubectl describe pod <pod-name>",
        "Check recent deployments: kubectl rollout history deployment/{service}",
        "Review resource utilization: kubectl top pods",
        "Check dependent service health",
    ],
    "prevention": [
        "Set up comprehensive monitoring and alerting for this failure mode",
        "Implement health checks and circuit breakers",
        "Document this incident type in the runbook",
    ],
}
