# Gemini project extraction prompt

Use this prompt with one or more selected PDF pages and their repository-relative
file name. Gemini produces extraction candidates; deterministic validation and a
human source check decide whether a record is accepted.

## Prompt

You extract electric transmission project facts from supplied source pages. Return
JSON only. Do not use outside knowledge and do not fill a field from a nearby
project.

For each project, return this object:

```json
{
  "source_reference": "repository-relative PDF path",
  "pdf_page": 1,
  "printed_page": "printed page label or null",
  "source_project_id": "source ID or null",
  "project_name": "exact source text or null",
  "company": "exact company or sponsor text or null",
  "project_type": "transmission_line, substation, other, or unknown",
  "terminal_a": "source-backed terminal or null",
  "terminal_b": "source-backed terminal or null",
  "terminal_basis": "title, description, both, or null",
  "in_service_date": "YYYY, YYYY-MM, YYYY-MM-DD, or null",
  "construction_start": "YYYY, YYYY-MM, YYYY-MM-DD, or null",
  "construction_end": "YYYY, YYYY-MM, YYYY-MM-DD, or null",
  "need_date": "YYYY, YYYY-MM, YYYY-MM-DD, or null",
  "schedule_text": "exact date labels and values in compact form or null",
  "uncertainties": ["specific source ambiguity"],
  "evidence": [
    {
      "pdf_page": 1,
      "printed_page": "printed page label or null",
      "supports": ["project_name"],
      "text": "short source excerpt"
    }
  ]
}
```

Rules:

1. `pdf_page` is the one-based physical PDF page supplied by the caller. Keep the
   document's printed page label separately because it can differ.
2. Preserve the exact project name, capitalization, voltage spacing, punctuation,
   and source identifiers. Normalization happens after review.
3. Extract an in-service date only when the source explicitly labels it as an
   in-service or planned in-service date. A `Need Date` is not an in-service date.
4. Extract construction start or end only from an explicit construction/start/end
   label for that project. Status text such as `Planned` or `In Progress`, a budget
   year, and a Need Date do not establish a construction window.
5. Keep `need_date` separate. Preserve every schedule label in `schedule_text` so
   a reviewer can audit the mapping.
6. Extract terminals only when the title or description identifies them. If the
   title's endpoints and the described work segment differ, use the title endpoints
   for `terminal_a` and `terminal_b` and describe the narrower segment in
   `uncertainties`.
7. Do not create coordinates, dates, costs, terminals, or company names. Use null
   when the page does not support a value.
8. Each populated factual field must appear in at least one `evidence.supports`
   list. Keep excerpts short and never include redacted or hidden content.
9. If a page carries confidentiality, CEII, or redistribution language, add that
   fact to `uncertainties`; do not decide that the content is safe to publish.

## Mapping to the shared project contract

- Map reviewed company values to the controlled `utility_id`; do not let the model
  invent a controlled ID.
- Combine reviewed terminal evidence into `location_text`. The shared v1 contract
  does not add terminal fields.
- Copy `construction_start`, `construction_end`, and `in_service_date` only after
  checking their labels on the cited page.
- Preserve `need_date` in `schedule_text` or `notes`; never map it to
  `in_service_date`.
- Set coordinates to null and `location_quality` to `unknown` until separate public
  location evidence is validated.
- A reviewer assigns `review_status`. Gemini never marks its own output validated.

For `DESC_2`, inspect Dominion PDF page 31. For `GPC_1`, inspect Georgia Power PDF
pages 189 and 410. Pass the physical PDF page number with each page image or text
chunk rather than asking Gemini to infer it.
