with open('frontend/src/TenderAssistant.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the analyzeTender function and replace the two-call approach with one call
old_prompt = '''{ type: "text", text: `Analyze this tender and return JSON: {"title":"","reference":"","department":"","deadline":"","scope":"","requirements":[],"evaluation_criteria":[],"bbbee_requirement":"","novacode_fit":"HIGH or MEDIUM or LOW","fit_reason":"","win_themes":[],"risks":[]}` }'''

new_prompt = '''{ type: "text", text: `Analyze this tender document and return a single JSON object with ALL of the following fields:
{
  "title": "tender title",
  "reference": "reference number or null",
  "department": "issuing department",
  "deadline": "closing date or null",
  "scope": "2-3 sentence summary of what is required",
  "requirements": ["requirement 1", "requirement 2"],
  "evaluation_criteria": ["criterion with weighting if available"],
  "bbbee_requirement": "BBBEE level required or null",
  "novacode_fit": "HIGH or MEDIUM or LOW",
  "fit_reason": "1-2 sentences on fit for NovaCode Consulting - AI automation fintech Cape Town",
  "win_themes": ["theme 1", "theme 2", "theme 3"],
  "risks": ["risk 1", "risk 2"],
  "draft": {
    "executive_summary": "2-3 paragraph executive summary positioning NovaCode",
    "company_overview": "1-2 paragraph company overview tailored to this tender",
    "technical_approach": "3-4 paragraphs on NovaCode approach to this scope",
    "relevant_experience": "paragraph on relevant NovaCode products and experience",
    "team": "paragraph on Don and Marnus as directors plus additional team as required",
    "pricing_note": "guidance on pricing approach for this tender type",
    "compliance_checklist": ["item 1", "item 2", "item 3"]
  }
}
Return ONLY valid JSON, no markdown, no preamble.` }'''

content = content.replace(old_prompt, new_prompt)

# Now remove the second API call entirely - find and remove the draftResp block
# Find the setProgress for draft
draft_start = content.find('setProgress("Generating response draft...");')
draft_end = content.find('setAnalysis({ ...parsed, draft });')

if draft_start > 0 and draft_end > 0:
    # Get everything between parsed and setAnalysis
    section = content[draft_start:draft_end]
    # Replace with simple extraction from parsed
    new_section = '''setProgress("Generating response draft...");
      const draft = parsed.draft || {};
      '''
    content = content[:draft_start] + new_section + content[draft_end:]

# Fix setAnalysis to use parsed.draft directly
content = content.replace(
    'setAnalysis({ ...parsed, draft });',
    'setAnalysis({ ...parsed, draft: parsed.draft || {} });'
)

with open('frontend/src/TenderAssistant.jsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
# Verify
with open('frontend/src/TenderAssistant.jsx', 'r') as f:
    c = f.read()
    print("Single call:", "draftResp" not in c)
    print("Draft extraction:", "parsed.draft" in c)
