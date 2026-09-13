"""Validated, versioned content. Add guides as JSON; restart to rebuild the index."""

from pathlib import Path

from backend.models import Guide


class KnowledgeBase:
    def __init__(self, directory: Path):
        self.guides: dict[str, Guide] = {}
        for path in sorted(directory.glob("*.json")):
            guide = Guide.model_validate_json(path.read_text(encoding="utf-8"))
            if guide.id in self.guides:
                raise ValueError(f"Duplicate guide id: {guide.id}")
            self.guides[guide.id] = guide
        if not self.guides:
            raise ValueError(f"No guides in {directory}")

    def get(self, guide_id: str) -> Guide:
        return self.guides[guide_id]

    def list(self, platform: str = "ios") -> list[Guide]:
        return [guide for guide in self.guides.values() if guide.platform == platform]
