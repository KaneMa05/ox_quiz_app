/** Vercel Serverless: `package.json`의 `"type": "module"`에 맞춰 ESM default export 사용 */
export default function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Access-Control-Allow-Origin", "*");

  if (req.method && req.method !== "GET") {
    res.statusCode = 405;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify({ message: "Method Not Allowed" }));
    return;
  }

  const url = new URL(req.url || "/api/env", "https://example.invalid");
  const pathname = url.pathname || "";

  if (pathname === "/api/env.js") {
    res.statusCode = 308;
    res.setHeader(
      "Location",
      url.toString().replace("/api/env.js", "/api/env").replace("https://example.invalid", "")
    );
    res.end();
    return;
  }

  const candidates = {
    SUPABASE_PROJECT_ID: [
      "SUPABASE_PROJECT_ID",
      "NEXT_PUBLIC_SUPABASE_PROJECT_ID",
      "VITE_SUPABASE_PROJECT_ID",
    ],
    SUPABASE_ANON_KEY: ["SUPABASE_ANON_KEY", "NEXT_PUBLIC_SUPABASE_ANON_KEY", "VITE_SUPABASE_ANON_KEY"],
    SUPABASE_URL: ["SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL", "VITE_SUPABASE_URL"],
  };

  const normalize = (value) => {
    let s = (value ?? "").toString().trim();
    if (
      (s.startsWith('"') && s.endsWith('"')) ||
      (s.startsWith("'") && s.endsWith("'"))
    ) {
      s = s.slice(1, -1).trim();
    }
    return s;
  };

  const readFirst = (keys) => {
    for (const k of keys) {
      const v = process.env[k];
      if (typeof v === "string" && v.trim() !== "") return v.trim();
    }
    return "";
  };

  const projectId = normalize(readFirst(candidates.SUPABASE_PROJECT_ID));
  const anonKey = normalize(readFirst(candidates.SUPABASE_ANON_KEY));
  const supabaseUrl = normalize(readFirst(candidates.SUPABASE_URL));

  const payload = {
    SUPABASE_PROJECT_ID: projectId,
    SUPABASE_ANON_KEY: anonKey,
    SUPABASE_URL: supabaseUrl,
  };

  const format = url.searchParams.get("format") || "";

  if (format === "json") {
    res.statusCode = 200;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify(payload));
    return;
  }

  res.statusCode = 200;
  res.setHeader("Content-Type", "text/javascript; charset=utf-8");
  res.end(`window.ENV = ${JSON.stringify(payload)};`);
}
