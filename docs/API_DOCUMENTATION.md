# AuthenticEye Platform — API Documentation

This document describes all API endpoints exposed by both the Express.js gateway backend and the Python FastAPI AI microservice.

---

## 1. Express.js Gateway Server (Port 5000)

All routes require authentication via JWT authorization header (`Authorization: Bearer <token>`) except where marked.

### Authentication Endpoints (`/api/auth`)

#### POST `/api/auth/register` (Public)
Registers a new user.
- **Request Body**: `{ "name", "email", "password" }`
- **Response**: `{ "token" }` (stored in LocalStorage)

#### POST `/api/auth/login` (Public)
Authenticates a user and issues JWT & HTTP-Only refresh token.
- **Request Body**: `{ "email", "password" }`
- **Response**: `{ "token", "user" }` (sets secure cookie `refreshToken`)

#### POST `/api/auth/refresh` (Public)
Validates the refresh token cookie and issues a new access token.
- **Response**: `{ "token" }`

---

### Detection Endpoints (`/api/detect`)

#### POST `/api/detect/image`
Uploads a single image for forensic scanning.
- **Request (Multipart)**: `image` (File)
- **Response**: Analysis JSON containing model scores, explainability URLs, and deepfake probabilities.

#### POST `/api/detect/video`
Uploads a single video file for frame-by-frame analysis.
- **Request (Multipart)**: `video` (File)
- **Response**: Frame-level metadata and overall deepfake prediction.


---

### History & Reports (`/api/history`)

#### GET `/api/history`
Returns paginated, searchable, sorted, and filtered detection logs.
- **Query Params**:
  - `page` (default 1)
  - `limit` (default 10)
  - `search` (filters by filename)
  - `result` (`real` | `fake`)
  - `mediaType` (`image` | `video`)
  - `sort` (`createdAt` | `confidence`)
  - `order` (`desc` | `asc`)
- **Response**: `{ "analyses", "totalPages", "currentPage", "total" }`

#### GET `/api/history/:id/report`
Generates and downloads a forensic PDF report compiling image metadata and visual heatmaps.
- **Response**: Binary PDF file stream.

---

### Admin Dashboard Endpoints (`/api/admin`)
Requires JWT admin credentials.

#### GET `/api/admin/feedback`
Lists user feedback items submitted for model correction.

#### POST `/api/admin/feedback/verify`
Approves user correction and copies the verification image to local retraining dataset directories.
- **Request Body**: `{ "feedbackId", "status", "verifiedLabel" }`

#### POST `/api/admin/retrain`
Triggers model retraining in the Python AI service.

#### POST `/api/admin/models/rollback`
Rolls back active models to a previous version checkpoint.
- **Request Body**: `{ "version" }`

#### GET `/api/admin/analytics`
Compiles live user, AI, and system health status.
- **Response**: `{ "users", "ai", "system" }`

---

## 2. FastAPI AI Microservice (Port 8000)

Internal endpoints consumed by the backend gateway.

#### POST `/detect/image`
Processes and alignments face crops, runs ensemble inference, and generates visual heatmaps.
- **Request**: `file` (Multipart Image)
- **Response**: Predictions and base64 heatmaps.

#### POST `/detect/video`
Extracts video frames and runs temporal LSTM classification.
- **Request**: `file` (Multipart Video)

#### POST `/retrain`
Initiates ensemble retraining on newly collected verification samples.

#### POST `/rollback`
Swaps the serving weight state files with older checkpoints.
