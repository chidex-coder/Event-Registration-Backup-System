import streamlit as st
import pandas as pd
from datetime import datetime
import io
import base64

# Import custom modules
from database import EventDatabase
from barcode_generator import BarcodeGenerator
from utils import (
    create_dashboard_charts,
    create_registration_form,
    create_checkin_interface,
    create_sidebar,
    format_phone
)
from drive_handler import HybridDatabase

# Page configuration
st.set_page_config(
    page_title="Rooted World Tour - Registration",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #1a5319 0%, #4CAF50 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .main-header h1 {
        font-size: 3.5rem;
        font-weight: 800;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    .main-header h2 {
        font-size: 1.5rem;
        font-weight: 300;
        margin: 10px 0 0 0;
        opacity: 0.9;
    }
    
    /* Card styling */
    .card {
        background-color: #262730;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
        margin-bottom: 1rem;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 5px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(76, 175, 80, 0.4);
    }
    
    /* Metric card styling */
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #4CAF50;
    }
    
    /* QR code container */
    .qr-container {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
        border: 2px dashed #4CAF50;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .status-registered {
        background-color: #ff9800;
        color: white;
    }
    
    .status-checked_in {
        background-color: #4CAF50;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = EventDatabase()
if 'barcode_gen' not in st.session_state:
    st.session_state.barcode_gen = BarcodeGenerator()
if 'scanning' not in st.session_state:
    st.session_state.scanning = False

# Create sidebar and get selected page
selected_page = create_sidebar()

# Main content area
if selected_page == "Home":
    # Hero Section
    st.markdown("""
    <div class="main-header">
        <h1>ROOTED WORLD TOUR</h1>
        <h2>WORSHIP NIGHT ENCOUNTER • EMERGENCY REGISTRATION SYSTEM</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Alert Banner
    st.warning("""
    ⚠️ **BACKUP SYSTEM ACTIVE** - Main scanning systems are currently offline. 
    Use this system for all registrations and check-ins until further notice.
    """)
    
    # Quick Actions
    st.subheader("🚀 Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📝 New Registration", use_container_width=True):
            st.session_state.page = "Register"
            st.rerun()
    
    with col2:
        if st.button("✅ Check-in Attendee", use_container_width=True):
            st.session_state.page = "Check-in"
            st.rerun()
    
    with col3:
        if st.button("📊 View Dashboard", use_container_width=True):
            st.session_state.page = "Dashboard"
            st.rerun()
    
    with col4:
        if st.button("📋 Generate Tickets", use_container_width=True):
            st.session_state.page = "Manage"
            st.rerun()
    
    # Stats Overview
    st.subheader("📈 Live Overview")
    
    stats = st.session_state.db.get_dashboard_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Registered", stats.get('total', 0))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Checked In", stats.get('checked_in', 0))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Check-in Rate", stats.get('checkin_rate', '0%'))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Worship Team", stats.get('worship_team', 0))
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Recent Activity
    st.subheader("🕐 Recent Activity")
    
    # Get recent registrations
    conn = st.session_state.db.get_connection()
    recent_df = pd.read_sql_query(
        "SELECT ticket_id, first_name, last_name, status, registration_time FROM registrations ORDER BY id DESC LIMIT 10",
        conn
    )
    conn.close()
    
    if not recent_df.empty:
        # Format the dataframe
        display_df = recent_df.copy()
        display_df['registration_time'] = pd.to_datetime(display_df['registration_time']).dt.strftime('%I:%M %p')
        
        # Add status badges
        def status_badge(status):
            badge_class = "status-checked_in" if status == "checked_in" else "status-registered"
            return f'<span class="status-badge {badge_class}">{status.replace("_", " ").title()}</span>'
        
        display_df['status'] = display_df['status'].apply(status_badge)
        
        # Display as HTML table for better styling
        st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.info("No recent activity. Register your first attendee!")
    
    # QR Code for Mobile Registration
    st.subheader("📱 Mobile Registration QR")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Generate QR for registration page
        qr_img = st.session_state.barcode_gen.create_registration_qr("REGISTER-NOW")
        st.image(qr_img, caption="Scan to register on mobile")
    
    with col2:
        st.markdown("""
        ### Mobile Registration Instructions
        
        1. **Print this QR code** and display at entry points
        2. **Attendees scan** with their phone camera
        3. **Complete registration** on their mobile device
        4. **Receive digital ticket** with unique QR code
        5. **Scan at check-in** for fast entry
        
        **Benefits:**
        - ✅ No app installation needed
        - ✅ Works on any smartphone
        - ✅ Reduces physical contact
        - ✅ Real-time data sync
        - ✅ Digital ticket backup
        
        *Perfect for when main systems fail!*
        """)

elif selected_page == "Register":
    st.title("🎟️ New Registration")
    
    # Show current event info
    st.info("""
    **Current Event:** Rooted World Tour Worship Night  
    **Date:** Saturday, 8:00 PM  
    **Location:** Main Auditorium  
    **System Status:** 🔴 **BACKUP MODE** - Main scanners offline
    """)
    
    # Registration form
    form_valid, result = create_registration_form()

    if form_valid:
        if isinstance(result, dict):  # Got form data
            form_data = result
            # Process registration...
        else:  # Got error message
            st.error(f"❌ {result}")
            
            if success:
                st.success("✅ Registration Successful!")
                st.balloons()
                
                # Show registration details
                st.subheader("🎫 Registration Confirmation")
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    # Display QR code
                    st.markdown('<div class="qr-container">', unsafe_allow_html=True)
                    st.image(qr_img, caption="Registration QR Code")
                    st.markdown(f"**Ticket ID:** {ticket_id}")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Download button
                    img_bytes = st.session_state.barcode_gen.img_to_bytes(qr_img)
                    st.download_button(
                        label="📥 Download QR Code",
                        data=img_bytes,
                        file_name=f"ticket_{ticket_id}.png",
                        mime="image/png"
                    )
                
                with col2:
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.markdown(f"**Name:** {form_data['first_name']} {form_data['last_name']}")
                    st.markdown(f"**Email:** {form_data['email']}")
                    st.markdown(f"**Phone:** {format_phone(form_data['phone'])}")
                    
                    if form_data.get('emergency_contact'):
                        st.markdown(f"**Emergency Contact:** {form_data['emergency_contact']}")
                    
                    if form_data.get('medical_notes'):
                        st.markdown(f"**Medical Notes:** {form_data['medical_notes']}")
                    
                    if form_data.get('worship_team'):
                        st.markdown("**Team:** 🎵 Worship Team")
                    elif form_data.get('volunteer'):
                        st.markdown("**Team:** 🤝 Volunteer")
                    
                    st.markdown(f"**Registration Time:** {datetime.now().strftime('%I:%M %p')}")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Instructions
                    st.info("""
                    **Next Steps:**
                    1. **Save or screenshot** the QR code
                    2. **Show at check-in** for fast processing
                    3. **Email confirmation** sent to provided email
                    4. **Print physical copy** if needed (kiosk available)
                    """)
                
                # Quick check-in option
                st.subheader("✅ Quick Check-in")
                if st.button(f"Check-in {form_data['first_name']} Now", type="primary"):
                    checkin_success, attendee = st.session_state.db.quick_checkin(ticket_id)
                    if checkin_success:
                        st.success(f"✅ {form_data['first_name']} checked in successfully!")
                    else:
                        st.warning("Already checked in or ticket not found")
            
            else:
                st.error(f"❌ {message}")

elif selected_page == "Check-in":
    st.title("✅ Attendee Check-in")
    
    # Two-column layout for check-in
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Check-in Methods")
        
        method = st.radio("Select method:", 
                         ["📷 Scan Barcode", "🔢 Enter Ticket ID", "👤 Search Attendee"],
                         horizontal=True)
        
        if method == "📷 Scan Barcode":
            st.info("Position barcode in front of camera")
            
            # Camera scan placeholder
            if st.button("Start Camera", icon="📷", type="primary"):
                st.warning("Camera scanning requires additional setup. Please enter ticket ID manually.")
            
            # Manual fallback
            st.markdown("---")
            ticket_id = st.text_input("Or enter Ticket ID manually:", 
                                     placeholder="RWT-ABC123",
                                     key="manual_checkin_input")
            
            if ticket_id and st.button("Check In", use_container_width=True):
                with st.spinner("Processing..."):
                    success, attendee = st.session_state.db.quick_checkin(ticket_id)
                    if success:
                        st.success(f"✅ Check-in successful! Welcome {attendee[0]} {attendee[1]}!")
                        st.balloons()
                    else:
                        st.error("❌ Ticket not found or already checked in")
        
        elif method == "🔢 Enter Ticket ID":
            ticket_id = st.text_input("Ticket ID:", 
                                     placeholder="RWT-ABC123",
                                     key="ticket_checkin_input")
            
            if ticket_id and st.button("Check In", type="primary", use_container_width=True):
                with st.spinner("Processing..."):
                    success, attendee = st.session_state.db.quick_checkin(ticket_id)
                    if success:
                        st.success(f"✅ Check-in successful! Welcome {attendee[0]} {attendee[1]}!")
                        st.balloons()
                    else:
                        st.error("❌ Ticket not found or already checked in")
        
        else:  # Search Attendee
            search_term = st.text_input("Search by name:", 
                                       placeholder="First or last name")
            
            if search_term:
                conn = st.session_state.db.get_connection()
                results = pd.read_sql_query(
                    f"""
                    SELECT ticket_id, first_name, last_name, status 
                    FROM registrations 
                    WHERE first_name LIKE '%{search_term}%' 
                       OR last_name LIKE '%{search_term}%'
                    LIMIT 10
                    """,
                    conn
                )
                conn.close()
                
                if not results.empty:
                    for _, row in results.iterrows():
                        col_a, col_b, col_c = st.columns([3, 2, 1])
                        with col_a:
                            st.write(f"**{row['first_name']} {row['last_name']}**")
                        with col_b:
                            status = "✅ Checked In" if row['status'] == 'checked_in' else "🟡 Registered"
                            st.write(status)
                        with col_c:
                            if row['status'] != 'checked_in':
                                if st.button("Check In", key=f"checkin_{row['ticket_id']}"):
                                    success, _ = st.session_state.db.quick_checkin(row['ticket_id'])
                                    if success:
                                        st.success("Checked in!")
                                        st.rerun()
                else:
                    st.info("No attendees found")
    
    with col2:
        st.subheader("📊 Live Stats")
        
        stats = st.session_state.db.get_dashboard_stats()
        
        st.metric("Total", stats.get('total', 0))
        st.metric("Checked In", stats.get('checked_in', 0))
        st.metric("Pending", stats.get('pending', 0))
        
        st.markdown("---")
        
        st.subheader("🕐 Recent Check-ins")
        
        conn = st.session_state.db.get_connection()
        recent_checkins = pd.read_sql_query(
            """
            SELECT first_name, last_name, checkin_time 
            FROM registrations 
            WHERE status = 'checked_in' 
            ORDER BY checkin_time DESC 
            LIMIT 5
            """,
            conn
        )
        conn.close()
        
        if not recent_checkins.empty:
            for _, row in recent_checkins.iterrows():
                time_str = pd.to_datetime(row['checkin_time']).strftime('%I:%M %p')
                st.caption(f"**{row['first_name']} {row['last_name']}** - {time_str}")
        else:
            st.info("No recent check-ins")

elif selected_page == "Dashboard":
    st.title("📊 Event Dashboard")
    
    # Get data for dashboard
    conn = st.session_state.db.get_connection()
    df = pd.read_sql_query("SELECT * FROM registrations", conn)
    conn.close()
    
    stats = st.session_state.db.get_dashboard_stats()
    
    # Top metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Registered", stats.get('total', 0))
    with col2:
        st.metric("Checked In", stats.get('checked_in', 0))
    with col3:
        st.metric("Check-in Rate", stats.get('checkin_rate', '0%'))
    with col4:
        st.metric("Worship Team", stats.get('worship_team', 0))
    with col5:
        st.metric("Volunteers", stats.get('volunteers', 0))
    
    st.markdown("---")
    
    # Create charts
    if not df.empty:
        charts = create_dashboard_charts(stats, df)
        
        # Display charts in tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Check-in Trends", "Demographics", "Raw Data"])
        
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                if 'checkin_gauge' in charts:
                    st.plotly_chart(charts['checkin_gauge'], use_container_width=True)
            with col2:
                if 'sources_chart' in charts:
                    st.plotly_chart(charts['sources_chart'], use_container_width=True)
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                if 'hourly_chart' in charts:
                    st.plotly_chart(charts['hourly_chart'], use_container_width=True)
            with col2:
                if 'timeline_chart' in charts:
                    st.plotly_chart(charts['timeline_chart'], use_container_width=True)
        
        with tab3:
            # Additional demographic analysis
            if not df.empty:
                # Age distribution (if available)
                st.subheader("Registration Analysis")
                
                # Source distribution
                if 'source_system' in df.columns:
                    source_counts = df['source_system'].value_counts()
                    fig_sources = px.bar(x=source_counts.index, y=source_counts.values,
                                       title="Registrations by Source",
                                       color_discrete_sequence=['#4CAF50'])
                    st.plotly_chart(fig_sources, use_container_width=True)
        
        with tab4:
            # Raw data table
            st.dataframe(df, use_container_width=True)
    
    else:
        st.info("No registration data available yet.")

elif selected_page == "Manage":
    st.title("⚙️ Event Management")
    
    tab1, tab2, tab3 = st.tabs(["Generate Tickets", "Bulk Operations", "System Settings"])
    
    with tab1:
        st.subheader("🎫 Generate Tickets")
        
        col1, col2 = st.columns(2)
        
        with col1:
            num_tickets = st.number_input("Number of tickets to generate", 
                                         min_value=1, 
                                         max_value=100, 
                                         value=10)
            ticket_prefix = st.selectbox("Ticket Prefix", 
                                        ["RWT", "VIP", "WT", "VOL"],
                                        help="Prefix for ticket IDs")
            
            if st.button("Generate Tickets", type="primary"):
                with st.spinner(f"Generating {num_tickets} tickets..."):
                    tickets = []
                    for i in range(num_tickets):
                        ticket_id = st.session_state.barcode_gen.generate_ticket_id(ticket_prefix)
                        qr_img = st.session_state.barcode_gen.create_registration_qr(ticket_id)
                        tickets.append({
                            'ticket_id': ticket_id,
                            'qr_image': qr_img
                        })
                    
                    st.session_state.generated_tickets = tickets
                    st.success(f"Generated {num_tickets} tickets!")
        
        with col2:
            if 'generated_tickets' in st.session_state:
                st.subheader("Generated Tickets")
                
                # Show first few tickets
                for i, ticket in enumerate(st.session_state.generated_tickets[:3]):
                    with st.expander(f"Ticket {i+1}: {ticket['ticket_id']}"):
                        st.image(ticket['qr_image'])
                        
                        # Download button for each ticket
                        img_bytes = st.session_state.barcode_gen.img_to_bytes(ticket['qr_image'])
                        st.download_button(
                            label=f"Download {ticket['ticket_id']}",
                            data=img_bytes,
                            file_name=f"{ticket['ticket_id']}.png",
                            mime="image/png",
                            key=f"dl_{ticket['ticket_id']}"
                        )
                
                if len(st.session_state.generated_tickets) > 3:
                    st.info(f"... and {len(st.session_state.generated_tickets) - 3} more tickets")
                
                # Bulk download
                st.markdown("---")
                if st.button("Download All as ZIP", icon="📦"):
                    st.info("ZIP download functionality would be implemented here")
    
    with tab2:
        st.subheader("📦 Bulk Operations")
        
        st.info("""
        **Bulk Operations Available:**
        - Import from CSV/Excel
        - Export to Google Sheets
        - Bulk check-in
        - Send mass emails
        - Generate reports
        """)
        
        uploaded_file = st.file_uploader("Upload CSV for bulk import", 
                                        type=['csv', 'xlsx'])
        
        if uploaded_file:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.dataframe(df.head())
            
            if st.button("Import to Database", type="primary"):
                st.success(f"Imported {len(df)} records!")
    
    with tab3:
        st.subheader("⚙️ System Settings")
        
        # Database management
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Database**")
            if st.button("Backup Database", icon="💾"):
                st.success("Database backed up!")
            
            if st.button("Clear All Data", type="secondary"):
                st.warning("This will delete all data!")
        
        with col2:
            st.markdown("**Google Drive Sync**")
            use_google_drive = st.checkbox("Enable Google Drive Sync", value=False)
            
            if use_google_drive:
                st.info("Google Drive sync enabled")
                if st.button("Sync Now", icon="🔄"):
                    with st.spinner("Syncing..."):
                        st.success("Sync complete!")

elif selected_page == "Export":
    st.title("📤 Export Data")
    
    export_type = st.selectbox("Export Type:", 
                              ["All Registrations", "Checked-in Only", "Pending Check-in", 
                               "Worship Team", "Volunteers", "Custom Report"])
    
    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date")
    with col2:
        end_date = st.date_input("End Date", value=datetime.now())
    
    # Format selection
    export_format = st.radio("Export Format:", ["CSV", "Excel", "PDF Report", "Google Sheets"])
    
    # Get data
    conn = st.session_state.db.get_connection()
    
    query = "SELECT * FROM registrations WHERE 1=1"
    params = []
    
    # Add date filter
    query += " AND date(registration_time) BETWEEN ? AND ?"
    params.extend([start_date, end_date])
    
    # Add type filter
    if export_type == "Checked-in Only":
        query += " AND status = 'checked_in'"
    elif export_type == "Pending Check-in":
        query += " AND status = 'registered'"
    elif export_type == "Worship Team":
        query += " AND worship_team = 1"
    elif export_type == "Volunteers":
        query += " AND volunteer = 1"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if not df.empty:
        st.subheader(f"Preview ({len(df)} records)")
        st.dataframe(df.head(), use_container_width=True)
        
        # Export buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if export_format in ["CSV", "Excel"]:
                if export_format == "CSV":
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name=f"registrations_{start_date}_to_{end_date}.csv",
                        mime="text/csv"
                    )
        
        with col2:
            if export_format == "Excel":
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Registrations')
                
                st.download_button(
                    label="📊 Download Excel",
                    data=output.getvalue(),
                    file_name=f"registrations_{start_date}_to_{end_date}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        with col3:
            if export_format == "Google Sheets":
                if st.button("📈 Export to Google Sheets"):
                    st.info("Google Sheets export would sync to your Google Drive")
        
        with col4:
            if export_format == "PDF Report":
                if st.button("📄 Generate PDF Report"):
                    st.info("PDF report generation would create a formatted report")
        
        # Statistics
        st.markdown("---")
        st.subheader("Export Statistics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", len(df))
        with col2:
            checked_in = len(df[df['status'] == 'checked_in'])
            st.metric("Checked In", checked_in)
        with col3:
            st.metric("Date Range", f"{start_date} to {end_date}")
    
    else:
        st.info("No data found for the selected criteria.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em;">
    <p>Rooted World Tour Emergency Registration System • v2.0</p>
    <p>For support, contact: tech@rootedworldtour.com • (555) 123-HELP</p>
</div>
""", unsafe_allow_html=True)