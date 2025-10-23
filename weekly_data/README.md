# Example Data Structure

This directory contains extracted schedule data from WebUntis.

## File Format

Each `week_N.json` file contains:

```json
{
  "week_url": "https://example.webuntis.com/?date=2025-10-20",
  "data": [
    {
      "text": "Subject Name",
      "time": "07:20 - 08:50",
      "teacher": "Teacher Name",
      "resources": ["Room O1101"],
      "notes": []
    }
  ]
}
```

## Example Week

See `week_1.json.example` for a complete example.

## Privacy Note

Real schedule data is excluded from version control (.gitignore).
