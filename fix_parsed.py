with open('frontend/src/TenderAssistant.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

old = """      const data = await response.json();
      setProgress("Generating response draft...");
      const draft = parsed.draft || {};
      setAnalysis({ ...parsed, draft: parsed.draft || {} });"""

new = """      const data = await response.json();
      const raw = data.content?.find((b) => b.type === "text")?.text || "";
      const clean = raw.replace(/```json|```/g, "").trim();
      const parsed = JSON.parse(clean);
      setProgress("Generating response draft...");
      const draft = parsed.draft || {};
      setAnalysis({ ...parsed, draft });"""

if old in content:
    content = content.replace(old, new)
    with open('frontend/src/TenderAssistant.jsx', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed!")
else:
    print("Pattern not found - printing context:")
    idx = content.find("const data = await response.json()")
    print(repr(content[idx:idx+300]))
