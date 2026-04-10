import { useState, useEffect } from "react";

const PERSONAS = {
  cio_cto: {
    label: "CIO / CTO",
    icon: "⚙️",
    m1Hook: "transformación digital centrada en las personas",
    m2Question: "¿cómo ha sido llevar analítica real a la operación clínica? ¿Dónde encuentra más fricción cuando intenta mover algo nuevo?",
    m2Angle: "Sabe dónde está el dato, pero también dónde se pierde antes de volverse inteligencia útil.",
    greeting: "Silverio"
  },
  gerente_tech: {
    label: "Gerente Tecnología",
    icon: "💻",
    m1Hook: "combina la visión estratégica con la base técnica en el sector salud",
    m2Question: "¿cómo ha sido ese proceso de innovación tecnológica? ¿Dónde encuentra más fricción cuando intenta mover algo nuevo institucionalmente?",
    m2Angle: "Tiene que hacer que los sistemas funcionen, que los equipos clínicos los adopten, y que todo tenga sentido estratégico.",
    greeting: "Maria Helena"
  },
  director_ops: {
    label: "Director Operaciones / Salud",
    icon: "🏥",
    m1Hook: "misión de mejorar la atención en salud desde la operación",
    m2Question: "¿cómo ha sido convertir datos clínicos en decisiones útiles a tiempo? ¿Qué sistemas les han dado más fricción?",
    m2Angle: "Toma decisiones con información que siempre llega tarde, incompleta o dispersa en múltiples sistemas.",
    greeting: "Javier"
  },
  medico_clinico: {
    label: "Médico / Clínico Senior",
    icon: "🩺",
    m1Hook: "dedicación a la práctica clínica y la investigación",
    m2Question: "¿cómo ha vivido la evolución de la tecnología en su práctica? ¿Qué cree que la tecnología aún no ha sabido darle bien al médico?",
    m2Angle: "Tiene décadas viendo cómo llega y fracasa la tecnología en el mundo clínico.",
    greeting: "Doctor"
  },
  director_comercial: {
    label: "Director Comercial",
    icon: "📈",
    m1Hook: "visión de negocio en el sector salud",
    m2Question: "¿cómo han abordado la relación entre tecnología y crecimiento comercial? ¿Qué barreras han encontrado?",
    m2Angle: "Ve la brecha entre lo que el paciente necesita y lo que los sistemas permiten ofrecer.",
    greeting: ""
  }
};

const INSTITUCIONES = {
  eps: { label: "EPS", pain: "tiempos de espera y Resolución 2117/2025", urgency: true },
  clinica: { label: "Clínica / Hospital", pain: "fragmentación de datos clínicos y adopción tecnológica", urgency: false },
  laboratorio: { label: "Laboratorio", pain: "volumen de datos y velocidad de procesamiento", urgency: false },
  ips: { label: "IPS", pain: "autorización y coordinación con aseguradoras", urgency: false }
};

export default function AimedicOutreachSystem() {
  const [step, setStep] = useState("form");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState({ m1: "", m2: "", m3: "" });
  const [copied, setCopied] = useState(null);
  const [activeMsg, setActiveMsg] = useState("m1");
  const [form, setForm] = useState({
    name: "",
    lastName: "",
    persona: "cio_cto",
    institution: "",
    institutionType: "eps",
    linkedin: "",
    bannerQuote: "",
    notes: ""
  });

  const persona = PERSONAS[form.persona];
  const instType = INSTITUCIONES[form.institutionType];

  async function generateMessages() {
    setLoading(true);
    setStep("loading");

    const prompt = `Eres el asistente de outreach de Aimedic, una startup colombiana de IA médica respaldada por Google for Startups y NVIDIA, que trabaja con Fundación Cardio Infantil y Fundación Neumológica.

CONTEXTO DEL PROSPECTO:
- Nombre: ${form.name} ${form.lastName}
- Cargo: ${persona.label}
- Institución: ${form.institution || "[Institución]"} (${instType.label})
- Pain point principal: ${instType.pain}
- ${instType.urgency ? "URGENCIA: Resolución 2117/2025 sobre tiempos de espera está activa." : ""}
- Frase del banner LinkedIn: "${form.bannerQuote || "No disponible"}"
- Notas adicionales: ${form.notes || "Ninguna"}

REGLAS DE TONO (CRÍTICAS):
- M1: 0 venta, 0 tecnología. Solo conexión humana y misión compartida. MAX 300 caracteres.
- M2: Solo descubrimiento. Preguntar sobre su experiencia/desafíos. Sin mencionar productos. Terminar con pregunta abierta que no pueda rechazar.
- M3: Solo después de que responda M2. Conectar lo que dijo con lo que resuelve Aimedic. Incluir calendario: https://calendar.app.google/iwNTpueCort26EuNA
- NUNCA usar "don/doña" para perfiles ejecutivos de tech. Para médicos senior usar "doctor/a".
- Nunca frases genéricas como "me pareció interesante tu perfil" o "admiro tu trayectoria".
- Tono: directo, sin lambonería, con curiosidad genuina. Despedida humana.

PRODUCTOS AIMEDIC (solo M3):
- Analítica Avanzada: modelos de anticipación de riesgos, optimización tiempos de espera, dashboards ejecutivos
- On-Premise: IA corre en sus servidores, cero datos salen de su infraestructura  
- Validado clínicamente: Cardio Infantil + Neumológica + Google for Startups + NVIDIA

Genera exactamente 3 mensajes de LinkedIn en JSON con este formato:
{
  "m1": "texto del mensaje M1",
  "m2": "texto del mensaje M2", 
  "m3": "texto del mensaje M3"
}

Solo el JSON, sin explicaciones ni markdown.`;

    try {
      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1000,
          messages: [{ role: "user", content: prompt }]
        })
      });
      const data = await res.json();
      const text = data.content[0].text.trim();
      const clean = text.replace(/```json|```/g, "").trim();
      const parsed = JSON.parse(clean);
      setMessages(parsed);
      setStep("result");
    } catch (e) {
      console.error(e);
      setStep("form");
    }
    setLoading(false);
  }

  function copyMsg(key, text) {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  }

  const msgConfig = {
    m1: { label: "M1 — Conexión", color: "#189685", desc: "Nota de conexión (0 venta)", maxChars: 300 },
    m2: { label: "M2 — Descubrimiento", color: "#006F80", desc: "Después de aceptar", maxChars: 600 },
    m3: { label: "M3 — Propuesta", color: "#082320", desc: "Después de que responda M2", maxChars: 800 }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(135deg, #061a18 0%, #082320 40%, #0d3d3d 100%)",
      fontFamily: "'DM Mono', 'Fira Code', 'Courier New', monospace",
      padding: "0",
      color: "#e0f0f0"
    }}>
      {/* Header */}
      <div style={{
        borderBottom: "1px solid rgba(24,150,133,0.3)",
        padding: "18px 32px",
        display: "flex",
        alignItems: "center",
        gap: "14px",
        background: "rgba(8,35,32,0.8)",
        backdropFilter: "blur(10px)"
      }}>
        <div style={{
          width: 36, height: 36,
          background: "linear-gradient(135deg, #189685, #006F80)",
          borderRadius: 8,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 18
        }}>⚕</div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15, letterSpacing: "0.08em", color: "#ceeaea" }}>
            AIMEDIC
          </div>
          <div style={{ fontSize: 10, color: "#189685", letterSpacing: "0.2em", textTransform: "uppercase" }}>
            LinkedIn Outreach System
          </div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          {["M1","M2","M3"].map(m => (
            <div key={m} style={{
              padding: "3px 10px", borderRadius: 4,
              fontSize: 10, letterSpacing: "0.1em",
              background: step === "result" ? "rgba(24,150,133,0.2)" : "rgba(255,255,255,0.05)",
              border: "1px solid rgba(24,150,133,0.3)",
              color: "#189685"
            }}>{m}</div>
          ))}
        </div>
      </div>

      <div style={{ maxWidth: 820, margin: "0 auto", padding: "32px 24px" }}>

        {step === "form" && (
          <div>
            <div style={{ marginBottom: 32 }}>
              <h2 style={{ margin: 0, fontSize: 22, color: "#ceeaea", fontWeight: 400, letterSpacing: "-0.02em" }}>
                Nuevo prospecto
              </h2>
              <p style={{ margin: "6px 0 0", fontSize: 12, color: "#4a8a8a", letterSpacing: "0.05em" }}>
                Ingresa los datos del contacto para generar los mensajes M1 → M2 → M3
              </p>
            </div>

            {/* Form grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
              {[
                { key: "name", label: "Nombre *", placeholder: "Silverio" },
                { key: "lastName", label: "Apellido", placeholder: "Carmona Lozano" },
                { key: "institution", label: "Institución *", placeholder: "Famisanar EPS" },
                { key: "bannerQuote", label: "Frase banner LinkedIn", placeholder: "Transformo la tecnología en un motor estratégico..." },
              ].map(f => (
                <div key={f.key}>
                  <label style={{ display: "block", fontSize: 10, color: "#189685", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 6 }}>
                    {f.label}
                  </label>
                  <input
                    value={form[f.key]}
                    onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                    placeholder={f.placeholder}
                    style={{
                      width: "100%", padding: "10px 14px",
                      background: "rgba(255,255,255,0.04)",
                      border: "1px solid rgba(24,150,133,0.25)",
                      borderRadius: 6, color: "#ceeaea",
                      fontSize: 13, outline: "none",
                      fontFamily: "inherit",
                      boxSizing: "border-box"
                    }}
                  />
                </div>
              ))}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
              <div>
                <label style={{ display: "block", fontSize: 10, color: "#189685", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 6 }}>
                  Tipo de cargo *
                </label>
                <select
                  value={form.persona}
                  onChange={e => setForm(p => ({ ...p, persona: e.target.value }))}
                  style={{
                    width: "100%", padding: "10px 14px",
                    background: "#0d2a28",
                    border: "1px solid rgba(24,150,133,0.25)",
                    borderRadius: 6, color: "#ceeaea",
                    fontSize: 13, outline: "none", fontFamily: "inherit",
                    boxSizing: "border-box"
                  }}
                >
                  {Object.entries(PERSONAS).map(([k, v]) => (
                    <option key={k} value={k}>{v.icon} {v.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{ display: "block", fontSize: 10, color: "#189685", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 6 }}>
                  Tipo institución *
                </label>
                <select
                  value={form.institutionType}
                  onChange={e => setForm(p => ({ ...p, institutionType: e.target.value }))}
                  style={{
                    width: "100%", padding: "10px 14px",
                    background: "#0d2a28",
                    border: "1px solid rgba(24,150,133,0.25)",
                    borderRadius: 6, color: "#ceeaea",
                    fontSize: 13, outline: "none", fontFamily: "inherit",
                    boxSizing: "border-box"
                  }}
                >
                  {Object.entries(INSTITUCIONES).map(([k, v]) => (
                    <option key={k} value={k}>{v.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div style={{ marginBottom: 24 }}>
              <label style={{ display: "block", fontSize: 10, color: "#189685", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 6 }}>
                Notas adicionales (opcional)
              </label>
              <textarea
                value={form.notes}
                onChange={e => setForm(p => ({ ...p, notes: e.target.value }))}
                placeholder="Ej: Tiene conexión con Claudia Patricia de Compensar. Acaba de publicar sobre IA en salud..."
                rows={3}
                style={{
                  width: "100%", padding: "10px 14px",
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(24,150,133,0.25)",
                  borderRadius: 6, color: "#ceeaea",
                  fontSize: 12, outline: "none", fontFamily: "inherit",
                  resize: "vertical", boxSizing: "border-box"
                }}
              />
            </div>

            {/* Pain point preview */}
            {instType && (
              <div style={{
                padding: "12px 16px", borderRadius: 8,
                background: "rgba(24,150,133,0.08)",
                border: "1px solid rgba(24,150,133,0.2)",
                marginBottom: 24
              }}>
                <div style={{ fontSize: 10, color: "#189685", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 4 }}>
                  Pain point detectado {instType.urgency ? "⚡ URGENCIA REGULATORIA" : ""}
                </div>
                <div style={{ fontSize: 12, color: "#9acaca" }}>{instType.pain}</div>
              </div>
            )}

            <button
              onClick={generateMessages}
              disabled={!form.name || !form.institution}
              style={{
                width: "100%", padding: "14px",
                background: form.name && form.institution
                  ? "linear-gradient(135deg, #189685, #006F80)"
                  : "rgba(255,255,255,0.05)",
                border: "none", borderRadius: 8,
                color: form.name && form.institution ? "white" : "#4a6a6a",
                fontSize: 13, fontWeight: 700,
                letterSpacing: "0.1em", textTransform: "uppercase",
                cursor: form.name && form.institution ? "pointer" : "not-allowed",
                fontFamily: "inherit"
              }}
            >
              ⚡ Generar mensajes M1 → M2 → M3
            </button>
          </div>
        )}

        {step === "loading" && (
          <div style={{ textAlign: "center", padding: "80px 0" }}>
            <div style={{
              width: 60, height: 60, margin: "0 auto 24px",
              border: "3px solid rgba(24,150,133,0.2)",
              borderTop: "3px solid #189685",
              borderRadius: "50%",
              animation: "spin 1s linear infinite"
            }} />
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            <div style={{ color: "#189685", fontSize: 13, letterSpacing: "0.1em" }}>
              Generando mensajes para {form.name}...
            </div>
            <div style={{ color: "#4a7a7a", fontSize: 11, marginTop: 8 }}>
              Aplicando reglas M1/M2/M3 · Tono Aimedic
            </div>
          </div>
        )}

        {step === "result" && (
          <div>
            {/* Header resultado */}
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              marginBottom: 28
            }}>
              <div>
                <h2 style={{ margin: 0, fontSize: 20, color: "#ceeaea", fontWeight: 400 }}>
                  {persona.icon} {form.name} {form.lastName}
                </h2>
                <div style={{ fontSize: 11, color: "#4a8a8a", marginTop: 4 }}>
                  {persona.label} · {form.institution} · {instType.label}
                </div>
              </div>
              <button
                onClick={() => { setStep("form"); setMessages({ m1: "", m2: "", m3: "" }); }}
                style={{
                  padding: "8px 16px", background: "transparent",
                  border: "1px solid rgba(24,150,133,0.3)",
                  borderRadius: 6, color: "#189685",
                  fontSize: 11, cursor: "pointer", fontFamily: "inherit",
                  letterSpacing: "0.08em"
                }}
              >
                ← Nuevo contacto
              </button>
            </div>

            {/* Tabs */}
            <div style={{ display: "flex", gap: 2, marginBottom: 0 }}>
              {Object.entries(msgConfig).map(([key, cfg]) => (
                <button
                  key={key}
                  onClick={() => setActiveMsg(key)}
                  style={{
                    flex: 1, padding: "12px 8px",
                    background: activeMsg === key ? cfg.color : "rgba(255,255,255,0.03)",
                    border: "1px solid",
                    borderColor: activeMsg === key ? cfg.color : "rgba(24,150,133,0.2)",
                    borderBottom: activeMsg === key ? `1px solid ${cfg.color}` : "1px solid rgba(24,150,133,0.2)",
                    borderRadius: "8px 8px 0 0",
                    color: activeMsg === key ? "white" : "#4a8a8a",
                    fontSize: 11, fontWeight: 700,
                    letterSpacing: "0.08em",
                    cursor: "pointer", fontFamily: "inherit",
                    transition: "all 0.15s"
                  }}
                >
                  {cfg.label}
                </button>
              ))}
            </div>

            {/* Message panel */}
            {Object.entries(msgConfig).map(([key, cfg]) => (
              activeMsg === key && (
                <div key={key} style={{
                  background: "rgba(255,255,255,0.03)",
                  border: `1px solid ${cfg.color}`,
                  borderTop: "none",
                  borderRadius: "0 0 12px 12px",
                  padding: "24px"
                }}>
                  <div style={{
                    display: "flex", justifyContent: "space-between",
                    alignItems: "center", marginBottom: 16
                  }}>
                    <div style={{ fontSize: 10, color: cfg.color, letterSpacing: "0.15em", textTransform: "uppercase" }}>
                      {cfg.desc}
                    </div>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <span style={{ fontSize: 10, color: "#4a7a7a" }}>
                        {messages[key]?.length || 0} chars
                        {key === "m1" && messages[key]?.length > 300 && (
                          <span style={{ color: "#ff6b6b", marginLeft: 4 }}>⚠ MAX 300</span>
                        )}
                      </span>
                      <button
                        onClick={() => copyMsg(key, messages[key])}
                        style={{
                          padding: "6px 14px",
                          background: copied === key ? "rgba(24,150,133,0.3)" : "rgba(24,150,133,0.1)",
                          border: `1px solid ${cfg.color}`,
                          borderRadius: 5, color: cfg.color,
                          fontSize: 10, cursor: "pointer",
                          fontFamily: "inherit", letterSpacing: "0.08em",
                          fontWeight: 700
                        }}
                      >
                        {copied === key ? "✓ COPIADO" : "COPIAR"}
                      </button>
                    </div>
                  </div>

                  <div style={{
                    background: "rgba(0,0,0,0.2)",
                    borderRadius: 8, padding: "18px 20px",
                    fontSize: 13, lineHeight: 1.7,
                    color: "#ceeaea", whiteSpace: "pre-wrap",
                    border: "1px solid rgba(255,255,255,0.04)"
                  }}>
                    {messages[key]}
                  </div>

                  {/* Next step hint */}
                  <div style={{
                    marginTop: 16, padding: "10px 14px",
                    background: "rgba(24,150,133,0.06)",
                    borderRadius: 6, borderLeft: `3px solid ${cfg.color}`
                  }}>
                    <div style={{ fontSize: 10, color: "#4a8a8a", letterSpacing: "0.08em" }}>
                      {key === "m1" && "📤 Enviar como nota al conectar · Esperar respuesta · Loguear en HubSpot → Lead Status: ATTEMPTED_TO_CONTACT"}
                      {key === "m2" && "📤 Enviar cuando acepte la conexión · Esperar respuesta · Loguear en HubSpot → Lead Status: CONNECTED"}
                      {key === "m3" && "📤 Enviar solo si respondió M2 · Si agenda → HubSpot → Lead Status: OPEN_DEAL"}
                    </div>
                  </div>
                </div>
              )
            ))}

            {/* HubSpot pipeline guide */}
            <div style={{
              marginTop: 24, padding: "20px",
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(24,150,133,0.15)",
              borderRadius: 10
            }}>
              <div style={{ fontSize: 10, color: "#189685", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 14 }}>
                🔄 HubSpot lifecycle para este contacto
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
                {[
                  { stage: "Lead", trigger: "Importado", color: "#4a7a7a" },
                  { stage: "MQL", trigger: "M1 enviado", color: "#006F80" },
                  { stage: "Connected", trigger: "Acepta M1", color: "#189685" },
                  { stage: "SQL", trigger: "Responde M2", color: "#0d9e8a" },
                  { stage: "Opportunity", trigger: "Agenda reunión", color: "#ceeaea" }
                ].map((s, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", flex: 1 }}>
                    <div style={{ textAlign: "center", flex: 1 }}>
                      <div style={{
                        fontSize: 9, fontWeight: 700, color: s.color,
                        textTransform: "uppercase", letterSpacing: "0.1em"
                      }}>{s.stage}</div>
                      <div style={{ fontSize: 8, color: "#4a6a6a", marginTop: 2 }}>{s.trigger}</div>
                    </div>
                    {i < 4 && <div style={{ color: "rgba(24,150,133,0.3)", fontSize: 16, padding: "0 4px" }}>→</div>}
                  </div>
                ))}
              </div>
            </div>

            {/* Examples used */}
            <div style={{
              marginTop: 16, padding: "14px 18px",
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(24,150,133,0.1)",
              borderRadius: 8, fontSize: 11, color: "#4a7a7a"
            }}>
              <span style={{ color: "#189685", fontWeight: 700 }}>Basado en:</span> casos reales Famisanar · Compensar · SaludMía · EPS Aida · Colcan
              <span style={{ marginLeft: 12, color: "#006F80" }}>Tono: sin lambonería · curiosidad genuina · despedida humana</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}