#!/usr/bin/env python3
"""
Build courses.json = curated platforms + fresh RSS course items.
Stdlib only. Run from cron; index.html fetches the JSON.
"""
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from hashlib import md5
from pathlib import Path

REPO = Path(__file__).resolve().parent
OUT = REPO / "courses.json"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Curated platforms — always present, hand-maintained.
PLATFORMS = [
    {"id": "coursera", "name": "Coursera (Audit)", "url": "https://coursera.org", "cat": "University", "difficulty": "mixed", "duration": 40, "desc": "University courses from top schools. Audit free, certificates paid.", "tags": ["CS", "Business", "Data", "Health"]},
    {"id": "edx", "name": "edX (Audit)", "url": "https://edx.org", "cat": "University", "difficulty": "mixed", "duration": 40, "desc": "Harvard, MIT, Berkeley courses. Verified track paid.", "tags": ["CS", "Engineering", "Humanities"]},
    {"id": "khan", "name": "Khan Academy", "url": "https://khanacademy.org", "cat": "Foundation", "difficulty": "beginner", "duration": 200, "desc": "K-12 math, science, computing. 100% free forever.", "tags": ["Math", "CS Basics", "Science"]},
    {"id": "fcc", "name": "freeCodeCamp", "url": "https://freecodecamp.org", "cat": "Web Dev", "difficulty": "beginner", "duration": 300, "desc": "Full cert paths: Responsive Web, JS, Python, Data Sci, ML. 100% free.", "tags": ["HTML/CSS", "JS", "Python", "Data", "ML"]},
    {"id": "mitocw", "name": "MIT OpenCourseWare", "url": "https://ocw.mit.edu", "cat": "University", "difficulty": "advanced", "duration": 120, "desc": "Complete MIT syllabi: lectures, notes, exams, solutions.", "tags": ["CS", "Math", "Physics", "Engineering"]},
    {"id": "cs50", "name": "Harvard CS50", "url": "https://cs50.harvard.edu", "cat": "Foundation", "difficulty": "beginner", "duration": 50, "desc": "Intro CS: C, Python, SQL, Web, algorithms. Free on edX/YouTube.", "tags": ["CS Fundamentals", "Systems", "Algo"]},
    {"id": "gcloud", "name": "Google Cloud Skills Boost", "url": "https://cloudskillsboost.google", "cat": "Cloud", "difficulty": "intermediate", "duration": 60, "desc": "GCP, AI, Data, Infra labs. Free tier + credits.", "tags": ["GCP", "AI", "Data", "K8s"]},
    {"id": "mslearn", "name": "Microsoft Learn", "url": "https://learn.microsoft.com/training/", "cat": "Cloud", "difficulty": "mixed", "duration": 80, "desc": "Azure, .NET, AI, GitHub, Power Platform. Free interactive modules.", "tags": ["Azure", "C#", "AI", "GitHub"]},
    {"id": "aws", "name": "AWS Skill Builder", "url": "https://skillbuilder.aws", "cat": "Cloud", "difficulty": "mixed", "duration": 100, "desc": "Cloud Practitioner to Pro/Specialty cert prep. Free digital training.", "tags": ["AWS", "Cloud", "Architecture"]},
    {"id": "odin", "name": "The Odin Project", "url": "https://theodinproject.com", "cat": "Web Dev", "difficulty": "intermediate", "duration": 400, "desc": "Full-stack curriculum: Ruby/Rails or JS/Node. Project-based.", "tags": ["Ruby", "Rails", "JS", "Node", "React"]},
    {"id": "codecademy", "name": "Codecademy (Free)", "url": "https://codecademy.com/catalog/subject/all?free=true", "cat": "Interactive", "difficulty": "beginner", "duration": 30, "desc": "Interactive coding basics. Pro locked but free tier solid.", "tags": ["Python", "JS", "SQL", "HTML/CSS"]},
    {"id": "mdn", "name": "MDN Web Docs", "url": "https://developer.mozilla.org", "cat": "Reference", "difficulty": "mixed", "duration": 50, "desc": "Web standards authority. Tutorials plus complete reference.", "tags": ["HTML", "CSS", "JS", "Web APIs"]},
    {"id": "fastai", "name": "Fast.ai", "url": "https://course.fast.ai", "cat": "AI/ML", "difficulty": "intermediate", "duration": 60, "desc": "Practical deep learning for coders. Top-down, code-first.", "tags": ["PyTorch", "CV", "NLP", "Tabular"]},
    {"id": "deeplearning", "name": "DeepLearning.AI (Audit)", "url": "https://deeplearning.ai/courses", "cat": "AI/ML", "difficulty": "intermediate", "duration": 90, "desc": "Andrew Ng ML/DL specializations. Audit free on Coursera.", "tags": ["ML", "DL", "Transformers", "MLOps"]},
    {"id": "hf", "name": "Hugging Face Course", "url": "https://huggingface.co/learn", "cat": "AI/ML", "difficulty": "intermediate", "duration": 40, "desc": "Transformers, NLP, Diffusion, RL. Hands-on with HF ecosystem.", "tags": ["Transformers", "NLP", "Diffusion"]},
    {"id": "classcentral", "name": "Class Central", "url": "https://classcentral.com", "cat": "Aggregator", "difficulty": "mixed", "duration": 10, "desc": "Search/review aggregator for all MOOCs. Track new free courses.", "tags": ["Discovery", "Reviews"]},
    {"id": "openlearn", "name": "OpenLearn (OU)", "url": "https://open.edu/openlearn", "cat": "Short Courses", "difficulty": "beginner", "duration": 20, "desc": "Open University UK. Short courses, digital badges, free.", "tags": ["Varied", "Badges"]},
    {"id": "youtube", "name": "YouTube Channels", "url": "https://youtube.com", "cat": "Video", "difficulty": "mixed", "duration": 9999, "desc": "Corey Schafer, Fireship, Traversy, NetworkChuck, TechWorld with Nana.", "tags": ["All topics"]},
]

# RSS/Atom feeds — verified reachable 2026-08.
FEEDS = [
    {"name": "freeCodeCamp", "url": "https://www.freecodecamp.org/news/rss/", "cat": "Web Dev", "difficulty": "beginner", "tags": ["JS", "Python", "Web"]},
    {"name": "Google Cloud Training", "url": "https://cloud.google.com/blog/topics/training-certifications/rss", "cat": "Cloud", "difficulty": "intermediate", "tags": ["GCP", "Cloud", "Certification"]},
    {"name": "AWS Training", "url": "https://aws.amazon.com/blogs/training-and-certification/feed/", "cat": "Cloud", "difficulty": "mixed", "tags": ["AWS", "Cloud", "Certification"]},
    {"name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml", "cat": "AI/ML", "difficulty": "intermediate", "tags": ["ML", "Transformers", "NLP"]},
    {"name": "Udacity Blog", "url": "https://blog.udacity.com/feed", "cat": "Career", "difficulty": "mixed", "tags": ["Career", "Nanodegree"]},
    {"name": "dev.to Beginners", "url": "https://dev.to/feed/tag/beginners", "cat": "Community", "difficulty": "beginner", "tags": ["Tutorial", "Beginner"]},
    {"name": "HN Free Courses", "url": "https://hnrss.org/newest?q=free+course", "cat": "Community", "difficulty": "mixed", "tags": ["Discovery", "HN"]},
]

# Only keep feed items that look like learning material.
KEEP = ("course", "learn", "tutorial", "guide", "handbook", "certification",
        "cert exam", "bootcamp", "how to", "introduction to", "beginner",
        "roadmap", "training", "crash course", "workshop", "curriculum")


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f"  [warn] {url}: {e}", file=sys.stderr)
        return None


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def parse_feed(raw):
    """Return [(title, link, summary)] from RSS or Atom."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"  [warn] bad xml: {e}", file=sys.stderr)
        return []
    items = []
    # RSS
    for it in root.iter("item"):
        title = it.findtext("title") or ""
        link = it.findtext("link") or ""
        desc = it.findtext("description") or ""
        if title and link:
            items.append((strip_tags(title), link.strip(), strip_tags(desc)))
    if items:
        return items
    # Atom
    ns = "{http://www.w3.org/2005/Atom}"
    for it in root.iter(f"{ns}entry"):
        title = it.findtext(f"{ns}title") or ""
        link = ""
        for l in it.iter(f"{ns}link"):
            if l.get("rel") in (None, "alternate"):
                link = l.get("href") or ""
                break
        desc = it.findtext(f"{ns}summary") or it.findtext(f"{ns}content") or ""
        if title and link:
            items.append((strip_tags(title), link.strip(), strip_tags(desc)))
    return items


def estimate_duration(title, difficulty):
    t = title.lower()
    if any(k in t for k in ("intro", "beginner", "basics", "fundamentals", "crash course")):
        return 10 if difficulty == "beginner" else 20
    if any(k in t for k in ("complete", "full", "comprehensive", "masterclass", "bootcamp", "specialization", "handbook")):
        return 60 if difficulty != "advanced" else 100
    if any(k in t for k in ("certification", "cert", "professional", "nanodegree")):
        return 80
    return 20 if difficulty == "beginner" else 40


def collect_feed(f):
    raw = fetch(f["url"])
    if not raw:
        return []
    out = []
    for title, link, desc in parse_feed(raw):
        low = title.lower()
        if not any(k in low for k in KEEP):
            continue
        if len(title) < 12:
            continue
        out.append({
            "id": md5(link.encode()).hexdigest()[:12],
            "name": title[:110],
            "url": link,
            "cat": f["cat"],
            "difficulty": f["difficulty"],
            "duration": estimate_duration(title, f["difficulty"]),
            "desc": (desc[:180] or title)[:180],
            "tags": f["tags"][:4],
            "source": f["name"],
        })
    print(f"  {f['name']}: {len(out)} items")
    return out


def main():
    items = []
    for f in FEEDS:
        items.extend(collect_feed(f))

    # Curated first, so a feed item never overwrites a platform entry.
    by_url = {}
    for c in PLATFORMS:
        c = dict(c)
        c["source"] = "Curated"
        by_url[c["url"]] = c
    for c in items:
        by_url.setdefault(c["url"], c)

    courses = sorted(by_url.values(), key=lambda x: (x["source"] != "Curated", x["cat"], x["name"]))
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(courses),
        "curated": len(PLATFORMS),
        "from_feeds": len(courses) - len(PLATFORMS),
        "courses": courses,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    print(f"\n{OUT}: {payload['total']} courses ({payload['from_feeds']} from feeds)")

    # self-check
    assert payload["total"] >= len(PLATFORMS), "curated platforms lost"
    assert all(c.get("url") and c.get("name") for c in courses), "bad record"
    return 0


if __name__ == "__main__":
    sys.exit(main())