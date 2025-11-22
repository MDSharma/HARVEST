# HARVEST Documentation

Welcome to the HARVEST (Human-in-the-loop Actionable Research and Vocabulary Extraction Technology) documentation.

## 📚 Documentation Index

### Getting Started
- **[Installation Guide](INSTALLATION.md)** - Complete setup instructions for HARVEST
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Deploy HARVEST in production (internal or nginx mode)
- **[nginx vs Internal Mode](NGINX_VS_INTERNAL_MODE.md)** - Choose the right deployment mode

### Features

#### Literature Management
- **[Semantic Search](SEMANTIC_SEARCH.md)** - AI-powered paper discovery from multiple academic sources
- **[Literature Review](LITERATURE_REVIEW.md)** - Active learning-based paper screening with ASReview
- **[PDF Features](PDF_FEATURES.md)** - PDF download, highlighting, and viewing capabilities

#### Data Collection & Security
- **[Email Verification](EMAIL_VERIFICATION.md)** - OTP-based email validation system
- **[Security Guide](SECURITY.md)** - Security best practices and compliance

### Legal & Compliance
- **[GDPR Privacy Policy](GDPR_PRIVACY.md)** - Privacy policy and data protection compliance

### Configuration & Maintenance
- **[Schema Update Guide](SCHEMA_UPDATE_GUIDE.md)** - Update database schema when new entity/relation types are added
- **[Schema Update Quickstart](SCHEMA_UPDATE_QUICKSTART.md)** - Quick reference for fixing dropdown issues
- **[nginx Configuration Example](nginx.conf.example)** - Sample nginx configuration for reverse proxy deployment

## 🏗️ Architecture Overview

HARVEST is a web-based application for annotating biological literature with semantic relationships. It consists of:

- **Frontend**: Dash/Plotly-based UI (port 8050)
- **Backend**: Flask REST API (port 5001)  
- **Database**: SQLite for storing annotations and metadata
- **PDF Management**: Intelligent multi-source PDF download and viewing
- **Literature Discovery**: Semantic search across Semantic Scholar, arXiv, Web of Science, OpenAlex
- **Literature Screening**: ASReview integration for AI-powered active learning

## 🚀 Quick Start

1. **Install**: Follow [INSTALLATION.md](INSTALLATION.md)
2. **Configure**: Edit `config.py` with your settings
3. **Deploy**: Choose deployment mode from [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
4. **Use**: Access the web interface at `http://localhost:8050`

## 📖 Common Tasks

### Enable Email Verification
See [Email Verification Guide](EMAIL_VERIFICATION.md#quick-start) for OTP setup.

### Set Up Literature Search  
Configure API keys in `config.py` - see [Semantic Search Guide](SEMANTIC_SEARCH.md#configuration).

### Enable Literature Review
Deploy ASReview service and configure - see [Literature Review Guide](LITERATURE_REVIEW.md#deployment).

### Deploy Behind nginx
Follow [Deployment Guide](DEPLOYMENT_GUIDE.md#nginx-reverse-proxy-mode) for nginx setup.

## 🆘 Getting Help

- Check the relevant feature guide above
- Review [Security Guide](SECURITY.md) for security-related questions
- Consult [Deployment Guide](DEPLOYMENT_GUIDE.md) for deployment issues

## 📝 Note on Documentation

This documentation has been consolidated from multiple implementation notes and guides. Archived historical documentation can be found in the `archive/` folder if needed.
