# API Documentation

This document provides detailed information about the Parental Control System's API endpoints, request/response formats, and authentication methods.

## Authentication

All API requests require authentication using JWT (JSON Web Tokens).

### Obtaining a Token

```
POST /api/token/
```

**Request Body:**
```json
{
  "username": "parent@example.com",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Using the Token

Include the token in the Authorization header of all requests:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### Refreshing a Token

```
POST /api/token/refresh/
```

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

## API Endpoints

### Device Registration

Register a new device to be monitored.

```
POST /api/register-device/
```

**Request Body:**
```json
{
  "device_name": "Child's Phone",
  "device_id": "unique_device_identifier",
  "child_name": "Alex",
  "device_model": "Samsung Galaxy S21"
}
```

### Screen Time Rules

Get screen time rules for a device.

```
GET /api/get-screen-time-rules/{device_id}/
```

**Response:**
```json
{
  "has_changes": true,
  "daily_limit_minutes": 120,
  "bedtime_start": "21:00",
  "bedtime_end": "07:00"
}
```

### Update Screen Time Usage

Send screen time usage data from device to server.

```
POST /api/update-screen-time/
```

**Request Body:**
```json
{
  "device_id": "unique_device_identifier",
  "usage_data": [
    {
      "timestamp": "2025-08-05T14:30:00",
      "minutes": 1
    },
    {
      "timestamp": "2025-08-05T14:31:00",
      "minutes": 1
    }
  ]
}
```

### App Usage Data

Send app usage data from device to server.

```
POST /api/update-app-usage/
```

**Request Body:**
```json
{
  "device_id": "unique_device_identifier",
  "usage_data": [
    {
      "app_name": "YouTube",
      "start_time": "2025-08-05T14:30:00",
      "end_time": "2025-08-05T14:45:00"
    }
  ]
}
```

### Get Blocked Apps

Get list of apps that should be blocked.

```
GET /api/get-blocked-apps/{device_id}/
```

**Response:**
```json
{
  "has_changes": true,
  "blocked_apps": [
    "com.facebook.katana",
    "com.instagram.android"
  ]
}
```

### Device Status Update

Update device status.

```
POST /api/device-status/
```

**Request Body:**
```json
{
  "device_id": "unique_device_identifier",
  "battery_level": 85,
  "last_sync": "2025-08-05T15:30:00",
  "is_online": true
}
```

## Error Handling

The API uses standard HTTP status codes and returns error details in the response body:

```json
{
  "error": "Invalid device ID",
  "code": "invalid_device",
  "status": 400
}
```

## Rate Limiting

API requests are limited to 100 requests per minute per user. If exceeded, a 429 Too Many Requests response will be returned.

## Data Formats

- All timestamps should be in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
- Times for bedtime are in 24-hour format (HH:MM)
- All requests and responses should use UTF-8 encoding

## Testing the API

You can use the included Postman collection for testing the API endpoints:

1. Import `Parental_Control_API.postman_collection.json` into Postman
2. Set up an environment with the variables:
   - `base_url`: Your API base URL
   - `token`: Your JWT token after authentication

## Webhook Integration

The API also provides webhooks for real-time notifications:

1. Register a webhook URL:
```
POST /api/register-webhook/
```

2. Events you can subscribe to:
   - `device_online`
   - `screen_time_exceeded`
   - `bedtime_activated`
   - `restricted_app_attempted`

## API Versioning

The current API version is v1. Include the version in the URL path:

```
/api/v1/endpoint/
```

Future versions will be accessible at `/api/v2/`, etc.
