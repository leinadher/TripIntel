import streamlit as st
import pandas as pd
import pydeck as pdk
from dotenv import load_dotenv
from scripts.geo_functions import geocode_place, get_route_coords, seconds_to_hours, meters_to_km
from datetime import datetime, time, timedelta
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import io
import xlsxwriter
from pathlib import Path
import base64

load_dotenv()

st.set_page_config(layout="wide")

svg_path = Path("assets/travel-svgrepo-com.svg")
if svg_path.exists():
    # Read the file and encode it
    svg_data = svg_path.read_bytes()
    b64_svg = base64.b64encode(svg_data).decode("utf-8")

    # Inject as an <img> tag using a data URI
    st.sidebar.markdown(
        f"""
        <div style='text-align:center; margin-top:-1rem; margin-bottom:1rem;'>
            <img src="data:image/svg+xml;base64,{b64_svg}" width="100" height="100" />
        </div>
        """,
        unsafe_allow_html=True
    )

st.sidebar.markdown(
    "<h1 style='text-align: center; margin-top: -1rem;'>TripIntel</h1>",
    unsafe_allow_html=True
)

if "trip_df" not in st.session_state:
    st.session_state.trip_df = pd.DataFrame(columns=[
        "from_place", "from_lat", "from_lon",
        "to_place", "to_lat", "to_lon",
        "departure_dt", "arrival_dt",
        "transport_type", "notes",
        "distance_m", "duration_s"
    ])

TRANSPORT_OPTIONS = {
    "hike": "🥾 Hike",
    "bike": "🚴‍♂️ Bike",
    "drive": "🚗 Drive",
    "fly": "✈️ Fly"
}

TRANSPORT_COLORS = {
    "hike": [34, 139, 34],     # forest green
    "bike": [255, 165, 0],     # orange
    "drive": [70, 130, 180],   # steel blue
    "fly": [128, 0, 128],      # purple
    "train": [200, 0, 0]       # red
}

#--- Sidebar new travel segment ---#

st.sidebar.subheader("Next Travel Segment")

with st.sidebar.form("add_segment"):
    if not st.session_state.trip_df.empty:
        last_segment = st.session_state.trip_df.iloc[-1]
        last_to_place = last_segment["to_place"]
        last_to_lat = last_segment["to_lat"]
        last_to_lon = last_segment["to_lon"]
        last_arrival_dt = pd.to_datetime(last_segment["arrival_dt"])

        # Suggest departure 1 hour after arrival
        suggested_departure = last_arrival_dt + timedelta(hours=1)

        # FROM place (auto-filled)
        st.markdown(
            f"**From:** <span style='color:lightgreen; font-weight:bold;'>{last_to_place}</span> (auto-filled)",
            unsafe_allow_html=True
        )
        from_place = last_to_place
        from_lat = last_to_lat
        from_lon = last_to_lon
    else:
        from_place = st.text_input("From Place")
        from_lat = from_lon = None

        suggested_departure = datetime.combine(datetime.today(), time(9, 0))

    # TO place (always editable)
    to_place = st.text_input("To Place")

    # Departure time
    departure_date = st.date_input("Departure Date", value=suggested_departure.date())
    departure_time = st.time_input("Departure Time", value=suggested_departure.time())
    departure_datetime = datetime.combine(departure_date, departure_time)

    transport = st.selectbox(
        "Transport Type",
        options=list(TRANSPORT_OPTIONS.keys()),
        format_func=lambda x: TRANSPORT_OPTIONS[x]
    )
    notes = st.text_area("Notes", "")

    submit = st.form_submit_button("Add Segment")

    if submit:
        if from_lat is None or from_lon is None:
            from_lat, from_lon = geocode_place(from_place)
        to_lat, to_lon = geocode_place(to_place)

        if None in [from_lat, from_lon, to_lat, to_lon]:
            st.error("Could not geocode one of the places.")
            st.stop()

        if not st.session_state.trip_df.empty and departure_datetime < last_arrival_dt:
            st.error(f"Departure must be after previous arrival at {last_arrival_dt.strftime('%Y-%m-%d %H:%M')}.")
            st.stop()

        coords, duration, distance = get_route_coords(from_lat, from_lon, to_lat, to_lon, transport)
        arrival_datetime = departure_datetime + timedelta(seconds=duration)

        new_row = {
            "from_place": from_place,
            "from_lat": from_lat,
            "from_lon": from_lon,
            "to_place": to_place,
            "to_lat": to_lat,
            "to_lon": to_lon,
            "departure_dt": departure_datetime,
            "arrival_dt": arrival_datetime,
            "transport_type": transport,
            "notes": notes,
            "distance_m": distance,
            "duration_s": duration
        }

        st.session_state.trip_df = pd.concat(
            [st.session_state.trip_df, pd.DataFrame([new_row])],
            ignore_index=True
        )

        st.success("Segment added!")
        st.rerun()

#--- Map Display ---#

with st.expander("🗺️ Map View", expanded=True):
    df = st.session_state.trip_df
    if not df.empty:
        # Generate scatter points
        points_df = pd.DataFrame({
            "place": df["from_place"].tolist() + df["to_place"].tolist(),
            "lat": df["from_lat"].tolist() + df["to_lat"].tolist(),
            "lon": df["from_lon"].tolist() + df["to_lon"].tolist()
        })

        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            points_df,
            get_position='[lon, lat]',
            get_radius=20,
            radius_min_pixels=4,
            get_color=[255, 0, 0],
            pickable=True
        )

        # Generate paths by transport type
        route_layers = []

        for transport_type in df["transport_type"].unique():
            subset = df[df["transport_type"] == transport_type]
            paths = []

            for _, row in subset.iterrows():
                coords, duration, distance = get_route_coords(
                    row["from_lat"], row["from_lon"],
                    row["to_lat"], row["to_lon"],
                    row["transport_type"]
                )
                paths.append({"path": coords})

            color = TRANSPORT_COLORS.get(transport_type, [100, 100, 100])

            layer = pdk.Layer(
                "PathLayer",
                paths,
                get_path="path",
                get_width=5,
                get_color=color,
                width_min_pixels=2
            )
            route_layers.append(layer)

        # View state should be defined once
        view_state = pdk.ViewState(
            latitude=points_df["lat"].mean(),
            longitude=points_df["lon"].mean(),
            zoom=4
        )

        st.pydeck_chart(pdk.Deck(
            layers=[scatter_layer] + route_layers,
            initial_view_state=view_state
        ))
    else:
        st.info("Add segments to see them on the map.")

#--- Trip KPIs ---#

with st.expander("📊 Trip Statistics", expanded=False):
    df = st.session_state.trip_df

    if df.empty:
        st.info("No data to show statistics.")
    else:
        total_km = df["distance_m"].sum() / 1000
        total_hr = df["duration_s"].sum() / 3600

        transport_breakdown = (
            df.groupby("transport_type")["distance_m"]
            .sum()
            .div(df["distance_m"].sum())
            .mul(100)
            .round(2)
            .sort_values(ascending=False)
        )

        st.markdown("#### **Total Distance (km)**")
        st.markdown(
            f"<h1 style='color:#21c55d;margin-top:-0.5rem;'>{total_km:,.2f}</h1>",
            unsafe_allow_html=True
        )

        st.markdown("#### **Total Duration (hours)**")
        st.markdown(
            f"<h1 style='color:#3b82f6;margin-top:-0.5rem;'>{total_hr:,.2f}</h1>",
            unsafe_allow_html=True
        )

        st.markdown("#### **Transport Type Share (by Distance)**")

        for mode, pct in transport_breakdown.items():
            emoji = TRANSPORT_OPTIONS.get(mode, "").split()[0]
            st.markdown(
                f"<p style='font-size:1.3rem;'>{emoji} <strong>{mode.title()}</strong>: "
                f"<span style='background-color:#16a34a;color:white;padding:0.2rem 0.5rem;"
                f"border-radius:0.3rem;'>{pct:.2f}%</span></p>",
                unsafe_allow_html=True
            )

# --- Table Display --- #

with st.expander("📜 Trip Breakdown", expanded=False):
    df_display = st.session_state.trip_df.copy()

    if not df_display.empty:
        # Ensure sort_order exists for consistent row order
        if "sort_order" not in df_display.columns:
            df_display["sort_order"] = list(range(len(df_display)))

        df_display = df_display.sort_values("sort_order").reset_index(drop=True)

        # Add human-readable fields
        df_display["distance_km"] = df_display["distance_m"].apply(meters_to_km)
        df_display["duration_hr"] = df_display["duration_s"].apply(seconds_to_hours)

        # Add delete checkbox column
        df_display["delete"] = False

        # Color mapping for transport types
        row_style_js = JsCode("""
        function(params) {
            const colors = {
                'hike': '#1a4d1a',
                'bike': '#4d2600',
                'drive': '#1e3a5f',
                'fly': '#3f0071',
                'train': '#660000'
            };
            const t = params.data.transport_type;
            return { 'backgroundColor': colors[t] || '#222', 'color': 'white' }
        }
        """)

        # Visible and editable columns
        visible_cols = [
            "from_place", "to_place", "departure_dt", "arrival_dt",
            "transport_type", "notes", "distance_km", "duration_hr", "delete"
        ]
        editable_cols = [
            "from_place", "to_place", "departure_dt", "arrival_dt",
            "transport_type", "notes", "delete"
        ]

        gb = GridOptionsBuilder.from_dataframe(df_display[visible_cols])
        gb.configure_columns(editable_cols, editable=True)
        gb.configure_column("transport_type", editable=True, cellEditor="agSelectCellEditor",
                            cellEditorParams={"values": list(TRANSPORT_OPTIONS.keys())})
        gb.configure_column("delete", header_name="🗑️ Delete", editable=True,
                            cellEditor="agCheckboxCellEditor")
        gb.configure_grid_options(rowDragManaged=True)
        gb.configure_selection("multiple", use_checkbox=True)
        gb.configure_grid_options(getRowStyle=row_style_js)

        grid_options = gb.build()

        grid_response = AgGrid(
            df_display[visible_cols],
            gridOptions=grid_options,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            height=450,
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True
        )

        updated_df = pd.DataFrame(grid_response["data"])

        # Preserve row order
        updated_df["sort_order"] = updated_df.index

        # --- Button Actions --- #
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

        with col1:
            if st.button("🗑️ Delete Checked Rows"):
                before = len(updated_df)
                updated_df = updated_df[updated_df["delete"] != True].drop(columns="delete")
                after = len(updated_df)
                st.session_state.trip_df = updated_df.drop(columns=["distance_km", "duration_hr"], errors="ignore")
                st.success(f"Deleted {before - after} row(s).")
                st.rerun()

        with col2:
            if st.button("🔄 Update Changes"):
                updated_rows = []
                for i, row in updated_df.iterrows():
                    from_lat, from_lon = geocode_place(row["from_place"])
                    to_lat, to_lon = geocode_place(row["to_place"])

                    if None in [from_lat, from_lon, to_lat, to_lon]:
                        st.warning(f"Row {i} could not be geocoded.")
                        continue

                    coords, duration, distance = get_route_coords(
                        from_lat, from_lon, to_lat, to_lon, row["transport_type"]
                    )

                    updated_rows.append({
                        "from_place": row["from_place"],
                        "from_lat": from_lat,
                        "from_lon": from_lon,
                        "to_place": row["to_place"],
                        "to_lat": to_lat,
                        "to_lon": to_lon,
                        "departure_dt": pd.to_datetime(row["departure_dt"]),
                        "arrival_dt": pd.to_datetime(row["arrival_dt"]),
                        "transport_type": row["transport_type"],
                        "notes": row["notes"],
                        "distance_m": distance,
                        "duration_s": duration,
                        "sort_order": i
                    })

                st.session_state.trip_df = pd.DataFrame(updated_rows)
                st.success("Changes saved and routes updated.")
                st.rerun()

        with col3:
            csv_buffer = io.StringIO()
            st.session_state.trip_df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="📀 Download as CSV",
                data=csv_buffer.getvalue(),
                file_name="trip_segments.csv",
                mime="text/csv"
            )

        with col4:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                st.session_state.trip_df.to_excel(writer, index=False, sheet_name="TripSegments")
            st.download_button(
                label="📈 Download as Excel",
                data=excel_buffer.getvalue(),
                file_name="trip_segments.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No trip segments available. Add some to begin planning.")