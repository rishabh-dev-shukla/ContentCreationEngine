# ContentCreationEngine Web Frontend Documentation

## Overview
The ContentCreationEngine web frontend is a Flask-based web application that provides a user-friendly interface for managing personas, generating content, reviewing research data, and handling content approval workflows. It is designed to work with the existing ContentCreationEngine backend and data pipeline.

---

## Main Features
- **Dashboard**: Overview of personas and quick access to main actions.
- **AI Provider Selection**: Choose between OpenAI, Deepseek, Grok, etc.
- **Persona Management**: Add, edit, and manage personas.
- **Content Generation**: Generate new content ideas, scripts, and visuals.
- **Platform Selection**: Select platforms (Instagram, Reddit, News, YouTube, Serper) for research and content.
- **Research Data View**: Tabbed and tile/table view of research data from all sources.
- **Content Review**: Approve, reject, or edit generated content. All actions are non-destructive.
- **Settings Page**: Manage API keys and configuration.

---

## File & Folder Structure

### `web/`
- **app.py**: Main Flask application. Contains all routes, API endpoints, and logic for serving pages and handling AJAX/API requests.
- **static/**: Static assets (CSS, JS, icons)
  - **css/style.css**: Custom styles, dark/light theme support.
  - **js/main.js**: JavaScript for UI interactivity (tab switching, AJAX, modals, etc).
- **templates/**: Jinja2 HTML templates for all pages
  - **base.html**: Base layout, navbar, theme toggle, and shared blocks.
  - **index.html**: Dashboard/homepage.
  - **personas.html**: Persona management page.
  - **persona_form.html**: Add/edit persona form.
  - **generate.html**: Content generation page.
  - **content.html**: List of generated content runs.
  - **content_detail.html**: Detailed view for a single content run (ideas, scripts, visuals, research, approve/reject/edit modals).
  - **research.html**: Research data browser with tabbed and tile/table views.
  - **settings.html**: API keys and configuration.
  - **404.html, 500.html**: Error pages.
- **run_web.py**: Entrypoint script to launch the Flask server.

### `data/`
- **output/**: Stores generated content JSON files, organized by persona.
- **personas/**: Persona configuration files.
- **research_cache/**: Cached research data from all platforms.

### `src/content_creation_engine/`
- **generators/**: Content generation logic (ideas, scripts, visuals).
- **persona/**: Persona management logic.
- **scheduler/**: Workflow and pipeline orchestration.
- **scrapers/**: Data collection from external platforms.
- **utils/**: Utility functions and AI client wrappers.

### `config/`
- **settings.py**: Central configuration for paths, API keys, and defaults.
- **prompts/**: Prompt templates for AI generation.

### `tests/`
- Unit and integration tests for all major modules.

### `docs/`
- **ARCHITECTURE.md**: System architecture and high-level design.
- **project_plan.txt**: Project planning notes.
- **frontend.md**: (This file) Documentation for the web frontend.

---

## How It Works
- The Flask app serves all frontend pages and provides REST API endpoints for AJAX actions (approve/reject/edit, persona management, etc).
- All data is stored in JSON files under `data/` (no database required).
- The UI uses Bootstrap 5 for styling and layout, with custom CSS and JavaScript for enhanced interactivity.
- All content actions (approve, reject, edit) are non-destructive: nothing is deleted, only status/fields are updated.
- Research data is shown in a tabbed interface, with special handling for YouTube/Instagram engagement stats.
- The app is designed for easy extension and customization.

---

## Extending or Modifying
- To add new features, create new templates and routes in `web/app.py` and `web/templates/`.
- To change data storage, update the logic in `web/app.py` and the relevant `src/content_creation_engine/` modules.
- For new research sources, add a scraper in `src/content_creation_engine/scrapers/` and update the research view.

---

## Authors & Credits
- Developed by rishabh-dev-shukla and contributors.
- Uses Flask, Bootstrap, and Jinja2.

---

For more details, see the code comments and the main `ARCHITECTURE.md`.
