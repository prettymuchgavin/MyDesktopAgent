---
name: Web Research & Fact Gathering
description: Fast internet research, information synthesis, and summary reports.
triggers: search, research, google, news, find information, what is, look up
---

# Web Research & Fact Gathering Skill

When the user asks you to research a topic, investigate a question, or find current facts:

## Recommended Fast Workflow:
1. **Initial Search**: Use the `web_search` tool first to query relevant keywords and review top results in milliseconds.
2. **Deep Inspection**: If a specific webpage or documentation link has deep details, use `fetch_url` to read its full text.
3. **Synthesis**: Combine facts from multiple sources into a concise, structured bulleted summary.
4. **Deliver Report**:
   - If requested to save, write the findings to a markdown file with `write_file`.
   - Announce the key takeaway in voice commentary and signal task completion.
