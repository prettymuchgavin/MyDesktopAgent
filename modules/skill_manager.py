import os
import glob
import re
from typing import Dict, Any, List, Optional
from modules.logger import setup_logger

logger = setup_logger("SkillManager")

class MarkdownSkill:
    """Represents an agent skill defined entirely in a Markdown (.md) document."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.name = os.path.splitext(self.filename)[0].replace("_", " ").title()
        self.description = ""
        self.triggers: List[str] = []
        self.content = ""
        self.raw_text = ""
        self._parse()

    def _parse(self):
        try:
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                self.raw_text = f.read()

            text = self.raw_text

            # Parse YAML frontmatter if present (--- ... ---)
            frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
            if frontmatter_match:
                fm_text = frontmatter_match.group(1)
                body = frontmatter_match.group(2)
                
                # Simple YAML line parsing
                for line in fm_text.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k = k.strip().lower()
                        v = v.strip().strip('"').strip("'")
                        if k == "name":
                            self.name = v
                        elif k == "description":
                            self.description = v
                        elif k in ["triggers", "keywords", "tags"]:
                            self.triggers = [t.strip().lower() for t in v.split(",") if t.strip()]
                self.content = body.strip()
            else:
                # Parse markdown headers
                lines = text.splitlines()
                body_lines = []
                for line in lines:
                    if line.startswith("# "):
                        self.name = line[2:].strip()
                    elif line.lower().startswith("description:"):
                        self.description = line.split(":", 1)[1].strip()
                    elif line.lower().startswith("triggers:"):
                        self.triggers = [t.strip().lower() for t in line.split(":", 1)[1].split(",") if t.strip()]
                    else:
                        body_lines.append(line)
                self.content = "\n".join(body_lines).strip()

            if not self.description:
                # Use first paragraph as description
                paragraphs = [p.strip() for p in self.content.split("\n\n") if p.strip() and not p.strip().startswith("#")]
                if paragraphs:
                    self.description = paragraphs[0][:150]
        except Exception as e:
            logger.error(f"Error parsing Markdown skill '{self.file_path}': {e}")

    def matches_task(self, query: str) -> bool:
        """Determines if this skill is relevant to a user task."""
        q_lower = query.lower()
        if any(trig in q_lower for trig in self.triggers):
            return True
        if self.name.lower() in q_lower:
            return True
        # Check significant keyword matches
        name_words = [w for w in re.findall(r'\w+', self.name.lower()) if len(w) > 3]
        if any(w in q_lower for w in name_words):
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "filename": self.filename,
            "description": self.description,
            "triggers": self.triggers,
            "content_length": len(self.content)
        }

class SkillManager:
    """Discovers, manages, and injects Markdown (.md) skills into Desktop Agent workflows."""
    def __init__(self, skills_dir: Optional[str] = None):
        if skills_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.skills_dir = os.path.join(base_dir, "skills")
        else:
            self.skills_dir = skills_dir

        os.makedirs(self.skills_dir, exist_ok=True)
        self.skills: Dict[str, MarkdownSkill] = {}
        self.reload_skills()

    def reload_skills(self):
        """Scans skills/ directory and loads all .md skill definitions."""
        self.skills = {}
        md_files = glob.glob(os.path.join(self.skills_dir, "*.md"))
        for f in md_files:
            skill = MarkdownSkill(f)
            self.skills[skill.name.lower()] = skill
        logger.info(f"🧩 Loaded {len(self.skills)} Markdown skills from '{self.skills_dir}'")

    def get_all_skills(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self.skills.values()]

    def find_relevant_skills(self, task_goal: str) -> List[MarkdownSkill]:
        """Finds markdown skills relevant to the current user goal."""
        matched = []
        for skill in self.skills.values():
            if skill.matches_task(task_goal):
                matched.append(skill)
        return matched

    def build_skill_context(self, task_goal: str) -> str:
        """Builds prompt context from relevant markdown skills to guide execution."""
        matched = self.find_relevant_skills(task_goal)
        if not matched:
            # If no specific skill matched, include high-level summary of available skills
            return ""

        context_blocks = []
        for s in matched[:3]:  # Top 3 matched skills
            context_blocks.append(f"### [Skill: {s.name}]\n{s.content}\n")

        return "--- ACTIVE MARKDOWN SKILLS & WORKFLOW GUIDELINES ---\n" + "\n".join(context_blocks) + "\n---------------------------------------------------"
