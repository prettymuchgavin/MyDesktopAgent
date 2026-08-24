# Contributing to My Desktop Agent

Thank you for your interest in improving **My Desktop Agent**! We welcome contributions ranging from new Markdown skills to core engine enhancements.

---

## 🧩 Adding Custom Markdown Skills

Skills in My Desktop Agent are defined entirely in Markdown (`.md`) files inside the [`skills/`](./skills/) directory:

1. Create a new file in `skills/` (e.g. `skills/spotify_player.md`).
2. Add the YAML frontmatter with `name`, `description`, and `triggers`:
   ```markdown
   ---
   name: Spotify Playback Controller
   description: Controls music playback, playlists, and tracks on Spotify.
   triggers: spotify, music, play song, next track, pause music
   ---

   # Spotify Playback Skill

   ## Recommended Workflow:
   1. Use `open_app` with `spotify` or `focus_window` with `Spotify`.
   2. Use `hotkey` with `["space"]` to toggle playback.
   3. Announce the action in voice commentary.
   ```
3. The agent will automatically discover and load the skill on next startup!

---

## 🛠️ Development Setup

1. Clone your fork:
   ```bash
   git clone https://github.com/your-username/my-desktop-agent.git
   cd my-desktop-agent
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run setup wizard:
   ```bash
   python setup.py
   ```
5. Launch the application:
   ```bash
   python main.py
   ```

---

## 📋 Pull Request Guidelines

- Ensure your code follows standard PEP 8 styling.
- Verify that terminal execution and screen capture tests pass without throwing unhandled exceptions.
- Provide a clear, descriptive summary of changes in your Pull Request.
