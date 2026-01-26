import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
from barcode_generator import BarcodeGenerator

class EventDatabase:
    def __init__(self, db_path="event_registration.db"):
        self.db_path = db_path
        self.barcode_gen = BarcodeGenerator()
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Enhanced registrations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checkin_time TIMESTAMP,
            status TEXT DEFAULT 'registered',
            source_system TEXT DEFAULT 'manual',
            barcode_data TEXT,
            emergency_contact TEXT,
            medical_notes TEXT,
            worship_team INTEGER DEFAULT 0,
            volunteer INTEGER DEFAULT 0,
            synced_to_cloud INTEGER DEFAULT 0
        )
        ''')
        
        # Events table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            event_date DATE,
            start_time TIME,
            end_time TIME,
            location TEXT,
            capacity INTEGER,
            spreadsheet_id TEXT,
            registration_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Check-in stations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS checkin_stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_name TEXT NOT NULL,
            station_code TEXT UNIQUE,
            location TEXT,
            ip_address TEXT,
            last_active TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_event(self, event_name, event_date, location, capacity=1000):
        """Create a new event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Generate registration URL with unique ID
        import uuid
        event_code = str(uuid.uuid4())[:8]
        registration_url = f"https://rooted-world-tour.streamlit.app/?event={event_code}"
        
        cursor.execute('''
        INSERT INTO events (event_name, event_date, location, capacity, registration_url)
        VALUES (?, ?, ?, ?, ?)
        ''', (event_name, event_date, location, capacity, registration_url))
        
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return event_id, registration_url
    
    def add_registration(self, data):
        """Add a new registration with all required fields"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Generate ticket ID if not provided
        if 'ticket_id' not in data or not data['ticket_id']:
            data['ticket_id'] = self.barcode_gen.generate_ticket_id()
        
        # Generate barcode data
        data['barcode_data'] = data['ticket_id']
        
        try:
            cursor.execute('''
            INSERT INTO registrations 
            (ticket_id, first_name, last_name, email, phone, 
             emergency_contact, medical_notes, worship_team, volunteer, barcode_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['ticket_id'], data['first_name'], data['last_name'],
                data['email'], data.get('phone', ''),
                data.get('emergency_contact', ''), data.get('medical_notes', ''),
                data.get('worship_team', 0), data.get('volunteer', 0),
                data['barcode_data']
            ))
            
            conn.commit()
            conn.close()
            
            # Generate QR code
            qr_img = self.barcode_gen.create_registration_qr(data['ticket_id'])
            
            return True, "Registration successful!", data['ticket_id'], qr_img
            
        except sqlite3.IntegrityError:
            conn.close()
            return False, "Ticket ID already exists!", None, None
        except Exception as e:
            conn.close()
            return False, f"Error: {str(e)}", None, None
    
    def quick_checkin(self, ticket_id):
        """Quick check-in using ticket ID or barcode scan"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # First try exact ticket ID match
        cursor.execute('''
        UPDATE registrations 
        SET checkin_time = ?, status = 'checked_in'
        WHERE ticket_id = ? AND status = 'registered'
        ''', (datetime.now(), ticket_id))
        
        if cursor.rowcount == 0:
            # Try partial match or barcode scan
            cursor.execute('''
            UPDATE registrations 
            SET checkin_time = ?, status = 'checked_in'
            WHERE ticket_id LIKE ? AND status = 'registered'
            ''', (datetime.now(), f"%{ticket_id}%"))
        
        conn.commit()
        updated = cursor.rowcount > 0
        
        if updated:
            cursor.execute('SELECT first_name, last_name FROM registrations WHERE ticket_id LIKE ?', (f"%{ticket_id}%",))
            attendee = cursor.fetchone()
            conn.close()
            return True, attendee
        else:
            conn.close()
            return False, None
    
    def get_dashboard_stats(self, event_date=None):
        """Get comprehensive dashboard statistics"""
        conn = self.get_connection()
        
        stats = {}
        
        # Base query with COALESCE to handle NULL values
        query = "SELECT "
        query += "COUNT(*) as total, "
        query += "COALESCE(SUM(CASE WHEN status = 'checked_in' THEN 1 ELSE 0 END), 0) as checked_in, "
        query += "COALESCE(SUM(CASE WHEN worship_team = 1 THEN 1 ELSE 0 END), 0) as worship_team, "
        query += "COALESCE(SUM(CASE WHEN volunteer = 1 THEN 1 ELSE 0 END), 0) as volunteers, "
        query += "COUNT(DISTINCT date(registration_time)) as active_days "
        query += "FROM registrations"
        
        params = ()
        
        if event_date:
            query += " WHERE date(registration_time) = ?"
            params = (event_date,)
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        # Initialize all stats with 0 to avoid None values
        stats['total'] = result[0] or 0 if result else 0
        stats['checked_in'] = result[1] or 0 if result and result[1] is not None else 0
        stats['worship_team'] = result[2] or 0 if result and result[2] is not None else 0
        stats['volunteers'] = result[3] or 0 if result and result[3] is not None else 0
        stats['active_days'] = result[4] or 0 if result and result[4] is not None else 0
        
        # Calculate derived stats safely
        stats['pending'] = stats['total'] - stats['checked_in']
        
        if stats['total'] > 0:
            stats['checkin_rate'] = f"{(stats['checked_in'] / stats['total'] * 100):.1f}%"
        else:
            stats['checkin_rate'] = "0%"
        
        # Hourly check-ins for today
        cursor.execute('''
        SELECT strftime('%H', checkin_time) as hour, COUNT(*) as count
        FROM registrations 
        WHERE date(checkin_time) = date('now') 
        AND status = 'checked_in'
        AND checkin_time IS NOT NULL
        GROUP BY hour
        ORDER BY hour
        ''')
        
        hourly_data = cursor.fetchall()
        stats['hourly_checkins'] = {str(hour): count for hour, count in hourly_data}
        
        conn.close()
        return stats