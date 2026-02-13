# Nextory API Authentication

## Overview
The Nextory API uses a two-tier authentication system:
1. **User Authentication** (DeviceAuth) - Authenticates the user account
2. **Profile Authentication** (ProfileAuth) - Authenticates a specific profile within the account

Most endpoints require both authentication levels, while some account-level operations only require user authentication.

## Required Headers
All API requests must include these device identification headers (see `components.parameters` in openapi.yaml):

- `X-Application-Id`: Device type ("200"=Android, "204"=Automotive, "205"=Wear)
- `X-Device-Id`: Firebase Installation ID (22-character Base64 string matching `^[A-Za-z0-9_-]{22}$`)
- `X-Locale`: Device locale in format `language_COUNTRY` (e.g., "en_US", "sv_SE")
- `X-Model`: URL-encoded device model (e.g., "Samsung%20SM-G991B")
- `X-App-Version`: App version (e.g., "2026.01.3")
- `X-Os-Info`: Operating system version (e.g., "Android 13")
- `X-Country-Code`: ISO 3166-1 alpha-2 country code (optional, but recommended)

## Security Schemes
Defined in `components.securitySchemes` in openapi.yaml:

### DeviceAuth
- **Type**: API Key
- **Header**: `X-Login-Token`
- **Purpose**: User-level authentication
- **Obtained from**: Sign-in response (`AccountResponse.login_token`)

### ProfileAuth
- **Type**: API Key  
- **Header**: `X-Profile-Token`
- **Purpose**: Profile-level authentication
- **Obtained from**: Profile authorization response (`ProfileTokenResponse.profile_token`)

## Authentication Flow

### Step 1: User Sign-In
**Endpoint**: `POST /user/v1/sessions` (see openapi.yaml)

**Security**: None (public endpoint)

**Request Body** (`SignInBody` schema):
```json
{
  "identifier": "user@example.com",
  "password": "user_password"
}
```

Alternatively, OAuth authentication:
```json
{
  "access_token": "oauth_access_token",
  "id_token": "oauth_id_token",
  "provider": "google"
}
```

**Response** (`AccountResponse` schema):
```json
{
  "id": 12345,
  "email": "user@example.com",
  "login_token": "user_login_token_here",
  "country": "US",
  ...
}
```

**Action**: Store `login_token` and add to all subsequent requests as `X-Login-Token` header.

### Step 2: List Profiles
**Endpoint**: `GET /user/v1/me/profiles` (see openapi.yaml)

**Security**: DeviceAuth only (requires `X-Login-Token`)

**Response** (`ProfilesResponse` schema):
```json
{
  "profiles": [
    {
      "id": 1,
      "name": "Main Profile",
      "login_key": "profile_login_key_here",
      "is_main": true,
      ...
    }
  ],
  "max_profiles": 5,
  ...
}
```

**Action**: Select a profile from the list (typically the main profile or first profile) and extract its `login_key`.

### Step 3: Authorize Profile
**Endpoint**: `POST /user/v1/profile/authorize` (see openapi.yaml)

**Security**: DeviceAuth only (requires `X-Login-Token`)

**Request Body** (`LoginKeyBody` schema):
```json
{
  "login_key": "profile_login_key_here"
}
```

**Response** (`ProfileTokenResponse` schema):
```json
{
  "profile_token": "profile_token_here"
}
```

**Action**: Store `profile_token` and add to all subsequent requests as `X-Profile-Token` header.

### Step 4: Access Protected Resources
Once authenticated, include both tokens in requests:

**Headers**:
```
X-Login-Token: user_login_token_here
X-Profile-Token: profile_token_here
X-Country-Code: US
```

Most endpoints require both `DeviceAuth` and `ProfileAuth` (see `security` field on each endpoint in openapi.yaml).

## Endpoint Security Requirements

### Public Endpoints (No Authentication)
- `POST /user/v1/sessions` - Sign in
- `POST /user/v1/registrations` - Register new user
- `POST /user/v1/forgot_password` - Request password reset
- `GET /user/v1.1/markets` - Get available markets

### DeviceAuth Only (X-Login-Token)
Profile management endpoints that don't require an active profile:
- `GET /user/v1/me/profiles` - List profiles
- `POST /user/v1/me/profile` - Create profile
- `PATCH /user/v1/me/profile` - Update profile
- `DELETE /user/v1/me/profile` - Delete profile
- `POST /user/v1/profile/authorize` - Authorize profile
- `GET /user/v1/me/account` - Get account details
- `PATCH /user/v1/me/account` - Update account
- `GET /user/v2/me/login/token` - Get auto-login token
- `GET /user/v1/avatars` - Get available avatars
- `GET /obgateway/v1/me/subscription` - Get subscription
- `GET /user/v1/me/reading/activity/feed` - Get reading activity

### DeviceAuth + ProfileAuth (Both Tokens)
All other endpoints require both authentication levels, including:
- Library operations (`/library/v1/*`, `/library/v2/*`)
- Reader operations (`/reader/*`)
- Discovery and search (`/discovery/*`)
- Reading analytics (`/reading-diary/*`)

## Error Handling

### Unauthorized Access (Error Code 7111)
When accessing protected resources without proper authentication:

**Response** (`NetworkErrorResponse` schema):
```json
{
  "error": {
    "code": 7111,
    "key": "Unauthorized",
    "message": "Not Authorized",
    "description": "Not Authorized"
  }
}
```

**HTTP Status**: 401 or 403

**Action**: Re-authenticate by repeating the authentication flow.

## Session Management

### Sign Out
**Endpoint**: `DELETE /user/v1/sessions` (see openapi.yaml)

**Security**: DeviceAuth (requires `X-Login-Token`)

**Action**: Invalidates the current session. Client should discard stored tokens.

### Token Lifecycle
- Tokens are session-based and expire after a period of inactivity
- No explicit token refresh mechanism - re-authenticate when tokens expire
- Monitor for 401/403 responses to detect expired tokens

## Implementation Considerations

1. **Token Storage**: Securely store `login_token` and `profile_token` for the session duration
2. **Profile Switching**: To switch profiles, call authorize endpoint with different `login_key`
3. **Multiple Profiles**: Accounts can have multiple profiles (see `ProfilesResponse.max_profiles`)
4. **Auto-Login**: Use `GET /user/v2/me/login/token` to generate auto-login links
5. **Error Recovery**: Implement automatic re-authentication on 401/403 responses
