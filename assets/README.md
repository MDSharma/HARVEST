# Assets Directory

This directory contains static files served by the Dash application.

## Partner Institution Logos

Place your partner institution logo files here as configured in `config.py`:

- `UOE.png` - University of Exeter logo
- `UM.jpg` - Maastricht University logo  
- `ARIA.jpg` - Advanced Research and Invention Agency logo

### Requirements

- Supported formats: PNG, JPG, JPEG, SVG
- Recommended size: Maximum height of 120px for best display
- Transparent backgrounds work best for PNG files

### Configuration

Logo files are configured in `config.py` under the `PARTNER_LOGOS` setting:

```python
PARTNER_LOGOS = [
    {
        "name": "University of Exeter",
        "url": "UOE.png",  # Filename in this directory
        "alt": "University of Exeter Logo"
    },
    # ... additional logos
]
```

The logos will be displayed in a responsive grid at the bottom of the page:
- 3 columns on desktop
- 2 columns on tablet
- 1 column on mobile

## Other Static Assets

You can also place other static assets (CSS, JS, images) in this directory. They will be automatically served by Dash at the `/assets/` URL path.
