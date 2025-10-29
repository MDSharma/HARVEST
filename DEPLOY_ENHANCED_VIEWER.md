# Deploy Enhanced PDF Viewer - Quick Guide

## 🚀 Instant Deployment (3 options)

### Option 1: Simple Rename (Fastest - 30 seconds)

```bash
# Backup original
mv assets/pdf_viewer.html assets/pdf_viewer_original.html

# Activate enhanced version
cp assets/pdf_viewer_enhanced.html assets/pdf_viewer.html

# Done! Enhanced viewer is now active.
```

**Rollback** (if needed):
```bash
mv assets/pdf_viewer_original.html assets/pdf_viewer.html
```

---

### Option 2: Configuration Toggle (Recommended - 2 minutes)

**Step 1**: Add to `config.py`:
```python
# PDF Viewer Configuration
USE_ENHANCED_PDF_VIEWER = True  # Set to False to use original viewer
```

**Step 2**: Update `t2t_training_be.py` (find the `/pdf-viewer` route around line 1383):

```python
# OLD CODE:
@server.route('/pdf-viewer')
def pdf_viewer():
    try:
        viewer_path = os.path.join(os.path.dirname(__file__), 'assets', 'pdf_viewer.html')
        # ...

# NEW CODE:
@server.route('/pdf-viewer')
def pdf_viewer():
    """
    Serve the PDF viewer HTML page with highlighting capabilities.
    Uses enhanced or original viewer based on configuration.
    """
    try:
        from config import USE_ENHANCED_PDF_VIEWER
        viewer_file = 'pdf_viewer_enhanced.html' if USE_ENHANCED_PDF_VIEWER else 'pdf_viewer.html'
        viewer_path = os.path.join(os.path.dirname(__file__), 'assets', viewer_file)
        with open(viewer_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading PDF viewer: {e}", exc_info=True)
        return (
            "<html><body><h1>Error loading PDF viewer</h1>"
            "<p>Please try again later.</p></body></html>",
            500
        )
```

**Step 3**: Restart the application

**Toggle** anytime by changing `USE_ENHANCED_PDF_VIEWER` in config.py

---

### Option 3: Direct Backend Update (Alternative - 1 minute)

Update the route in `t2t_training_be.py`:

```python
@server.route('/pdf-viewer')
def pdf_viewer():
    try:
        # Use enhanced viewer
        viewer_path = os.path.join(
            os.path.dirname(__file__),
            'assets',
            'pdf_viewer_enhanced.html'  # ← Changed this line
        )
        with open(viewer_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading PDF viewer: {e}", exc_info=True)
        return (
            "<html><body><h1>Error loading PDF viewer</h1></body></html>",
            500
        )
```

Restart the application.

---

## ✅ Testing the Enhanced Viewer

After deployment:

1. **Open the application**
   - Navigate to the Annotate tab
   - Select a project with PDFs

2. **Select a DOI**
   - Click on any DOI from the project list
   - PDF should load in the viewer

3. **Test new features**:
   - ✓ Try zoom buttons (+/-)
   - ✓ Click "Fit Width" button
   - ✓ Try page jump input
   - ✓ Click the color presets
   - ✓ Click the ? button for help
   - ✓ Try keyboard shortcuts (H, +, -, W, F)
   - ✓ Highlight some text
   - ✓ Check the highlight counter
   - ✓ Save and reload to verify persistence

4. **Verify toolbar**:
   - Buttons should NOT expand/contract
   - Layout should stay fixed
   - Hover effects should be smooth

## 🎯 What You Should See

### Enhanced Toolbar:
```
[← ] [Page 1/10] [→ ] │ [ - ] [100%] [ + ] [📐 Fit] [1:1] │
[🖍️ Highlight] [⬤] [🟡🟢🔴🔵] │ [💾 Save] [🗑️ Clear] [⛶ Full]
```

### Status Bar (below toolbar):
```
✓ Loaded 3 existing highlights          3 highlights
```

### Help Button (bottom-right):
```
  ?   ← Click for keyboard shortcuts
```

## 🐛 Troubleshooting

### Issue: Still seeing old viewer
**Solution**: Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)

### Issue: Buttons still expanding
**Solution**:
1. Clear browser cache
2. Verify you're loading the enhanced file
3. Check browser dev tools console for errors

### Issue: New buttons not working
**Solution**:
1. Check browser console for JavaScript errors
2. Verify PDF.js CDN is accessible
3. Test with original viewer to isolate issue

### Issue: Can't find the route in backend
**Solution**: Search for `@server.route('/pdf-viewer')` in t2t_training_be.py

## 📊 Verification Checklist

After deployment, verify these features work:

- [ ] Toolbar layout is stable (buttons don't shift)
- [ ] Zoom in/out buttons work
- [ ] Zoom level shows percentage
- [ ] Fit Width button calculates correct zoom
- [ ] Page jump input accepts page numbers
- [ ] Color picker is larger and easier to click
- [ ] 4 color presets are clickable
- [ ] Status bar shows below toolbar
- [ ] Highlight counter updates in real-time
- [ ] Fullscreen button toggles fullscreen
- [ ] ? button shows keyboard shortcuts
- [ ] Keyboard shortcuts work (try H, +, -, W, F)
- [ ] Highlighting still works normally
- [ ] Save/load highlights still works
- [ ] Mobile/tablet responsive design works

## 🔄 Rollback Plan

If you need to revert to the original viewer:

**Option 1 users**:
```bash
mv assets/pdf_viewer_original.html assets/pdf_viewer.html
```

**Option 2 users**:
```python
USE_ENHANCED_PDF_VIEWER = False  # in config.py
```
Restart application.

**Option 3 users**:
Change `pdf_viewer_enhanced.html` back to `pdf_viewer.html` in the route.
Restart application.

## 📚 Additional Resources

- **Full Documentation**: PDF_VIEWER_IMPROVEMENTS.md
- **Feature Comparison**: See table in PDF_VIEWER_IMPROVEMENTS.md
- **Keyboard Shortcuts**: Click ? button in viewer or see PDF_VIEWER_IMPROVEMENTS.md

## 🎉 Success!

If all tests pass, the enhanced PDF viewer is successfully deployed!

Users will immediately see:
- Better toolbar layout
- Zoom controls
- Color presets
- Status indicators
- Keyboard shortcuts help
- Professional visual design

No training needed - the interface is intuitive and improvements are immediately noticeable.

---

**Note**: The enhanced viewer maintains full backward compatibility with the original API. No changes to the frontend (t2t_training_fe.py) or database are required.
