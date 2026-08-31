#!/bin/bash
# Cron script to update course list from Class Central + known sources
# Run periodically via cron to discover new free courses
# Output: writes new_courses.json which can be imported into the tracker

set -e

OUTPUT_DIR="/home/ec2-user/course-tracker"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${OUTPUT_DIR}/new_courses_${TIMESTAMP}.json"

echo "{\"timestamp\":\"${TIMESTAMP}\","'"'courses'"': []}" > "$OUTPUT_FILE"

# Source list of free course platforms with discovery URLs
# These are public pages we can scrape or RSS feeds
SOURCES=(
  "https://classcentral.com/search?q=free%20course&filters%5Blevel%5D=beginner"
  "https://classcentral.com/search?q=free%20course&filters%5Blevel%5D=intermediate"
  "https://freecodecamp.org/news/"
  "https://mit-ocw.mit.edu/latest-updates/"
  "https://www.edx.org/learn/free"
  "https://www.coursera.org/learn?q=free"
)

for SOURCE in "${SOURCES[@]}"; do
  echo "Checking: ${SOURCE}" >> "$OUTPUT_FILE"
  # Try curl silently, extract course names if possible
  if command -v curl >/dev/null 2>&1; then
    BODY=$(curl -s --max-time 15 "$SOURCE" 2>/dev/null || echo "")
    if [ -n "$BODY" ]; then
      # Very naive extraction: look for course titles in h3/h4 tags (Class Central pattern)
      COUNT=$(echo "$BODY" | grep -oiE '<h[34]>[^<]{3,60}</h[34]>' | wc -l)
      echo "  Found $COUNT title tags" >> "$OUTPUT_FILE"
      # Extract a few sample titles
      TITLES=$(echo "$BODY" | grep -oiE '<h[34]>[^<]{3,60}</h[34]>' | head -3 | sed 's/<[^>]*>//g')
      echo "  Sample: ${TITLES}" >> "$OUTPUT_FILE"
    fi
  else
    echo "  curl not available, skipping" >> "$OUTPUT_FILE"
  fi
done

echo "Update complete: ${OUTPUT_FILE}" >> "$OUTPUT_FILE"
echo "Run: hermes agent import this JSON into course-tracker to add new courses"