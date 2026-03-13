# AI-Powered DevOps Incident Copilot

> **Automated incident detection, AI-powered root cause analysis, and intelligent incident reporting for Kubernetes environments**

An AI-powered DevOps assistant that automatically analyzes production incidents from Kubernetes logs, detects anomalies using machine learning, generates comprehensive root cause analysis with LLMs, and creates detailed GitHub issues — all without human intervention.

---

## Table of Contents

- [What It Does](#-what-it-does)
- [Architecture](#️-architecture)
- [Usage Guide](#-usage-guide)
- [API Endpoints Reference](#-api-endpoints-reference)
- [Demo Walkthrough](#-demo-walkthrough)
- [Configuration Guide](#-configuration-guide)
- [Use Cases & Applications](#-use-cases--applications)
- [Tips & Best Practices](#-tips--best-practices)
- [Running Tests](#-running-tests)
- [Anomaly Scenarios Explained](#-anomaly-scenarios-explained)
- [Production Deployment Path](#-production-deployment-path)

---

### Demo Architecture (Current Implementation)
```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI DevOps Incident Copilot                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────┐   │
│  │ Log Simulator│───▶│ Anomaly Detector │───▶│  LLM Analyzer   │   │
│  │ (Generates   │    │ • Rule-based     │    │ • Ollama/Llama  │   │
│  │  8 K8s       │    │ • Statistical    │    │ • Mock Templates│   │
│  │  Scenarios)  │    │ • Z-score        │    │ • Structured RCA│   │
│  └──────────────┘    └──────────────────┘    └────────┬────────┘   │
│                                                       │            │
│                                                       ▼            │
│                                             ┌─────────────────┐    │
│                                             │ Incident Manager│    │
│                                             │ • Orchestration │    │
│                                             │ • Storage       │    │
│                                             │ • API           │    │
│                                             └───────┬─────────┘    │
│                                                     │              │
│                          ┌──────────────────────────┼──────┐       │
│                          ▼                          ▼      │       │
│                   ┌────────────┐           ┌──────────┐    │       │
│                   │  GitHub    │           │ SQLite   │    │       │
│                   │  Issues    │           │ Database │    │       │
│                   │ (Auto RCA) │           │(History) │    │       │
│                   └────────────┘           └──────────┘    │       │
│                                                            │       │
└────────────────────────────────────────────────────────────┘       │
```

### Production Architecture (Future Integration)
```
┌─────────────────────────────────────────────────────────────────────┐
│                        Production K8s Cluster                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐       │
│  │ Application  │  │  Fluentd /   │  │    Prometheus        │       │
│  │    Pods      │─▶│   Vector     │─▶│     Metrics          │       │
│  └──────────────┘  └──────┬───────┘  └──────────┬───────────┘       │
└─────────────────────────┬─│────────────────────┬─│──────────────────┘
                          │ │                    │ │
                          ▼ ▼                    ▼ ▼
                   ┌────────────┐         ┌────────────┐
                   │    Loki    │         │ Prometheus │
                   │ (Log Store)│         │   (TSDB)   │
                   └──────┬─────┘         └──────┬─────┘
                          │                      │
                          └──────────┬───────────┘
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │  AI Copilot API     │
                          │  • Real log ingestion│
                          │  • Live metrics     │
                          │  • Enhanced ML      │
                          └─────────┬───────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              ┌──────────┐   ┌──────────┐   ┌──────────┐
              │  GitHub  │   │   Slack  │   │PagerDuty │
              │  Issues  │   │  Alerts  │   │ Incident │
              └──────────┘   └──────────┘   └──────────┘
```

### 📊 **Automated Incident Reporting**
- **GitHub Integration** — Auto-creates detailed issues with full context
- **Rich Metadata** — Severity, affected services, confidence scores, log snippets
- **Actionable Recommendations** — Immediate fixes + long-term prevention strategies

### 🚀 **Production-Ready Architecture**
- **REST API** — Full FastAPI with interactive docs
- **Persistent Storage** — SQLite database for incident history
- **Docker Support** — One-command deployment
- **Comprehensive Tests** — 42 unit tests covering all components

---

## What It Does

```
Simulated K8s Logs → Anomaly Detection → LLM Analysis → GitHub Issue
         ↓                    ↓                ↓              ↓
  8 Scenarios          Rules + Stats      Root Cause     Full RCA Report
  (realistic)          (combined)         (AI-powered)   + Suggested Fixes
```

---

## Usage Guide

**1. Clone the repository and enter the directory**
```bash
git clone <your-repo-url>
cd ai-devops-copilot
```

**2. Create and activate virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows
```

**3. Install all dependencies**
```bash
pip install -r requirements.txt
```

**4. Set up environment configuration**
```bash
cp .env.example .env
# The defaults work perfectly for demo mode (mock LLM, dry-run GitHub)
```

**5. Initialize the database**
```bash
python -c "from src.database import init_db; init_db()"
```

**6. Start the server**
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

**That's it!** The server will start and you'll see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     AI DevOps Incident Copilot - Starting Up
INFO:     Database initialized
INFO:     LLM Mode: Mock (template-based)
INFO:     GitHub: Dry Run
INFO:     Pipeline started - monitoring for anomalies...
```

**Open your browser:**
- API Docs: http://localhost:8000/docs
- Root: http://localhost:8000

---

### Option 2: Run with Docker Compose

Perfect for containerized deployment or if you don't want to install Python dependencies locally.

```bash
# 1. Navigate to project directory
cd ai-devops-copilot

# 2. Build and run
docker compose up --build

# Or run in background (detached mode)
docker compose up --build -d

# 3. View logs
docker compose logs -f copilot

# 4. Stop the containers
docker compose down
```

The API will be available at http://localhost:8000

### Option 3: Run with Ollama (Real AI Analysis)

For production-quality LLM-powered root cause analysis:

```bash
# 1. Install Ollama
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# 2. Start Ollama server (runs on port 11434)
ollama serve

# 3. Pull a model (in a new terminal)
ollama pull llama3.2       # Recommended: fast, 2GB
# OR
ollama pull mistral        # Alternative: also good
# OR  
ollama pull llama3.1:8b    # Larger, more capable

# 4. Update your .env file
# Change these lines:
LLM_MOCK_MODE=false
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# 5. Start the copilot
python -m uvicorn src.main:app --port 8000 --reload
```

**Pro Tip**: Start with mock mode to understand the flow, then switch to Ollama for real AI analysis.

---

### Demo: See It In Action

1. **Start the server** (using any of the methods above)

2. **Open the Interactive API Docs**: http://localhost:8000/docs

3. **Trigger a Manual Scan**:
   - Find `POST /api/v1/scan`
   - Click "Try it out"
   - Click "Execute"

4. **See the Results**:
   ```json
   {
     "message": "Scan completed. 1 incident(s) detected and reported.",
     "incidents": [{
       "incident_id": 1,
       "title": "OOMKilled - Memory Exhaustion in payment-service",
       "severity": "critical",
       "service": "payment-service",
       "summary": "The payment-service pod was terminated...",
       "root_cause": "The container's memory usage grew beyond...",
       "suggested_fixes": [
         "IMMEDIATE: Increase memory limits...",
         "SHORT-TERM: Profile memory usage..."
       ],
       "github_issue_url": "https://github.com/.../issues/1234",
       "confidence": 0.92
     }]
   }
   ```

5. **View Full Incident Details**:
   - Go to `GET /api/v1/incidents/{id}`
   - Enter `1` as the incident_id
   - Execute to see complete RCA with log snippets

### Using the API Programmatically

```bash
# Check pipeline status
curl http://localhost:8000/api/v1/status

# Trigger a scan
curl -X POST http://localhost:8000/api/v1/scan

# List all incidents
curl http://localhost:8000/api/v1/incidents

# Get specific incident
curl http://localhost:8000/api/v1/incidents/1

# View recent logs
curl http://localhost:8000/api/v1/logs?count=50

# Get detector statistics
curl http://localhost:8000/api/v1/detector/stats
```

## API Endpoints Reference

Once running, visit **http://localhost:8000/docs** for the full interactive Swagger UI.

### Core Endpoints

| Method | Endpoint | Description | Use Case |
|--------|----------|-------------|----------|
| `GET` | `/` | API info and available endpoints | Quick overview |
| `GET` | `/health` | Health check | Monitoring, load balancer checks |
| `GET` | `/api/v1/status` | Pipeline status & metrics | Dashboard, monitoring |

### Incident Detection

| Method | Endpoint | Description | Key Response |
|--------|----------|-------------|--------------|
| `POST` | `/api/v1/scan` | **🎯 Trigger manual scan** | Detected incidents with RCA |
| `GET` | `/api/v1/incidents` | List all incidents | Array of incident summaries |
| `GET` | `/api/v1/incidents/{id}` | Get incident details | Full RCA with logs |

---

## Demo Walkthrough - Complete

**1. Start the Application**
```bash
source venv/bin/activate
python -m uvicorn src.main:app --port 8000 --reload
```

**2. Explain the Console Output**
```
INFO: AI DevOps Incident Copilot - Starting Up
INFO: Database initialized
INFO: LLM Mode: Mock (template-based)
INFO: GitHub: Dry Run
INFO: Simulator: Enabled
INFO: Pipeline started - monitoring for anomalies...
```
 Point out: The pipeline is already running in the background, continuously generating logs and scanning for anomalies.

**3. Open the Interactive Docs**
Navigate to: http://localhost:8000/docs

 Explain: "This is auto-generated from our FastAPI code with full request/response schemas."

**4. Show the Pipeline Status**
- Execute `GET /api/v1/status`
- Show:
  - `simulator_running: true` — Mock K8s logs being generated
  - `detector_running: true` — Continuous anomaly scanning
  - `total_logs_processed` — Logs analyzed so far
  - `total_anomalies_detected` — Auto-detected anomalies

**5. Trigger a Manual Scan** (The Highlight!)
- Execute `POST /api/v1/scan`
- Wait 2-3 seconds
- Show the response:

```json
{
  "message": "Scan completed. 1 incident(s) detected and reported.",
  "incidents": [{
    "incident_id": 2,
    "title": "OOMKilled - Memory Exhaustion in payment-service",
    "severity": "critical",
    "service": "payment-service",
    "anomaly_type": "OOMKilled",
    "summary": "The payment-service pod was terminated by the OOM killer...",
    "root_cause": "Container's memory usage exceeded the configured limit...",
    "suggested_fixes": [
      "IMMEDIATE: Increase memory limits in pod spec to 1.5x",
      "SHORT-TERM: Profile application for memory leaks",
      "LONG-TERM: Implement VPA for auto-tuning"
    ],
    "github_issue_url": "https://github.com/.../issues/1234",
    "confidence": 0.92
  }]
}
```

**6. View Full Incident Details**
- Execute `GET /api/v1/incidents/2`
- Show the complete RCA with:
  - Raw log snippets
  - Detailed root cause explanation
  - Prevention steps
  - Metadata (severity, service, timestamp)

**7. Explain the Value Proposition**
> "In a real production environment, this would:
> - Ingest logs from Loki/Elasticsearch instead of simulation
> - Query Prometheus for metrics
> - Use Ollama/GPT-4 for analysis
> - Create actual GitHub/Jira issues
> - Alert via Slack/PagerDuty
> - Save SREs hours of manual triage per incident"

**8. Show Different Anomaly Types** (Optional)
Trigger multiple scans to show variety:
- OOMKilled (memory)
- CrashLoopBackOff (startup failures)  
- HTTP 5xx spikes (backend errors)
- Database connection exhaustion
- Disk pressure
- Certificate expiry

---

## Configuration Guide

All configuration is managed through environment variables (`.env` file). Copy `.env.example` to `.env` and customize.

### Core Settings

| Variable | Default | Options | Description |
|----------|---------|---------|-------------|
| `APP_HOST` | `0.0.0.0` | Any IP/host | Server bind address |
| `APP_PORT` | `8000` | Any port | Server port |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | Logging verbosity |

### LLM Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MOCK_MODE` | `true` | `true` = Use templates, `false` = Use Ollama |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Model name: `llama3.2`, `mistral`, `llama3.1:8b` |

**When to use what:**
- **Mock Mode (`true`)**: Demos, testing, no LLM setup needed, instant RCA
- **Ollama Mode (`false`)**: Real AI analysis, dynamic responses, more detailed insights

### GitHub Integration

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_DRY_RUN` | `true` | `true` = Simulate, `false` = Create real issues |
| `GITHUB_TOKEN` | — | Personal Access Token (get from [GitHub Settings](https://github.com/settings/tokens)) |
| `GITHUB_REPO_OWNER` | `your_github_username` | Your GitHub username |
| `GITHUB_REPO_NAME` | `ai-devops-copilot` | Repository name for issues |

**To create real GitHub issues:**
1. Generate a Personal Access Token at https://github.com/settings/tokens
2. Select scope: `repo` (full repository access)
3. Copy the token
4. Update `.env`:
   ```bash
   GITHUB_DRY_RUN=false
   GITHUB_TOKEN=ghp_your_token_here
   GITHUB_REPO_OWNER=yourusername
   GITHUB_REPO_NAME=your-repo-name
   ```

### Simulator Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SIMULATOR_ENABLED` | `true` | Enable log generation |
| `SIMULATOR_INTERVAL` | `2.0` | Seconds between log batches |
| `SIMULATOR_BATCH_SIZE` | `10` | Normal logs per batch |

**Tuning Tips:**
- Lower `SIMULATOR_INTERVAL` → More logs, faster anomaly injection
- Higher `SIMULATOR_BATCH_SIZE` → More realistic log volume
- Set `SIMULATOR_ENABLED=false` when testing with real logs

### Detection Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SCAN_INTERVAL` | `30` | Seconds between anomaly scans |
| `DATABASE_URL` | `sqlite:///./data/incidents.db` | SQLite database path |

**Performance Tuning:**
- Shorter `SCAN_INTERVAL` → Faster detection, more CPU usage
- Longer `SCAN_INTERVAL` → Lower overhead, delayed detection

### Complete Example: Production-like Setup

```bash
# .env for production simulation with Ollama
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO

# Real LLM analysis
LLM_MOCK_MODE=false
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Real GitHub issues
GITHUB_DRY_RUN=false
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx
GITHUB_REPO_OWNER=myusername
GITHUB_REPO_NAME=incident-tracker

# Aggressive detection
SCAN_INTERVAL=15
SIMULATOR_INTERVAL=1.5
SIMULATOR_BATCH_SIZE=20

DATABASE_URL=sqlite:///./data/production_incidents.db
```

---

## Tips & Best Practices

### For Demos & Presentations

1. **Start Clean**: Delete `data/incidents.db` before presenting for a fresh start
2. **Pre-warm Ollama**: Pull models beforehand if using real LLM
3. **Have Backups**: Keep both mock and Ollama configs ready
4. **Explain Progressive**: Start simple, then show advanced features
5. **Show Logs**: Terminal output adds authenticity

### For Development

1. **Use Mock Mode First**: Iterate quickly without LLM overhead
2. **Test Incrementally**: Run specific test files during development
   ```bash
   pytest tests/test_simulator.py -v
   ```
3. **Hot Reload**: Use `--reload` flag for instant code changes
4. **Check Coverage**: 
   ```bash
   pytest --cov=src --cov-report=html
   open htmlcov/index.html
   ```

### For Production Readiness

1. **Replace SQLite**: Use PostgreSQL for multi-user scenarios
   ```python
   DATABASE_URL=postgresql://user:pass@localhost/incidents
   ```
2. **Add Authentication**: Implement API keys or JWT
3. **Rate Limiting**: Prevent abuse of scan endpoint
4. **Prometheus Metrics**: Export stats for monitoring
5. **Log Retention**: Implement cleanup for old incidents
6. **Caching**: Redis for detector cooldown state
7. **Message Queue**: Kafka/RabbitMQ for high-volume logs

### Performance Optimization

1. **Batch Processing**: Process logs in larger batches
2. **Async Database**: Use `asyncpg` for PostgreSQL
3. **Connection Pooling**: Configure SQLAlchemy pool size
4. **Index Database**: Add indexes on commonly queried fields
   ```sql
   CREATE INDEX idx_severity ON incidents(severity);
   CREATE INDEX idx_created_at ON incidents(created_at DESC);
   ```

### Security Considerations

1. **Environment Variables**: Never commit `.env` to git
2. **API Keys**: Use secrets management (AWS Secrets Manager, Vault)
3. **Input Validation**: Pydantic models already handle this
4. **SQL Injection**: SQLAlchemy ORM prevents this
5. **CORS**: Configure properly for production
6. **HTTPS**: Use behind reverse proxy (nginx/Traefik)

---

## Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_simulator.py -v

# Run with coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html  # View in browser

# Run only API tests
pytest tests/test_api.py -v

# Run and stop on first failure
pytest -x
```

**Test Coverage**: Currently at **42 passing tests** covering:
- Log simulation & scenario generation
- Anomaly detection (rule-based & statistical)
- LLM analyzer with mock mode
- API endpoints (health, status, incidents, scan)
- Database operations

---

### Troubleshooting Common Issues

#### 1. Dependencies Installation Failed

**Problem**: pip install errors  
**Solution**:
```bash
# Upgrade pip first
pip install --upgrade pip

# Then install requirements
pip install -r requirements.txt
```

#### 2. Ollama Server Not Running

**Problem**: Ollama server not running  
**Solution**:
```bash
# In a separate terminal
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

#### 3. "Table 'incidents' doesn't exist"

**Problem**: Database not initialized  
**Solution**:
```bash
python -c "from src.database import init_db; init_db()"
```

#### 4. Port 8000 Already in Use

**Problem**: Another process is using port 8000  
**Solution**:
```bash
# Option 1: Use a different port
python -m uvicorn src.main:app --port 8001

# Option 2: Kill the process on port 8000 (macOS/Linux)
lsof -ti:8000 | xargs kill -9
```

#### 5. Tests Failing

**Problem**: Environment not set up correctly  
**Solution**:
```bash
# Ensure you're in the virtual environment
source venv/bin/activate

# Run tests with proper Python path
./venv/bin/python -m pytest -v

# Or set PYTHONPATH
export PYTHONPATH=$PWD
pytest -v
```

#### 6. Ollama Model Not Found

**Problem**: Model not downloaded  
**Solution**:
```bash
# Pull the model
ollama pull llama3.2

# List available models
ollama list

# Update .env to match an available model
OLLAMA_MODEL=llama3.2
```

#### 7. GitHub API Rate Limit

**Problem**: Too many API calls (if using real GitHub integration)  
**Solution**:
```bash
# Check your rate limit
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit

# Switch to dry-run mode temporarily
GITHUB_DRY_RUN=true
```

### Debug Mode

Enable detailed logging:
```bash
# In .env
LOG_LEVEL=DEBUG

# Then check logs for detailed output
python -m uvicorn src.main:app --port 8000 --reload
```

### Still Having Issues?

1. Check that all files are present: `ls -R src/`
2. Verify Python version: `python --version` (should be 3.11+)
3. Check virtual environment: `which python` (should point to `venv/bin/python`)
4. Review logs for specific error messages
5. Check the [GitHub Issues](../../issues) for similar problems

---

## Anomaly Scenarios Explained

The simulator includes **8 realistic production incident scenarios** based on real-world Kubernetes failures:

### 1. **OOMKilled** 🔴 Critical
**What it is**: Container killed due to memory exhaustion  
**Symptoms**:
- `OutOfMemoryError: Java heap space`
- `Exit code 137`
- Pod restarts frequently

**Real-world causes**:
- Memory leaks (unclosed connections, reference cycles)
- Traffic spikes exceeding capacity
- Misconfigured memory limits

**RCA includes**:
- Heap analysis recommendations
- JVM tuning suggestions
- VPA (Vertical Pod Autoscaler) setup

---

### 2. **CrashLoopBackOff** 🔴 Critical
**What it is**: Container repeatedly crashes during startup  
**Symptoms**:
- `Back-off restarting failed container`
- Startup/readiness probe failures
- Exponential backoff (10s, 20s, 40s, ...)

**Real-world causes**:
- Missing dependencies (database unreachable)
- Invalid configuration (wrong ConfigMap)
- Application bugs in startup code

**RCA includes**:
- Dependency health checks
- Init container recommendations
- Startup probe configuration

---

### 3. **HTTP 5xx Error Spike** 🟠 High
**What it is**: Sudden increase in server errors  
**Symptoms**:
- `500 Internal Server Error`
- `502 Bad Gateway`
- Circuit breakers tripping

**Real-world causes**:
- Database connection pool exhaustion
- Upstream service failures
- Unhandled exceptions from recent deploy

**RCA includes**:
- Connection pool tuning
- Circuit breaker configuration
- Canary deployment suggestions

---

### 4. **Database Connection Exhaustion** 🟠 High
**What it is**: All DB connections consumed  
**Symptoms**:
- `QueuePool limit reached`
- `Cannot acquire connection`
- Queries timing out

**Real-world causes**:
- Slow queries holding connections
- Connection leaks (not closing properly)
- Insufficient pool size for traffic

**RCA includes**:
- Slow query identification
- Connection pooling best practices
- PgBouncer recommendations

---

### 5. **Disk Pressure** 🟠 High
**What it is**: Persistent volume running out of space  
**Symptoms**:
- `No space left on device (ENOSPC)`
- `DiskPressure` node condition
- Pod evictions

**Real-world causes**:
- Unbounded log growth
- Database WAL accumulation
- Missing cleanup jobs

**RCA includes**:
- Log rotation configuration
- PVC expansion guidance
- ILM (Index Lifecycle Management) setup

---

### 6. **DNS/Network Failures** 🟡 Medium
**What it is**: Service discovery failures  
**Symptoms**:
- `NXDOMAIN` errors
- `Name or service not known`
- Intermittent connection failures

**Real-world causes**:
- CoreDNS overload
- Excessive DNS lookups (ndots issue)
- Network policies blocking DNS

**RCA includes**:
- NodeLocal DNSCache setup
- ndots optimization
- CoreDNS scaling guidance

---

### 7. **CPU Throttling** 🟡 Medium
**What it is**: Container CPU limits causing slowdowns  
**Symptoms**:
- High percentage of throttled periods
- Increased latency (p99 spikes)
- Probe failures

**Real-world causes**:
- CPU limits set too low
- Garbage collection spikes
- Traffic increase requiring more CPU

**RCA includes**:
- CPU limit removal considerations
- VPA recommendations
- QoS class optimization

---

### 8. **Certificate Expiry** 🔴 Critical
**What it is**: TLS certificates expired  
**Symptoms**:
- `x509: certificate has expired`
- `ERR_CERT_DATE_INVALID`
- All HTTPS traffic failing

**Real-world causes**:
- cert-manager renewal failure
- Manual certificates not renewed
- ACME challenge timeouts

**RCA includes**:
- cert-manager setup and troubleshooting
- Certificate monitoring alerts
- Automated renewal configuration

---

## Production Deployment Path

This demo simulates a production system. Here's how to adapt it for **real production** use:

### Phase 1: Local Validation (Current State)

### Phase 2: Real Log Integration
**Replace the simulator with actual log sources:**

#### Option A: Kubernetes API
#### Option B: Loki Integration
#### Option C: Fluentd/Vector

### Phase 3: Metrics Integration

### Phase 4: Database Upgrade

### Phase 5: Production LLM Strategy

#### Option A: Self-Hosted (Cost-Effective, Private)
#### Option B: Cloud LLM APIs  

### Phase 6: Enhanced Integrations

#### Slack Notifications
#### PagerDuty Integration
#### Grafana Dashboard  

### Phase 7: Kubernetes Deployment

### Phase 8: Monitoring & Observability

---

### Production Readiness Checklist

- [ ] Replace log simulator with real ingestion
- [ ] Migrate to PostgreSQL
- [ ] Configure production LLM (Ollama/vLLM or API)
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Implement authentication & authorization
- [ ] Add rate limiting
- [ ] Configure backup & disaster recovery
- [ ] Set up CI/CD pipeline
- [ ] Write operational runbooks
- [ ] Implement log retention policies
- [ ] Add incident acknowledgment workflow
- [ ] Configure multi-channel alerting (Slack/PagerDuty/Email)
- [ ] Implement incident correlation
- [ ] Add feedback loop for RCA quality

---
