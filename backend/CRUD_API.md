# Appointment CRUD API Documentation

This document describes the SQLite-based CRUD API for managing appointments in the FastLane RAG system.

## Database Schema

### Table: `appointments`

- `id` (TEXT, PRIMARY KEY) - Unique appointment ID (e.g., "A-1000")
- `patient` (TEXT, NOT NULL) - Patient name
- `slot` (TEXT, NOT NULL) - Appointment slot in ISO format
- `location` (TEXT, NOT NULL) - Appointment location
- `notes` (TEXT) - Optional notes
- `status` (TEXT, NOT NULL, DEFAULT 'scheduled') - Appointment status
- `created_at` (TEXT, NOT NULL) - Creation timestamp (ISO format)
- `updated_at` (TEXT) - Last update timestamp (ISO format)
- `cancelled_at` (TEXT) - Cancellation timestamp (ISO format)

### Table: `booked_slots`

- `patient_lower` (TEXT, NOT NULL) - Lowercase patient name
- `slot` (TEXT, NOT NULL) - Appointment slot
- `location_lower` (TEXT, NOT NULL) - Lowercase location name
- PRIMARY KEY (patient_lower, slot, location_lower)

## API Endpoints

### 1. CREATE Appointment

**POST** `/tools/schedule_appointment`

Create a new appointment.

**Request Body:**

```json
{
  "patient": "John Doe",
  "preferred_slot_iso": "2024-01-15T10:00:00",
  "location": "Main Clinic",
  "notes": "Regular checkup"
}
```

**Response:**

```json
{
  "ok": true,
  "appt_id": "A-1000",
  "normalized_slot_iso": "2024-01-15T10:00:00",
  "status": "created",
  "latency_ms": 15.23
}
```

### 2. READ - List All Appointments

**GET** `/tools/appointments`

Get all appointments with pagination.

**Query Parameters:**

- `limit` (optional, default: 100) - Maximum number of appointments to return
- `offset` (optional, default: 0) - Number of appointments to skip

**Response:**

```json
{
  "appointments": [
    {
      "id": "A-1000",
      "patient": "John Doe",
      "slot": "2024-01-15T10:00:00",
      "location": "Main Clinic",
      "notes": "Regular checkup",
      "status": "scheduled",
      "created_at": "2024-01-10T12:00:00",
      "updated_at": null,
      "cancelled_at": null
    }
  ],
  "total": 1
}
```

### 3. READ - Get Single Appointment

**GET** `/tools/appointments/{appointment_id}`

Get a single appointment by ID.

**Response:**

```json
{
  "ok": true,
  "appointment": {
    "id": "A-1000",
    "patient": "John Doe",
    "slot": "2024-01-15T10:00:00",
    "location": "Main Clinic",
    "notes": "Regular checkup",
    "status": "scheduled",
    "created_at": "2024-01-10T12:00:00",
    "updated_at": null,
    "cancelled_at": null
  }
}
```

### 4. UPDATE Appointment

**PUT** `/tools/appointments/{appointment_id}`

Update an appointment (full update).

**Request Body:**

```json
{
  "patient": "John Doe",
  "preferred_slot_iso": "2024-01-15T14:00:00",
  "location": "Main Clinic",
  "notes": "Updated notes",
  "status": "confirmed"
}
```

**Response:**

```json
{
  "ok": true,
  "appointment": {
    "id": "A-1000",
    "patient": "John Doe",
    "slot": "2024-01-15T14:00:00",
    "location": "Main Clinic",
    "notes": "Updated notes",
    "status": "confirmed",
    "created_at": "2024-01-10T12:00:00",
    "updated_at": "2024-01-10T13:30:00",
    "cancelled_at": null
  }
}
```

### 5. PATCH Appointment

**PATCH** `/tools/appointments/{appointment_id}`

Partially update an appointment.

**Request Body:**

```json
{
  "preferred_slot_iso": "2024-01-15T15:00:00"
}
```

**Response:** Same as UPDATE endpoint

### 6. DELETE Appointment (Permanent)

**DELETE** `/tools/appointments/{appointment_id}`

Permanently delete an appointment.

**Response:**

```json
{
  "ok": true,
  "appt_id": "A-1000",
  "message": "Appointment deleted successfully"
}
```

### 7. CANCEL Appointment (Soft Delete)

**POST** `/tools/appointments/{appointment_id}/cancel`

Cancel an appointment (soft delete - marks as cancelled).

**Response:**

```json
{
  "ok": true,
  "appt_id": "A-1000",
  "appointment": {
    "id": "A-1000",
    "patient": "John Doe",
    "slot": "2024-01-15T10:00:00",
    "location": "Main Clinic",
    "notes": "Regular checkup",
    "status": "cancelled",
    "created_at": "2024-01-10T12:00:00",
    "updated_at": "2024-01-10T14:00:00",
    "cancelled_at": "2024-01-10T14:00:00"
  },
  "message": "Appointment cancelled successfully"
}
```

### 8. DELETE All Appointments (Testing)

**DELETE** `/tools/appointments`

Delete all appointments (for testing purposes).

**Response:**

```json
{
  "ok": true,
  "message": "All appointments cleared (5 deleted)"
}
```

## Status Codes

- `200 OK` - Successful operation
- `404 Not Found` - Appointment not found
- `400 Bad Request` - Invalid input data

## Error Responses

When an appointment is not found:

```json
{
  "detail": "Appointment not found"
}
```

## Example Usage

### Create an Appointment

```bash
curl -X POST "http://localhost:8000/tools/schedule_appointment" \
  -H "Content-Type: application/json" \
  -d '{
    "patient": "Jane Smith",
    "preferred_slot_iso": "2024-01-20T10:00:00",
    "location": "Downtown Clinic",
    "notes": "Follow-up appointment"
  }'
```

### Get All Appointments

```bash
curl -X GET "http://localhost:8000/tools/appointments"
```

### Update an Appointment

```bash
curl -X PUT "http://localhost:8000/tools/appointments/A-1000" \
  -H "Content-Type: application/json" \
  -d '{
    "patient": "Jane Smith",
    "preferred_slot_iso": "2024-01-20T14:00:00",
    "location": "Downtown Clinic",
    "notes": "Rescheduled appointment"
  }'
```

### Cancel an Appointment

```bash
curl -X POST "http://localhost:8000/tools/appointments/A-1000/cancel"
```

### Delete an Appointment

```bash
curl -X DELETE "http://localhost:8000/tools/appointments/A-1000"
```

## Database File Location

The SQLite database is stored at: `backend/appointments.db`

This file is automatically created when the application starts if it doesn't exist.

## Notes

- Appointments are idempotent: attempting to book the same slot for the same patient and location will return the existing appointment instead of creating a duplicate.
- The `booked_slots` table is used to prevent duplicate bookings.
- Cancelled appointments still exist in the database but are marked with `status='cancelled'` and a `cancelled_at` timestamp.
- All timestamps are in ISO 8601 format.
