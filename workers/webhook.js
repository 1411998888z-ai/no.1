// Cloudflare Worker: LINE webhookを受け、GitHub Actionsを起動する
// secrets: LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN, GITHUB_TOKEN, GITHUB_REPO

const LINE_REPLY = "https://api.line.me/v2/bot/message/reply";

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("OK", { status: 200 });
    }

    const bodyText = await request.text();
    const signature = request.headers.get("x-line-signature") || "";
    const valid = await verifySignature(env.LINE_CHANNEL_SECRET, bodyText, signature);
    if (!valid) {
      return new Response("invalid signature", { status: 401 });
    }

    const body = JSON.parse(bodyText);
    for (const event of body.events || []) {
      if (event.type !== "postback") continue;
      await handlePostback(env, event);
    }
    return new Response("OK", { status: 200 });
  },
};

async function handlePostback(env, event) {
  const params = parseQuery(event.postback.data);
  const action = params.get("action");
  const jobId = params.get("job");
  const candidateId = params.get("id");
  const replyToken = event.replyToken;

  if (action === "approve") {
    await dispatchGitHub(env, "publish", { job_id: jobId, candidate_id: candidateId });
    await replyText(env, replyToken,
      `✅ 案${candidateId}を採用しました。1〜2分以内にThreadsへ投稿します。`);
    return;
  }
  if (action === "regenerate") {
    await dispatchGitHub(env, "regenerate", { job_id: jobId });
    await replyText(env, replyToken, "🔄 投稿候補を再生成中です。少しお待ちください。");
    return;
  }
  if (action === "reject") {
    await dispatchGitHub(env, "reject", { job_id: jobId });
    await replyText(env, replyToken, "🚫 今回はスキップしました。");
    return;
  }
}

async function dispatchGitHub(env, eventType, payload) {
  const url = `https://api.github.com/repos/${env.GITHUB_REPO}/dispatches`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
      "Accept": "application/vnd.github+json",
      "Content-Type": "application/json",
      "User-Agent": "threads-bot-webhook",
    },
    body: JSON.stringify({ event_type: eventType, client_payload: payload }),
  });
  if (!res.ok) {
    const text = await res.text();
    console.error("dispatch failed", res.status, text);
  }
}

async function replyText(env, replyToken, text) {
  await fetch(LINE_REPLY, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${env.LINE_CHANNEL_ACCESS_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      replyToken,
      messages: [{ type: "text", text }],
    }),
  });
}

function parseQuery(s) {
  const params = new Map();
  for (const part of (s || "").split("&")) {
    const [k, v] = part.split("=");
    if (k) params.set(decodeURIComponent(k), decodeURIComponent(v || ""));
  }
  return params;
}

async function verifySignature(secret, body, signature) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const mac = await crypto.subtle.sign("HMAC", key, enc.encode(body));
  const expected = btoa(String.fromCharCode(...new Uint8Array(mac)));
  return timingSafeEqual(expected, signature);
}

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}
