# 🐳 TEP Demo - Docker Edition

**One-command deployment for Mac, Windows, and Linux**

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)
[![Platform](https://img.shields.io/badge/Platform-Mac%20%7C%20Windows%20%7C%20Linux-green)]()
[![License](https://img.shields.io/badge/License-Proprietary-lightgrey)](LICENSE)

> **Note:** The Docker setup in this folder is from an earlier iteration of
> the project and has not been re-verified against the new Live Copilot
> backend (port 8000 routes added Phase 1). The non-Docker path documented
> in the main [`README.md`](README.md) — `./START_TEP_COPILOT.command` —
> is the supported way to run everything end to end. Use the Docker files
> as a reference; expect to fix the `Dockerfile.backend` `COPY ... || true`
> lines and add `NVIDIA_API_KEY` to `.env.template` before it will build.

---

## 🚀 Quick Start (3 Commands)

```bash
# 1. Configure API keys
cp .env.template .env && nano .env

# 2. Start all services
docker-compose up -d

# 3. Open in browser
open http://localhost:5173
```

**That's it!** No Python, no Node.js, no virtual environments needed.

---

## 📋 What You Get

- ✅ **TEP Simulation** - Tennessee Eastman Process (Fortran-based)
- ✅ **Anomaly Detection** - PyTorch + scikit-learn models
- ✅ **Multi-LLM Analysis** - Claude, Gemini, LMStudio support
- ✅ **RAG System** - Knowledge base with PDF processing
- ✅ **React Frontend** - Real-time data visualization
- ✅ **Flask Console** - System control panel

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Docker Network (tep-network)               │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Backend Container                        │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │   TEP    │  │   LLM    │  │   RAG    │      │  │
│  │  │Simulator │  │  Client  │  │  System  │      │  │
│  │  └──────────┘  └──────────┘  └──────────┘      │  │
│  │         FastAPI (Port 8000)                     │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────┐      ┌──────────────────┐       │
│  │    Frontend      │      │ Unified Console  │       │
│  │  React + Nginx   │      │      Flask       │       │
│  │   Port 5173      │      │    Port 9002     │       │
│  └──────────────────┘      └──────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 Prerequisites

### Install Docker Desktop

**Mac:**
```bash
brew install --cask docker
# Or download: https://docs.docker.com/desktop/setup/install/mac-install/
```

**Windows:**
```bash
# Download: https://docs.docker.com/desktop/setup/install/windows-install/
```

**Linux:**
```bash
sudo apt-get install docker.io docker-compose
sudo systemctl start docker
```

### Get API Keys (Optional)

- **Claude**: https://console.anthropic.com/
- **Gemini**: https://aistudio.google.com/app/apikey

---

## 🛠️ Common Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart a service
docker-compose restart backend

# Rebuild after code changes
docker-compose up -d --build

# Check status
docker-compose ps
```

---

## 🌐 Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:5173 | React UI for data visualization |
| **Backend API** | http://localhost:8000 | FastAPI backend (docs at /docs) |
| **Unified Console** | http://localhost:9002 | Flask control panel |

---

## 📚 Documentation

- **Quick Start**: [DOCKER_QUICK_START.md](DOCKER_QUICK_START.md) - Step-by-step deployment guide
- **Strategy**: [DOCKER_STRATEGY.md](DOCKER_STRATEGY.md) - Architecture decisions and learning path
- **Summary**: [DOCKER_DEPLOYMENT_SUMMARY.md](DOCKER_DEPLOYMENT_SUMMARY.md) - Complete overview

---

## 🧪 Testing

```bash
# Run automated test suite
./test-docker.sh

# Manual testing
docker-compose up -d
curl http://localhost:8000/  # Backend
curl http://localhost:5173/  # Frontend
curl http://localhost:9002/  # Console
```

---

## 🔄 Development Mode

For active development with hot-reload:

```bash
# Use development compose file
docker-compose -f docker-compose.dev.yml up

# Changes auto-reload:
# - backend/*.py (FastAPI)
# - frontend/src/* (Vite HMR)
# - templates/*.html (Flask)
```

---

## 📊 Before vs After Docker

| Aspect | Before | After |
|--------|--------|-------|
| Setup Time | 30-60 min | 5 min |
| Setup Steps | 10+ steps | 3 commands |
| Platform Issues | Mac-specific | Cross-platform |
| Deployment | Multi-step scripts | `docker-compose up -d` |
| Coworker Onboarding | 1-2 hours | 30 minutes |

---

## 🆘 Troubleshooting

**Port already in use:**
```bash
lsof -ti:8000 | xargs kill -9
```

**API keys not working:**
```bash
cat .env  # Verify keys
docker-compose down && docker-compose up -d  # Restart
```

**View detailed logs:**
```bash
docker-compose logs -f backend
```

See [DOCKER_QUICK_START.md](DOCKER_QUICK_START.md) for more troubleshooting.

---

## 🎯 What's Included

### Docker Files
- `docker-compose.yml` - Production orchestration
- `docker-compose.dev.yml` - Development mode
- `Dockerfile.backend` - FastAPI + TEP + LLM + RAG
- `Dockerfile.console` - Flask console
- `frontend/Dockerfile` - React production build
- `frontend/Dockerfile.dev` - React dev server
- `.dockerignore` - Build optimization

### Documentation
- `DOCKER_QUICK_START.md` - Deployment guide
- `DOCKER_STRATEGY.md` - Architecture and learning
- `DOCKER_DEPLOYMENT_SUMMARY.md` - Complete overview
- `test-docker.sh` - Automated testing

---

## 🚀 Next Steps

1. **Deploy locally**: `docker-compose up -d`
2. **Test the system**: `./test-docker.sh`
3. **Share with coworker**: Send `DOCKER_QUICK_START.md`
4. **Iterate**: Gather feedback and optimize

---

## 📞 Support

- **Documentation**: See docs above
- **Test Script**: `./test-docker.sh`
- **Logs**: `docker-compose logs -f`
- **Issues**: Open a GitHub issue

---

## 🎉 Benefits

- ✅ **Cross-platform** - Works on Mac, Windows, Linux
- ✅ **One-command deployment** - No manual setup
- ✅ **Isolated environment** - No dependency conflicts
- ✅ **Easy rollback** - `docker-compose down && git checkout`
- ✅ **Production-ready** - Multi-stage builds, health checks
- ✅ **Interview-ready** - Clear architecture and decisions

---

**Ready to deploy!** 🚀

For detailed instructions, see [DOCKER_QUICK_START.md](DOCKER_QUICK_START.md)

