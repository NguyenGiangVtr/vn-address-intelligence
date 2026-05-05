# Boundary Visualization Integration

This project now includes the boundary visualization workflow from `vnai_boundary_visualization`.

## What was integrated

- Database-backed polygon loading for `mat.area_polygon`.
- Folium rendering helpers for admin boundaries grouped by partner.
- A FastAPI endpoint that generates an HTML map preview.
- A new UI page for generating and previewing boundary maps.

## Backend entry points

- `GET /api/boundary/map`
  - Query params:
    - `scope=province|district|ward`
    - `province_id`
    - `district_id`
    - `ward_id`
    - `zoom_start`
  - Returns JSON with `url` and `rings`.

## Frontend entry point

- `ui/pages/boundary-visualization.html`
  - Accessible from the sidebar as `Ranh giới hành chính`.
  - Lets the user choose scope and IDs, then renders the generated HTML map in an iframe.

## Source files

- `app/api/boundary.py`
- `app/tools/boundary_visualization/folium_boundaries.py`
- `app/tools/boundary_visualization/load_polygons.py`
- `ui/app.js`
- `ui/index.html`
- `ui/pages/boundary-visualization.html`
