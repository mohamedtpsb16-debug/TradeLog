import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

const SYSTEM = `Tu es TradeLog AI, l'assistant d'analyse du journal de trading TradeLog.
Réponds en français, clairement, avec des conclusions structurées. Tu aides à analyser et apprendre, tu ne donnes jamais d'ordre financier ni de promesse de résultat.

RÉFÉRENTIEL SMC 2025 (synthèse des règles communiquées depuis le document de référence) :
- Lire la structure : tendance haussière par HH/BH, tendance baissière par BB/HB. HH et BB sont associés au BoS dans le support.
- IDM : identifier la liquidité/structure interne avant de valider une cassure ou une zone.
- Un Order Block n'est valide dans le référentiel que s'il comporte une imbalance non mitigée et un sweep de liquidité. Sans sweep ou sans IMB, ne pas le valider comme OB.
- Zone décisionnelle : zone après IDM ; zone extrême située aux extrêmes, avec ENG-LQ comme élément de traçage indiqué dans le support.
- Configurations contre-tendance : rechercher le sweep de l'IDM / de zone, puis la confirmation par sweep de l'IDM et cassure HH/BB.
- Après arrivée du prix dans une zone ou un sweep sur UT supérieure (D1/H4/H1/M15), rechercher des confirmations sur UT inférieures (H1/M15/M5/M3/M1).
- Plan présenté dans le support : exclusivement Gold ; 3 configurations ; maximum 2 trades/jour et 8/semaine ; risque usuel 0,25 % ou 0,50 % par trade ; RR minimum 5R ; UT H4 et M15 ou M15 seulement ; clôture des trades le vendredi soir.
- Gestion : protéger le trade ; déplacement du SL à BE lorsque le marché casse le HH ou BB récent ; pas de trailing stop. Une clôture partielle peut être envisagée après passage de 5R selon le support.
IMPORTANT : l'utilisateur a précisé que son propre résultat « CP » ne signifie PAS une clôture partielle. CP = le marché avance dans son sens, l'utilisateur déplace son SL pour sécuriser au moins +1R (parfois davantage), puis le prix revient toucher ce SL avant le TP. Le TP visé est au minimum 4R et peut atteindre 10R ou plus. Distingue CP de BE et de TP. Ne suppose jamais que CP vaut exactement +1R : le R réalisé doit être calculé à partir du PNL net réel et du risque de référence.
- Les règles de gestion personnelle de l'utilisateur peuvent différer du plan général du document. Signale les écarts sans les confondre.

DONNÉES INCOMPLÈTES :
- L’historique MT5 peut contenir uniquement les données d’exécution. Il ne prouve pas que le trade a été documenté manuellement.
- Si setup, capture, émotions, biais psychologiques, notes, respect du plan ou autres champs sont absents/null, indique explicitement « non renseigné / indisponible ».
- N’infère jamais les biais psychologiques, le contexte graphique, le sweep, l’IDM ou la qualité du setup à partir du seul résultat MT5.
- Une capture n’est disponible que si elle est effectivement jointe à la demande en cours. Ne prétends pas avoir consulté une capture enregistrée ailleurs.
- Limite l’analyse aux données présentes et précise ce qu’il faudrait renseigner pour la compléter.

RÈGLES D'ANALYSE :
1. Sépare toujours les faits visibles / données fournies, les déductions et les éléments impossibles à vérifier.
2. N'invente jamais une zone, un sweep, une imbalance, un IDM, un HH/BB ou une valeur R qui n'est pas visible ou fournie.
3. Si une capture est floue, incomplète ou sans UT/prix, demande la précision nécessaire et limite la conclusion.
4. Pour analyser un trade, examine contexte/structure, liquidité, zone, confirmation, entrée, SL, TP/RR, gestion et résultat.
5. Pour un historique, calcule les statistiques uniquement à partir des données transmises. Signale les échantillons trop petits.
6. Distingue « conforme au référentiel SMC 2025 » de « conforme au plan personnel de l'utilisateur ».
7. Termine par un verdict nuancé : conforme, partiellement conforme, non conforme ou impossible à déterminer, avec raisons précises.`;

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return new Response(JSON.stringify({ error: "Méthode non autorisée." }), { status: 405, headers: { ...corsHeaders, "Content-Type": "application/json" } });

  try {
    const auth = req.headers.get("Authorization") || "";
    if (!auth.startsWith("Bearer ")) return new Response(JSON.stringify({ error: "Connexion requise." }), { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } });

    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const anonKey = Deno.env.get("SUPABASE_ANON_KEY")!;
    const supabase = createClient(supabaseUrl, anonKey, { global: { headers: { Authorization: auth } } });
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) return new Response(JSON.stringify({ error: "Session invalide. Reconnecte-toi." }), { status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" } });

    const groqApiKey = Deno.env.get("GROQ_API_KEY");
    const geminiApiKey = Deno.env.get("GEMINI_API_KEY");
    if (!groqApiKey && !geminiApiKey) return new Response(JSON.stringify({ error: "Aucune clé IA configurée dans Supabase." }), { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } });

    const body = await req.json();
    const message = String(body.message || "").trim();
    if (!message) return new Response(JSON.stringify({ error: "Écris une question ou une demande d'analyse." }), { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } });
    const context = body.context && typeof body.context === "object" ? JSON.stringify(body.context).slice(0, 30000) : "";
    const parts: Array<Record<string, unknown>> = [{ text: "CONTEXTE TRADELOG (données fournies par l'utilisateur) :\n" + context + "\n\nDEMANDE :\n" + message }];
    if (body.image?.data && body.image?.mimeType) {
      const allowed = ["image/png", "image/jpeg", "image/webp"];
      if (!allowed.includes(body.image.mimeType) || String(body.image.data).length > 12000000) {
        return new Response(JSON.stringify({ error: "Image non prise en charge ou trop volumineuse (PNG/JPEG/WebP, 8 Mo max)." }), { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } });
      }
      parts.push({ inline_data: { mime_type: body.image.mimeType, data: body.image.data } });
    }

    let answer = "";
    let lastError = "Service IA temporairement indisponible.";
    if (groqApiKey) {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 25000);
      try {
        const userContent: Array<Record<string, unknown>> = [{ type: "text", text: "CONTEXTE TRADELOG :\n" + context + "\n\nDEMANDE :\n" + message }];
        if (body.image?.data && body.image?.mimeType) userContent.push({ type: "image_url", image_url: { url: `data:${body.image.mimeType};base64,${body.image.data}` } });
        const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
          signal: controller.signal, method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${groqApiKey}` },
          body: JSON.stringify({ model: "qwen/qwen3.8-27b", messages: [{ role: "system", content: SYSTEM }, { role: "user", content: userContent }], temperature: 0.25, max_tokens: 1600 }),
        });
        const payload = await response.json().catch(() => ({}));
        if (response.ok) answer = payload?.choices?.[0]?.message?.content?.trim() || "";
        else { lastError = payload?.error?.message || `Groq HTTP ${response.status}`; console.error("tradelog-ai Groq", response.status, lastError.slice(0, 500)); }
      } catch (e) {
        lastError = e instanceof Error && e.name === "AbortError" ? "Délai dépassé sur Groq." : (e instanceof Error ? e.message : "Erreur réseau Groq.");
        console.error("tradelog-ai Groq transport", lastError);
      } finally { clearTimeout(timeoutId); }
    }
    if (!answer && geminiApiKey) {
      for (const model of ["gemini-3.5-flash-lite", "gemini-3.7-flash", "gemini-3.8-flash"]) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 7000);
        try {
          const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
            signal: controller.signal, method: "POST",
            headers: { "Content-Type": "application/json", "x-goog-api-key": geminiApiKey },
            body: JSON.stringify({ system_instruction: { parts: [{ text: SYSTEM }] }, contents: [{ role: "user", parts }], generationConfig: { temperature: 0.25, maxOutputTokens: 1600 } }),
          });
          const payload = await response.json().catch(() => ({}));
          if (response.ok) {
            answer = payload?.candidates?.[0]?.content?.parts?.map((p: { text?: string }) => p.text || "").join("\n").trim() || "";
            if (answer) break;
          } else {
            lastError = payload?.error?.message || `Gemini HTTP ${response.status}`;
            console.error("tradelog-ai Gemini", model, response.status, lastError.slice(0, 500));
            if ([400, 401, 403].includes(response.status)) break;
          }
        } catch (e) {
          lastError = e instanceof Error && e.name === "AbortError" ? `Délai dépassé sur ${model}.` : (e instanceof Error ? e.message : "Erreur réseau Gemini.");
          console.error("tradelog-ai Gemini transport", model, lastError);
        } finally { clearTimeout(timeoutId); }
      }
    }
    if (!answer) throw new Error("Aucun fournisseur IA n'a répondu. " + lastError);
    return new Response(JSON.stringify({ answer }), { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } });
  } catch (error) {
    return new Response(JSON.stringify({ error: error instanceof Error ? error.message : "Erreur inattendue." }), { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } });
  }
});