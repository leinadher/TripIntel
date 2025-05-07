# 🌍 TripIntel – Intelligent Trip Planning & Visualization Tool

**Author:** Daniel Herrera  
**Date:** 03/05/2025  

---

## 1. Project Overview

**TripMapper** is a Streamlit-based web application designed to assist users in planning travel routes interactively. The tool allows users to create GPS-based travel segments, calculate total distance and time, and visualize results on an interactive map and dynamic table. With built-in export functionality, users can also download their itineraries in Excel or CSV formats for offline use.

Key features include:

- 🧭 **Route Building**: Easily construct travel paths by placing segment points with GPS coordinates.
- ⏱️ **Duration & Distance Calculator**: Automatically sums the travel time and distance for all segments.
- 🗺️ **Interactive Map**: Visualizes the full trip layout with markers, lines, and real-time updates.
- 📊 **Dynamic Table View**: Lists all segments, times, and distances with editable fields.
- 📤 **Export Options**: Download your itinerary as a clean Excel or CSV spreadsheet.

---

## 2. Repository Structure

- 📁 **`assets/`**: Contains images, icons, and future UI visuals.
- 📁 **`scripts/`**: Modular Python scripts for calculations, formatting, and map functions.
- 📁 **`.devcontainer/`**: Development container configuration for VS Code Dev Containers.
- 📄 **`main.py`**: Main Streamlit application entry point.
- 📄 **`activate.txt`**: Activation or environment setup instructions.
- 📄 **`requirements.txt`**: List of required Python dependencies.
- 📄 **`README.md`**: This file.

---

## 3. How It Works

1. 📍 **User inputs waypoints** via an intuitive interface.
2. 🧮 **Each segment is computed** for both time and distance.
3. 🌐 **Route is plotted** on a map with dynamic updates for each adjustment.
4. 📋 **Segment data is displayed** in a table for reference or manual tweaking.
5. 💾 **Itinerary can be exported** as Excel or CSV for external use.

---

## 4. Data & Libraries

TripMapper utilizes well-supported libraries and mapping tools:

- 🐍 **Python + Streamlit** – core application and frontend framework.
- 📍 **geopy / haversine / folium** – distance calculations and map rendering.
- 📦 **pandas / openpyxl** – data manipulation and Excel export.

---

## 5. Running the App Locally

To launch the app on your local machine:

```bash
git clone https://github.com/leinadher/TripMapper.git
cd TripMapper
pip install -r requirements.txt
streamlit run main.py
