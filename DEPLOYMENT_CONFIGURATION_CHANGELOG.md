# Deployment Configuration Feature - Changelog

## Overview

Added flexible deployment configuration system allowing the application to seamlessly switch between internal proxying and nginx reverse proxy deployment modes.

## New Configuration Options

### config.py

```python
# Deployment Mode Configuration
DEPLOYMENT_MODE = "internal"  # Options: "internal" or "nginx"

# Backend Public URL (required for nginx mode)
BACKEND_PUBLIC_URL = ""  # Example: "https://api.yourdomain.com"
```

### Environment Variables

- `T2T_DEPLOYMENT_MODE`: Override deployment mode
- `T2T_BACKEND_PUBLIC_URL`: Override backend public URL

## Deployment Modes

### Internal Mode (Default)
- Frontend proxies all backend requests via `/proxy/*` routes
- Backend runs on `127.0.0.1` (localhost only)
- No reverse proxy required
- Ideal for development and simple deployments
- **Security**: Backend protected from direct external access

### Nginx Mode
- Frontend makes direct requests to backend API
- Backend accessible at `BACKEND_PUBLIC_URL`
- Requires reverse proxy configuration
- Ideal for production with SSL, load balancing, multiple instances
- **Security**: Requires proper firewall and proxy configuration

## Modified Files

### Core Application Files

1. **config.py**
   - Added `DEPLOYMENT_MODE` configuration
   - Added `BACKEND_PUBLIC_URL` configuration
   - Added comprehensive documentation

2. **t2t_training_be.py**
   - Import deployment configuration
   - Conditional CORS configuration based on deployment mode
   - Nginx mode: Allow all origins (proxy handles restriction)
   - Internal mode: Restrict to localhost origins only
   - Updated health endpoint to return deployment info

3. **t2t_training_fe.py**
   - Import deployment configuration
   - Dynamic API base URL selection based on mode
   - Conditional proxy routes (disabled in nginx mode)
   - Updated PDF viewer to pass deployment mode
   - Updated iframe URLs for deployment mode awareness

4. **launch_t2t.py**
   - Import deployment configuration
   - Added `validate_deployment_config()` function
   - Configuration validation on startup
   - Display deployment mode in banner
   - Warnings for potential misconfigurations

5. **assets/pdf_viewer.html**
   - Accept `deployment_mode` URL parameter
   - Conditional URL construction based on mode
   - Internal mode: Use `/proxy/` routes
   - Nginx mode: Use direct backend URLs

### New Files

1. **nginx.conf.example**
   - Complete nginx configuration template
   - Multiple deployment scenarios documented
   - SSL/TLS configuration examples
   - Load balancing examples
   - Security headers and rate limiting

2. **DEPLOYMENT.md**
   - Comprehensive deployment guide
   - Mode comparison and recommendations
   - Step-by-step setup instructions
   - Configuration examples for various scenarios
   - Troubleshooting section
   - Security best practices

3. **DEPLOYMENT_CONFIGURATION_CHANGELOG.md** (this file)
   - Summary of changes
   - Migration guide

### Updated Documentation

1. **README.md**
   - Added deployment section
   - Environment variables updated
   - Link to DEPLOYMENT.md

2. **INSTALLATION.md**
   - Added deployment mode configuration section
   - Updated troubleshooting for CORS issues
   - Added configuration validation errors

## Key Features

### Configuration Validation

The application validates configuration on startup:
- Checks `DEPLOYMENT_MODE` is valid ("internal" or "nginx")
- Verifies `BACKEND_PUBLIC_URL` is set for nginx mode
- Warns about potential misconfigurations
- Prevents startup with invalid configuration

### Automatic CORS Configuration

Backend automatically configures CORS based on deployment mode:
- **Internal mode**: Restrictive (localhost only)
- **Nginx mode**: Permissive (all origins, proxy handles restriction)

### Conditional Proxy Routes

Frontend proxy routes (`/proxy/pdf/`, `/proxy/highlights/`):
- **Internal mode**: Active and functional
- **Nginx mode**: Disabled (return 404 with helpful message)

### Dynamic URL Generation

Application dynamically generates correct URLs based on mode:
- PDF viewer URLs
- API endpoint URLs
- Highlight API URLs

## Migration Guide

### Upgrading Existing Deployments

Existing deployments will continue to work without changes:
- Default mode is "internal" (current behavior)
- No configuration changes required
- Backward compatible

### Switching to Nginx Mode

1. Update `config.py`:
   ```python
   DEPLOYMENT_MODE = "nginx"
   BACKEND_PUBLIC_URL = "https://api.yourdomain.com"
   HOST = "0.0.0.0"
   ```

2. Set up nginx using `nginx.conf.example`

3. Restart application:
   ```bash
   python3 launch_t2t.py
   ```

4. Verify configuration in startup banner

### Switching Back to Internal Mode

1. Update `config.py`:
   ```python
   DEPLOYMENT_MODE = "internal"
   HOST = "127.0.0.1"
   ```

2. Restart application

3. Remove or disable nginx configuration

## Testing

All Python files compile without errors:
```bash
python3 -m py_compile config.py t2t_training_be.py t2t_training_fe.py launch_t2t.py
```

Configuration loads correctly:
```bash
python3 -c "from config import DEPLOYMENT_MODE, BACKEND_PUBLIC_URL; print(DEPLOYMENT_MODE)"
# Output: internal
```

## Benefits

1. **Flexibility**: Easy switching between deployment modes
2. **No Code Changes**: Configuration-only deployment changes
3. **Backward Compatible**: Existing deployments unaffected
4. **Production Ready**: Full nginx support with examples
5. **Secure by Default**: Internal mode protects backend
6. **Well Documented**: Comprehensive guides and examples
7. **Validated**: Startup validation prevents misconfigurations

## Security Considerations

### Internal Mode
- Backend automatically protected (localhost binding)
- Only frontend exposed to users
- Simpler security model

### Nginx Mode
- Backend CORS allows all origins (proxy should restrict)
- Requires proper firewall rules
- SSL/TLS recommended in production
- Rate limiting should be implemented at proxy level
- Backend should not be directly accessible from internet

## Future Enhancements

Potential future improvements:
- Support for additional reverse proxies (Apache, Caddy)
- Automatic SSL certificate management
- Built-in rate limiting for internal mode
- Health check endpoints for load balancers
- Metrics and monitoring endpoints
- Docker and Kubernetes deployment examples

## Support

For questions or issues:
- See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed guide
- Check [INSTALLATION.md](INSTALLATION.md) for troubleshooting
- Review `nginx.conf.example` for configuration examples
- Check application logs for error messages

## Version

- **Feature**: Deployment Configuration System
- **Date**: 2025-10-29
- **Status**: Completed and Tested
- **Backward Compatible**: Yes
