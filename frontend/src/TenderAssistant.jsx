import { useState, useRef } from "react";

const NOVACODE_PROFILE = `
NovaCode Consulting (Pty) Ltd is a Cape Town-based AI, automation, and software consultancy.
Registration: CIPC 2024/683414/07. Website: nova-code.co. Offices in Cape Town and Pretoria.

Core Products & Services:
- NovaBanks: Real-time bank statement analytics engine — income verification, fraud detection, behavioural profiling. Does NOT store client statements (privacy-first).
- NovaCollect: AI-powered debtors management and collections platform.
- NovaLoans: End-to-end loan origination platform with facial recognition onboarding, AI credit decisioning (Gradient Boosted Trees), React/FastAPI/PostgreSQL stack.
- Bespoke AI/ML development, automation pipelines, fintech platforms, digital transformation.

Key Capabilities:
- Python, FastAPI, React, PostgreSQL, SQLite
- Machine learning model development and deployment
- Web scraping, data pipelines, API integrations
- NCA-compliant financial software (South Africa)
- BBBEE: Level 4 contributor (confirm current certificate before submission)

Directors: Donovan (Don) - COO/Co-founder, Marnus de Jager - Co-founder
Target Markets: Financial services, credit providers, government, cross-industry
`;

export default function TenderAssistant() {
  const [stage, setStage] = useState("upload"); // upload | analyzing | draft | error
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState("");
  const fileRef = useRef();

  const handleFile = (f) => {
    if (f && f.type === "application/pdf") {
      setFile(f);
      setError("");
    } else {
      setError("Please upload a PDF file.");
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files[0]);
  };

  const analyzeTender = async () => {
    if (!file) return;
    setStage("analyzing");
    setProgress("Reading tender document...");

    try {
      // Convert PDF to base64
      const base64 = await new Promise((res, rej) => {
        const reader = new FileReader();
        reader.onload = () => res(reader.result.split(",")[1]);
        reader.onerror = () => rej(new Error("Failed to read file"));
        reader.readAsDataURL(file);
      });

      setProgress("Extracting requirements with Claude AI...");

      const response = await fetch("https://novacode-tenders-api-production.up.railway.app/api/proxy/claude", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 4000,
          system: `You are a tender response specialist for NovaCode Consulting. 
Here is NovaCode's company profile:
${NOVACODE_PROFILE}

Analyze tender documents and extract structured information. 
Respond ONLY with valid JSON, no markdown, no preamble.`,
          messages: [
            {
              role: "user",
              content: [
                {
                  type: "document",
                  source: { type: "base64", media_type: "application/pdf", data: base64 },
                },
                {
                  type: "text",
                  text: `Analyze this tender document and return JSON with this exact structure:
{
  "title": "tender title",
  "reference": "tender reference number or null",
  "department": "issuing department/entity",
  "deadline": "closing date or null",
  "value": "estimated value or null",
  "scope": "2-3 sentence summary of what is required",
  "requirements": ["requirement 1", "requirement 2", ...],
  "evaluation_criteria": ["criterion 1 with weighting if available", ...],
  "bbbee_requirement": "BBBEE level required or null",
  "novacode_fit": "HIGH or MEDIUM or LOW",
  "fit_reason": "1-2 sentences on why NovaCode is or isn't a good fit",
  "win_themes": ["key theme 1", "key theme 2", "key theme 3"],
  "risks": ["risk 1", "risk 2"]
}`,
                },
              ],
            },
          ],
        }),
      });

      const data = await response.json();
      setProgress("Generating response draft...");

      const raw = data.content?.find((b) => b.type === "text")?.text || "";
      const clean = raw.replace(/```json|```/g, "").trim();
      const parsed = JSON.parse(clean);

      // Now generate the full response draft
      const draftResp = await fetch("https://novacode-tenders-api-production.up.railway.app/api/proxy/claude", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 4000,
          system: `You are a tender response writer for NovaCode Consulting.
${NOVACODE_PROFILE}
Write professional, winning tender responses. Be specific, confident, and tailor every section to NovaCode's actual capabilities.
Respond ONLY with valid JSON, no markdown, no preamble.`,
          messages: [
            {
              role: "user",
              content: `Based on this tender analysis: ${JSON.stringify(parsed)}
              
Generate a tender response draft as JSON with this structure:
{
  "executive_summary": "2-3 paragraph executive summary positioning NovaCode",
  "company_overview": "1-2 paragraph company overview tailored to this tender",
  "technical_approach": "3-4 paragraphs detailing NovaCode's technical approach to this specific scope",
  "relevant_experience": "paragraph highlighting relevant NovaCode products and experience",
  "team": "paragraph on the team (Don and Marnus as directors, can note additional team as required)",
  "pricing_note": "guidance on pricing approach for this type of tender",
  "compliance_checklist": ["item 1", "item 2", "item 3"]
}`,
            },
          ],
        }),
      });

      const draftData = await draftResp.json();
      const draftRaw = draftData.content?.find((b) => b.type === "text")?.text || "";
      const draftClean = draftRaw.replace(/```json|```/g, "").trim();
      const draft = JSON.parse(draftClean);

      setAnalysis({ ...parsed, draft });
      setStage("draft");
    } catch (err) {
      console.error(err);
      setError("Analysis failed: " + err.message);
      setStage("error");
    }
  };

  const downloadDocx = () => {
    if (!analysis) return;
    const { draft, title, reference, deadline, department } = analysis;

    const content = `TENDER RESPONSE
${title || "Tender Response"}
${reference ? `Reference: ${reference}` : ""}
${department ? `Department: ${department}` : ""}
${deadline ? `Closing Date: ${deadline}` : ""}

Prepared by: NovaCode Consulting (Pty) Ltd
Registration: 2024/683414/07
Website: nova-code.co
Contact: Cape Town & Pretoria

================================================================================

1. EXECUTIVE SUMMARY

${draft.executive_summary}

================================================================================

2. COMPANY OVERVIEW

${draft.company_overview}

================================================================================

3. TECHNICAL APPROACH

${draft.technical_approach}

================================================================================

4. RELEVANT EXPERIENCE

${draft.relevant_experience}

================================================================================

5. TEAM

${draft.team}

================================================================================

6. PRICING

${draft.pricing_note}

================================================================================

7. COMPLIANCE CHECKLIST

${draft.compliance_checklist?.map((item, i) => `${i + 1}. ${item}`).join("\n")}

================================================================================

NovaCode Consulting (Pty) Ltd
nova-code.co | Cape Town & Pretoria, South Africa
`;

    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `NovaCode_TenderResponse_${(title || "draft").replace(/[^a-zA-Z0-9]/g, "_").slice(0, 40)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const fitColor = (fit) => {
    if (fit === "HIGH") return "#22c55e";
    if (fit === "MEDIUM") return "#f59e0b";
    return "#ef4444";
  };

  return (
    <div style={{ padding: "24px", maxWidth: "900px", margin: "0 auto" }}>
      {/* Upload Stage */}
      {stage === "upload" && (
        <div>
          <div style={{ marginBottom: "20px" }}>
            <h2 style={{ fontSize: "18px", fontWeight: 600, color: "#111", marginBottom: "4px" }}>
              Tender Document Assistant
            </h2>
            <p style={{ fontSize: "13px", color: "#666" }}>
              Upload a tender PDF — Claude will extract requirements and generate a response draft tailored to NovaCode.
            </p>
          </div>

          {/* Drop Zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current.click()}
            style={{
              border: `2px dashed ${dragOver ? "#E8500A" : file ? "#22c55e" : "#ddd"}`,
              borderRadius: "12px",
              padding: "48px 24px",
              textAlign: "center",
              cursor: "pointer",
              background: dragOver ? "#fff8f5" : file ? "#f0fdf4" : "#fafafa",
              transition: "all 0.2s",
              marginBottom: "16px",
            }}
          >
            <div style={{ fontSize: "36px", marginBottom: "12px" }}>
              {file ? "📄" : "⬆️"}
            </div>
            <div style={{ fontSize: "15px", fontWeight: 500, color: "#333", marginBottom: "4px" }}>
              {file ? file.name : "Drop tender PDF here"}
            </div>
            <div style={{ fontSize: "12px", color: "#888" }}>
              {file ? `${(file.size / 1024).toFixed(0)} KB` : "or click to browse"}
            </div>
            <input
              ref={fileRef}
              type="file"
              accept="application/pdf"
              style={{ display: "none" }}
              onChange={(e) => handleFile(e.target.files[0])}
            />
          </div>

          {error && (
            <div style={{ color: "#ef4444", fontSize: "13px", marginBottom: "12px" }}>{error}</div>
          )}

          <button
            onClick={analyzeTender}
            disabled={!file}
            style={{
              background: file ? "#E8500A" : "#ddd",
              color: file ? "#fff" : "#999",
              border: "none",
              borderRadius: "8px",
              padding: "12px 28px",
              fontSize: "14px",
              fontWeight: 600,
              cursor: file ? "pointer" : "not-allowed",
              width: "100%",
            }}
          >
            Analyse Tender with Claude AI
          </button>
        </div>
      )}

      {/* Analyzing Stage */}
      {stage === "analyzing" && (
        <div style={{ textAlign: "center", padding: "60px 24px" }}>
          <div style={{ fontSize: "40px", marginBottom: "16px" }}>🤖</div>
          <div style={{ fontSize: "16px", fontWeight: 600, color: "#111", marginBottom: "8px" }}>
            Analysing Tender Document
          </div>
          <div style={{ fontSize: "13px", color: "#666", marginBottom: "24px" }}>{progress}</div>
          <div style={{
            height: "4px", background: "#f0f0f0", borderRadius: "2px", overflow: "hidden",
          }}>
            <div style={{
              height: "100%", background: "#E8500A", borderRadius: "2px",
              animation: "progress-bar 2s ease-in-out infinite",
              width: "60%",
            }} />
          </div>
          <style>{`@keyframes progress-bar { 0%{transform:translateX(-100%)} 100%{transform:translateX(250%)} }`}</style>
        </div>
      )}

      {/* Error Stage */}
      {stage === "error" && (
        <div style={{ textAlign: "center", padding: "40px 24px" }}>
          <div style={{ fontSize: "36px", marginBottom: "12px" }}>⚠️</div>
          <div style={{ fontSize: "15px", color: "#ef4444", marginBottom: "16px" }}>{error}</div>
          <button onClick={() => { setStage("upload"); setFile(null); setError(""); }}
            style={{ background: "#E8500A", color: "#fff", border: "none", borderRadius: "8px", padding: "10px 24px", cursor: "pointer" }}>
            Try Again
          </button>
        </div>
      )}

      {/* Draft Stage */}
      {stage === "draft" && analysis && (
        <div>
          {/* Header */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
            <div>
              <h2 style={{ fontSize: "17px", fontWeight: 700, color: "#111", marginBottom: "4px" }}>
                {analysis.title || "Tender Analysis"}
              </h2>
              <div style={{ fontSize: "12px", color: "#888" }}>
                {[analysis.reference, analysis.department, analysis.deadline].filter(Boolean).join(" · ")}
              </div>
            </div>
            <div style={{ display: "flex", gap: "8px" }}>
              <span style={{
                background: fitColor(analysis.novacode_fit) + "20",
                color: fitColor(analysis.novacode_fit),
                border: `1px solid ${fitColor(analysis.novacode_fit)}40`,
                borderRadius: "20px", padding: "4px 12px", fontSize: "12px", fontWeight: 600,
              }}>
                {analysis.novacode_fit} FIT
              </span>
              <button onClick={downloadDocx} style={{
                background: "#111", color: "#fff", border: "none", borderRadius: "8px",
                padding: "6px 14px", fontSize: "12px", fontWeight: 600, cursor: "pointer",
              }}>
                ⬇ Download Draft
              </button>
              <button onClick={() => { setStage("upload"); setFile(null); setAnalysis(null); }} style={{
                background: "#f5f5f5", color: "#333", border: "none", borderRadius: "8px",
                padding: "6px 14px", fontSize: "12px", cursor: "pointer",
              }}>
                New Tender
              </button>
            </div>
          </div>

          {/* Fit Reason */}
          <div style={{ background: "#fff8f5", border: "1px solid #fed7aa", borderRadius: "8px", padding: "12px 16px", marginBottom: "16px", fontSize: "13px", color: "#92400e" }}>
            🤖 {analysis.fit_reason}
          </div>

          {/* Two column summary */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "16px" }}>
            <Card title="Scope">
              <p style={{ fontSize: "13px", color: "#444", lineHeight: 1.6 }}>{analysis.scope}</p>
            </Card>
            <Card title="Win Themes">
              <ul style={{ margin: 0, padding: "0 0 0 16px" }}>
                {analysis.win_themes?.map((t, i) => (
                  <li key={i} style={{ fontSize: "13px", color: "#444", marginBottom: "4px" }}>{t}</li>
                ))}
              </ul>
            </Card>
            <Card title="Requirements">
              <ul style={{ margin: 0, padding: "0 0 0 16px" }}>
                {analysis.requirements?.slice(0, 6).map((r, i) => (
                  <li key={i} style={{ fontSize: "12px", color: "#444", marginBottom: "3px" }}>{r}</li>
                ))}
              </ul>
            </Card>
            <Card title="Evaluation Criteria">
              <ul style={{ margin: 0, padding: "0 0 0 16px" }}>
                {analysis.evaluation_criteria?.map((c, i) => (
                  <li key={i} style={{ fontSize: "12px", color: "#444", marginBottom: "3px" }}>{c}</li>
                ))}
              </ul>
            </Card>
          </div>

          {/* Response Draft */}
          <Card title="📝 Response Draft" accent>
            <DraftSection label="Executive Summary" text={analysis.draft?.executive_summary} />
            <DraftSection label="Company Overview" text={analysis.draft?.company_overview} />
            <DraftSection label="Technical Approach" text={analysis.draft?.technical_approach} />
            <DraftSection label="Relevant Experience" text={analysis.draft?.relevant_experience} />
            <DraftSection label="Team" text={analysis.draft?.team} />
            <DraftSection label="Pricing Guidance" text={analysis.draft?.pricing_note} />
            {analysis.draft?.compliance_checklist?.length > 0 && (
              <div style={{ marginTop: "16px" }}>
                <div style={{ fontSize: "11px", fontWeight: 700, color: "#E8500A", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
                  Compliance Checklist
                </div>
                {analysis.draft.compliance_checklist.map((item, i) => (
                  <div key={i} style={{ display: "flex", gap: "8px", alignItems: "flex-start", marginBottom: "6px" }}>
                    <span style={{ color: "#E8500A", fontWeight: 700, marginTop: "1px" }}>☐</span>
                    <span style={{ fontSize: "13px", color: "#444" }}>{item}</span>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Risks */}
          {analysis.risks?.length > 0 && (
            <div style={{ marginTop: "12px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "8px", padding: "12px 16px" }}>
              <div style={{ fontSize: "11px", fontWeight: 700, color: "#dc2626", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>
                ⚠ Risks to Address
              </div>
              {analysis.risks.map((r, i) => (
                <div key={i} style={{ fontSize: "13px", color: "#7f1d1d", marginBottom: "4px" }}>• {r}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Card({ title, children, accent }) {
  return (
    <div style={{
      background: "#fff", border: `1px solid ${accent ? "#E8500A40" : "#e5e7eb"}`,
      borderRadius: "8px", padding: "14px 16px",
      ...(accent ? { gridColumn: "1 / -1" } : {}),
    }}>
      <div style={{ fontSize: "11px", fontWeight: 700, color: accent ? "#E8500A" : "#888", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "10px" }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function DraftSection({ label, text }) {
  if (!text) return null;
  return (
    <div style={{ marginBottom: "16px" }}>
      <div style={{ fontSize: "11px", fontWeight: 700, color: "#E8500A", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>
        {label}
      </div>
      <p style={{ fontSize: "13px", color: "#333", lineHeight: 1.7, margin: 0, whiteSpace: "pre-line" }}>{text}</p>
    </div>
  );
}



