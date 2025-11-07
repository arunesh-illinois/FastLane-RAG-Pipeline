import aiosqlite
import json
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path


# Database file path
DB_PATH = "backend/appointments.db"


class DatabaseService:
    """Service for managing SQLite database operations for appointments"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        """Initialize the database and create tables if they don't exist"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    id TEXT PRIMARY KEY,
                    patient TEXT NOT NULL,
                    slot TEXT NOT NULL,
                    location TEXT NOT NULL,
                    notes TEXT,
                    status TEXT NOT NULL DEFAULT 'scheduled',
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    cancelled_at TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS booked_slots (
                    patient_lower TEXT NOT NULL,
                    slot TEXT NOT NULL,
                    location_lower TEXT NOT NULL,
                    PRIMARY KEY (patient_lower, slot, location_lower)
                )
            """)
            await db.commit()
            print(f"✅ Database initialized at {self.db_path}")

    async def create_appointment(self, appointment_id: str, patient: str, slot: str, location: str, notes: Optional[str] = None) -> Dict:
        """Create a new appointment"""
        patient_lower = patient.lower()
        location_lower = location.lower()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Check if slot is already booked
            cursor = await db.execute("""
                SELECT 1 FROM booked_slots 
                WHERE patient_lower = ? AND slot = ? AND location_lower = ?
            """, (patient_lower, slot, location_lower))
            existing = await cursor.fetchone()
            
            if existing:
                # Return existing appointment
                cursor = await db.execute("""
                    SELECT * FROM appointments 
                    WHERE patient = ? AND slot = ? AND location = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (patient, slot, location))
                row = await cursor.fetchone()
                if row:
                    return {
                        "ok": True,
                        "appt_id": row[0],
                        "normalized_slot_iso": row[2],
                        "status": "already_booked"
                    }
            
            # Create new appointment
            now = datetime.now().isoformat()
            await db.execute("""
                INSERT INTO appointments (id, patient, slot, location, notes, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (appointment_id, patient, slot, location, notes or "", "scheduled", now))
            
            # Add to booked_slots
            try:
                await db.execute("""
                    INSERT INTO booked_slots (patient_lower, slot, location_lower)
                    VALUES (?, ?, ?)
                """, (patient_lower, slot, location_lower))
            except aiosqlite.IntegrityError:
                pass  # Already booked
            
            await db.commit()
            
            return {
                "ok": True,
                "appt_id": appointment_id,
                "normalized_slot_iso": slot,
                "status": "created"
            }

    async def get_appointment(self, appointment_id: str) -> Optional[Dict]:
        """Get a single appointment by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM appointments WHERE id = ?
            """, (appointment_id,))
            row = await cursor.fetchone()
            
            if row:
                return dict(row)
            return None

    async def get_all_appointments(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get all appointments with pagination"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM appointments 
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_appointments_count(self) -> int:
        """Get total count of appointments"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM appointments")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def update_appointment(self, appointment_id: str, **updates) -> Optional[Dict]:
        """Update an appointment"""
        # Build update query dynamically
        update_fields = []
        values = []
        
        allowed_fields = ['patient', 'slot', 'location', 'notes', 'status']
        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                update_fields.append(f"{field} = ?")
                values.append(value)
        
        if not update_fields:
            return None
        
        # Add updated_at timestamp
        update_fields.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        
        values.append(appointment_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(f"""
                UPDATE appointments 
                SET {', '.join(update_fields)}
                WHERE id = ?
            """, values)
            
            await db.commit()
            
            if cursor.rowcount > 0:
                return await self.get_appointment(appointment_id)
            return None

    async def delete_appointment(self, appointment_id: str) -> bool:
        """Delete an appointment"""
        async with aiosqlite.connect(self.db_path) as db:
            # First get the appointment to remove from booked_slots
            appointment = await self.get_appointment(appointment_id)
            if not appointment:
                return False
            
            # Remove from booked_slots
            patient_lower = appointment['patient'].lower()
            location_lower = appointment['location'].lower()
            await db.execute("""
                DELETE FROM booked_slots 
                WHERE patient_lower = ? AND slot = ? AND location_lower = ?
            """, (patient_lower, appointment['slot'], location_lower))
            
            # Delete appointment
            cursor = await db.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
            await db.commit()
            
            return cursor.rowcount > 0

    async def cancel_appointment(self, appointment_id: str) -> Optional[Dict]:
        """Cancel an appointment (soft delete)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                UPDATE appointments 
                SET status = ?, cancelled_at = ?, updated_at = ?
                WHERE id = ?
            """, ("cancelled", datetime.now().isoformat(), datetime.now().isoformat(), appointment_id))
            
            await db.commit()
            
            if cursor.rowcount > 0:
                # Remove from booked_slots
                appointment = await self.get_appointment(appointment_id)
                if appointment:
                    patient_lower = appointment['patient'].lower()
                    location_lower = appointment['location'].lower()
                    await db.execute("""
                        DELETE FROM booked_slots 
                        WHERE patient_lower = ? AND slot = ? AND location_lower = ?
                    """, (patient_lower, appointment['slot'], location_lower))
                    await db.commit()
                
                return await self.get_appointment(appointment_id)
            return None

    async def clear_all_appointments(self) -> int:
        """Clear all appointments (for testing)"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM appointments")
            await db.execute("DELETE FROM booked_slots")
            await db.commit()
            return cursor.rowcount


# Global database service instance
db_service = DatabaseService()
