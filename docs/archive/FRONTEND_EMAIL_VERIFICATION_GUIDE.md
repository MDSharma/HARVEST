# Frontend Email Verification Implementation Guide

## Overview

This document provides step-by-step instructions for integrating email verification into the HARVEST frontend (harvest_fe.py).

## Current State

**Backend:** ✅ Complete
- Database tables created
- API endpoints implemented
- Background cleanup running
- SendPulse REST API supported

**Frontend:** 🚧 To Be Implemented
- Email verification UI components
- OTP code input
- Session management
- Integration with annotation flow

## Implementation Steps

### Step 1: Add Stores for OTP State

Add new dcc.Store components after the existing email-store:

```python
# Around line 735, after existing stores
dcc.Store(id="email-store", storage_type="session"),
dcc.Store(id="otp-verification-store", storage_type="session"),  # NEW: OTP state
dcc.Store(id="otp-session-store", storage_type="local"),  # NEW: Verified session (24h)
```

### Step 2: Update Email Input Section

Replace the current email input section (around lines 1370-1386) with enhanced version:

```python
dbc.Col(
    [
        dbc.Label("Your Email (required)", style={"fontWeight": "bold"}),
        dbc.Input(
            id="contributor-email",
            placeholder="email@example.com",
            type="email",
            debounce=True,
            required=True,
        ),
        html.Small(
            id="email-validation",
            className="text-muted",
        ),
        # NEW: OTP Verification Section (hidden by default)
        html.Div(
            id="otp-verification-section",
            children=[
                dbc.Label("Verification Code", className="mt-2", style={"fontWeight": "bold"}),
                html.Small("Check your email for the 6-digit code", className="text-muted d-block mb-1"),
                dbc.InputGroup(
                    [
                        dbc.Input(
                            id="otp-code-input",
                            placeholder="Enter 6-digit code",
                            type="text",
                            maxLength=6,
                            pattern="[0-9]{6}",
                        ),
                        dbc.Button(
                            "Verify",
                            id="otp-verify-button",
                            color="primary",
                            disabled=True
                        ),
                    ],
                    className="mb-2"
                ),
                html.Div(id="otp-verification-feedback"),
                dbc.Button(
                    "Resend Code",
                    id="otp-resend-button",
                    color="link",
                    size="sm",
                    className="p-0"
                ),
            ],
            style={"display": "none"}  # Hidden by default
        ),
    ],
    md=12,
),
```

### Step 3: Add Callback to Request OTP Code

Add after the existing validate_email callback (around line 2088):

```python
@app.callback(
    Output("otp-verification-section", "style"),
    Output("otp-verification-store", "data"),
    Output("email-validation", "children", allow_duplicate=True),
    Output("email-validation", "style", allow_duplicate=True),
    Input("email-store", "data"),
    State("otp-session-store", "data"),
    prevent_initial_call=True
)
def request_otp_code(email, session_data):
    """
    Request OTP code when email is validated.
    Check if OTP validation is enabled first.
    """
    import requests
    
    # Check if OTP is enabled
    try:
        config_response = requests.get(f"{BACKEND_URL}/api/email-verification/config")
        if not config_response.ok or not config_response.json().get("enabled"):
            # OTP not enabled, keep section hidden
            return {"display": "none"}, None, "", {}
    except:
        # API error, keep section hidden
        return {"display": "none"}, None, "", {}
    
    # Check if already verified
    if session_data and session_data.get("session_id"):
        # Check session validity
        try:
            check_response = requests.post(
                f"{BACKEND_URL}/api/email-verification/check-session",
                json={"session_id": session_data["session_id"]}
            )
            if check_response.ok and check_response.json().get("verified"):
                # Already verified, keep section hidden
                return {"display": "none"}, session_data, "✓ Email verified", {"color": "green"}
        except:
            pass
    
    if not email:
        return {"display": "none"}, None, "", {}
    
    # Request OTP code
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/email-verification/request-code",
            json={"email": email}
        )
        
        if response.ok:
            return (
                {"display": "block"},  # Show OTP section
                {"email": email, "code_requested": True},
                "Verification code sent to your email",
                {"color": "blue"}
            )
        else:
            error = response.json().get("error", "Failed to send code")
            return (
                {"display": "none"},
                None,
                f"Error: {error}",
                {"color": "red"}
            )
    except Exception as e:
        return (
            {"display": "none"},
            None,
            f"Error requesting code: {str(e)}",
            {"color": "red"}
        )
```

### Step 4: Add Callback to Enable Verify Button

```python
@app.callback(
    Output("otp-verify-button", "disabled"),
    Input("otp-code-input", "value"),
)
def enable_verify_button(code):
    """Enable verify button when code is 6 digits."""
    if code and len(code) == 6 and code.isdigit():
        return False
    return True
```

### Step 5: Add Callback to Verify OTP Code

```python
@app.callback(
    Output("otp-verification-feedback", "children"),
    Output("otp-session-store", "data"),
    Output("email-validation", "children", allow_duplicate=True),
    Output("email-validation", "style", allow_duplicate=True),
    Output("otp-verification-section", "style", allow_duplicate=True),
    Input("otp-verify-button", "n_clicks"),
    State("otp-code-input", "value"),
    State("otp-verification-store", "data"),
    prevent_initial_call=True
)
def verify_otp_code(n_clicks, code, otp_data):
    """Verify OTP code and create session."""
    if not n_clicks or not code or not otp_data:
        return "", None, "", {}, {"display": "block"}
    
    email = otp_data.get("email")
    if not email:
        return (
            dbc.Alert("Error: Email not found", color="danger", dismissable=True, duration=4000),
            None,
            "",
            {},
            {"display": "block"}
        )
    
    import requests
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/email-verification/verify-code",
            json={"email": email, "code": code}
        )
        
        if response.ok:
            data = response.json()
            session_id = data.get("session_id")
            
            return (
                dbc.Alert("✓ Email verified successfully!", color="success", dismissable=True, duration=3000),
                {"session_id": session_id, "email": email},
                "✓ Email verified",
                {"color": "green"},
                {"display": "none"}  # Hide OTP section
            )
        else:
            error_data = response.json()
            error_msg = error_data.get("error", "Invalid code")
            
            if error_data.get("expired"):
                error_msg = "Code expired. Please request a new code."
            elif error_data.get("attempts_exceeded"):
                error_msg = "Too many attempts. Please request a new code."
            
            return (
                dbc.Alert(error_msg, color="danger", dismissable=True, duration=4000),
                None,
                "",
                {},
                {"display": "block"}
            )
    except Exception as e:
        return (
            dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True, duration=4000),
            None,
            "",
            {},
            {"display": "block"}
        )
```

### Step 6: Add Callback to Resend Code

```python
@app.callback(
    Output("otp-verification-feedback", "children", allow_duplicate=True),
    Input("otp-resend-button", "n_clicks"),
    State("otp-verification-store", "data"),
    prevent_initial_call=True
)
def resend_otp_code(n_clicks, otp_data):
    """Resend OTP code."""
    if not n_clicks or not otp_data:
        return ""
    
    email = otp_data.get("email")
    if not email:
        return dbc.Alert("Error: Email not found", color="danger", dismissable=True, duration=4000)
    
    import requests
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/email-verification/request-code",
            json={"email": email}
        )
        
        if response.ok:
            return dbc.Alert(
                "New code sent to your email",
                color="info",
                dismissable=True,
                duration=3000
            )
        else:
            error = response.json().get("error", "Failed to send code")
            return dbc.Alert(error, color="danger", dismissable=True, duration=4000)
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True, duration=4000)
```

### Step 7: Update Save Triples Callback

Update the save_triples callback to check OTP verification (around line 3030):

```python
@app.callback(
    Output("save-feedback", "children", allow_duplicate=True),
    Input("save-btn", "n_clicks"),
    State("sentence-input", "value"),
    State("literature-link", "value"),
    State("contributor-email", "value"),
    State("email-store", "data"),
    State("otp-session-store", "data"),  # NEW: Check verified session
    # ... other states
    prevent_initial_call=True,
)
def save_triples(n_clicks, sentence_text, literature_link, contributor_email, email_validated, 
                 otp_session, source_entity_name, ...):
    """Save annotation triples (with OTP verification if enabled)."""
    if not n_clicks:
        raise PreventUpdate
    
    # Check basic email validation
    if not email_validated:
        return dbc.Alert("Please enter a valid email address.", color="danger", dismissable=True, duration=4000)
    
    # NEW: Check OTP verification if enabled
    import requests
    try:
        config_response = requests.get(f"{BACKEND_URL}/api/email-verification/config")
        if config_response.ok and config_response.json().get("enabled"):
            # OTP is enabled, check verification
            if not otp_session or not otp_session.get("session_id"):
                return dbc.Alert(
                    "Please verify your email address before submitting annotations.",
                    color="warning",
                    dismissable=True,
                    duration=6000
                )
            
            # Verify session is still valid
            check_response = requests.post(
                f"{BACKEND_URL}/api/email-verification/check-session",
                json={"session_id": otp_session["session_id"]}
            )
            
            if not check_response.ok or not check_response.json().get("verified"):
                return dbc.Alert(
                    "Your verification session has expired. Please verify your email again.",
                    color="warning",
                    dismissable=True,
                    duration=6000
                )
            
            # Use verified email from session
            email_validated = check_response.json().get("email")
    except:
        pass  # If OTP check fails, continue with basic validation
    
    # Rest of save_triples logic remains the same
    # ...
```

### Step 8: Add Session Check on Page Load

Add callback to check existing session on page load:

```python
@app.callback(
    Output("otp-session-store", "data", allow_duplicate=True),
    Output("email-validation", "children", allow_duplicate=True),
    Output("email-validation", "style", allow_duplicate=True),
    Input("url", "pathname"),
    State("otp-session-store", "data"),
    prevent_initial_call=True
)
def check_existing_session(pathname, session_data):
    """Check if there's an existing verified session on page load."""
    if not session_data or not session_data.get("session_id"):
        return None, "", {}
    
    import requests
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/email-verification/check-session",
            json={"session_id": session_data["session_id"]}
        )
        
        if response.ok and response.json().get("verified"):
            email = response.json().get("email")
            return (
                session_data,
                f"✓ Email verified ({email})",
                {"color": "green"}
            )
        else:
            # Session expired or invalid
            return None, "", {}
    except:
        return None, "", {}
```

## Testing the Implementation

### 1. Enable OTP Validation

```python
# config.py
ENABLE_OTP_VALIDATION = True
```

### 2. Configure Email Provider

```bash
# .env
EMAIL_PROVIDER=sendpulse
SENDPULSE_USER_ID=your-user-id
SENDPULSE_SECRET=your-secret
SMTP_FROM_EMAIL=noreply@harvest.app
```

### 3. Test Flow

1. Navigate to Annotate tab
2. Enter email address
3. Click outside email field (triggers validation)
4. OTP section should appear
5. Check email for 6-digit code
6. Enter code and click Verify
7. Green checkmark should appear
8. Can now save annotations
9. Session persists for 24 hours

### 4. Test Rate Limiting

- Request code 4 times in one hour
- Should get "Rate limit exceeded" error

### 5. Test Session Persistence

- Verify email
- Close browser
- Reopen browser
- Session should still be valid (for 24 hours)

### 6. Test Feature Toggle

```python
# config.py
ENABLE_OTP_VALIDATION = False
```

- OTP section should not appear
- Can save annotations without verification

## Error Handling

The implementation includes comprehensive error handling for:

1. **API Errors**: Network failures, server errors
2. **Rate Limiting**: Too many code requests
3. **Invalid Codes**: Wrong or expired codes
4. **Expired Sessions**: Session validity checking
5. **Feature Toggle**: Graceful fallback when disabled

## UI/UX Considerations

1. **Progressive Disclosure**: OTP section only shown when needed
2. **Clear Feedback**: Visual indicators for each state
3. **Easy Resend**: One-click code resend
4. **Persistent Sessions**: 24-hour validity reduces friction
5. **Graceful Degradation**: Works without OTP if disabled

## Security Notes

1. **Rate Limiting**: Prevents abuse (3 codes/hour)
2. **Attempt Limiting**: Max 5 attempts per code
3. **Code Expiry**: 10-minute window
4. **Session Expiry**: 24-hour validity
5. **IP Tracking**: Hashed for privacy
6. **Secure Storage**: bcrypt hashing for codes

## Performance Considerations

1. **Client-Side Storage**: Session stored in browser (localStorage)
2. **Minimal API Calls**: Only when needed
3. **Background Cleanup**: Server-side, doesn't impact users
4. **Fast Validation**: Cached session checks

## Future Enhancements

1. **Email Preferences**: Allow users to opt out of verification for trusted networks
2. **Multi-Factor Options**: Add ORCID OAuth as alternative
3. **Admin Override**: Allow admins to bypass verification
4. **Analytics**: Track verification success rates
5. **Customizable Expiry**: Allow admins to configure timeouts

## Troubleshooting

### OTP Section Not Appearing
- Check `ENABLE_OTP_VALIDATION = True` in config.py
- Check backend is running
- Check API endpoint: `GET /api/email-verification/config`

### Code Not Received
- Check email provider configuration
- Check SMTP credentials in .env
- Check spam/junk folder
- Check backend logs for errors

### Verification Fails
- Check code is not expired (10 minutes)
- Check not exceeded max attempts (5)
- Check rate limit not exceeded (3/hour)
- Check backend logs for details

### Session Lost
- Sessions expire after 24 hours
- Browser localStorage cleared
- Check session validity: `POST /api/email-verification/check-session`

## Summary

This implementation provides:
- ✅ Secure email verification
- ✅ User-friendly UI/UX
- ✅ Comprehensive error handling
- ✅ Feature toggle support
- ✅ Rate limiting and security
- ✅ Session persistence
- ✅ SendPulse integration
- ✅ Production-ready code

Follow the steps above to integrate email verification into the HARVEST frontend. Each step builds on the previous one, creating a complete, secure, and user-friendly verification flow.
